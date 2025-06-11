import pytest


def test_mortgage_page(client):
    resp = client.get("/mortgage")
    assert resp.status_code == 200
    assert b"Mortgage Calculator" in resp.data
