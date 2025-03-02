from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, EvaluationRequest, AlertPreference

routes = Blueprint("routes", __name__)

@routes.route("/dashboard/agency")
@jwt_required()
def serve_dashboard_agency():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user and user.user_type == "Real Estate Agency":
        return render_template("dashboard.html", user=user)
    return jsonify({"message": "Unauthorized or user not found"}), 403

@routes.route("/dashboard/private")
@jwt_required()
def serve_dashboard_private():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user and user.user_type == "Private Owner":
        return render_template("dashboard-private.html", user=user)
    return jsonify({"message": "Unauthorized or user not found"}), 403

@routes.route("/dashboard/buyer-renter")
@jwt_required()
def serve_dashboard_buyer_renter():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user and user.user_type == "Buyer/Renter":
        return render_template("dashboard-buyer-renter.html", user=user)
    return jsonify({"message": "Unauthorized or user not found"}), 403

@routes.route("/properties")
def serve_properties():
    return render_template("properties.html")

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

        # Optional user_id if logged in
        user_id = get_jwt_identity() if 'Authorization' in request.headers else None

        # Simple estimation logic (replace with real calculation later)
        base_value = int(data['area']) * 2000  # €2000 per m² as placeholder
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

        # Optional user_id if logged in
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

        user_id = get_jwt_identity()  # Optional, null if not logged in
        # Here you could save the request to a new table or send an email/notification to the agency
        print(f"Offer Request: User {user_id or 'Anonymous'}, Agency: {data['agency']}, Name: {data['name']}, Date: {data['date']}, Phone: {data.get('phone', '')}, Email: {data.get('email', '')}")
        return jsonify({"message": "Offer request sent successfully"}), 200
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
