import pytest
from conftest import app, db, User, app_module

Property = app_module.Property
EvaluationRequest = app_module.EvaluationRequest
Agent = app_module.Agent


@pytest.fixture
def admin_user(client):
    client.post(
        "/signup",
        json={"name": "Admin", "email": "admin@example.com", "password": "pass", "user_type": "Landlord"},
    )
    with app.app_context():
        user = User.query.filter_by(email="admin@example.com").first()
        user.is_admin = True
        db.session.commit()
        return user.id


@pytest.fixture
def normal_user(client):
    client.post(
        "/signup",
        json={"name": "User", "email": "user@example.com", "password": "pass", "user_type": "Landlord"},
    )
    with app.app_context():
        return User.query.filter_by(email="user@example.com").first().id


@pytest.fixture
def sample_property(normal_user):
    with app.app_context():
        p = Property(
            user_id=normal_user,
            title="Sample Home",
            slug="sample-home",
            location="City",
            purpose="buy",
            property_type="apartment",
            price=100,
            beds=2,
            baths=1,
            size=80,
        )
        db.session.add(p)
        db.session.commit()
        return p.id


@pytest.fixture
def sample_request(normal_user):
    with app.app_context():
        r = EvaluationRequest(
            user_id=normal_user,
            location="City",
            property_type="apartment",
            area=100,
            bedrooms=2,
            bathrooms=1,
            condition="new",
        )
        db.session.add(r)
        db.session.commit()
        return r.id


@pytest.fixture
def sample_agent():
    with app.app_context():
        a = Agent(name="Agent Smith", slug="agent-smith", email="agent@example.com")
        db.session.add(a)
        db.session.commit()
        return a.id


def login(client, email, password="pass"):
    resp = client.post("/signin", json={"email": email, "password": password})
    assert resp.status_code == 200
    return {"X-CSRF-TOKEN": resp.get_json()["csrf_token"]}


# --- Basic access tests ---

def test_admin_route_requires_admin(client, admin_user, normal_user):
    login(client, "admin@example.com")
    assert client.get("/admin").status_code == 200
    login(client, "user@example.com")
    assert client.get("/admin").status_code == 403


def test_dashboard_role_mismatch(client, normal_user):
    login(client, "user@example.com")
    assert client.get("/dashboard/landlord").status_code == 200
    assert client.get("/dashboard/buyer-renter").status_code == 403


# --- User endpoints ---

def test_admin_user_crud(client, admin_user):
    headers = login(client, "admin@example.com")
    with app.app_context():
        start = User.query.count()
    resp = client.post(
        "/admin/users",
        json={"name": "A", "email": "a@example.com", "password": "p", "user_type": "Buyer/Renter"},
        headers=headers,
    )
    assert resp.status_code == 201
    new_id = resp.get_json()["id"]
    with app.app_context():
        assert User.query.count() == start + 1

    assert client.get("/admin/users", headers=headers).status_code == 200
    assert client.get(f"/admin/users/{new_id}", headers=headers).status_code == 200

    resp = client.put(f"/admin/users/{new_id}", json={"name": "B"}, headers=headers)
    assert resp.status_code == 200
    with app.app_context():
        assert User.query.get(new_id).name == "B"

    resp = client.delete(f"/admin/users/{new_id}", headers=headers)
    assert resp.status_code == 200
    with app.app_context():
        assert User.query.get(new_id) is None


def test_user_endpoints_forbidden(client, normal_user):
    headers = login(client, "user@example.com")
    assert client.get("/admin/users", headers=headers).status_code == 403
    assert client.post(
        "/admin/users",
        json={"name": "X", "email": "x@example.com", "password": "p", "user_type": "Buyer/Renter"},
        headers=headers,
    ).status_code == 403


# --- Property endpoints ---

def test_admin_property_crud(client, admin_user, normal_user, sample_property):
    headers = login(client, "admin@example.com")
    with app.app_context():
        start = Property.query.count()
    resp = client.post(
        "/admin/properties",
        json={
            "user_id": normal_user,
            "title": "New Home",
            "location": "Town",
            "purpose": "buy",
            "property_type": "villa",
            "price": 200,
            "beds": 3,
            "baths": 2,
            "size": 120,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    new_id = resp.get_json()["id"]
    with app.app_context():
        assert Property.query.count() == start + 1

    assert client.get("/admin/properties", headers=headers).status_code == 200
    assert client.get(f"/admin/properties/{sample_property}", headers=headers).status_code == 200

    resp = client.put(f"/admin/properties/{sample_property}", json={"title": "Updated"}, headers=headers)
    assert resp.status_code == 200
    with app.app_context():
        assert Property.query.get(sample_property).title == "Updated"

    resp = client.delete(f"/admin/properties/{sample_property}", headers=headers)
    assert resp.status_code == 200
    with app.app_context():
        assert Property.query.get(sample_property) is None


def test_property_endpoints_forbidden(client, normal_user, sample_property):
    headers = login(client, "user@example.com")
    assert client.get("/admin/properties", headers=headers).status_code == 403
    assert client.post(
        "/admin/properties",
        json={
            "user_id": normal_user,
            "title": "X",
            "location": "Town",
            "purpose": "buy",
            "property_type": "villa",
            "price": 100,
            "beds": 1,
            "baths": 1,
            "size": 50,
        },
        headers=headers,
    ).status_code == 403


# --- Evaluation request endpoints ---

def test_admin_request_crud(client, admin_user, normal_user, sample_request):
    headers = login(client, "admin@example.com")
    with app.app_context():
        start = EvaluationRequest.query.count()
    resp = client.post(
        "/admin/evaluation-requests",
        json={
            "user_id": normal_user,
            "location": "Town",
            "property_type": "villa",
            "area": 150,
            "bedrooms": 4,
            "bathrooms": 3,
            "condition": "old",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    new_id = resp.get_json()["id"]
    with app.app_context():
        assert EvaluationRequest.query.count() == start + 1

    assert client.get("/admin/evaluation-requests", headers=headers).status_code == 200
    assert client.get(f"/admin/evaluation-requests/{sample_request}", headers=headers).status_code == 200

    resp = client.put(
        f"/admin/evaluation-requests/{sample_request}",
        json={"location": "New City"},
        headers=headers,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert EvaluationRequest.query.get(sample_request).location == "New City"

    resp = client.delete(f"/admin/evaluation-requests/{sample_request}", headers=headers)
    assert resp.status_code == 200
    with app.app_context():
        assert EvaluationRequest.query.get(sample_request) is None


def test_request_endpoints_forbidden(client, normal_user, sample_request):
    headers = login(client, "user@example.com")
    assert client.get("/admin/evaluation-requests", headers=headers).status_code == 403
    assert client.post(
        "/admin/evaluation-requests",
        json={
            "user_id": normal_user,
            "location": "Town",
            "property_type": "villa",
            "area": 150,
            "bedrooms": 4,
            "bathrooms": 3,
            "condition": "old",
        },
        headers=headers,
    ).status_code == 403


# --- Agent endpoints ---

def test_admin_agent_crud(client, admin_user, sample_agent):
    headers = login(client, "admin@example.com")
    with app.app_context():
        start = Agent.query.count()
    resp = client.post("/admin/agents", json={"name": "New Agent"}, headers=headers)
    assert resp.status_code == 201
    new_id = resp.get_json()["id"]
    with app.app_context():
        assert Agent.query.count() == start + 1

    assert client.get("/admin/agents", headers=headers).status_code == 200
    assert client.get(f"/admin/agents/{sample_agent}", headers=headers).status_code == 200

    resp = client.put(
        f"/admin/agents/{sample_agent}", json={"name": "Updated"}, headers=headers
    )
    assert resp.status_code == 200
    with app.app_context():
        assert Agent.query.get(sample_agent).name == "Updated"

    resp = client.delete(f"/admin/agents/{sample_agent}", headers=headers)
    assert resp.status_code == 200
    with app.app_context():
        assert Agent.query.get(sample_agent) is None


def test_agent_endpoints_forbidden(client, normal_user, sample_agent):
    headers = login(client, "user@example.com")
    assert client.get("/admin/agents", headers=headers).status_code == 403
    assert client.post("/admin/agents", json={"name": "X"}, headers=headers).status_code == 403

