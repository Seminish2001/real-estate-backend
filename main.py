import os
from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies, create_refresh_token
)
from marshmallow import Schema, fields, validate, ValidationError
from datetime import timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///properties.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default_secret_key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)  # "Private Owner" or "Real Estate Agency"

# Initialize the database
with app.app_context():
    db.create_all()

# Input validation schemas
class UserSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=6))
    user_type = fields.String(required=True, validate=validate.OneOf(["Private Owner", "Real Estate Agency"]))

user_schema = UserSchema()

# Routes to serve templates
@app.route('/')
def serve_homepage():
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def serve_login():
    return render_template('login.html')

@app.route('/signup')
def serve_signup():
    return render_template('signup.html')

@app.route('/dashboard')
@jwt_required()
def serve_dashboard():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user:
            if request.headers.get('Accept') == 'application/json':
                return jsonify({
                    "message": "Dashboard loaded successfully",
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "user_type": user.user_type
                    }
                }), 200
            else:
                return render_template('dashboard.html', user=user)
        else:
            return jsonify({"message": "User not found"}), 404

    except Exception as e:
        logger.error(f"Error in /dashboard: {e}")
        return jsonify({"message": "An error occurred while loading the dashboard"}), 500

@app.route('/for-owners')
def serve_for_owners():
    return render_template('for-owners.html')

@app.route('/logout', methods=['POST'])
def logout():
    response = jsonify({"message": "Successfully logged out!"})
    unset_jwt_cookies(response)
    return response

# Register a new user
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        errors = user_schema.validate(data)
        if errors:
            return jsonify({"message": "Validation errors", "errors": errors}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({"message": "Email already registered!"}), 409

        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(name=data['name'], email=data['email'], password=hashed_password, user_type=data['user_type'])
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "User registered successfully!"}), 201

    except Exception as e:
        logger.error(f"Error in /register: {e}")
        return jsonify({"message": "An error occurred during registration"}), 500

# User login
@app.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.json
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"message": "Invalid input!"}), 400

        user = User.query.filter_by(email=data['email']).first()
        if user and bcrypt.check_password_hash(user.password, data['password']):
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            return jsonify({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "message": "Login successful!"
            }), 200
        return jsonify({"message": "Invalid credentials!"}), 401

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"message": "An error occurred during login"}), 500

# Refresh token
@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    try:
        current_user_id = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user_id)
        return jsonify({"access_token": new_access_token}), 200
    except Exception as e:
        logger.error(f"Error in /refresh: {e}")
        return jsonify({"message": "An error occurred while refreshing the token"}), 500

# Redirect unauthorized users to login page
@jwt.unauthorized_loader
def unauthorized_callback(callback):
    return jsonify({"message": "Missing or invalid token. Please log in again."}), 401

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
