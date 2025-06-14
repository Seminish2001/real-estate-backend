import os
import logging
from datetime import timedelta

from flask import Flask, jsonify, request, render_template, make_response, abort
from werkzeug.exceptions import HTTPException
import re
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    jwt_required,
    get_jwt_identity,
    verify_jwt_in_request,
    get_csrf_token,
)
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from cloudinary.uploader import upload
from marshmallow import Schema, fields, ValidationError, pre_load

# For OAuth
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import facebook
from decouple import config

# --- App & Config ---
app = Flask(__name__, template_folder="templates")
app.config["SQLALCHEMY_DATABASE_URI"] = config(
    "DATABASE_URL", default="sqlite:///properties.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = config("JWT_SECRET_KEY", default="default_secret_key")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
jwt_cookie_secure = config("JWT_COOKIE_SECURE", default="True")
app.config["JWT_COOKIE_SECURE"] = str(jwt_cookie_secure).lower() in ["true", "1", "yes"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = True
app.config["GOOGLE_MAPS_API_KEY"] = config("GOOGLE_MAPS_API_KEY", default="")

if app.config["JWT_SECRET_KEY"] == "default_secret_key":
    print("WARNING: Using default JWT_SECRET_KEY. Set this in production!")

# --- Extensions ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)
limiter = Limiter(
    get_remote_address, app=app, default_limits=["200 per day", "50 per hour"]
)

logging.basicConfig(level=logging.INFO)
app.logger.info("Application started")


def slugify(text: str) -> str:
    """Return a URL-friendly slug for the given text."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# --- Models ---
class User(db.Model):
    """Application user with authentication credentials."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(
        db.String(50), nullable=False
    )  # "Landlord", "Agency", "Buyer/Renter"
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        """Hash and store the given password."""

        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        """Return True if the password matches the stored hash."""

        return bcrypt.check_password_hash(self.password, password)


class Property(db.Model):
    """Real estate listing posted by a user."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, index=True)
    location = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # "buy" or "rent"
    property_type = db.Column(
        db.String(50), nullable=False
    )  # "apartment", "villa", etc.
    price = db.Column(db.Integer, nullable=False)
    beds = db.Column(db.Integer, nullable=False)
    baths = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class EvaluationRequest(db.Model):
    """Request submitted to estimate a property's value."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    location = db.Column(db.String(100), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    area = db.Column(db.Integer, nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    estimated_value = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


# New Agent model to store real estate agents
class Agent(db.Model):
    """Real estate agent profile."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, index=True)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    agency = db.Column(db.String(100))
    specialty = db.Column(db.String(100))
    languages = db.Column(db.String(200))
    location = db.Column(db.String(100))
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class AlertPreference(db.Model):
    """Saved search alert settings for a user."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    min_price = db.Column(db.Integer, nullable=False)
    max_price = db.Column(db.Integer, nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class Favorite(db.Model):
    """Mapping of users to properties they like."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class Offer(db.Model):
    """Bid made by a user on a property."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


# --- Schemas ---


class PropertySchema(Schema):
    title = fields.Str(required=True)
    location = fields.Str(required=True)
    purpose = fields.Str(required=True)
    property_type = fields.Str(required=True, data_key="type")
    price = fields.Integer(required=True)
    beds = fields.Integer(required=True)
    baths = fields.Integer(required=True)
    size = fields.Integer(required=True)
    lat = fields.Float(load_default=0)
    lng = fields.Float(load_default=0)

    @pre_load
    def normalize_fields(self, data, **kwargs):
        if "bathrooms" in data and "baths" not in data:
            data["baths"] = data["bathrooms"]
        return data


property_schema = PropertySchema()


class AgentSchema(Schema):
    name = fields.Str(required=True)
    email = fields.Email(load_default=None)
    phone = fields.Str(load_default=None)
    agency = fields.Str(load_default=None)
    specialty = fields.Str(load_default=None)
    languages = fields.Str(load_default=None)
    location = fields.Str(load_default=None)
    bio = fields.Str(load_default=None)
    photo_url = fields.Str(load_default=None)


agent_schema = AgentSchema()


# --- Authentication Endpoints ---
@app.route("/signin", methods=["POST"])
@limiter.limit("10 per minute")
def signin():
    """Authenticate a user and return JWT cookies."""
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
                            "user_type": user.user_type,
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


@app.route("/signup", methods=["POST"])
@limiter.limit("10 per minute")
def signup():
    """Register a new user and set authentication cookies."""
    try:
        data = request.json
        if not all(key in data for key in ["name", "email", "password", "user_type"]):
            return jsonify({"message": "Missing required fields"}), 400

        if data.get("is_admin"):
            return jsonify({"message": "Cannot register as admin"}), 403

        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"message": "Email already registered!"}), 409

        if data["user_type"] not in ["Landlord", "Agency", "Buyer/Renter"]:
            return jsonify({"message": "Invalid user type"}), 400

        new_user = User(
            name=data["name"],
            email=data["email"],
            user_type=data["user_type"],
            password="",  # This will be set in the next line
        )
        new_user.set_password(data["password"])
        db.session.add(new_user)
        db.session.commit()

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
                        "user_type": new_user.user_type,
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


@app.route("/logout", methods=["POST"])
def logout():
    """Clear authentication cookies and end the session."""
    verify_jwt_in_request(csrf_token=request.headers.get("X-CSRF-TOKEN"))
    response = make_response(jsonify({"message": "Logged out successfully"}), 200)
    unset_jwt_cookies(response)
    return response


@app.route("/auth/google", methods=["POST"])
def google_auth():
    """Authenticate or register a user using a Google OAuth token."""
    try:
        token = request.json.get("token")
        if not token:
            return jsonify({"message": "Missing Google token"}), 400

        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            config("GOOGLE_CLIENT_ID", default="your-google-client-id"),
        )
        email = idinfo["email"]
        name = idinfo.get("name", "Google User")

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, user_type="Buyer/Renter", password="")
            db.session.add(user)
            db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        csrf_token = get_csrf_token(access_token)
        response = make_response(
            jsonify(
                {
                    "message": "Google auth successful",
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "user_type": user.user_type,
                    },
                    "csrf_token": csrf_token,
                }
            ),
            200,
        )
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response
    except ValueError:
        return jsonify({"message": "Invalid Google token"}), 401
    except Exception as e:
        logging.error(f"Google auth error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/auth/facebook", methods=["POST"])
def facebook_auth():
    """Authenticate or register a user using a Facebook token."""
    try:
        access_token = request.json.get("accessToken")
        if not access_token:
            return jsonify({"message": "Missing Facebook token"}), 400

        graph = facebook.GraphAPI(access_token)
        profile = graph.get_object("me", fields="id,name,email")
        email = profile.get("email")
        name = profile["name"]

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, user_type="Buyer/Renter", password="")
            db.session.add(user)
            db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        csrf_token = get_csrf_token(access_token)
        response = make_response(
            jsonify(
                {
                    "message": "Facebook auth successful",
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "user_type": user.user_type,
                    },
                    "csrf_token": csrf_token,
                }
            ),
            200,
        )
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response
    except facebook.GraphAPIError:
        return jsonify({"message": "Invalid Facebook token"}), 401
    except Exception as e:
        logging.error(f"Facebook auth error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/update-type", methods=["POST"])
@jwt_required()
def update_user_type():
    """Change the authenticated user's type."""
    try:
        verify_jwt_in_request(csrf_token=request.headers.get("X-CSRF-TOKEN"))
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
        return (
            jsonify(
                {
                    "message": "User type updated successfully",
                    "user_type": user.user_type,
                }
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        logging.error(f"Update user type error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/whoami", methods=["GET"])
@jwt_required()
def whoami():
    """Return the currently authenticated user's info."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404
        return (
            jsonify(
                {
                    "message": "User info retrieved",
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "user_type": user.user_type,
                    },
                }
            ),
            200,
        )
    except Exception as e:
        logging.error(f"Whoami error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


# New route to check authentication status
@app.route("/api/auth/status", methods=["GET"])
@jwt_required(optional=True)
def auth_status():
    """Return whether a user is authenticated and basic user info."""
    try:
        user_id = get_jwt_identity()
        if user_id:
            user = User.query.get(user_id)
            if user:
                return (
                    jsonify(
                        {
                            "authenticated": True,
                            "user": {
                                "id": user.id,
                                "name": user.name,
                                "email": user.email,
                                "user_type": user.user_type,
                            },
                        }
                    ),
                    200,
                )
        return jsonify({"authenticated": False}), 200
    except Exception as e:
        logging.error(f"Auth status error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


# --- Template & Dashboard Routes ---
@app.route("/")
def home():
    """Render the landing page."""
    return render_template(
        "index.html", google_maps_api_key=app.config["GOOGLE_MAPS_API_KEY"]
    )


@app.route("/signin")
def signin_page():
    """Render the sign in HTML page."""
    return render_template("signin.html")


@app.route("/reset-password")
def reset_password_page():
    """Render the password reset form."""
    return render_template("reset-password.html")


@app.route("/for-owners")
def for_owners():
    """Return the page describing services for property owners."""
    return render_template("for-owners.html")


@app.route("/properties")
def properties_page():
    """Serve the public properties listing page."""
    return render_template(
        "properties.html", google_maps_api_key=app.config["GOOGLE_MAPS_API_KEY"]
    )


@app.route("/property/<slug>")
def property_detail(slug):
    """Display a single property's details."""
    prop = Property.query.filter_by(slug=slug).first()
    if not prop and slug.isdigit():
        prop = Property.query.get(int(slug))
    if not prop:
        abort(404)
    return render_template(
        "property_detail.html",
        property=prop,
        google_maps_api_key=app.config["GOOGLE_MAPS_API_KEY"],
    )


@app.route("/sell")
def sell_page():
    """Render the selling information page."""
    return render_template("sell.html")


@app.route("/diy-sell")
def diy_sell_page():
    """Show resources for selling a property yourself."""
    return render_template("diy-sell.html")


@app.route("/instant-offer")
def instant_offer_page():
    """Provide a page for getting an instant offer."""
    return render_template("instant-offer.html")


@app.route("/market")
def market_page():
    """Render the market statistics page."""
    return render_template("market.html")


@app.route("/market-trends")
def market_trends_page():
    """Show in-depth market trends."""
    return render_template("market-trends.html")


@app.route("/alerts")
def alerts_page():
    """Show the alerts management page."""
    return render_template("alerts.html")


@app.route("/evaluation")
def evaluation_page():
    """Render the property evaluation page."""
    return render_template("evaluation.html")


@app.route("/terms")
def terms_page():
    """Show the terms of service."""
    return render_template("terms.html")


@app.route("/privacy")
def privacy_page():
    """Display the privacy policy."""
    return render_template("privacy.html")


@app.route("/blog")
def blog_page():
    """Render the blog page."""
    return render_template("blog.html")


@app.route("/about")
def about_page():
    """Render the about page."""
    return render_template("about.html")


@app.route("/agents")
def agents_page():
    """List real estate agents."""
    return render_template("agents.html")


@app.route("/agent/<slug>")
def agent_detail(slug):
    """Display a single agent's profile."""
    ag = Agent.query.filter_by(slug=slug).first()
    if not ag and slug.isdigit():
        ag = Agent.query.get(int(slug))
    if not ag:
        abort(404)
    return render_template("agent_detail.html", agent=ag)


@app.route("/join-as-agent")
def join_as_agent_page():
    """Render the join as agent page."""
    return render_template("join-as-agent.html")


@app.route("/list/private-agent")
def private_agent_page():
    """Render the private agent listing page."""
    return render_template("private-agent.html")


@app.route("/contact")
def contact_page():
    """Render the contact page."""
    return render_template("contact.html")


@app.route("/mortgage")
def mortgage_page():
    """Render the mortgage calculator page."""
    return render_template("mortgage.html")


@app.route("/dashboard/<role>")
@jwt_required()
def dashboard(role):
    """Render the dashboard template for the given user role."""
    templates = {
        "agency": "dashboard-agency.html",
        "landlord": "dashboard-landlord.html",
        "buyer-renter": "dashboard-buyer-renter.html",
        "independent": "dashboard-independent.html",
    }
    template = templates.get(role)
    if not template:
        abort(404)

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        abort(404)
    expected_role = user.user_type.lower().replace("/", "-")
    if expected_role != role:
        abort(403)

    property_count = Property.query.filter_by(user_id=user_id).count()
    saved_count = Favorite.query.filter_by(user_id=user_id).count()
    alert_count = AlertPreference.query.filter_by(user_id=user_id).count()

    return render_template(
        template,
        user=user,
        property_count=property_count,
        saved_count=saved_count,
        alert_count=alert_count,
        match_count=alert_count,
    )


@app.route("/admin")
@jwt_required()
def admin_panel():
    """Admin dashboard showing basic statistics."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.is_admin:
        abort(403)
    users = User.query.all()
    properties = Property.query.all()
    user_count = len(users)
    property_count = len(properties)
    request_count = EvaluationRequest.query.count()
    agent_count = Agent.query.count()

    return render_template(
        "admin.html",
        users=users,
        properties=properties,
        user=user,
        user_count=user_count,
        property_count=property_count,
        request_count=request_count,
        agent_count=agent_count,
    )


# --- API Endpoints for Properties, Favorites, Evaluation, and Alerts ---
@app.route("/api/properties", methods=["GET"])
@jwt_required(optional=True)
def api_properties():
    """List active properties with optional filters."""
    try:
        purpose = request.args.get("purpose")
        location = request.args.get("location")
        property_type_filter = request.args.get("type")
        price = request.args.get("price")
        beds = request.args.get("beds")
        baths = request.args.get("baths")
        query = Property.query.filter_by(status="active")
        if purpose:
            query = query.filter_by(purpose=purpose.lower())
        if location:
            query = query.filter(Property.location.ilike(f"%{location}%"))
        if property_type_filter:
            query = query.filter_by(property_type=property_type_filter.lower())
        if price:
            query = query.filter(Property.price <= int(price))
        if beds:
            query = query.filter(Property.beds >= int(beds))
        if baths:
            query = query.filter(Property.baths >= int(baths))
        properties = query.all()
        return jsonify(
            {
                "properties": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "price": p.price,
                        "beds": p.beds,
                        "baths": p.baths,
                        "size": p.size,
                        "purpose": p.purpose,
                        "location": p.location,
                        "type": p.property_type,
                        "image_url": p.image_url,
                        "lat": p.lat,
                        "lng": p.lng,
                    }
                    for p in properties
                ],
                "count": len(properties),
            }
        )
    except Exception as e:
        logging.error(f"Properties GET error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/properties", methods=["POST"])
@jwt_required()
def create_property():
    """Create a new property listing for the authenticated user."""
    try:
        verify_jwt_in_request(csrf_token=request.headers.get("X-CSRF-TOKEN"))
        user_id = get_jwt_identity()
        data = request.form.to_dict()
        file = request.files.get("image")
        validated = property_schema.load(data)

        image_url = upload(file)["url"] if file else None
        new_property = Property(
            user_id=user_id,
            title=validated["title"],
            slug=slugify(validated["title"]),
            location=validated["location"],
            purpose=validated["purpose"],
            property_type=validated["property_type"],
            price=validated["price"],
            beds=validated["beds"],
            baths=validated["baths"],
            size=validated["size"],
            image_url=image_url,
            lat=validated.get("lat", 0),
            lng=validated.get("lng", 0),
        )
        db.session.add(new_property)
        db.session.commit()
        return (
            jsonify({"message": "Property listed successfully", "id": new_property.id}),
            201,
        )
    except ValidationError as err:
        return jsonify({"message": "Invalid input", "errors": err.messages}), 400
    except Exception as e:
        db.session.rollback()
        logging.error(f"Property creation error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/favorites", methods=["POST"])
@jwt_required()
def add_favorite():
    """Save a property to the authenticated user's favorites."""
    try:
        verify_jwt_in_request(csrf_token=request.headers.get("X-CSRF-TOKEN"))
        user_id = get_jwt_identity()
        property_id = request.json.get("property_id")
        if not Property.query.get(property_id):
            return jsonify({"message": "Property not found"}), 404
        favorite = Favorite(user_id=user_id, property_id=property_id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({"message": "Added to favorites"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/favorites", methods=["GET"])
@jwt_required()
def get_favorites():
    """Return the authenticated user's saved properties."""
    try:
        user_id = get_jwt_identity()
        favorites = Favorite.query.filter_by(user_id=user_id).all()
        properties = [Property.query.get(f.property_id) for f in favorites]
        return jsonify(
            {
                "saved": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "price": p.price,
                        "image_url": p.image_url,
                    }
                    for p in properties
                ],
                "count": len(properties),
            }
        )
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/evaluation", methods=["POST"])
def process_evaluation():
    """Estimate a property's value and store the request."""
    try:
        data = request.json
        required_fields = [
            "location",
            "type",
            "area",
            "bedrooms",
            "bathrooms",
            "condition",
        ]
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        user_id = get_jwt_identity() if "Authorization" in request.headers else None
        base_value = int(data["area"]) * 2000
        estimated_value = f"€{base_value - 50000} - €{base_value + 50000}"

        evaluation = EvaluationRequest(
            user_id=user_id,
            location=data["location"],
            property_type=data["type"],
            area=int(data["area"]),
            bedrooms=int(data["bedrooms"]),
            bathrooms=int(data["bathrooms"]),
            condition=data["condition"],
            estimated_value=estimated_value,
        )
        db.session.add(evaluation)
        db.session.commit()
        return jsonify({"message": estimated_value}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/alerts", methods=["POST"])
def save_alerts():
    """Persist a new email alert configuration."""
    try:
        data = request.json
        required_fields = [
            "email",
            "purpose",
            "location",
            "minPrice",
            "maxPrice",
            "type",
            "frequency",
        ]
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        user_id = get_jwt_identity() if "Authorization" in request.headers else None
        alert = AlertPreference(
            user_id=user_id,
            email=data["email"],
            purpose=data["purpose"],
            location=data["location"],
            min_price=int(data["minPrice"]),
            max_price=int(data["maxPrice"]),
            property_type=data["type"],
            frequency=data["frequency"],
        )
        db.session.add(alert)
        db.session.commit()
        return jsonify({"message": "Alerts saved successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/alerts", methods=["GET"])
@jwt_required()
def api_alerts():
    """Return alert preferences for the authenticated user."""
    try:
        user_id = get_jwt_identity()
        alerts = AlertPreference.query.filter_by(user_id=user_id).all()
        return jsonify(
            {
                "count": len(alerts),
                "alerts": [
                    {
                        "purpose": a.purpose,
                        "location": a.location,
                        "min_price": a.min_price,
                        "max_price": a.max_price,
                    }
                    for a in alerts
                ],
            }
        )
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


# --- Agent Endpoints ---
@app.route("/api/agents", methods=["GET"])
def get_agents():
    """List all registered agents."""
    try:
        agents = Agent.query.all()
        return jsonify(
            {
                "count": len(agents),
                "agents": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "email": a.email,
                        "phone": a.phone,
                        "agency": a.agency,
                        "specialty": a.specialty,
                        "languages": a.languages,
                        "location": a.location,
                        "bio": a.bio,
                        "photo_url": a.photo_url,
                    }
                    for a in agents
                ],
            }
        )
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/agents", methods=["POST"])
@jwt_required()
def create_agent():
    """Create a new real estate agent record."""
    try:
        verify_jwt_in_request(csrf_token=request.headers.get("X-CSRF-TOKEN"))
        data = request.get_json() or {}
        validated = agent_schema.load(data)
        agent = Agent(**validated, slug=slugify(validated["name"]))
        db.session.add(agent)
        db.session.commit()
        return jsonify({"message": "Agent created", "id": agent.id}), 201
    except ValidationError as err:
        return jsonify({"message": "Invalid input", "errors": err.messages}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/agents/add", methods=["POST"])
@jwt_required()
def add_agent():
    """Alias route to create a new agent."""
    verify_jwt_in_request(csrf_token=request.headers.get("X-CSRF-TOKEN"))
    return create_agent()


@app.route("/api/agents/<int:agent_id>", methods=["GET"])
def get_agent(agent_id):
    """Retrieve a single agent by ID."""
    try:
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({"message": "Agent not found"}), 404
        return jsonify(
            {
                "id": agent.id,
                "name": agent.name,
                "email": agent.email,
                "phone": agent.phone,
                "agency": agent.agency,
                "specialty": agent.specialty,
                "languages": agent.languages,
                "location": agent.location,
                "bio": agent.bio,
                "photo_url": agent.photo_url,
            }
        )
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/agents/<int:agent_id>", methods=["PUT"])
@jwt_required()
def update_agent(agent_id):
    """Modify an existing agent's information."""
    try:
        verify_jwt_in_request(csrf_token=request.headers.get("X-CSRF-TOKEN"))
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({"message": "Agent not found"}), 404
        data = request.json
        for field in [
            "name",
            "email",
            "phone",
            "agency",
            "specialty",
            "languages",
            "location",
            "bio",
            "photo_url",
        ]:
            if field in data:
                setattr(agent, field, data[field])
        db.session.commit()
        return jsonify({"message": "Agent updated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/agents/<int:agent_id>", methods=["DELETE"])
@jwt_required()
def delete_agent(agent_id):
    """Remove an agent from the system."""
    try:
        verify_jwt_in_request(csrf_token=request.headers.get("X-CSRF-TOKEN"))
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({"message": "Agent not found"}), 404
        db.session.delete(agent)
        db.session.commit()
        return jsonify({"message": "Agent deleted"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/agency/properties")
@jwt_required()
def agency_properties():
    """Return basic stats for properties listed by the agency."""
    try:
        user_id = get_jwt_identity()
        properties = Property.query.filter_by(user_id=user_id).all()
        return jsonify(
            {
                "count": len(properties),
                "properties": [
                    {"id": p.id, "views": 150, "inquiries": 10} for p in properties
                ],  # Placeholder stats
            }
        )
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/user/properties")
@jwt_required()
def user_properties():
    """List properties created by the authenticated user."""
    try:
        user_id = get_jwt_identity()
        properties = Property.query.filter_by(user_id=user_id).all()
        return jsonify(
            {
                "count": len(properties),
                "properties": [
                    {"id": p.id, "title": p.title, "status": p.status, "price": p.price}
                    for p in properties
                ],
            }
        )
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/analytics", methods=["GET"])
@jwt_required()
def analytics():
    """Return placeholder analytics data."""
    try:
        data = {
            "conversion_rate": "2.5%",
            "chart": {
                "labels": ["Jan", "Feb", "Mar", "Apr"],
                "views": [120, 150, 170, 160],
            },
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/requests", methods=["GET"])
@jwt_required()
def agency_requests():
    """List incoming requests for an agency."""
    try:
        requests_list = [
            {"id": 1, "client": "John Doe", "property": "Apartment"},
            {"id": 2, "client": "Jane Smith", "property": "Villa"},
        ]
        return jsonify({"count": len(requests_list), "requests": requests_list})
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/agency/profile", methods=["POST"])
@jwt_required()
def update_agency_profile():
    """Update the authenticated agency's profile."""
    try:
        verify_jwt_in_request(csrf_token=request.headers.get("X-CSRF-TOKEN"))
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        data = request.form or request.json or {}
        if "name" in data:
            user.name = data["name"]
        if "email" in data:
            user.email = data["email"]
        db.session.commit()
        return jsonify({"message": "Profile updated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@app.route("/api/market-snapshot", methods=["GET"])
@jwt_required()
def market_snapshot():
    """Return a simplified market snapshot."""
    try:
        return jsonify({"avg_price": "€1,350/m²", "trend": "up"})
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


# --- Global Error Handler ---
@app.errorhandler(Exception)
def handle_exception(e):
    """Log unexpected exceptions and return a generic error message."""
    if isinstance(e, HTTPException):
        return e
    logging.exception("Unhandled exception: %s", e)
    return jsonify({"message": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
