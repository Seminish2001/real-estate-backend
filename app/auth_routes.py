from flask import Blueprint, jsonify, request, redirect, url_for
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
        response = jsonify({"message": "User registered and logged in successfully!"})
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        # Redirect to the appropriate dashboard based on user_type
        if new_user.user_type == "Real Estate Agency":
            response.headers['Location'] = url_for("routes.serve_dashboard_agency")
        elif new_user.user_type == "Private Owner":
            response.headers['Location'] = url_for("routes.serve_dashboard_private")
        elif new_user.user_type == "Buyer/Renter":
            response.headers['Location'] = url_for("routes.serve_dashboard_buyer_renter")
        else:
            return jsonify({"message": "Invalid user type"}), 400

        return response, 201
    except Exception as e:
        db.session.rollback()  # Rollback on error
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
            
            response = jsonify({"message": "Login successful!"})
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)

            # Redirect to the appropriate dashboard based on user_type
            if user.user_type == "Real Estate Agency":
                response.headers['Location'] = url_for("routes.serve_dashboard_agency")
            elif user.user_type == "Private Owner":
                response.headers['Location'] = url_for("routes.serve_dashboard_private")
            elif user.user_type == "Buyer/Renter":
                response.headers['Location'] = url_for("routes.serve_dashboard_buyer_renter")
            else:
                return jsonify({"message": "Invalid user type"}), 400

            return response, 200
        return jsonify({"message": "Invalid credentials!"}), 401
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@auth_routes.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"message": "Successfully logged out!"})
    unset_jwt_cookies(response)
    response.headers['Location'] = url_for("views.login")
    return response, 200
