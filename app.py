import os
import logging
from datetime import timedelta

from flask import Flask, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, unset_jwt_cookies, verify_jwt_in_request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO # NEW IMPORT for WebSockets
from werkzeug.exceptions import HTTPException
from decouple import config

# --- App & Config ---
app = Flask(__name__, template_folder="templates")
app._check_setup_finished = lambda *a, **k: None

# Load config from environment variables
app.config["SQLALCHEMY_DATABASE_URI"] = config(
    "DATABASE_URL", default="sqlite:///properties.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = config("JWT_SECRET_KEY", default="default_secret_key")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
jwt_cookie_secure = config("JWT_COOKIE_SECURE", default="True")
app.config["JWT_COOKIE_SECURE"] = str(jwt_cookie_secure).lower() in ["true", "1", "yes"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = True
app.config["GOOGLE_MAPS_API_KEY"] = config("GOOGLE_MAPS_API_KEY", default="")

if app.config["JWT_SECRET_KEY"] == "default_secret_key":
    print("WARNING: Using default JWT_SECRET_KEY. Set this in production!")

# --- Extensions ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)
limiter = Limiter(
    get_remote_address, app=app, default_limits=["200 per day", "50 per hour"]
)
limiter.enabled = False

# NEW: SocketIO Setup for Chat
socketio = SocketIO(
    app, 
    manage_session=False, 
    cors_allowed_origins="*", # Allow all origins for development
    async_mode='eventlet' # Recommended for production-ready SocketIO
)

logging.basicConfig(level=logging.INFO)
app.logger.info("Application started")


# --- Global Handlers & Helpers ---
@jwt.unauthorized_loader
def unauthorized_callback(reason):
    return jsonify(msg="Missing Authorization Header"), 401

@app.errorhandler(Exception)
def handle_exception(e):
    """Log unexpected exceptions and return a generic error message."""
    if isinstance(e, HTTPException):
        return e
    logging.exception("Unhandled exception: %s", e)
    return jsonify({"message": "Internal server error"}), 500


# --- Register Blueprints and Routes ---
# IMPORTANT: This step connects the separate route files to the app instance.

# 1. Update models.py to use the configured db/bcrypt instances
from models import db as models_db, bcrypt as models_bcrypt
models_db.init_app(app)
# Note: bcrypt is a class, the object is initialized above

# 2. Import and Register Blueprints (You will wrap your existing routes in these files)
from flask import Blueprint

# NEW: Authentication routes (signin, signup, oauth)
from auth_routes import auth_bp
app.register_blueprint(auth_bp)

# NEW: Property and search routes (listings, favorites, alerts)
from property_routes import property_bp
app.register_blueprint(property_bp)

# NEW: Agent management and profile routes
from agent_routes import agent_bp
app.register_blueprint(agent_bp)

# Existing Admin Blueprint (Ensure you update admin_routes.py to use the new models/db)
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "admin_routes", Path(__file__).with_name("admin_routes.py")
)
admin_routes = importlib.util.module_from_spec(spec)
# Note: You need to ensure the admin_routes file is updated to work with the new structure.
# We will skip the admin registration here as it's outside the core refactor.
# app.register_blueprint(admin_routes.admin_bp) 


# --- Keep the simple root template routes here for simplicity ---
@app.route("/")
def home():
    """Render the landing page."""
    return render_template(
        "index.html", google_maps_api_key=app.config["GOOGLE_MAPS_API_KEY"]
    )
# ... (Keep all your simple @app.route("/template-name") functions here)

# Final step is to update main.py to run the app using socketio.run
