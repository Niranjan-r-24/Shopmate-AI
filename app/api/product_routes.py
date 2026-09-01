from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from app.database import get_db
from app.models.product import Product

router = APIRouter(prefix="/products", tags=["Product Catalog & Discovery"])

@router.get("")
def list_products(
    search: Optional[str] = Query(None, description="Search term for product name, brand or SKU"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    in_stock_only: bool = Query(False),
    sort_by: str = Query("rating", description="rating, price_asc, price_desc, name"),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)

    if search:
        s = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(s)) | (Product.brand.ilike(s)) | (Product.sku.ilike(s)) | (Product.description.ilike(s))
        )
    if category and category != "all":
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if brand and brand != "all":
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if in_stock_only:
        query = query.filter(Product.stock_count > 0)

    # Sorting
    if sort_by == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort_by == "name":
        query = query.order_by(Product.name.asc())
    else: # rating
        query = query.order_by(Product.rating.desc())

    products = query.all()
    return {
        "count": len(products),
        "products": [p.to_dict() for p in products]
    }

@router.get("/meta/categories")
def get_categories_and_brands(db: Session = Depends(get_db)):
    categories = [r[0] for r in db.query(Product.category).distinct().all() if r[0]]
    brands = [r[0] for r in db.query(Product.brand).distinct().all() if r[0]]
    price_stats = db.query(func.min(Product.price), func.max(Product.price)).first()
    
    return {
        "categories": sorted(categories),
        "brands": sorted(brands),
        "min_price": price_stats[0] or 0.0,
        "max_price": price_stats[1] or 2000.0,
        "total_products": db.query(Product).count()
    }

@router.get("/{sku}")
def get_product_by_sku(sku: str, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.sku.ilike(sku)).first()
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product with SKU '{sku}' not found")
    return {"product": prod.to_dict()}
