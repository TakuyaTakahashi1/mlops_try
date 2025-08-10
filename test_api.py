from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_total_sales():
    r = client.get("/total_sales")
    assert r.status_code == 200
    assert r.json()["total"] == 4550

def test_total_sales_by_year():
    r = client.get("/total_sales/2025")
    assert r.status_code == 200
    assert r.json()["total"] == 4550

def test_total_sales_by_year_invalid():
    r = client.get("/total_sales/1800")   # 範囲外
    assert r.status_code == 422           # バリデーションで弾く

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

