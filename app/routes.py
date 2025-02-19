from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from app.models import db, User, bcrypt

auth_routes = Blueprint("auth_routes", __name__)

@auth_routes.route("/register", methods=["POST"])
def register():
    try:
        data = request.json
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"message": "Email already registered!"}), 409

        new_user = User(
            name=data["name"],
            email=data["email"],
            user_type=data["user_type"]
        )
        new_user.set_password(data["password"])
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "User registered successfully!"}), 201
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@auth_routes.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()
    if user and user.check_password(data["password"]):
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        response = jsonify({"message": "Login successful!"})
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response, 200
    return jsonify({"message": "Invalid credentials!"}), 401

@auth_routes.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"message": "Successfully logged out!"})
    unset_jwt_cookies(response)
    return response
