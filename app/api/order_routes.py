from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models.order import Order, ReturnRequest
from app.agents.tools import tool_get_order_status, tool_check_return_eligibility

router = APIRouter(prefix="/orders", tags=["Orders & Returns Tracking"])

class ReturnCheckRequest(BaseModel):
    order_number: str
    sku: Optional[str] = None
    reason: Optional[str] = "Item returned by customer"

@router.get("")
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    return {"count": len(orders), "orders": [o.to_dict() for o in orders]}

@router.get("/{order_number}")
def get_order(order_number: str):
    res = tool_get_order_status(order_number)
    if res.get("status") != "success":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

@router.post("/return-eligibility")
def check_return(req: ReturnCheckRequest):
    res = tool_check_return_eligibility(
        order_number=req.order_number,
        sku=req.sku,
        reason=req.reason
    )
    return res
