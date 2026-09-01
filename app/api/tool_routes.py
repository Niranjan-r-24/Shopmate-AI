from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.agents.tools import (
    tool_search_products,
    tool_check_inventory,
    tool_get_order_status,
    tool_check_return_eligibility,
    tool_validate_coupon,
    tool_search_policy,
    tool_search_amazon_products,
    tool_search_ebay_products,
    tool_compare_product_prices,
    tool_apply_price_match
)

router = APIRouter(prefix="/tools", tags=["Deterministic Retail Tools Registry"])

class ProductSearchToolReq(BaseModel):
    query: str
    category: Optional[str] = None
    max_price: Optional[float] = None
    in_stock_only: bool = False

class InventoryToolReq(BaseModel):
    sku_or_name: str

class OrderStatusToolReq(BaseModel):
    order_number: str

class ReturnEligibilityToolReq(BaseModel):
    order_number: str
    sku: Optional[str] = None
    reason: Optional[str] = "Return check via tool registry"

class CouponToolReq(BaseModel):
    code: str
    cart_total: float = 100.0

class PolicySearchToolReq(BaseModel):
    query: str
    top_k: int = 3

class AmazonSearchToolReq(BaseModel):
    query: str
    amazon_domain: str = "amazon.com"
    max_results: int = 5

class EbaySearchToolReq(BaseModel):
    query: str
    ebay_domain: str = "ebay.com"
    max_results: int = 5

class PriceCompareToolReq(BaseModel):
    query: str
    sku: Optional[str] = None

class ApplyPriceMatchToolReq(BaseModel):
    sku: str
    competitor_name: str = "Amazon"
    competitor_price: float
    competitor_url: Optional[str] = None

@router.post("/search-products")
def execute_search_products(req: ProductSearchToolReq):
    return tool_search_products(
        query=req.query,
        category=req.category,
        max_price=req.max_price,
        in_stock_only=req.in_stock_only
    )

@router.post("/check-inventory")
def execute_check_inventory(req: InventoryToolReq):
    return tool_check_inventory(sku_or_name=req.sku_or_name)

@router.post("/get-order-status")
def execute_get_order_status(req: OrderStatusToolReq):
    return tool_get_order_status(order_number=req.order_number)

@router.post("/check-return")
def execute_check_return(req: ReturnEligibilityToolReq):
    return tool_check_return_eligibility(
        order_number=req.order_number,
        sku=req.sku,
        reason=req.reason
    )

@router.post("/validate-coupon")
def execute_validate_coupon(req: CouponToolReq):
    return tool_validate_coupon(code=req.code, cart_total=req.cart_total)

@router.post("/search-policy")
def execute_search_policy(req: PolicySearchToolReq):
    return tool_search_policy(query=req.query, top_k=req.top_k)

@router.post("/search-amazon")
def execute_search_amazon(req: AmazonSearchToolReq):
    return tool_search_amazon_products(
        query=req.query,
        amazon_domain=req.amazon_domain,
        max_results=req.max_results
    )

@router.post("/search-ebay")
def execute_search_ebay(req: EbaySearchToolReq):
    return tool_search_ebay_products(
        query=req.query,
        ebay_domain=req.ebay_domain,
        max_results=req.max_results
    )

@router.post("/compare-prices")
def execute_compare_prices(req: PriceCompareToolReq):
    return tool_compare_product_prices(
        query=req.query,
        sku=req.sku
    )

@router.post("/apply-price-match")
def execute_apply_price_match(req: ApplyPriceMatchToolReq):
    return tool_apply_price_match(
        sku=req.sku,
        competitor_name=req.competitor_name,
        competitor_price=req.competitor_price,
        competitor_url=req.competitor_url
    )

