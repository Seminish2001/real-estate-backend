import logging
from typing import Optional

from cloudinary.uploader import upload
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request
from marshmallow import ValidationError
from sqlalchemy import func

from models import (
    AlertPreference,
    EvaluationRequest,
    Favorite,
    Property,
    User,
    db,
    property_schema,
    safe_get,
    slugify,
)

property_bp = Blueprint("properties", __name__)


def _generate_unique_slug(base_title: str, property_id: Optional[int] = None) -> str:
    """Generate a unique slug for a property title."""

    base_slug = slugify(base_title)
    slug = base_slug
    counter = 1

    query = Property.query.filter(Property.slug == slug)
    if property_id:
        query = query.filter(Property.id != property_id)

    while query.first() is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
        query = Property.query.filter(Property.slug == slug)
        if property_id:
            query = query.filter(Property.id != property_id)

    return slug


@property_bp.route("/api/properties", methods=["GET"])
@jwt_required(optional=True)
def api_properties():
    """Return a list of public property listings with basic filtering."""

    query = Property.query.filter(Property.status == "active")

    purpose = request.args.get("purpose")
    if purpose:
        purpose_value = purpose.upper()
        if purpose_value in ("BUY", "SELL"):
            purpose_value = "SALE"
        elif purpose_value in ("RENT", "LEASE"):
            purpose_value = "RENT"
        query = query.filter(Property.purpose == purpose_value)

    location = request.args.get("location")
    if location:
        query = query.filter(Property.location.ilike(f"%{location}%"))

    property_type = request.args.get("type") or request.args.get("property_type")
    if property_type:
        query = query.filter(Property.property_type.ilike(f"%{property_type}%"))

    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    if min_price is not None:
        query = query.filter(
            func.coalesce(Property.price, Property.monthly_rent) >= min_price
        )
    if max_price is not None:
        query = query.filter(
            func.coalesce(Property.price, Property.monthly_rent) <= max_price
        )

    properties = query.order_by(Property.created_at.desc()).all()

    return jsonify(
        {
            "count": len(properties),
            "results": [
                {
                    "id": p.id,
                    "title": p.title,
                    "slug": p.slug,
                    "location": p.location,
                    "purpose": p.purpose,
                    "property_type": p.property_type,
                    "price": p.price,
                    "monthly_rent": p.monthly_rent,
                    "beds": p.beds,
                    "baths": p.baths,
                    "size": p.size,
                    "image_url": p.image_url,
                    "status": p.status,
                }
                for p in properties
            ],
        }
    )


@property_bp.route("/api/properties/<int:property_id>", methods=["GET"])
@jwt_required(optional=True)
def get_property(property_id: int):
    """Return detailed information about a single property."""

    prop = safe_get(Property, property_id)
    if not prop:
        return jsonify({"message": "Property not found"}), 404

    if prop.status != "active":
        current_user_id = get_jwt_identity()
        if not current_user_id or current_user_id != prop.user_id:
            return jsonify({"message": "Property not available"}), 404

    owner = safe_get(User, prop.user_id)

    return jsonify(
        {
            "id": prop.id,
            "title": prop.title,
            "slug": prop.slug,
            "location": prop.location,
            "purpose": prop.purpose,
            "property_type": prop.property_type,
            "price": prop.price,
            "monthly_rent": prop.monthly_rent,
            "beds": prop.beds,
            "baths": prop.baths,
            "size": prop.size,
            "description": getattr(prop, "description", None),
            "lat": prop.lat,
            "lng": prop.lng,
            "status": prop.status,
            "image_url": prop.image_url,
            "virtual_tour_url": prop.virtual_tour_url,
            "agent": {
                "id": owner.id if owner else None,
                "name": owner.name if owner else None,
                "email": owner.email if owner else None,
            },
        }
    )


@property_bp.route("/api/properties", methods=["POST"])
@jwt_required()
def create_property():
    """Create a new property listing for the authenticated user."""

    try:
        user_id = get_jwt_identity()
        user = safe_get(User, user_id)

        if not user:
            return jsonify({"message": "User not found"}), 404

        if user.role not in ["AGENT", "BROKER", "ADMIN", "LANDLORD"]:
            return (
                jsonify(
                    {
                        "message": "Forbidden: Only authorized agents/brokers can list properties"
                    }
                ),
                403,
            )

        data = request.form.to_dict()
        file = request.files.get("image")
        validated = property_schema.load(data)

        purpose = validated.get("purpose", "").upper()
        if purpose == "SALE" and validated.get("price") is None:
            return jsonify({"message": "Sale properties must include a price"}), 400
        if purpose == "RENT" and validated.get("monthly_rent") is None:
            return jsonify({"message": "Rental properties must include a monthly rent"}), 400
        if purpose not in ["SALE", "RENT"]:
            return jsonify({"message": "Purpose must be 'SALE' or 'RENT'"}), 400

        image_url = upload(file)["url"] if file else None

        title = validated["title"]
        slug = _generate_unique_slug(title)

        new_property = Property(
            user_id=user_id,
            title=title,
            slug=slug,
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
            status="active",
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


@property_bp.route("/api/favorites", methods=["GET"])
@jwt_required()
def list_favorites():
    """Return favorite properties for the authenticated user."""

    user_id = get_jwt_identity()
    favorites = (
        Favorite.query.join(Property, Favorite.property_id == Property.id)
        .filter(Favorite.user_id == user_id)
        .all()
    )

    return jsonify(
        {
            "count": len(favorites),
            "results": [
                {
                    "id": fav.property.id,
                    "title": fav.property.title,
                    "location": fav.property.location,
                    "purpose": fav.property.purpose,
                    "price": fav.property.price,
                    "monthly_rent": fav.property.monthly_rent,
                }
                for fav in favorites
            ],
        }
    )


@property_bp.route("/api/favorites", methods=["POST"])
@jwt_required()
def create_favorite():
    """Create a favorite entry from a JSON payload."""

    user_id = get_jwt_identity()
    data = request.get_json() or {}
    property_id = data.get("property_id")
    if not property_id:
        return jsonify({"message": "Missing property_id"}), 400

    prop = safe_get(Property, property_id)
    if not prop:
        return jsonify({"message": "Property not found"}), 404

    existing = Favorite.query.filter_by(user_id=user_id, property_id=property_id).first()
    if existing:
        return jsonify({"message": "Property already in favorites"}), 200

    favorite = Favorite(user_id=user_id, property_id=property_id)
    db.session.add(favorite)
    db.session.commit()
    return jsonify({"message": "Favorite created", "id": favorite.id}), 201


@property_bp.route("/api/favorites/<int:property_id>", methods=["POST"])
@jwt_required()
def add_favorite(property_id: int):
    """Add a property to the authenticated user's favorites."""

    user_id = get_jwt_identity()
    prop = safe_get(Property, property_id)
    if not prop:
        return jsonify({"message": "Property not found"}), 404

    existing = Favorite.query.filter_by(user_id=user_id, property_id=prop.id).first()
    if existing:
        return jsonify({"message": "Property already in favorites"}), 200

    favorite = Favorite(user_id=user_id, property_id=prop.id)
    db.session.add(favorite)
    db.session.commit()
    return jsonify({"message": "Property added to favorites"}), 201


@property_bp.route("/api/favorites/<int:property_id>", methods=["DELETE"])
@jwt_required()
def remove_favorite(property_id: int):
    """Remove a property from favorites."""

    user_id = get_jwt_identity()
    favorite = Favorite.query.filter_by(user_id=user_id, property_id=property_id).first()

    if not favorite:
        return jsonify({"message": "Favorite not found"}), 404

    db.session.delete(favorite)
    db.session.commit()
    return jsonify({"message": "Favorite removed"})


@property_bp.route("/evaluation", methods=["POST"])
def request_evaluation():
    """Allow users to request an automated property evaluation."""

    data = request.get_json() or {}

    property_type = data.get("property_type") or data.get("type")

    required_fields = ["location", "area", "bedrooms", "bathrooms", "condition"]
    if not property_type or not all(field in data for field in required_fields):
        return jsonify({"message": "Missing required fields"}), 400

    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except Exception:
        user_id = None

    eval_request = EvaluationRequest(
        user_id=user_id,
        location=data["location"],
        property_type=property_type,
        area=data["area"],
        bedrooms=data["bedrooms"],
        bathrooms=data["bathrooms"],
        condition=data["condition"],
        estimated_value=data.get("estimated_value"),
    )
    db.session.add(eval_request)
    db.session.commit()

    return jsonify({"message": "Evaluation request submitted"})


@property_bp.route("/alerts", methods=["POST"])
def create_alert():
    """Create an alert preference for property updates."""

    data = request.get_json() or {}

    required_fields = ["email", "purpose", "location", "minPrice", "maxPrice", "type", "frequency"]
    if not all(field in data for field in required_fields):
        return jsonify({"message": "Missing required fields"}), 400

    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except Exception:
        user_id = None

    purpose_value = data["purpose"].upper()
    if purpose_value in ["BUY", "SELL"]:
        purpose_value = "SALE"
    elif purpose_value in ["RENT", "LEASE"]:
        purpose_value = "RENT"

    alert = AlertPreference(
        user_id=user_id,
        email=data["email"],
        purpose=purpose_value,
        location=data["location"],
        min_price=data["minPrice"],
        max_price=data["maxPrice"],
        property_type=data["type"],
        frequency=data["frequency"],
    )
    db.session.add(alert)
    db.session.commit()

    return jsonify({"message": "Alert preference saved"})


@property_bp.route("/api/alerts", methods=["GET"])
@jwt_required(optional=True)
def list_alerts():
    """List alert preferences. Authenticated users see their own; others see totals."""

    user_id = get_jwt_identity()

    if user_id:
        alerts = AlertPreference.query.filter_by(user_id=user_id).all()
        if not alerts:
            alerts = AlertPreference.query.order_by(AlertPreference.created_at.desc()).limit(20).all()
    else:
        alerts = AlertPreference.query.order_by(AlertPreference.created_at.desc()).limit(20).all()

    return jsonify(
        {
            "count": len(alerts),
            "results": [
                {
                    "id": alert.id,
                    "email": alert.email,
                    "purpose": alert.purpose,
                    "location": alert.location,
                    "min_price": alert.min_price,
                    "max_price": alert.max_price,
                    "property_type": alert.property_type,
                    "frequency": alert.frequency,
                }
                for alert in alerts
            ],
        }
    )
