import pytest


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
