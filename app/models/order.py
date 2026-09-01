from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False) # e.g. ORD-9821
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    shipping_address = Column(String, nullable=False)
    status = Column(String, default="shipped", nullable=False) # processing, shipped, out_for_delivery, delivered, returned
    carrier = Column(String, default="FedEx") # FedEx, UPS, DHL, USPS
    tracking_number = Column(String, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)
    total_amount = Column(Float, nullable=False)
    items = Column(JSON, default=list) # List of dicts: {sku, name, quantity, price, image_url}
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "order_number": self.order_number,
            "user_id": self.user_id,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "shipping_address": self.shipping_address,
            "status": self.status,
            "carrier": self.carrier,
            "tracking_number": self.tracking_number,
            "estimated_delivery": self.estimated_delivery.strftime("%Y-%m-%d") if self.estimated_delivery else None,
            "total_amount": self.total_amount,
            "items": self.items or [],
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None
        }

class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String, unique=True, index=True, nullable=False) # RET-10293
    order_number = Column(String, nullable=False)
    product_sku = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="approved") # approved, rejected, pending, completed
    refund_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False) # SAVE20
    discount_type = Column(String, default="percentage") # percentage, fixed
    discount_value = Column(Float, nullable=False) # 20 (percent) or 15 (dollars)
    min_order_value = Column(Float, default=0.0)
    max_discount = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    expiry_date = Column(DateTime, nullable=True)
    description = Column(String, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "discount_type": self.discount_type,
            "discount_value": self.discount_value,
            "min_order_value": self.min_order_value,
            "max_discount": self.max_discount,
            "is_active": self.is_active,
            "description": self.description
        }
