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
        return render_template("dashboard.html", user=user)
    return jsonify({"message": "Unauthorized or user not found"}), 403

@routes.route("/dashboard/private")
@jwt_required()
def serve_dashboard_private():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user and user.user_type == "Landlord":
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

# API Endpoint for Properties Data
@routes.route("/api/properties")
def api_properties():
    purpose = request.args.get('purpose')
    location = request.args.get('location')
    type = request.args.get('type')
    price = request.args.get('price')
    beds = request.args.get('beds')
    baths = request.args.get('baths')

    query = Property.query
    if purpose:
        query = query.filter_by(purpose=purpose.lower())
    if location:
        query = query.filter(Property.location.ilike(f"%{location}%"))
    if type:
        query = query.filter_by(type=type.lower())
    if price:
        query = query.filter(Property.price <= int(price))
    if beds:
        query = query.filter(Property.bedrooms >= int(beds))
    if baths:
        query = query.filter(Property.bathrooms >= int(baths))

    properties = query.all()
    return jsonify({
        "properties": [{"id": p.id, "title": p.title, "price": p.price, "beds": p.bedrooms, "baths": p.bathrooms, "size": p.size, "purpose": p.purpose, "location": p.location, "type": p.type} for p in properties],
        "count": len(properties)
    })

    filtered = properties
    if purpose:
        filtered = [p for p in filtered if p['purpose'] == purpose.lower()]
    if location:
        filtered = [p for p in filtered if location.lower() in p['location'].lower()]
    if type:
        filtered = [p for p in filtered if p['type'] == type.lower()]
    if price:
        filtered = [p for p in filtered if p['price'] <= int(price)]
    if beds:
        filtered = [p for p in filtered if p['beds'] >= int(beds)]
    if baths:
        filtered = [p for p in filtered if p['baths'] >= int(baths)]

    return jsonify({"properties": filtered, "count": len(filtered)})

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
