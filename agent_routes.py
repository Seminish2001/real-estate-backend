from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
import logging
from app import db # Import the db instance from the core app
from models import User, AgentProfile, agent_profile_schema, Property, slugify 
from sqlalchemy import or_

# Create a Blueprint instance
agent_bp = Blueprint('agents', __name__, url_prefix='/api/agents')

# Helper function to check if the user is an AGENT or BROKER
def agent_role_required(fn):
    """Decorator ensuring the requester is an authenticated AGENT or BROKER."""
    @jwt_required()
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role not in ['AGENT', 'BROKER', 'ADMIN']:
            abort(403, description="Forbidden: Must be an authorized agent or broker.")
        return fn(*args, **kwargs)
    return wrapper

from functools import wraps # Import wraps for the decorator

# --- AGENT PROFILE MANAGEMENT (Self-Service) ---

@agent_bp.route("/me", methods=["GET"])
@agent_role_required
def get_my_profile():
    """Retrieve the authenticated agent's profile and key metrics."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Ensure a profile exists for the user's role
    if not user.agent_profile:
        return jsonify({"message": "Agent profile not found. Complete setup."}), 404
    
    profile = user.agent_profile
    
    # Calculate simple metrics
    total_listings = Property.query.filter_by(user_id=user_id).count()
    active_listings = Property.query.filter_by(user_id=user_id, status='active').count()

    return jsonify({
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
            "tier": profile.feature_flags.get('tier', 'BASIC'),
            "listings_total": total_listings,
            "listings_active": active_listings,
        }
    })


@agent_bp.route("/me", methods=["PUT"])
@agent_role_required
def update_my_profile():
    """Update the authenticated agent's profile details."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Check if a profile exists and create one if not (first-time setup)
    if not user.agent_profile:
        return jsonify({"message": "Agent profile not found. Please create via POST /api/agents/me/setup first."}), 404
        
    profile = user.agent_profile
    data = request.get_json() or {}

    try:
        # We only validate the fields that are present in the request
        validated_data = agent_profile_schema.load(data, partial=True)
        
        for field, value in validated_data.items():
            setattr(profile, field, value)
            
        if "name" in validated_data:
            profile.slug = slugify(validated_data["name"])

        db.session.commit()
        return jsonify({"message": "Agent profile updated successfully"}), 200

    except ValidationError as err:
        return jsonify({"message": "Invalid input", "errors": err.messages}), 400
    except Exception as e:
        db.session.rollback()
        logging.error(f"Agent profile update error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@agent_bp.route("/me/setup", methods=["POST"])
@agent_role_required
def setup_my_profile():
    """Endpoint for initial agent profile creation (only if one doesn't exist)."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if user.agent_profile:
        return jsonify({"message": "Agent profile already exists."}), 409
        
    data = request.get_json() or {}
    try:
        # Must pass full validation for initial setup
        validated_data = agent_profile_schema.load(data) 
        
        new_profile = AgentProfile(
            name=validated_data["name"],
            slug=slugify(validated_data["name"]),
            **validated_data
        )
        db.session.add(new_profile)
        
        # Link the profile back to the User
        user.agent_profile = new_profile
        user.agent_profile_id = new_profile.id
        
        db.session.commit()
        return jsonify({"message": "Agent profile created successfully", "profile_id": new_profile.id}), 201

    except ValidationError as err:
        return jsonify({"message": "Invalid input", "errors": err.messages}), 400
    except Exception as e:
        db.session.rollback()
        logging.error(f"Agent profile setup error: {str(e)}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


# --- PUBLIC AGENT LISTING AND SEARCH ---

@agent_bp.route("", methods=["GET"])
def list_agents():
    """List all agents with a public profile and a role of AGENT or BROKER."""
    # Find users who have a linked AgentProfile and a suitable role
    agents = db.session.query(AgentProfile).join(User).filter(
        or_(User.role == 'AGENT', User.role == 'BROKER')
    ).all()

    return jsonify([{
        "id": a.id,
        "name": a.name,
        "slug": a.slug,
        "agency": a.agency,
        "location": a.location,
        "specialty": a.specialty,
        "rating": a.rating,
        "photo_url": a.photo_url
    } for a in agents])


@agent_bp.route("/<string:agent_slug>", methods=["GET"])
def get_public_agent_profile(agent_slug):
    """Retrieve a single agent's public profile page by slug."""
    profile = AgentProfile.query.filter_by(slug=agent_slug).first_or_404()
    
    # Ensure the linked user has a public-facing role
    user = User.query.get(profile.user_id) if profile.user_id else None
    if not user or user.role not in ['AGENT', 'BROKER', 'ADMIN']:
        return jsonify({"message": "Agent profile not authorized for public viewing."}), 404
        
    # Get all active properties listed by this agent
    agent_properties = Property.query.filter_by(user_id=user.id, status='active').all()

    return jsonify({
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
        "listings": [{
            "id": p.id,
            "title": p.title,
            "location": p.location,
            "price": p.price if p.purpose == 'SALE' else p.monthly_rent,
            "purpose": p.purpose
        } for p in agent_properties]
    })
