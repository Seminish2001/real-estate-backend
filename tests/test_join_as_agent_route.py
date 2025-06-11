import pytest


def test_join_as_agent_page(client):
    resp = client.get("/join-as-agent")
    assert resp.status_code == 200
    assert b"Join as an Agent" in resp.data
