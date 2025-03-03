from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Property, EvaluationRequest, AlertPreference, Favorite, Offer
from cloudinary.uploader import upload
import logging

routes = Blueprint("routes", __name__)

# Dashboard Routes
@routes.route("/dashboard/agency")
@jwt_required()
def serve_dashboard_agency():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user and user.user_type == "Agency":
        return render_template("dashboard-agency.html", user=user)
    return jsonify({"message": "Unauthorized or user not found"}), 403

@routes.route("/dashboard/landlord")
@jwt_required()
def serve_dashboard_landlord():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user and user.user_type == "Landlord":
        return render_template("dashboard-landlord.html", user=user)
    return jsonify({"message": "Unauthorized or user not found"}), 403

@routes.route("/dashboard/buyer-renter")
@jwt_required()
def serve_dashboard_buyer_renter():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user and user.user_type == "Buyer/Renter":
        return render_template("dashboard-buyer-renter.html", user=user)
    return jsonify({"message": "Unauthorized or user not found"}), 403

# Static Page Routes
@routes.route("/properties")
def serve_properties():
    return render_template("properties.html")

@routes.route("/sell")
def serve_sell():
    return render_template("sell.html")

@routes.route("/market")
def serve_market():
    return render_template("market.html")

@routes.route("/alerts")
def serve_alerts():
    return render_template("alerts.html")

@routes.route("/evaluation")
def serve_evaluation():
    return render_template("evaluation.html")

@routes.route("/terms")
def terms():
    return render_template("terms.html")

@routes.route("/privacy")
def privacy():
    return render_template("privacy.html")

# Property APIs
@routes.route("/api/properties", methods=["GET"])
@jwt_required(optional=True)
def api_properties():
    try:
        purpose = request.args.get('purpose')
        location = request.args.get('location')
        type = request.args.get('type')
        price = request.args.get('price')
        beds = request.args.get('beds')
        baths = request.args.get('baths')
        query = Property.query.filter_by(status="active")
        if purpose:
            query = query.filter_by(purpose=purpose.lower())
        if location:
            query = query.filter(Property.location.ilike(f"%{location}%"))
        if type:
            query = query.filter_by(property_type=type.lower())
        if price:
            query = query.filter(Property.price <= int(price))
        if beds:
            query = query.filter(Property.beds >= int(beds))
        if baths:
            query = query.filter(Property.baths >= int(baths))
        properties = query.all()
        return jsonify({
            "properties": [{"id": p.id, "title": p.title, "price": p.price, "beds": p.beds, "baths": p.baths, "size": p.size, "purpose": p.purpose, "location": p.location, "type": p.property_type, "image_url": p.image_url, "lat": p.lat, "lng": p.lng} for p in properties],
            "count": len(properties)
        })
    except Exception as e:
        logging.error(f"Properties GET error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@routes.route("/api/properties", methods=["POST"])
@jwt_required()
def create_property():
    try:
        user_id = get_jwt_identity()
        data = request.form
        file = request.files.get('image')
        image_url = upload(file)['url'] if file else None
        property = Property(
            user_id=user_id,
            title=data["title"],
            location=data["location"],
            purpose=data["purpose"],
            property_type=data["type"],
            price=int(data["price"]),
            beds=int(data["beds"]),
            baths=int(data["baths"]),
            size=int(data["size"]),
            image_url=image_url,
            lat=float(data.get("lat", 0)),  # Default to 0 if not provided
            lng=float(data.get("lng", 0))
        )
        db.session.add(property)
        db.session.commit()
        return jsonify({"message": "Property listed successfully", "id": property.id}), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"Property creation error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# Favorites
@routes.route("/api/favorites", methods=["POST"])
@jwt_required()
def add_favorite():
    try:
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

@routes.route("/api/favorites", methods=["GET"])
@jwt_required()
def get_favorites():
    try:
        user_id = get_jwt_identity()
        favorites = Favorite.query.filter_by(user_id=user_id).all()
        properties = [Property.query.get(f.property_id) for f in favorites]
        return jsonify({
            "saved": [{"id": p.id, "title": p.title, "price": p.price, "image_url": p.image_url} for p in properties],
            "count": len(properties)
        })
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# Evaluation
@routes.route("/evaluation", methods=["POST"])
def process_evaluation():
    try:
        data = request.json
        required_fields = ['location', 'type', 'area', 'bedrooms', 'bathrooms', 'condition']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        user_id = get_jwt_identity() if 'Authorization' in request.headers else None
        base_value = int(data['area']) * 2000  # Simplified logic
        estimated_value = f"€{base_value - 50000} - €{base_value + 50000}"

        evaluation = EvaluationRequest(
            user_id=user_id,
            location=data['location'],
            property_type=data['type'],
            area=int(data['area']),
            bedrooms=int(data['bedrooms']),
            bathrooms=int(data['bathrooms']),
            condition=data['condition'],
            estimated_value=estimated_value
        )
        db.session.add(evaluation)
        db.session.commit()
        return jsonify({"message": estimated_value}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# Alerts
@routes.route("/alerts", methods=["POST"])
def save_alerts():
    try:
        data = request.json
        required_fields = ['email', 'purpose', 'location', 'minPrice', 'maxPrice', 'type', 'frequency']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        user_id = get_jwt_identity() if 'Authorization' in request.headers else None
        alert = AlertPreference(
            user_id=user_id,
            email=data['email'],
            purpose=data['purpose'],
            location=data['location'],
            min_price=int(data['minPrice']),
            max_price=int(data['maxPrice']),
            property_type=data['type'],
            frequency=data['frequency']
        )
        db.session.add(alert)
        db.session.commit()
        return jsonify({"message": "Alerts saved successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@routes.route("/api/alerts", methods=["GET"])
@jwt_required()
def api_alerts():
    try:
        user_id = get_jwt_identity()
        alerts = AlertPreference.query.filter_by(user_id=user_id).all()
        return jsonify({
            "count": len(alerts),
            "alerts": [{"purpose": a.purpose, "location": a.location, "min_price": a.min_price, "max_price": a.max_price} for a in alerts]
        })
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# Dashboard APIs
@routes.route("/api/agency/properties")
@jwt_required()
def agency_properties():
    try:
        user_id = get_jwt_identity()
        properties = Property.query.filter_by(user_id=user_id).all()
        return jsonify({
            "count": len(properties),
            "properties": [{"id": p.id, "views": 150, "inquiries": 10} for p in properties]  # Placeholder stats
        })
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@routes.route("/api/user/properties")
@jwt_required()
def user_properties():
    try:
        user_id = get_jwt_identity()
        properties = Property.query.filter_by(user_id=user_id).all()
        return jsonify({
            "count": len(properties),
            "properties": [{"id": p.id, "title": p.title, "status": p.status, "price": p.price} for p in properties]
        })
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
