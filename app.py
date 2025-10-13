import os
import logging
from datetime import timedelta
from decouple import config

from flask import Flask, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, unset_jwt_cookies
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from werkzeug.exceptions import HTTPException

# --- App & Config Initialization ---
app = Flask(__name__, template_folder="templates")
# This line prevents certain warnings during testing/deployment
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

# Secure Cookie Settings
jwt_cookie_secure = config("JWT_COOKIE_SECURE", default="False") # Set to 'True' in production
app.config["JWT_COOKIE_SECURE"] = str(jwt_cookie_secure).lower() in ["true", "1", "yes"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = True
app.config["GOOGLE_MAPS_API_KEY"] = config("GOOGLE_MAPS_API_KEY", default="")

if app.config["JWT_SECRET_KEY"] == "default_secret_key":
    app.logger.warning("Using default JWT_SECRET_KEY. Set this in production!")

# --- Core Extensions (Created ONCE and initialized) ---
db = SQLAlchemy(app) # Database initialized once here
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)
limiter = Limiter(
    get_remote_address, app=app, default_limits=["200 per day", "50 per hour"]
)
limiter.enabled = True # Enable limiter by default
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


# --- MODEL IMPORT (Crucial Fix) ---
# Import models *after* 'db' is initialized to avoid circular imports.
# Note: Since 'db' is initialized above, we DO NOT call db.init_app(app) again!
from models import * # This import ensures all models are known to SQLAlchemy before db.create_all() is run in main.py.


# --- BLUEPRINT REGISTRATION (Routes) ---
from auth_routes import auth_bp
from property_routes import property_bp
from agent_routes import agent_bp
from chat_routes import chat_bp
from template_routes import template_bp # The new frontend routes

# Register all API routes
app.register_blueprint(auth_bp)
app.register_blueprint(property_bp)
app.register_blueprint(agent_bp)
app.register_blueprint(chat_bp)

# Register all frontend template routes
app.register_blueprint(template_bp)

# OPTIONAL: Admin routes, if they are defined
# from admin_routes import admin_bp
# app.register_blueprint(admin_bp)

app.logger.info("All blueprints registered.")

# Final check to see if the app instance is ready to be used by gunicorn/main.py
if __name__ == "__main__":
    app.logger.warning("Running app.py directly is not recommended. Use main.py or gunicorn.")

