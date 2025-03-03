from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, EvaluationRequest, AlertPreference

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

# API Endpoints (Placeholders)
@routes.route("/api/user/properties")
@jwt_required()
def api_user_properties():
    user_id = get_jwt_identity()
    properties = [
        {"id": 1, "title": "Tirana Skyline Penthouse", "price": 450000, "beds": 3, "baths": 2, "size": 1500, "purpose": "buy", "location": "Tirana", "type": "apartment"}
    ]
    return jsonify({"properties": properties, "count": len(properties)})

@routes.route("/api/evaluations")
@jwt_required()
def api_evaluations():
    user_id = get_jwt_identity()
    evaluations = EvaluationRequest.query.filter_by(user_id=user_id).order_by(EvaluationRequest.created_at.desc()).limit(1).all()
    return jsonify({"latest": {"estimated_value": evaluations[0].estimated_value if evaluations else "No evaluations yet"}})

@routes.route("/api/offers")
@jwt_required()
def api_offers():
    return jsonify({"offers": [{"id": 1, "property": "Tirana Skyline Penthouse", "amount": 425000, "status": "pending"}], "count": 1})

@routes.route("/api/agency/properties")
@jwt_required()
def api_agency_properties():
    return jsonify({"properties": [{"id": 1, "title": "Vlora Coastal Villa", "views": 150, "inquiries": 5}], "count": 1})

@routes.route("/api/requests")
@jwt_required()
def api_requests():
    return jsonify({"requests": [{"id": 1, "client": "John Doe", "property": "Vlora Coastal Villa", "status": "new"}], "count": 1})

@routes.route("/api/analytics")
@jwt_required()
def api_analytics():
    return jsonify({"views": 150, "inquiries": 10, "conversion_rate": "6.7%"})

@routes.route("/api/saved")
@jwt_required()
def api_saved():
    return jsonify({"saved": [{"id": 3, "title": "Saranda Seafront Apartment", "price": 220000}], "count": 1})

@routes.route("/api/alerts")
@jwt_required()
def api_alerts():
    user_id = get_jwt_identity()
    alerts = AlertPreference.query.filter_by(user_id=user_id).all()
    return jsonify({"alerts": [{"purpose": a.purpose, "location": a.location} for a in alerts], "count": len(alerts)})

@routes.route("/api/market-snapshot")
@jwt_required()
def api_market_snapshot():
    return jsonify({"avg_price": "€1,350/m²", "trend": "Up 5%"})

# Other Routes (Unchanged)
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

@routes.route("/evaluation", methods=["POST"])
def process_evaluation():
    try:
        data = request.json
        required_fields = ['location', 'type', 'area', 'bedrooms', 'bathrooms', 'condition']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        user_id = get_jwt_identity() if 'Authorization' in request.headers else None
        base_value = int(data['area']) * 2000
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

@routes.route("/request-offer", methods=["POST"])
@jwt_required(optional=True)
def request_offer():
    try:
        data = request.json
        required_fields = ['agency', 'name', 'date']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        user_id = get_jwt_identity()
        print(f"Offer Request: User {user_id or 'Anonymous'}, Agency: {data['agency']}, Name: {data['name']}, Date: {data['date']}, Phone: {data.get('phone', '')}, Email: {data.get('email', '')}")
        return jsonify({"message": "Offer request sent successfully"}), 200
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
