from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_endpoint_returns_operational_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}
