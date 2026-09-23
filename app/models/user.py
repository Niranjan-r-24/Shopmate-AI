from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
import enum
from app.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"
    SUPPORT = "support"

class AuthProvider(str, enum.Enum):
    LOCAL = "local"
    GOOGLE = "google"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    role = Column(String, default=UserRole.CUSTOMER.value, nullable=False)
    auth_provider = Column(String, default=AuthProvider.LOCAL.value, nullable=False)
    profile_image = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Backward compatibility with existing schema and codebase
    username = Column(String, unique=True, index=True, nullable=True)

    def __init__(self, **kwargs):
        # Ensure both password_hash and hashed_password are synchronized
        ph = kwargs.get("password_hash") or kwargs.get("hashed_password")
        if ph:
            kwargs["password_hash"] = ph
            kwargs["hashed_password"] = ph
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "auth_provider": self.auth_provider,
            "profile_image": self.profile_image,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "username": self.username or (self.email.split("@")[0] if self.email else "")
        }
