import pytest
from conftest import app, db, User

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
