from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import timedelta
import re

from app.database import get_db
from app.models.user import User, UserRole, AuthProvider
from app.auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    rate_limiter,
    verify_google_oauth_token
)
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    confirm_password: Optional[str] = None
    role: Optional[str] = None  # Ignored if passed; public signup is strictly customer

class UserLoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None  # Supported for backwards compatibility
    password: str
    remember_me: Optional[bool] = False

class GoogleAuthRequest(BaseModel):
    credential: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: dict

# Helper to validate email format
EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$")

# ==========================================
# AUTH ENDPOINTS
# ==========================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Public registration endpoint.
    SECURITY RULE: Only 'customer' accounts can be created publicly.
    Admin and Support accounts CANNOT be created publicly.
    """
    clean_email = req.email.strip().lower()
    if not EMAIL_REGEX.match(clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid email address"
        )
    
    if req.confirm_password and req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # Check if email is already registered
    from sqlalchemy import func
    existing_user = db.query(User).filter(func.lower(User.email) == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please sign in."
        )

    # Enforce Customer role strictly
    assigned_role = UserRole.CUSTOMER.value

    # Generate username fallback for compatibility
    base_username = clean_email.split("@")[0]
    username_candidate = base_username
    counter = 1
    while db.query(User).filter(func.lower(User.username) == username_candidate.lower()).first():
        username_candidate = f"{base_username}_{counter}"
        counter += 1

    pw_clean = req.password.strip()
    pw_hash = get_password_hash(pw_clean)

    user = User(
        full_name=req.full_name.strip(),
        email=clean_email,
        username=username_candidate,
        password_hash=pw_hash,
        hashed_password=pw_hash,
        role=assigned_role,
        auth_provider=AuthProvider.LOCAL.value,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate JWT access & refresh tokens
    token_data = {"sub": user.email, "role": user.role, "id": user.id}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Email or username login endpoint with rate limiting.
    Supports empty initial state on frontend and bcrypt verification.
    """
    from sqlalchemy import func
    identifier = (req.email or req.username or "").strip().lower()
    if not identifier or not req.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email/username and password are required"
        )

    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{identifier}"

    # Rate limiting check (allows 10 attempts in sliding window)
    is_limited, remaining_sec = rate_limiter.is_rate_limited(rate_key)
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please try again in {remaining_sec} seconds."
        )

    # Find user by email or username (case-insensitive)
    user = db.query(User).filter(
        ((func.lower(User.email) == identifier) | (func.lower(User.username) == identifier)),
        User.is_active == True
    ).first()

    pw_input = req.password
    pw_input_trimmed = req.password.strip()

    valid_password = False
    if user:
        # Check primary password_hash
        if user.password_hash:
            if verify_password(pw_input, user.password_hash) or verify_password(pw_input_trimmed, user.password_hash):
                valid_password = True

        # Check secondary hashed_password fallback
        if not valid_password and user.hashed_password:
            if verify_password(pw_input, user.hashed_password) or verify_password(pw_input_trimmed, user.hashed_password):
                valid_password = True

    if not user or not valid_password:
        rate_limiter.record_failure(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Success: clear rate limiter
    rate_limiter.record_success(rate_key)

    # Upgrade legacy hash to bcrypt if needed
    current_hash = user.password_hash or user.hashed_password or ""
    if not current_hash.startswith("$2b$"):
        try:
            new_hash = get_password_hash(pw_input_trimmed)
            user.password_hash = new_hash
            user.hashed_password = new_hash
            db.commit()
        except Exception:
            pass

    # Longer expiration if "Remember Me" is selected
    expires_delta = timedelta(days=30) if req.remember_me else None
    token_data = {"sub": user.email, "role": user.role, "id": user.id}
    access_token = create_access_token(data=token_data, expires_delta=expires_delta)
    refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }


@router.post("/google", response_model=TokenResponse)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Google OAuth 2.0 Sign-In endpoint.
    Flow:
      - Authenticate Google token
      - Retrieve Name, Email, Profile Picture
      - Check if user exists:
          * If user does NOT exist: Automatically create Customer account.
          * If user exists: Log them in.
    SECURITY RULES:
      - Google Sign In can ONLY create Customer accounts.
      - Google Sign In must NEVER create Admin accounts.
      - Google Sign In must NEVER create Support accounts.
    """
    google_data = verify_google_oauth_token(req.credential)
    if not google_data or not google_data.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authenticate Google account. Invalid or expired Google token."
        )

    email = google_data["email"].strip().lower()
    full_name = google_data.get("full_name") or email.split("@")[0].title()
    profile_image = google_data.get("profile_image")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Create Customer account automatically
        base_username = email.split("@")[0]
        username_candidate = base_username
        counter = 1
        while db.query(User).filter(User.username == username_candidate).first():
            username_candidate = f"{base_username}_{counter}"
            counter += 1

        user = User(
            full_name=full_name,
            email=email,
            username=username_candidate,
            role=UserRole.CUSTOMER.value,  # Google Sign In strictly creates Customer accounts
            auth_provider=AuthProvider.GOOGLE.value,
            profile_image=profile_image,
            hashed_password="oauth_google_account",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # User already exists - update profile picture if missing
        if profile_image and not user.profile_image:
            user.profile_image = profile_image
            db.commit()

    token_data = {"sub": user.email, "role": user.role, "id": user.id}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a fresh access token.
    """
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    sub = payload.get("sub")
    user = db.query(User).filter(
        ((User.email == sub) | (User.username == sub)),
        User.is_active == True
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this refresh token no longer exists"
        )

    token_data = {"sub": user.email, "role": user.role, "id": user.id}
    new_access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Secure password reset request.
    Does not leak whether the email is registered or not (preventing user enumeration).
    """
    clean_email = req.email.strip().lower()
    # In production, an email with a secure timed reset token would be dispatched here.
    return {
        "message": f"If an account is associated with {clean_email}, instructions to reset your password have been dispatched."
    }


@router.post("/token", response_model=TokenResponse)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Standard OAuth2 password flow endpoint for Swagger / API Docs."""
    identifier = form_data.username.strip().lower()
    user = db.query(User).filter(
        ((User.email == identifier) | (User.username == identifier)),
        User.is_active == True
    ).first()

    current_hash = user.password_hash if (user and user.password_hash) else (user.hashed_password if user else None)
    if not user or not current_hash or not verify_password(form_data.password, current_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    token_data = {"sub": user.email, "role": user.role, "id": user.id}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }


@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Retrieves authenticated user profile."""
    return {"user": current_user.to_dict()}
