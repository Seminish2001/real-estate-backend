import os
import importlib.util
from pathlib import Path
import pytest

# Set up environment variables for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

# Dynamically import the app module from the repository
app_path = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("test_app", app_path)
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)

# Expose commonly used objects
app = app_module.app
db = app_module.db
User = getattr(app_module, "User", None)


@pytest.fixture()
def client():
    """Provide a Flask test client with a fresh database."""
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()
