from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.models import db, User, bcrypt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import facebook
from decouple import config
import logging

auth_routes = Blueprint("auth_routes", __name__)
limiter = Limiter(get_remote_address, default_limits=["200 per day", "50 per hour"])

# Sign In (Email/Password)
@auth_routes.route("/signin", methods=["POST"])
@limiter.limit("10 per minute")
def signin():
    try:
        data = request.json
        if not all(key in data for key in ["email", "password"]):
            return jsonify({"message": "Missing email or password"}), 400

        user = User.query.filter_by(email=data["email"]).first()
        if user and user.check_password(data["password"]):
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            response = make_response(jsonify({
                "message": "Signed in successfully",
                "user": {"id": user.id, "name": user.name, "email": user.email, "user_type": user.user_type}
            }), 200)
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            logging.info(f"User {user.email} signed in")
            return response
        return jsonify({"message": "Invalid credentials!"}), 401
    except Exception as e:
        logging.error(f"Signin error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# Sign Up (Email/Password)
@auth_routes.route("/signup", methods=["POST"])
@limiter.limit("10 per minute")
def signup():
    try:
        data = request.json
        if not all(key in data for key in ["name", "email", "password", "user_type"]):
            return jsonify({"message": "Missing required fields"}), 400

        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"message": "Email already registered!"}), 409

        if data["user_type"] not in ["Landlord", "Agency", "Buyer/Renter"]:
            return jsonify({"message": "Invalid user type"}), 400

        new_user = User(
            name=data["name"],
            email=data["email"],
            user_type=data["user_type"]
        )
        new_user.set_password(data["password"])
        db.session.add(new_user)
        db.session.commit()

        access_token = create_access_token(identity=new_user.id)
        refresh_token = create_refresh_token(identity=new_user.id)
        response = make_response(jsonify({
            "message": "Signed up successfully",
            "user": {"id": new_user.id, "name": new_user.name, "email": new_user.email, "user_type": new_user.user_type}
        }), 201)
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        logging.info(f"User {new_user.email} signed up")
        return response
    except Exception as e:
        db.session.rollback()
        logging.error(f"Signup error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# Logout
@auth_routes.route("/logout", methods=["POST"])
def logout():
    response = make_response(jsonify({"message": "Logged out successfully"}), 200)
    unset_jwt_cookies(response)
    return response

# Google OAuth Sign In/Sign Up
@auth_routes.route("/auth/google", methods=["POST"])
def google_auth():
    try:
        token = request.json.get("token")
        if not token:
            return jsonify({"message": "Missing Google token"}), 400

        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), config("GOOGLE_CLIENT_ID", default="your-google-client-id"))
        email = idinfo['email']
        name = idinfo.get('name', 'Google User')

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, user_type="Buyer/Renter")
            db.session.add(user)
            db.session.commit()

        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        response = make_response(jsonify({
            "message": "Google auth successful",
            "user": {"id": user.id, "name": user.name, "email": user.email, "user_type": user.user_type}
        }), 200)
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response
    except ValueError:
        return jsonify({"message": "Invalid Google token"}), 401
    except Exception as e:
        logging.error(f"Google auth error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# Facebook OAuth Sign In/Sign Up
@auth_routes.route("/auth/facebook", methods=["POST"])
def facebook_auth():
    try:
        access_token = request.json.get("accessToken")
        if not access_token:
            return jsonify({"message": "Missing Facebook token"}), 400

        graph = facebook.GraphAPI(access_token)
        profile = graph.get_object("me", fields="id,name,email")
        email = profile.get('email')
        name = profile['name']

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, user_type="Buyer/Renter")
            db.session.add(user)
            db.session.commit()

        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        response = make_response(jsonify({
            "message": "Facebook auth successful",
            "user": {"id": user.id, "name": user.name, "email": user.email, "user_type": user.user_type}
        }), 200)
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response
    except facebook.GraphAPIError:
        return jsonify({"message": "Invalid Facebook token"}), 401
    except Exception as e:
        logging.error(f"Facebook auth error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# Update User Type
@auth_routes.route("/update-type", methods=["POST"])
@jwt_required()
def update_user_type():
    try:
        user_id = get_jwt_identity()
        data = request.json
        user_type = data.get("user_type")

        if user_type not in ["Landlord", "Agency", "Buyer/Renter"]:
            return jsonify({"message": "Invalid user type"}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        user.user_type = user_type
        db.session.commit()
        logging.info(f"User {user_id} updated type to {user_type}")
        return jsonify({"message": "User type updated successfully", "user_type": user.user_type}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Update user type error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
