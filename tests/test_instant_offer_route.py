import pytest


def test_instant_offer_page(client):
    resp = client.get("/instant-offer")
    assert resp.status_code == 200
    assert b"Get an Instant Offer" in resp.data
