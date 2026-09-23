from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.models.user import User, UserRole
from app.auth.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

def extract_token_from_request(request: Request, bearer_token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """Extracts JWT token from Authorization header or cookie."""
    if bearer_token:
        return bearer_token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    # Also support cookie if present
    cookie_token = request.cookies.get("shopmate_jwt_token")
    if cookie_token:
        return cookie_token
    return None

def get_current_user_optional(
    request: Request,
    token: Optional[str] = Depends(extract_token_from_request),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Retrieves authenticated user or None if anonymous."""
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    
    # Reject refresh tokens used as bearer access tokens
    if payload.get("token_type") == "refresh":
        return None

    sub = payload.get("sub")
    if not sub:
        return None
    
    # Query by email or username
    user = db.query(User).filter(
        ((User.email == sub) | (User.username == sub)),
        User.is_active == True
    ).first()
    return user

def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """Enforces authentication: raises 401 if unauthenticated."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_roles(allowed_roles: List[str]):
    """Role-based access control (RBAC) dependency factory."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = (current_user.role or "").lower()
        normalized_allowed = [r.lower() for r in allowed_roles]

        # Admin has full access to everything
        if user_role == UserRole.ADMIN.value.lower():
            return current_user

        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Insufficient permissions for role '{current_user.role}'. Required: {allowed_roles}"
            )
        return current_user
    return role_checker
