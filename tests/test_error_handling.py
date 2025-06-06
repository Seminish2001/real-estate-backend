import os
import importlib.util
from pathlib import Path
import pytest

# Configure environment for tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret"

app_path = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("test_app", app_path)
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app
db = app_module.db

@pytest.fixture()
def client():
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()


def test_generic_error_message(client):
    @app.route("/trigger-error")
    def trigger_error():
        raise ValueError("Sensitive details")

    resp = client.get("/trigger-error")
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["message"] == "Internal server error"
    assert "Sensitive details" not in resp.get_data(as_text=True)
