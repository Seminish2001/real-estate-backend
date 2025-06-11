import pytest


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
    assert "csrf_token" in resp.get_json()

    resp = client.post(
        "/signin",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Signed in successfully"
    assert "csrf_token" in resp.get_json()

