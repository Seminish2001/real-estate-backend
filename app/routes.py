from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User

routes = Blueprint("routes", __name__)

@routes.route("/dashboard")
@jwt_required()
def serve_dashboard():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user:
        return render_template("dashboard.html", user=user)
    return jsonify({"message": "User not found"}), 404

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
