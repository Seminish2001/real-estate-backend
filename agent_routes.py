from functools import wraps

from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from sqlalchemy import or_

from extensions import db
from models import (
    AgentProfile,
    EvaluationRequest,
    Property,
    User,
    agent_profile_schema,
    safe_get,
    slugify,
)

agent_bp = Blueprint("agents", __name__, url_prefix="/api/agents")
agency_bp = Blueprint("agency", __name__)


def agent_role_required(fn):
    """Decorator ensuring the requester is an authenticated AGENT or BROKER."""

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = safe_get(User, user_id)
        if not user or user.role not in ["AGENT", "BROKER", "ADMIN", "LANDLORD"]:
            abort(403, description="Forbidden: Must be an authorized agent or broker.")
        return fn(*args, **kwargs)

    return wrapper


@agent_bp.route("/me", methods=["GET"])
@agent_role_required
def get_my_profile():
    """Retrieve the authenticated agent's profile and key metrics."""

    user_id = get_jwt_identity()
    user = safe_get(User, user_id)

    if not user.agent_profile:
        return jsonify({"message": "Agent profile not found. Complete setup."}), 404

    profile = user.agent_profile
    total_listings = Property.query.filter_by(user_id=user_id).count()
    active_listings = Property.query.filter_by(user_id=user_id, status="active").count()

    return jsonify(
        {
            "profile": {
                "id": profile.id,
                "user_id": user_id,
                "name": profile.name,
                "email": profile.email,
                "phone": profile.phone,
                "agency": profile.agency,
                "specialty": profile.specialty,
                "bio": profile.bio,
                "rating": profile.rating,
                "tier": profile.feature_flags.get("tier", "BASIC"),
                "listings_total": total_listings,
                "listings_active": active_listings,
            }
        }
    )


@agent_bp.route("/me", methods=["PUT"])
@agent_role_required
def update_my_profile():
    """Update the authenticated agent's profile details."""

    user_id = get_jwt_identity()
    user = safe_get(User, user_id)

    if not user.agent_profile:
        return (
            jsonify(
                {
                    "message": "Agent profile not found. Please create via POST /api/agents/me/setup first."
                }
            ),
            404,
        )

    profile = user.agent_profile
    data = request.get_json() or {}

    try:
        validated_data = agent_profile_schema.load(data, partial=True)
    except ValidationError as err:
        return jsonify({"message": "Invalid input", "errors": err.messages}), 400

    if "name" in validated_data:
        profile.name = validated_data.pop("name")
        profile.slug = slugify(profile.name)

    for field, value in validated_data.items():
        setattr(profile, field, value)

    db.session.commit()
    return jsonify({"message": "Agent profile updated successfully"}), 200


@agent_bp.route("/me/setup", methods=["POST"])
@agent_role_required
def setup_my_profile():
    """Endpoint for initial agent profile creation (only if one doesn't exist)."""

    user_id = get_jwt_identity()
    user = safe_get(User, user_id)

    if user.agent_profile:
        return jsonify({"message": "Agent profile already exists."}), 409

    data = request.get_json() or {}
    try:
        validated_data = agent_profile_schema.load(data)
    except ValidationError as err:
        return jsonify({"message": "Invalid input", "errors": err.messages}), 400

    name = validated_data.pop("name")
    new_profile = AgentProfile(
        user_id=user.id,
        name=name,
        slug=slugify(name),
        **validated_data,
    )
    db.session.add(new_profile)

    user.agent_profile = new_profile
    db.session.commit()

    return (
        jsonify({"message": "Agent profile created successfully", "profile_id": new_profile.id}),
        201,
    )


@agent_bp.route("", methods=["GET"])
def list_agents():
    """List all agents with a public profile and a role of AGENT or BROKER."""

    agents = (
        db.session.query(AgentProfile)
        .join(User, AgentProfile.user_id == User.id)
        .filter(or_(User.role == "AGENT", User.role == "BROKER", User.role == "ADMIN", User.role == "LANDLORD"))
        .all()
    )

    return jsonify(
        {
            "count": len(agents),
            "results": [
                {
                    "id": a.id,
                    "name": a.name,
                    "slug": a.slug,
                    "agency": a.agency,
                    "location": a.location,
                    "specialty": a.specialty,
                    "rating": a.rating,
                    "photo_url": a.photo_url,
                }
                for a in agents
            ],
        }
    )


@agent_bp.route("", methods=["POST"])
@jwt_required()
def create_agent_profile():
    """Create a lightweight agent profile entry (legacy support for admin tools)."""

    user_id = get_jwt_identity()
    user = safe_get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    payload = request.get_json() or {}
    if "name" not in payload:
        return jsonify({"message": "Missing name"}), 400

    try:
        validated = agent_profile_schema.load(payload, partial=True)
    except ValidationError as err:
        return jsonify({"message": "Invalid input", "errors": err.messages}), 400

    name = validated.pop("name", payload.get("name"))
    profile = AgentProfile(
        user_id=user.id if user.role in ["AGENT", "BROKER", "ADMIN", "LANDLORD"] else None,
        name=name,
        slug=slugify(name),
        **validated,
    )

    db.session.add(profile)
    db.session.commit()

    if profile.user_id and not user.agent_profile:
        user.agent_profile = profile
        db.session.commit()

    return jsonify({"id": profile.id}), 201


@agent_bp.route("/<string:agent_slug>", methods=["GET"])
def get_public_agent_profile(agent_slug):
    """Retrieve a single agent's public profile page by slug."""

    profile = AgentProfile.query.filter_by(slug=agent_slug).first_or_404()
    user = profile.user
    if not user or user.role not in ["AGENT", "BROKER", "ADMIN", "LANDLORD"]:
        return jsonify({"message": "Agent profile not authorized for public viewing."}), 404

    agent_properties = Property.query.filter_by(user_id=user.id, status="active").all()

    return jsonify(
        {
            "id": profile.id,
            "name": profile.name,
            "bio": profile.bio,
            "phone": profile.phone,
            "email": profile.email,
            "agency": profile.agency,
            "specialty": profile.specialty,
            "location": profile.location,
            "rating": profile.rating,
            "transaction_history": profile.transaction_history,
            "listings": [
                {
                    "id": p.id,
                    "title": p.title,
                    "location": p.location,
                    "price": p.price if p.purpose == "SALE" else p.monthly_rent,
                    "purpose": p.purpose,
                }
                for p in agent_properties
            ],
        }
    )


@agency_bp.route("/api/analytics", methods=["GET"])
@jwt_required()
def get_agency_analytics():
    """Return simple analytics data for the authenticated agent dashboard."""

    user_id = get_jwt_identity()
    user = safe_get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    total_properties = Property.query.count()
    active_properties = Property.query.filter_by(status="active").count()
    pending_properties = Property.query.filter_by(status="pending").count()

    return jsonify(
        {
            "total_properties": total_properties,
            "active_properties": active_properties,
            "pending_properties": pending_properties,
        }
    )


@agency_bp.route("/api/requests", methods=["GET"])
@jwt_required()
def get_evaluation_requests():
    """Return evaluation requests for the authenticated agent."""

    user_id = get_jwt_identity()
    user = safe_get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    requests = (
        EvaluationRequest.query.order_by(EvaluationRequest.created_at.desc())
        .limit(25)
        .all()
    )

    return jsonify(
        {
            "count": len(requests),
            "results": [
                {
                    "id": r.id,
                    "location": r.location,
                    "property_type": r.property_type,
                    "estimated_value": r.estimated_value,
                }
                for r in requests
            ],
        }
    )


@agency_bp.route("/api/agency/profile", methods=["POST"])
@jwt_required()
def update_agency_profile():
    """Allow agents to update their profile name and contact details."""

    user_id = get_jwt_identity()
    user = safe_get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json() or {}

    profile = user.agent_profile
    if not profile:
        default_name = data.get("name") or user.name or "Agent"
        profile = AgentProfile(name=default_name, slug=slugify(default_name), user_id=user.id)
        db.session.add(profile)
        user.agent_profile = profile

    if "name" in data:
        user.name = data["name"]
        profile.name = data["name"]
        profile.slug = slugify(data["name"])

    for field in ["email", "phone", "agency", "specialty", "bio"]:
        if field in data:
            setattr(profile, field, data[field])

    db.session.commit()
    return jsonify({"message": "Profile updated"})


@agency_bp.route("/api/agents/add", methods=["POST"])
@jwt_required()
def add_agency_teammate():
    """Create a lightweight agent contact record for collaboration tools."""

    data = request.get_json() or {}
    if "name" not in data:
        return jsonify({"message": "Missing name"}), 400

    teammate = AgentProfile(
        name=data["name"],
        slug=slugify(data["name"]),
        email=data.get("email"),
        phone=data.get("phone"),
        agency=data.get("agency"),
    )
    db.session.add(teammate)
    db.session.commit()

    return jsonify({"id": teammate.id}), 201


@agency_bp.route("/api/market-snapshot", methods=["GET"])
@jwt_required(optional=True)
def get_market_snapshot():
    """Return a simplified market snapshot used on dashboards."""

    total_properties = Property.query.count()
    for_sale = Property.query.filter_by(purpose="SALE").count()
    for_rent = Property.query.filter_by(purpose="RENT").count()

    latest = (
        Property.query.filter(Property.status == "active")
        .order_by(Property.created_at.desc())
        .limit(3)
        .all()
    )

    return jsonify(
        {
            "total_properties": total_properties,
            "for_sale": for_sale,
            "for_rent": for_rent,
            "latest": [
                {
                    "id": p.id,
                    "title": p.title,
                    "location": p.location,
                    "price": p.price if p.purpose == "SALE" else p.monthly_rent,
                }
                for p in latest
            ],
        }
    )
