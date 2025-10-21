from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps

# These will be populated by the main application at import time
# Agent is now AgentProfile
db = None
User = None
Property = None
EvaluationRequest = None
AgentProfile = None  # CHANGED: Rename Agent to AgentProfile
slugify = None


def configure_admin_blueprint(database, user_model, property_model, evaluation_model, agent_profile_model, slugify_func):
    """Bind real model classes to the admin blueprint after app initialization."""

    global db, User, Property, EvaluationRequest, AgentProfile, slugify

    db = database
    User = user_model
    Property = property_model
    EvaluationRequest = evaluation_model
    AgentProfile = agent_profile_model
    slugify = slugify_func


def _safe_get(model, identity):
    if identity is None or db is None:
        return None

    try:
        lookup_id = int(identity)
    except (TypeError, ValueError):
        return None

    return db.session.get(model, lookup_id)


def _get_or_404(model, identity):
    instance = _safe_get(model, identity)
    if not instance:
        abort(404)
    return instance


def _normalize_role(data):
    role = data.get("role")
    if role:
        return role.upper()

    user_type = data.get("user_type") or data.get("userType")
    if user_type:
        mapping = {
            "BUYER/RENTER": "USER",
            "BUYER": "USER",
            "RENTER": "USER",
            "LANDLORD": "LANDLORD",
            "AGENCY": "AGENT",
            "AGENT": "AGENT",
            "BROKER": "BROKER",
            "ADMIN": "ADMIN",
        }
        return mapping.get(user_type.strip().upper(), "USER")

    return "USER"


def admin_required(fn):
    """Decorator ensuring the requester is an authenticated admin."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = _safe_get(User, user_id)
        # REQUIRED CHANGE: Check for 'ADMIN' role instead of just is_admin flag
        if not user or (user.role != 'ADMIN' and not getattr(user, 'is_admin', False)):
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
            "role": u.role, # CHANGED: user_type -> role
            "is_active": u.is_active, # Added for completeness
            "is_admin": getattr(u, "is_admin", False),
        }
        for u in users
    ])


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_required
def get_user(user_id):
    user = _get_or_404(User, user_id)
    return jsonify(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role, # CHANGED: user_type -> role
            "is_active": user.is_active,
            "is_admin": getattr(user, "is_admin", False),
        }
    )


@admin_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    data = request.get_json() or {}
    if not all(k in data for k in ("name", "email", "password")):
        return jsonify({"message": "Missing fields"}), 400

    role = _normalize_role(data)
    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered"}), 409
    new_user = User(
        name=data["name"],
        email=email,
        role=role,
        password="",
    )
    new_user.is_admin = role == 'ADMIN'
    new_user.set_password(data["password"])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"id": new_user.id}), 201


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    user = _get_or_404(User, user_id)
    data = request.get_json() or {}
    
    # REQUIRED CHANGE: Check for 'role' instead of 'user_type' and 'is_admin'
    if "name" in data:
        user.name = data["name"]
    if "email" in data:
        user.email = data["email"].strip().lower()
    if "role" in data or "user_type" in data or "userType" in data:
        user.role = _normalize_role(data)
        user.is_admin = user.role == 'ADMIN'
    if "is_active" in data:
        user.is_active = data["is_active"]
    if "is_admin" in data:
        user.is_admin = bool(data["is_admin"])

    if "password" in data:
        user.set_password(data["password"])
        
    db.session.commit()
    return jsonify({"message": "User updated"})


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    user = _get_or_404(User, user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"})


# --- Property CRUD (Mostly fine, but ensure all fields are handled) ---
@admin_bp.route("/properties", methods=["GET"])
@admin_required
def list_properties():
    # Showing all properties regardless of status is useful for Admin
    properties = Property.query.all() 
    return jsonify([
        {
            "id": p.id,
            "title": p.title,
            "user_id": p.user_id,
            "purpose": p.purpose, # Added for admin context
            "status": p.status,   # Added for admin context
            "price": p.price,
            "monthly_rent": p.monthly_rent, # NEW FIELD
        }
        for p in properties
    ])


@admin_bp.route("/properties/<int:prop_id>", methods=["GET"])
@admin_required
def get_property(prop_id):
    prop = _get_or_404(Property, prop_id)
    return jsonify(
        {
            "id": prop.id,
            "title": prop.title,
            "user_id": prop.user_id,
            "purpose": prop.purpose,
            "status": prop.status,
            "price": prop.price,
            "monthly_rent": prop.monthly_rent, # NEW FIELD
            "virtual_tour_url": prop.virtual_tour_url, # NEW FIELD
            # Add other fields as needed for the admin detail view
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
        "beds",
        "baths",
        "size",
    ]
    purpose_value = data.get("purpose", "").upper()
    if purpose_value in ('BUY', 'SELL'):
        purpose_value = 'SALE'

    # NEW: Check for price OR monthly_rent based on purpose
    if purpose_value == 'SALE' and 'price' not in data:
        return jsonify({"message": "Missing 'price' for sale property"}), 400
    if purpose_value == 'RENT' and 'monthly_rent' not in data:
        return jsonify({"message": "Missing 'monthly_rent' for rental property"}), 400

    if not all(k in data for k in required):
        return jsonify({"message": "Missing fields"}), 400

    prop = Property(
        user_id=data["user_id"],
        title=data["title"],
        slug=slugify(data["title"]),
        location=data["location"],
        purpose=purpose_value,
        property_type=data["property_type"],
        price=data.get("price"),
        monthly_rent=data.get("monthly_rent"), # NEW FIELD
        beds=data["beds"],
        baths=data["baths"],
        size=data["size"],
        status=data.get("status", "pending"), # Admin setting status is key
        sale_method=data.get("sale_method", "STANDARD"), # NEW FIELD
        virtual_tour_url=data.get("virtual_tour_url"), # NEW FIELD
    )
    db.session.add(prop)
    db.session.commit()
    return jsonify({"id": prop.id}), 201


@admin_bp.route("/properties/<int:prop_id>", methods=["PUT"])
@admin_required
def update_property(prop_id):
    prop = _get_or_404(Property, prop_id)
    data = request.get_json() or {}

    if "purpose" in data:
        purpose_value = data["purpose"].upper()
        if purpose_value in ('BUY', 'SELL'):
            data["purpose"] = 'SALE'
        else:
            data["purpose"] = purpose_value

    for field in [
        "title",
        "location",
        "purpose",
        "property_type",
        "price",
        "monthly_rent", # NEW FIELD
        "beds",
        "baths",
        "size",
        "status",
        "user_id",
        "sale_method", # NEW FIELD
        "virtual_tour_url", # NEW FIELD
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
    prop = _get_or_404(Property, prop_id)
    db.session.delete(prop)
    db.session.commit()
    return jsonify({"message": "Property deleted"})


# --- Evaluation Request CRUD (No changes needed here) ---
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
            "estimated_value": r.estimated_value, # Include value in list for admin
        }
        for r in requests
    ])


@admin_bp.route("/evaluation-requests/<int:req_id>", methods=["GET"])
@admin_required
def get_request(req_id):
    r = _get_or_404(EvaluationRequest, req_id)
    return jsonify(
        {
            "id": r.id,
            "user_id": r.user_id,
            "location": r.location,
            "property_type": r.property_type,
            "estimated_value": r.estimated_value,
            "area": r.area,
            "bedrooms": r.bedrooms,
            "bathrooms": r.bathrooms,
            "condition": r.condition,
        }
    )

@admin_bp.route("/evaluation-requests", methods=["POST"])
@admin_required
def create_request():
    data = request.get_json() or {}
    required = ["user_id", "location", "property_type", "area", "bedrooms", "bathrooms", "condition"]
    if not all(field in data for field in required):
        return jsonify({"message": "Missing fields"}), 400

    req = EvaluationRequest(
        user_id=data.get("user_id"),
        location=data["location"],
        property_type=data["property_type"],
        area=data["area"],
        bedrooms=data["bedrooms"],
        bathrooms=data["bathrooms"],
        condition=data["condition"],
        estimated_value=data.get("estimated_value"),
    )
    db.session.add(req)
    db.session.commit()
    return jsonify({"id": req.id}), 201


@admin_bp.route("/evaluation-requests/<int:req_id>", methods=["PUT"])
@admin_required
def update_request(req_id):
    req = _get_or_404(EvaluationRequest, req_id)
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
            setattr(req, field, data[field])

    db.session.commit()
    return jsonify({"message": "Evaluation request updated"})


@admin_bp.route("/evaluation-requests/<int:req_id>", methods=["DELETE"])
@admin_required
def delete_request(req_id):
    req = _get_or_404(EvaluationRequest, req_id)
    db.session.delete(req)
    db.session.commit()
    return jsonify({"message": "Evaluation request deleted"})


# --- Agent Profile CRUD (UPDATED) ---
@admin_bp.route("/agents", methods=["GET"])
@admin_required
def list_agents():
    # CHANGED: Agent -> AgentProfile
    agents = AgentProfile.query.all() 
    return jsonify([
        {
            "id": a.id,
            "name": a.name,
            "email": a.email,
            "agency": a.agency,
            "rating": a.rating, # NEW FIELD
            "tier": a.feature_flags.get('tier'), # NEW FIELD
        }
        for a in agents
    ])


@admin_bp.route("/agents/<int:agent_id>", methods=["GET"])
@admin_required
def get_agent(agent_id):
    # CHANGED: Agent -> AgentProfile
    a = _get_or_404(AgentProfile, agent_id)
    return jsonify(
        {
            "id": a.id,
            "name": a.name,
            "email": a.email,
            "agency": a.agency,
            "rating": a.rating, 
            "transaction_history": a.transaction_history, 
            "tier": a.feature_flags.get('tier'),
            "location": a.location,
            "phone": a.phone,
        }
    )


@admin_bp.route("/agents", methods=["POST"])
@admin_required
def create_agent():
    data = request.get_json() or {}
    if "name" not in data:
        return jsonify({"message": "Missing fields"}), 400
        
    # CHANGED: Agent -> AgentProfile
    a = AgentProfile( 
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
        rating=data.get("rating", 0.0), # NEW FIELD
        transaction_history=data.get("transaction_history", 0), # NEW FIELD
        feature_flags=data.get("feature_flags", {'tier': 'BASIC'}), # NEW FIELD
    )
    db.session.add(a)
    db.session.commit()
    return jsonify({"id": a.id}), 201


@admin_bp.route("/agents/<int:agent_id>", methods=["PUT"])
@admin_required
def update_agent(agent_id):
    # CHANGED: Agent -> AgentProfile
    a = _get_or_404(AgentProfile, agent_id)
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
        "rating", # NEW FIELD
        "transaction_history", # NEW FIELD
    ]:
        if field in data:
            setattr(a, field, data[field])
    
    if "feature_flags" in data:
        a.feature_flags = data["feature_flags"] # NEW FIELD
        
    if "name" in data:
        a.slug = slugify(data["name"])
        
    db.session.commit()
    return jsonify({"message": "Agent updated"})


@admin_bp.route("/agents/<int:agent_id>", methods=["DELETE"])
@admin_required
def delete_agent(agent_id):
    # CHANGED: Agent -> AgentProfile
    a = _get_or_404(AgentProfile, agent_id)
    db.session.delete(a)
    db.session.commit()
    return jsonify({"message": "Agent deleted"})
