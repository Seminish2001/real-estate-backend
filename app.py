import os
import sys
import logging
from datetime import timedelta
from pathlib import Path

# Ensure the repository root is available on the import path when the module is
# loaded dynamically (e.g., via importlib in tests).
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from decouple import config
from flask import Flask, jsonify, make_response
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from extensions import db, bcrypt, jwt, limiter, socketio

# --- App & Config Initialization ---
app = Flask(__name__, template_folder="templates")
app._check_setup_finished = lambda *a, **k: None

# Load config from environment variables
# CRITICAL CHANGE: Use EXTERNAL_DATABASE_URL if available, then fallback to DATABASE_URL
db_uri = config("EXTERNAL_DATABASE_URL", config("DATABASE_URL", default="sqlite:///properties.db"))

# Render/PostgreSQL-specific adjustment for SQLAlchemy 2.0+
if db_uri.startswith('postgres://'):
    db_uri = db_uri.replace('postgres://', 'postgresql+psycopg2://', 1)
elif db_uri.startswith('postgresql://') and not db_uri.startswith('postgresql+'):
    db_uri = db_uri.replace('postgresql://', 'postgresql+psycopg2://', 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Configure connection pooling settings for deployment stability
engine_options = {"pool_pre_ping": True}
if not db_uri.startswith("sqlite"):
    engine_options.update({"pool_size": 20, "max_overflow": 30})

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

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

# Diagnostic Log: CRITICAL - Log the HOST part of the URI to confirm environment variable value
try:
    if 'sqlite' in db_uri:
        log_uri = db_uri
    else:
        # Mask credentials but show host:port/dbname
        parts = db_uri.split('@')
        if len(parts) > 1:
             # This will show 'host:port/dbname'
             log_uri = f"postgresql+psycopg2://***@ {parts[1]}"
        else:
             # This will likely show the incorrect 'localhost' URI if no host/port was provided.
             log_uri = db_uri 
except Exception:
    log_uri = "URI extraction failed"

app.logger.info(f"--- DIAGNOSTIC: Database URI being used: {log_uri}")
app.logger.info("Application configuration loaded.")

# --- Core Extensions (Deferred initialization for DB) ---
db.init_app(app)
bcrypt.init_app(app)
jwt.init_app(app)
CORS(app)
limiter.init_app(app)
limiter.enabled = True
socketio.init_app(app)

logging.basicConfig(level=logging.INFO)
app.logger.info("Application extensions loaded.")


# --- GLOBAL HANDLERS & HELPERS ---
@jwt.unauthorized_loader
def unauthorized_callback(reason):
    """Handler for missing or invalid JWTs."""
    return jsonify(msg="Missing Authorization Header"), 401

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
from agent_routes import agent_bp, agency_bp
from chat_routes import chat_bp
from template_routes import template_bp
from admin_routes import admin_bp, configure_admin_blueprint

# Register all routes
app.register_blueprint(auth_bp)
app.register_blueprint(property_bp)
app.register_blueprint(agent_bp)
app.register_blueprint(agency_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(template_bp)

app.logger.info("All blueprints registered.")

# Re-export models for compatibility with modules/tests that import them from
# the application package.
from models import (  # noqa: E402
    User,
    AgentProfile,
    Property,
    PropertyImage,
    ChatSession,
    Message,
    Appointment,
    EvaluationRequest,
    AlertPreference,
    Favorite,
    Offer,
    AgentProfileSchema,
    agent_profile_schema,
    property_schema,
    slugify,
)

# Legacy alias maintained for backward compatibility.
Agent = AgentProfile

configure_admin_blueprint(db, User, Property, EvaluationRequest, AgentProfile, slugify)
app.register_blueprint(admin_bp)
app.logger.info("Admin blueprint registered.")

