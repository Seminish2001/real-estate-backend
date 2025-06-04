import os
import pytest
import importlib.util
from pathlib import Path

# Configure environment for tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret"

# Import the app module from the repository directly to avoid conflicts with any
# installed packages named "app".
app_path = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("test_app", app_path)
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app
db = app_module.db
User = app_module.User

@pytest.fixture()
def client():
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()


def test_signup_and_signin(client):
    resp = client.post(
        "/signup",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "password123",
            "user_type": "Buyer/Renter",
        },
    )
    assert resp.status_code == 201
    assert resp.get_json()["message"] == "Signed up successfully"

    resp = client.post(
        "/signin",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Signed in successfully"

