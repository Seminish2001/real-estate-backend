import logging
from typing import Optional

from flask import Blueprint, jsonify, make_response, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_csrf_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)
from extensions import limiter
from models import User, db, safe_get

auth_bp = Blueprint("auth", __name__)


def _role_from_payload(payload: dict) -> str:
    """Translate legacy payload fields into the new role attribute."""

    if not payload:
        return "USER"

    role = payload.get("role")
    if role:
        return role.upper()

    user_type = payload.get("user_type") or payload.get("userType")
    if user_type:
        normalized = user_type.strip().upper()
        mapping = {
            "BUYER/RENTER": "USER",
            "BUYER": "USER",
            "RENTER": "USER",
            "LANDLORD": "LANDLORD",
            "AGENCY": "AGENT",
            "AGENT": "AGENT",
            "BROKER": "BROKER",
            "ADMIN": "ADMIN",
        }
        return mapping.get(normalized, "USER")

    return "USER"


def _token_response(user: User, message: str, status_code: int = 200):
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    csrf_token = get_csrf_token(access_token)

    response = make_response(
        jsonify(
            {
                "message": message,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                },
                "csrf_token": csrf_token,
            }
        ),
        status_code,
    )
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response


@auth_bp.route("/signin", methods=["POST"])
@limiter.limit("1000 per minute")
def signin():
    try:
        data = request.json or {}
        if not all(key in data for key in ["email", "password"]):
            return jsonify({"message": "Missing email or password"}), 400

        user = User.query.filter_by(email=data["email"].strip().lower()).first()
        if user and user.check_password(data["password"]):
            logging.info("User %s signed in", user.email)
            return _token_response(user, "Signed in successfully")

        return jsonify({"message": "Invalid credentials!"}), 401
    except Exception as exc:  # pragma: no cover - safety net
        logging.error("Signin error: %s", exc)
        return jsonify({"message": f"An error occurred: {exc}"}), 500


@auth_bp.route("/signup", methods=["POST"])
@limiter.limit("1000 per minute")
def signup():
    try:
        data = request.json or {}
        if not all(key in data for key in ["name", "email", "password"]):
            return jsonify({"message": "Missing required fields"}), 400

        role = _role_from_payload(data)

        email = data["email"].strip().lower()
        if User.query.filter_by(email=email).first():
            return jsonify({"message": "Email already registered!"}), 409

        new_user = User(name=data["name"].strip(), email=email, role=role, password="")
        new_user.is_admin = role == "ADMIN"
        new_user.set_password(data["password"])
        db.session.add(new_user)
        db.session.commit()

        logging.info("User %s signed up", new_user.email)
        return _token_response(new_user, "Signed up successfully", 201)
    except Exception as exc:  # pragma: no cover - safety net
        db.session.rollback()
        logging.error("Signup error: %s", exc)
        return jsonify({"message": f"An error occurred: {exc}"}), 500


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    response = jsonify({"message": "Logged out"})
    unset_jwt_cookies(response)
    return response


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = safe_get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    access_token = create_access_token(identity=str(user.id))
    csrf_token = get_csrf_token(access_token)

    response = make_response(
        jsonify({"message": "Token refreshed", "csrf_token": csrf_token}),
        200,
    )
    set_access_cookies(response, access_token)
    return response


@auth_bp.route("/whoami", methods=["GET"])
@jwt_required()
def whoami():
    user_id = get_jwt_identity()
    user = safe_get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }
    )


@auth_bp.route("/auth/status", methods=["GET"])
@jwt_required(optional=True)
def auth_status():
    identity: Optional[str] = get_jwt_identity()
    if not identity:
        return jsonify({"authenticated": False}), 200

    user = safe_get(User, identity)
    if not user:
        return jsonify({"authenticated": False}), 200

    return jsonify({"authenticated": True, "user": {"id": user.id, "role": user.role}})


# OAuth endpoints would go here. They are omitted for brevity but the helpers above
# ensure the rest of the system can operate end-to-end.
