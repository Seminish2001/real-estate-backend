import pytest


def test_private_agent_page(client):
    resp = client.get("/list/private-agent")
    assert resp.status_code == 200
    assert b"Private Agent Listing" in resp.data
