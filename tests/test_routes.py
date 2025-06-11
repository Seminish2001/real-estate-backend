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


def test_create_and_get_property(client):
    csrf = signup_and_login(client)
    data = {
        "title": "Test Home",
        "location": "Test City",
        "purpose": "buy",
        "type": "apartment",
        "price": "100000",
        "beds": "2",
        "baths": "1",
        "size": "80",
    }
    resp = client.post("/api/properties", data=data, headers={"X-CSRF-TOKEN": csrf})
    assert resp.status_code == 201
    prop_id = resp.get_json()["id"]
    assert prop_id is not None

    resp = client.get("/api/properties")
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["count"] == 1


def test_property_creation_requires_auth(client):
    data = {
        "title": "Test Home",
        "location": "Test City",
        "purpose": "buy",
        "type": "apartment",
        "price": "100000",
        "beds": "2",
        "baths": "1",
        "size": "80",
    }
    resp = client.post("/api/properties", data=data)
    assert resp.status_code == 401
    # flask-jwt-extended returns a default 'msg' key for missing auth header
    assert resp.get_json()["msg"] == "Missing Authorization Header"


def test_property_missing_fields(client):
    csrf = signup_and_login(client)
    data = {"location": "City"}
    resp = client.post("/api/properties", data=data, headers={"X-CSRF-TOKEN": csrf})
    assert resp.status_code == 400


def test_create_agent_and_retrieve(client):
    csrf = signup_and_login(client)
    agent_data = {"name": "Agent Smith", "email": "a@example.com"}
    resp = client.post("/api/agents", json=agent_data, headers={"X-CSRF-TOKEN": csrf})
    assert resp.status_code == 201
    agent_id = resp.get_json()["id"]
    assert agent_id is not None

    resp = client.get("/api/agents")
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["count"] == 1


def test_create_agent_missing_name(client):
    csrf = signup_and_login(client)
    resp = client.post(
        "/api/agents", json={"email": "a@example.com"}, headers={"X-CSRF-TOKEN": csrf}
    )
    assert resp.status_code == 400


def test_evaluation_success(client):
    data = {
        "location": "City",
        "type": "apartment",
        "area": 100,
        "bedrooms": 2,
        "bathrooms": 1,
        "condition": "new",
    }
    resp = client.post("/evaluation", json=data)
    assert resp.status_code == 200
    assert "message" in resp.get_json()


def test_evaluation_missing_fields(client):
    resp = client.post("/evaluation", json={"type": "apartment"})
    assert resp.status_code == 400


def test_alerts_create_and_get(client):
    signup_and_login(client)
    alert_data = {
        "email": "a@example.com",
        "purpose": "buy",
        "location": "City",
        "minPrice": 100,
        "maxPrice": 200,
        "type": "apartment",
        "frequency": "daily",
    }
    resp = client.post("/alerts", json=alert_data)
    assert resp.status_code == 200
    resp = client.get("/api/alerts")
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["count"] == 1


def test_alerts_missing_fields(client):
    resp = client.post("/alerts", json={"email": "a@example.com"})
    assert resp.status_code == 400
