import os
import importlib.util
from pathlib import Path
import pytest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret"

app_path = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("test_app_admin", app_path)
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

def create_admin(client):
    client.post(
        "/signup",
        json={
            "name": "Admin",
            "email": "admin@example.com",
            "password": "pass",
            "user_type": "Landlord",
        },
    )
    with app.app_context():
        user = User.query.filter_by(email="admin@example.com").first()
        user.is_admin = True
        db.session.commit()


def login(client, email="admin@example.com", password="pass"):
    return client.post("/signin", json={"email": email, "password": password})


def test_admin_route_requires_admin(client):
    create_admin(client)
    login(client)
    resp = client.get("/admin")
    assert resp.status_code == 200

    # normal user should be forbidden
    client.post(
        "/signup",
        json={
            "name": "User",
            "email": "user@example.com",
            "password": "pass",
            "user_type": "Landlord",
        },
    )
    client.post("/signin", json={"email": "user@example.com", "password": "pass"})
    resp = client.get("/admin")
    assert resp.status_code == 403


def test_dashboard_role_mismatch(client):
    client.post(
        "/signup",
        json={
            "name": "Landlord",
            "email": "land@example.com",
            "password": "pass",
            "user_type": "Landlord",
        },
    )
    client.post("/signin", json={"email": "land@example.com", "password": "pass"})
    resp = client.get("/dashboard/landlord")
    assert resp.status_code == 200
    resp = client.get("/dashboard/buyer-renter")
    assert resp.status_code == 403
