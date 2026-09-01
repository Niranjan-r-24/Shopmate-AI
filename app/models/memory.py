from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from app.database import Base

class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    memory_type = Column(String, default="preference") # preference, past_interest, constraint, note
    category = Column(String, nullable=True) # e.g. electronics, apparel, shoes, general
    key = Column(String, nullable=False) # e.g. preferred_brand, shoe_size, price_ceiling
    value = Column(String, nullable=False) # e.g. Sony, 10.5 US, 150 USD
    confidence = Column(Float, default=1.0)
    chroma_id = Column(String, nullable=True) # ID in Chroma user_memories collection
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "memory_type": self.memory_type,
            "category": self.category,
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None
        }
