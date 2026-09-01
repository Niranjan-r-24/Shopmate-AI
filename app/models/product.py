from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)
    brand = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    description = Column(Text, nullable=False)
    features = Column(JSON, default=list) # List of feature strings
    specifications = Column(JSON, default=dict) # Key-value specs
    stock_count = Column(Integer, default=0, nullable=False)
    rating = Column(Float, default=4.5)
    review_count = Column(Integer, default=0)
    image_url = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "category": self.category,
            "brand": self.brand,
            "price": self.price,
            "original_price": self.original_price or self.price,
            "description": self.description,
            "features": self.features or [],
            "specifications": self.specifications or {},
            "stock_count": self.stock_count,
            "in_stock": self.stock_count > 0,
            "rating": self.rating,
            "review_count": self.review_count,
            "image_url": self.image_url,
            "tags": self.tags or []
        }
