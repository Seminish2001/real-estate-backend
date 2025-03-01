from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User

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

@routes.route("/terms")
def terms():
    return render_template("terms.html")

@routes.route("/privacy")
def privacy():
    return render_template("privacy.html")
