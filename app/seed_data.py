import json
import logging
from pathlib import Path
from datetime import datetime
from app.config import settings
from app.database import init_db, SessionLocal
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.order import Order, Coupon
from app.auth.security import get_password_hash
from app.rag.ingest import ingestion_pipeline
from app.rag.hybrid_search import hybrid_searcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopmate.seeder")

def seed_all():
    """Initializes tables, seeds database records, and indexes RAG documents."""
    logger.info("Initializing Database Tables...")
    init_db()
    
    db = SessionLocal()
    try:
        # 1. Seed Users (Admin, Support, Customer: Niranjan R)
        if db.query(User).count() == 0:
            logger.info("Seeding default user accounts...")
            users = [
                User(
                    username="admin",
                    email="admin@shopmate.ai",
                    hashed_password=get_password_hash("admin123"),
                    full_name="ShopMate Lead Admin",
                    role=UserRole.ADMIN.value
                ),
                User(
                    username="support",
                    email="support@shopmate.ai",
                    hashed_password=get_password_hash("support123"),
                    full_name="Customer Care Specialist",
                    role=UserRole.SUPPORT.value
                ),
                User(
                    username="niranjan",
                    email="niranjan@shopmate.ai",
                    hashed_password=get_password_hash("niranjan123"),
                    full_name="Niranjan R",
                    role=UserRole.CUSTOMER.value
                )
            ]
            db.add_all(users)
            db.commit()
            logger.info("Users seeded successfully.")

        # 2. Seed Products from data/products.json
        products_file = settings.DATA_DIR / "products.json"
        products_data = []
        if products_file.exists():
            products_data = json.loads(products_file.read_text(encoding="utf-8"))
            
        if db.query(Product).count() == 0 and products_data:
            logger.info(f"Seeding {len(products_data)} products into database...")
            for p in products_data:
                prod = Product(
                    sku=p["sku"],
                    name=p["name"],
                    category=p["category"],
                    brand=p["brand"],
                    price=float(p["price"]),
                    original_price=float(p.get("original_price", p["price"])),
                    description=p["description"],
                    features=p.get("features", []),
                    specifications=p.get("specifications", {}),
                    stock_count=int(p.get("stock_count", 0)),
                    rating=float(p.get("rating", 4.5)),
                    review_count=int(p.get("review_count", 0)),
                    image_url=p.get("image_url", ""),
                    tags=p.get("tags", [])
                )
                db.add(prod)
            db.commit()
            logger.info("Products seeded in SQL database.")

        # 3. Seed Orders from data/sample_orders.json
        orders_file = settings.DATA_DIR / "sample_orders.json"
        if orders_file.exists() and db.query(Order).count() == 0:
            orders_data = json.loads(orders_file.read_text(encoding="utf-8"))
            logger.info(f"Seeding {len(orders_data)} sample orders...")
            for o in orders_data:
                est_del = None
                if o.get("estimated_delivery"):
                    try:
                        est_del = datetime.strptime(o["estimated_delivery"], "%Y-%m-%d")
                    except Exception:
                        pass
                ord_rec = Order(
                    order_number=o["order_number"],
                    customer_name=o.get("customer_name", "Niranjan R"),
                    customer_email=o.get("customer_email", "niranjan@shopmate.ai"),
                    shipping_address=o["shipping_address"],
                    status=o["status"],
                    carrier=o.get("carrier", "FedEx"),
                    tracking_number=o.get("tracking_number"),
                    estimated_delivery=est_del,
                    total_amount=float(o["total_amount"]),
                    items=o.get("items", [])
                )
                db.add(ord_rec)
            db.commit()
            logger.info("Orders seeded in SQL database.")

        # 4. Seed Coupons
        if db.query(Coupon).count() == 0:
            logger.info("Seeding promotional coupons...")
            coupons = [
                Coupon(
                    code="SAVE20",
                    discount_type="percentage",
                    discount_value=20.0,
                    min_order_value=50.0,
                    max_discount=100.0,
                    description="20% luxury discount on orders of $50 or more"
                ),
                Coupon(
                    code="FREESHIP",
                    discount_type="fixed",
                    discount_value=12.99,
                    min_order_value=35.0,
                    description="Complimentary white-glove expedited shipping"
                ),
                Coupon(
                    code="VIP10",
                    discount_type="percentage",
                    discount_value=10.0,
                    min_order_value=0.0,
                    description="10% VIP member savings on all luxury collections"
                ),
                Coupon(
                    code="TECH50",
                    discount_type="fixed",
                    discount_value=50.0,
                    min_order_value=300.0,
                    description="$50 off premium laptops and acoustic gear over $300"
                )
            ]
            db.add_all(coupons)
            db.commit()
            logger.info("Coupons seeded.")

        # 5. Ingest and index documents into ChromaDB & BM25
        logger.info("Ingesting products catalog into ChromaDB vector store...")
        if products_data:
            ingestion_pipeline.ingest_products_catalog(products_data)
            
        logger.info("Ingesting store policy documents into ChromaDB vector store...")
        ingestion_pipeline.ingest_default_policies()

        # 6. Rebuild BM25 In-Memory Indexes
        logger.info("Building BM25 sparse indices...")
        hybrid_searcher.refresh_bm25_index("products_catalog")
        hybrid_searcher.refresh_bm25_index("store_policies")

        logger.info("🎉 Database & RAG Vector Collections successfully initialized and indexed!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_all()
