import pytest


def test_contact_page(client):
    resp = client.get("/contact")
    assert resp.status_code == 200
    assert b"Contact Us" in resp.data
