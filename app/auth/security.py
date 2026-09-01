from datetime import datetime, timedelta
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import os
from app.config import settings

# Using pbkdf2_sha256 which is clean and robust across all Python versions (including 3.14)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if ":" in hashed_password and not hashed_password.startswith("$"):
            salt, h = hashed_password.split(":", 1)
            check = hashlib.sha256((salt + plain_password).encode()).hexdigest()
            return check == h
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        if ":" in hashed_password:
            salt, h = hashed_password.split(":", 1)
            check = hashlib.sha256((salt + plain_password).encode()).hexdigest()
            return check == h
        return False

def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception:
        salt = os.urandom(8).hex()
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}:{h}"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
