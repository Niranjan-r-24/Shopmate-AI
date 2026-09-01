import pytest
from app.auth.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.database import SessionLocal
from app.models.user import User

def test_password_hashing():
    pwd = "secretpassword123"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_jwt_token_generation_and_decoding():
    payload = {"sub": "testuser", "role": "customer"}
    token = create_access_token(payload)
    assert isinstance(token, str)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded.get("sub") == "testuser"
    assert decoded.get("role") == "customer"
