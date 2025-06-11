import pytest
from conftest import app


def test_generic_error_message(client):
    @app.route("/trigger-error")
    def trigger_error():
        raise ValueError("Sensitive details")

    resp = client.get("/trigger-error")
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["message"] == "Internal server error"
    assert "Sensitive details" not in resp.get_data(as_text=True)


def test_page_not_found_returns_404(client):
    resp = client.get("/nonexistent")
    assert resp.status_code == 404


def test_resource_not_found_returns_404(client):
    resp = client.get("/api/agents/999")
    assert resp.status_code == 404
