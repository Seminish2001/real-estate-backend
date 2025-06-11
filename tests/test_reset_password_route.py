import pytest


def test_reset_password_page(client):
    resp = client.get("/reset-password")
    assert resp.status_code == 200
    assert b"Reset Password" in resp.data
