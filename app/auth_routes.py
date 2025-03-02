from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from app.models import db, User, bcrypt

auth_routes = Blueprint("auth_routes", __name__)

@auth_routes.route("/register", methods=["POST"])
def register():
    try:
        data = request.json
        if not all(key in data for key in ["name", "email", "password", "user_type"]):
            return jsonify({"message": "Missing required fields"}), 400

        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"message": "Email already registered!"}), 409

        new_user = User(
            name=data["name"],
            email=data["email"],
            user_type=data["user_type"]  # "Private Owner", "Real Estate Agency", "Buyer/Renter"
        )
        new_user.set_password(data["password"])
        db.session.add(new_user)
        db.session.commit()

        # Auto-login after signup
        access_token = create_access_token(identity=new_user.id)
        refresh_token = create_refresh_token(identity=new_user.id)
        response = make_response('', 201)  # Empty response with 201 status
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        # Set redirect based on user_type
        if new_user.user_type == "Real Estate Agency":
            response.headers['Location'] = '/dashboard/agency'
        elif new_user.user_type == "Private Owner":
            response.headers['Location'] = '/dashboard/private'
        elif new_user.user_type == "Buyer/Renter":
            response.headers['Location'] = '/dashboard/buyer-renter'
        else:
            return jsonify({"message": "Invalid user type"}), 400

        return response
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@auth_routes.route("/login", methods=["POST"])
def login():
    try:
        data = request.json
        if not all(key in data for key in ["email", "password"]):
            return jsonify({"message": "Missing email or password"}), 400

        user = User.query.filter_by(email=data["email"]).first()
        if user and user.check_password(data["password"]):
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            
            response = make_response('', 200)  # Empty response with 200 status
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)

            # Set redirect based on user_type
            if user.user_type == "Real Estate Agency":
                response.headers['Location'] = '/dashboard/agency'
            elif user.user_type == "Private Owner":
                response.headers['Location'] = '/dashboard/private'
            elif user.user_type == "Buyer/Renter":
                response.headers['Location'] = '/dashboard/buyer-renter'
            else:
                return jsonify({"message": "Invalid user type"}), 400

            return response
        return jsonify({"message": "Invalid credentials!"}), 401
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@auth_routes.route("/logout", methods=["POST"])
def logout():
    response = make_response('', 200)  # Empty response
    unset_jwt_cookies(response)
    response.headers['Location'] = '/login'
    return response
