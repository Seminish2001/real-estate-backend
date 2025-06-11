import pytest


def signup_and_login(client, email="user@example.com", password="password"):
    client.post(
        "/signup",
        json={
            "name": "User",
            "email": email,
            "password": password,
            "user_type": "Landlord",
        },
    )
    resp = client.post("/signin", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.get_json()["csrf_token"]


def test_nonexistent_property_returns_404(client):
    resp = client.get("/property/nonexistent")
    assert resp.status_code == 404


def test_nonexistent_agent_returns_404(client):
    resp = client.get("/api/agents/12345")
    assert resp.status_code == 404


def test_create_agent_invalid_email_returns_400(client):
    csrf = signup_and_login(client)
    resp = client.post(
        "/api/agents",
        json={"name": "Bad Agent", "email": "not-an-email"},
        headers={"X-CSRF-TOKEN": csrf},
    )
    assert resp.status_code == 400


def test_create_property_invalid_price_returns_400(client):
    csrf = signup_and_login(client)
    data = {
        "title": "Home",
        "location": "City",
        "purpose": "buy",
        "type": "apartment",
        "price": "not-a-number",
        "beds": "2",
        "baths": "1",
        "size": "80",
    }
    resp = client.post("/api/properties", data=data, headers={"X-CSRF-TOKEN": csrf})
    assert resp.status_code == 400


def test_add_favorite_nonexistent_property_returns_404(client):
    csrf = signup_and_login(client)
    resp = client.post(
        "/api/favorites",
        json={"property_id": 999},
        headers={"X-CSRF-TOKEN": csrf},
    )
    assert resp.status_code == 404
