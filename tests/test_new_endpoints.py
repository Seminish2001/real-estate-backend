import pytest

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
    resp = client.post(
        "/signin",
        json={"email": "agency@example.com", "password": "password123"},
    )
    return resp.get_json()["csrf_token"]


def test_new_endpoints_authenticated(client):
    csrf = authenticate(client)

    resp = client.get("/api/analytics")
    assert resp.status_code == 200

    resp = client.get("/api/requests")
    assert resp.status_code == 200

    resp = client.post("/api/agency/profile", json={"name": "New Name"}, headers={"X-CSRF-TOKEN": csrf})
    assert resp.status_code == 200

    resp = client.post("/api/agents/add", json={"name": "Agent X"}, headers={"X-CSRF-TOKEN": csrf})
    assert resp.status_code == 201

    resp = client.get("/api/market-snapshot")
    assert resp.status_code == 200
