from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies, get_csrf_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import facebook
import logging
from decouple import config
from app import app, limiter
from models import User, db, bcrypt

# Create a Blueprint instance
auth_bp = Blueprint('auth', __name__)

# --- Authentication Endpoints ---

@auth_bp.route("/signin", methods=["POST"])
@limiter.limit("10 per minute")
def signin():
    # ... (Paste your existing signin function code here)
    # Ensure you replace all 'user_type' references with 'role'
    # Example:
    try:
        data = request.json
        if not all(key in data for key in ["email", "password"]):
            return jsonify({"message": "Missing email or password"}), 400

        user = User.query.filter_by(email=data["email"]).first()
        if user and user.check_password(data["password"]):
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            csrf_token = get_csrf_token(access_token)
            response = make_response(
                jsonify(
                    {
                        "message": "Signed in successfully",
                        "user": {
                            "id": user.id,
                            "name": user.name,
                            "email": user.email,
                            "role": user.role, # CHANGED: user_type to role
                        },
                        "csrf_token": csrf_token,
                    }
                ),
                200,
            )
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            logging.info(f"User {user.email} signed in")
            return response
        return jsonify({"message": "Invalid credentials!"}), 401
    except Exception as e:
        logging.error(f"Signin error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@auth_bp.route("/signup", methods=["POST"])
@limiter.limit("10 per minute")
def signup():
    # ... (Paste your existing signup function code here)
    # Ensure you replace all 'user_type' references with 'role' and enforce new role limits
    try:
        data = request.json
        # REQUIRED CHANGE: Check for 'role' instead of 'user_type'
        if not all(key in data for key in ["name", "email", "password", "role"]):
            return jsonify({"message": "Missing required fields"}), 400

        valid_roles = ["USER", "AGENT", "BROKER"] 
        role = data["role"].upper()
        if role not in valid_roles:
            return jsonify({"message": "Invalid user role"}), 400

        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"message": "Email already registered!"}), 409

        new_user = User(
            name=data["name"],
            email=data["email"],
            role=role, # Use the new role field
            password="", 
        )
        new_user.set_password(data["password"])
        db.session.add(new_user)
        db.session.commit()

        # ... (rest of the token creation and response logic)
        access_token = create_access_token(identity=str(new_user.id))
        refresh_token = create_refresh_token(identity=str(new_user.id))
        csrf_token = get_csrf_token(access_token)
        response = make_response(
            jsonify(
                {
                    "message": "Signed up successfully",
                    "user": {
                        "id": new_user.id,
                        "name": new_user.name,
                        "email": new_user.email,
                        "role": new_user.role,
                    },
                    "csrf_token": csrf_token,
                }
            ),
            201,
        )
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        logging.info(f"User {new_user.email} signed up")
        return response
    except Exception as e:
        db.session.rollback()
        logging.error(f"Signup error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# ... (Paste the rest of your signin/signup-related routes, updating user_type to role)
# E.g., /logout, /auth/google, /auth/facebook, /update-type, /whoami, /api/auth/status
