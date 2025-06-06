import os
import importlib.util
from pathlib import Path
import pytest

# Configure environment for tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret"

app_path = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("test_app_error", app_path)
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


def signup(client, email="test@example.com", password="password123"):
    client.post(
        "/signup",
        json={
            "name": "Test",
            "email": email,
            "password": password,
            "user_type": "Buyer/Renter",
        },
    )


def test_invalid_login_returns_401(client):
    signup(client)
    resp = client.post(
        "/signin",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["message"] == "Invalid credentials!"
