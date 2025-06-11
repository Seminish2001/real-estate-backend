import pytest


def test_diy_sell_page(client):
    resp = client.get("/diy-sell")
    assert resp.status_code == 200
    assert b"DIY Sell Your Property" in resp.data
