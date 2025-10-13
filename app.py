import os
import logging
from datetime import timedelta
from decouple import config

from flask import Flask, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from werkzeug.exceptions import HTTPException

# --- App & Config Initialization ---
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

jwt_cookie_secure = config("JWT_COOKIE_SECURE", default="False")
app.config["JWT_COOKIE_SECURE"] = str(jwt_cookie_secure).lower() in ["true", "1", "yes"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = True
app.config["GOOGLE_MAPS_API_KEY"] = config("GOOGLE_MAPS_API_KEY", default="")

if app.config["JWT_SECRET_KEY"] == "default_secret_key":
    app.logger.warning("Using default JWT_SECRET_KEY. Set this in production!")

# --- Core Extensions (Deferred initialization for DB) ---
# CRITICAL FIX: Initialize SQLAlchemy without the app instance.
db = SQLAlchemy() 
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)
limiter = Limiter(
    get_remote_address, app=app, default_limits=["200 per day", "50 per hour"]
)
limiter.enabled = True 
socketio = SocketIO(
    app, 
    manage_session=False, 
    cors_allowed_origins="*", 
    async_mode='eventlet'
)

logging.basicConfig(level=logging.INFO)
app.logger.info("Application extensions loaded.")


# --- GLOBAL HANDLERS & HELPERS ---
@jwt.unauthorized_loader
def unauthorized_callback(reason):
    """Handler for missing or invalid JWTs."""
    return jsonify(msg="Missing or Invalid Authorization Token"), 401

@app.errorhandler(Exception)
def handle_exception(e):
    """Log unexpected exceptions and return a generic error message."""
    if isinstance(e, HTTPException):
        return e
    logging.exception("Unhandled exception: %s", e)
    return jsonify({"message": "Internal server error"}), 500


# --- CRITICAL: NO MODEL IMPORTS HERE ---
# Model imports are moved to main.py to prevent circular imports.


# --- BLUEPRINT REGISTRATION (Routes) ---
from auth_routes import auth_bp
from property_routes import property_bp
from agent_routes import agent_bp
from chat_routes import chat_bp
from template_routes import template_bp

# Register all routes
app.register_blueprint(auth_bp)
app.register_blueprint(property_bp)
app.register_blueprint(agent_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(template_bp)

app.logger.info("All blueprints registered.")
