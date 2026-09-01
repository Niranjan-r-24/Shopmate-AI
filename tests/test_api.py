import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.seed_data import seed_all

@pytest.fixture(scope="session", autouse=True)
def init_data():
    seed_all()

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_list_products_api():
    response = client.get("/api/products?category=Audio")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert any("Headphones" in p["name"] or "Earbuds" in p["name"] for p in data["products"])

def test_product_categories_meta_api():
    response = client.get("/api/products/meta/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert len(data["categories"]) > 0

def test_chat_message_api():
    response = client.post("/api/chat/message", json={
        "query": "Show me wireless headphones under $250",
        "session_id": "test_session_api"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "product_search"
    assert "response" in data
    assert len(data["product_cards"]) > 0
    assert len(data["execution_trace"]) > 0

def test_rag_stats_api():
    response = client.get("/api/rag/stats")
    assert response.status_code == 200
    data = response.json()
    assert "collections" in data
    assert data["collections"]["products_catalog"] > 0

def test_user_memory_api():
    response = client.post("/api/memory", json={
        "category": "apparel",
        "key": "shoe_size",
        "value": "10.5 US",
        "session_id": "test_session_mem"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    mem_id = data["preference"]["id"]

    # Delete memory
    del_res = client.delete(f"/api/memory/{mem_id}")
    assert del_res.status_code == 200

def test_analytics_overview_api():
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_queries" in data
    assert "avg_latency_ms" in data

def test_price_comparison_and_price_match_api():
    # 1. Compare prices
    compare_res = client.post("/api/tools/compare-prices", json={
        "query": "AuraSound Pro Wireless Headphones"
    })
    assert compare_res.status_code == 200
    comp_data = compare_res.json()
    assert comp_data["status"] == "success"
    assert "shopmate_product" in comp_data

    # 2. Apply price match coupon (ShopMate price is 199.99, competitor is 179.99)
    match_res = client.post("/api/tools/apply-price-match", json={
        "sku": "ELEC-1001",
        "competitor_name": "Amazon",
        "competitor_price": 179.99
    })
    assert match_res.status_code == 200
    match_data = match_res.json()
    assert match_data["status"] == "success"
    assert "coupon_code" in match_data
    assert match_data["coupon_code"].startswith("PM-AMA")
    assert match_data["savings_amount"] == 20.0


