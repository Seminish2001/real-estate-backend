import os
import importlib.util
from pathlib import Path
import pytest

# Configure environment for tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret"

app_path = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("test_app", app_path)
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app
db = app_module.db

@pytest.fixture()
def client():
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()

def authenticate(client):
    client.post(
        "/signup",
        json={
            "name": "Agency User",
            "email": "agency@example.com",
            "password": "password123",
            "user_type": "Agency",
        },
    )
    client.post(
        "/signin",
        json={"email": "agency@example.com", "password": "password123"},
    )


def test_new_endpoints_authenticated(client):
    authenticate(client)

    resp = client.get("/api/analytics")
    assert resp.status_code == 200

    resp = client.get("/api/requests")
    assert resp.status_code == 200

    resp = client.post("/api/agency/profile", json={"name": "New Name"})
    assert resp.status_code == 200

    resp = client.post("/api/agents/add", json={"name": "Agent X"})
    assert resp.status_code == 201

    resp = client.get("/api/market-snapshot")
    assert resp.status_code == 200
