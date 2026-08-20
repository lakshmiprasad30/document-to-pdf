from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Document to PDF API"}


def test_health_check_no_redis():
    # Since we aren't mocking redis here, it will fail to connect if it's not running
    # but the endpoint should still return 200 with error statuses.
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "ok"
    assert "redis" in data
    assert "worker" in data
