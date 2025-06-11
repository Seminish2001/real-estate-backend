import pytest


def test_about_page(client):
    resp = client.get("/about")
    assert resp.status_code == 200
    assert b"About Us" in resp.data
