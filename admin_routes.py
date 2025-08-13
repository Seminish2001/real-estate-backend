from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps

# These will be populated by the main application at import time
db = None
User = None
Property = None
EvaluationRequest = None
Agent = None
slugify = None


def admin_required(fn):
    """Decorator ensuring the requester is an authenticated admin."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")


# --- User CRUD ---
@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    users = User.query.all()
    return jsonify([
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "user_type": u.user_type,
            "is_admin": u.is_admin,
        }
        for u in users
    ])


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_required
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "user_type": user.user_type,
            "is_admin": user.is_admin,
        }
    )


@admin_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    data = request.get_json() or {}
    if not all(k in data for k in ("name", "email", "password", "user_type")):
        return jsonify({"message": "Missing fields"}), 400
    new_user = User(
        name=data["name"],
        email=data["email"],
        user_type=data["user_type"],
        is_admin=data.get("is_admin", False),
        password="",
    )
    new_user.set_password(data["password"])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"id": new_user.id}), 201


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    for field in ["name", "email", "user_type", "is_admin"]:
        if field in data:
            setattr(user, field, data[field])
    if "password" in data:
        user.set_password(data["password"])
    db.session.commit()
    return jsonify({"message": "User updated"})


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"})


# --- Property CRUD ---
@admin_bp.route("/properties", methods=["GET"])
@admin_required
def list_properties():
    properties = Property.query.all()
    return jsonify([
        {
            "id": p.id,
            "title": p.title,
            "user_id": p.user_id,
            "price": p.price,
        }
        for p in properties
    ])


@admin_bp.route("/properties/<int:prop_id>", methods=["GET"])
@admin_required
def get_property(prop_id):
    prop = Property.query.get_or_404(prop_id)
    return jsonify(
        {
            "id": prop.id,
            "title": prop.title,
            "user_id": prop.user_id,
            "price": prop.price,
        }
    )


@admin_bp.route("/properties", methods=["POST"])
@admin_required
def create_property():
    data = request.get_json() or {}
    required = [
        "user_id",
        "title",
        "location",
        "purpose",
        "property_type",
        "price",
        "beds",
        "baths",
        "size",
    ]
    if not all(k in data for k in required):
        return jsonify({"message": "Missing fields"}), 400
    prop = Property(
        user_id=data["user_id"],
        title=data["title"],
        slug=slugify(data["title"]),
        location=data["location"],
        purpose=data["purpose"],
        property_type=data["property_type"],
        price=data["price"],
        beds=data["beds"],
        baths=data["baths"],
        size=data["size"],
        status=data.get("status", "active"),
    )
    db.session.add(prop)
    db.session.commit()
    return jsonify({"id": prop.id}), 201


@admin_bp.route("/properties/<int:prop_id>", methods=["PUT"])
@admin_required
def update_property(prop_id):
    prop = Property.query.get_or_404(prop_id)
    data = request.get_json() or {}
    for field in [
        "title",
        "location",
        "purpose",
        "property_type",
        "price",
        "beds",
        "baths",
        "size",
        "status",
        "user_id",
    ]:
        if field in data:
            setattr(prop, field, data[field])
    if "title" in data:
        prop.slug = slugify(data["title"])
    db.session.commit()
    return jsonify({"message": "Property updated"})


@admin_bp.route("/properties/<int:prop_id>", methods=["DELETE"])
@admin_required
def delete_property(prop_id):
    prop = Property.query.get_or_404(prop_id)
    db.session.delete(prop)
    db.session.commit()
    return jsonify({"message": "Property deleted"})


# --- Evaluation Request CRUD ---
@admin_bp.route("/evaluation-requests", methods=["GET"])
@admin_required
def list_requests():
    requests = EvaluationRequest.query.all()
    return jsonify([
        {
            "id": r.id,
            "user_id": r.user_id,
            "location": r.location,
            "property_type": r.property_type,
        }
        for r in requests
    ])


@admin_bp.route("/evaluation-requests/<int:req_id>", methods=["GET"])
@admin_required
def get_request(req_id):
    r = EvaluationRequest.query.get_or_404(req_id)
    return jsonify(
        {
            "id": r.id,
            "user_id": r.user_id,
            "location": r.location,
            "property_type": r.property_type,
            "estimated_value": r.estimated_value,
        }
    )


@admin_bp.route("/evaluation-requests", methods=["POST"])
@admin_required
def create_request():
    data = request.get_json() or {}
    required = [
        "user_id",
        "location",
        "property_type",
        "area",
        "bedrooms",
        "bathrooms",
        "condition",
    ]
    if not all(k in data for k in required):
        return jsonify({"message": "Missing fields"}), 400
    r = EvaluationRequest(
        user_id=data.get("user_id"),
        location=data["location"],
        property_type=data["property_type"],
        area=data["area"],
        bedrooms=data["bedrooms"],
        bathrooms=data["bathrooms"],
        condition=data["condition"],
        estimated_value=data.get("estimated_value"),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"id": r.id}), 201


@admin_bp.route("/evaluation-requests/<int:req_id>", methods=["PUT"])
@admin_required
def update_request(req_id):
    r = EvaluationRequest.query.get_or_404(req_id)
    data = request.get_json() or {}
    for field in [
        "user_id",
        "location",
        "property_type",
        "area",
        "bedrooms",
        "bathrooms",
        "condition",
        "estimated_value",
    ]:
        if field in data:
            setattr(r, field, data[field])
    db.session.commit()
    return jsonify({"message": "Evaluation request updated"})


@admin_bp.route("/evaluation-requests/<int:req_id>", methods=["DELETE"])
@admin_required
def delete_request(req_id):
    r = EvaluationRequest.query.get_or_404(req_id)
    db.session.delete(r)
    db.session.commit()
    return jsonify({"message": "Evaluation request deleted"})


# --- Agent CRUD ---
@admin_bp.route("/agents", methods=["GET"])
@admin_required
def list_agents():
    agents = Agent.query.all()
    return jsonify([
        {
            "id": a.id,
            "name": a.name,
            "email": a.email,
            "agency": a.agency,
        }
        for a in agents
    ])


@admin_bp.route("/agents/<int:agent_id>", methods=["GET"])
@admin_required
def get_agent(agent_id):
    a = Agent.query.get_or_404(agent_id)
    return jsonify(
        {
            "id": a.id,
            "name": a.name,
            "email": a.email,
            "agency": a.agency,
        }
    )


@admin_bp.route("/agents", methods=["POST"])
@admin_required
def create_agent():
    data = request.get_json() or {}
    if "name" not in data:
        return jsonify({"message": "Missing fields"}), 400
    a = Agent(
        name=data["name"],
        slug=slugify(data["name"]),
        email=data.get("email"),
        phone=data.get("phone"),
        agency=data.get("agency"),
        specialty=data.get("specialty"),
        languages=data.get("languages"),
        location=data.get("location"),
        bio=data.get("bio"),
        photo_url=data.get("photo_url"),
    )
    db.session.add(a)
    db.session.commit()
    return jsonify({"id": a.id}), 201


@admin_bp.route("/agents/<int:agent_id>", methods=["PUT"])
@admin_required
def update_agent(agent_id):
    a = Agent.query.get_or_404(agent_id)
    data = request.get_json() or {}
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
            setattr(a, field, data[field])
    if "name" in data:
        a.slug = slugify(data["name"])
    db.session.commit()
    return jsonify({"message": "Agent updated"})


@admin_bp.route("/agents/<int:agent_id>", methods=["DELETE"])
@admin_required
def delete_agent(agent_id):
    a = Agent.query.get_or_404(agent_id)
    db.session.delete(a)
    db.session.commit()
    return jsonify({"message": "Agent deleted"})
