from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from cloudinary.uploader import upload
import logging
from marshmallow import ValidationError
from app import app # Needed for the config
from models import Property, User, Favorite, EvaluationRequest, AlertPreference, property_schema, db, slugify

# Create a Blueprint instance
property_bp = Blueprint('properties', __name__)

# --- Property API Endpoints ---

@property_bp.route("/api/properties", methods=["GET"])
@jwt_required(optional=True)
def api_properties():
    # ... (Paste your existing api_properties GET logic here)
    # This search logic will need to be replaced with the Elasticsearch search engine later!
    pass

@property_bp.route("/api/properties", methods=["POST"])
@jwt_required()
def create_property():
    """Create a new property listing for the authenticated user."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # REQUIRED CHANGE: Role-based Authorization Check
        if user.role not in ['AGENT', 'BROKER', 'ADMIN']:
            return jsonify({"message": "Forbidden: Only authorized agents/brokers can list properties"}), 403

        data = request.form.to_dict()
        file = request.files.get("image")
        validated = property_schema.load(data)

        # NEW: Tiered Logic Check
        purpose = validated.get("purpose", "").upper()
        if purpose == 'SALE' and validated.get('price') is None:
            return jsonify({"message": "Sale properties must include a price"}), 400
        if purpose == 'RENT' and validated.get('monthly_rent') is None: 
            return jsonify({"message": "Rental properties must include a monthly rent"}), 400
        
        if purpose not in ['SALE', 'RENT']:
             return jsonify({"message": "Purpose must be 'SALE' or 'RENT'"}), 400

        image_url = upload(file)["url"] if file else None
        
        new_property = Property(
            user_id=user_id,
            title=validated["title"],
            slug=slugify(validated["title"]),
            location=validated["location"],
            purpose=purpose,
            sale_method=validated.get("sale_method", "STANDARD").upper(),
            property_type=validated["property_type"],
            price=validated.get("price"),
            monthly_rent=validated.get("monthly_rent"),
            beds=validated["beds"],
            baths=validated["baths"],
            size=validated["size"],
            image_url=image_url,
            lat=validated.get("lat", 0),
            lng=validated.get("lng", 0),
            status="pending" # All new properties require Admin approval
        )
        db.session.add(new_property)
        db.session.commit()
        return (
            jsonify({"message": "Property submitted for approval", "id": new_property.id}),
            201,
        )
    except ValidationError as err:
        return jsonify({"message": "Invalid input", "errors": err.messages}), 400
    except Exception as e:
        db.session.rollback()
        logging.error(f"Property creation error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# ... (Paste the rest of your property/favorite/alert routes here)
# E.g., /api/favorites, /evaluation (POST), /alerts (POST), /api/alerts (GET)
