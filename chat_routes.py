from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db 
from models import User, ChatSession, Message, Property
from sqlalchemy import or_

# Create a Blueprint instance
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# --- CHAT SESSION ENDPOINTS ---

@chat_bp.route("/sessions", methods=["GET"])
@jwt_required()
def list_sessions():
    """Retrieve all chat sessions relevant to the authenticated user (as user or agent)."""
    user_id = get_jwt_identity()
    
    sessions = ChatSession.query.filter(
        or_(
            ChatSession.user_id == user_id,
            ChatSession.agent_id == user_id
        )
    ).order_by(ChatSession.last_message_at.desc()).all()
    
    # Fetch details for the other party and property
    session_list = []
    for session in sessions:
        # Determine the "other party" (the person not the current user)
        if session.user_id == user_id:
            other_party = User.query.get(session.agent_id)
            is_agent = False
        else:
            other_party = User.query.get(session.user_id)
            is_agent = True
            
        # Get the latest message (optimized query could be used here)
        latest_message = Message.query.filter_by(session_id=session.id).order_by(Message.timestamp.desc()).first()
        
        session_list.append({
            "session_id": session.id,
            "is_agent_view": is_agent,
            "status": session.status,
            "other_party": {
                "id": other_party.id,
                "name": other_party.name,
                "role": other_party.role,
            },
            "property_id": session.property_id,
            "last_message": latest_message.content if latest_message else None,
            "last_message_at": latest_message.timestamp.isoformat() if latest_message else session.created_at.isoformat(),
        })

    return jsonify(session_list)


@chat_bp.route("/start", methods=["POST"])
@jwt_required()
def start_session():
    """Initiate a new chat session between a USER and an AGENT/BROKER."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    # Required: ID of the agent to talk to, and optionally the property
    agent_id = data.get("agent_id")
    property_id = data.get("property_id")
    
    if not agent_id:
        return jsonify({"message": "Missing agent_id to start chat"}), 400

    # 1. Validate Agent
    agent_user = User.query.get(agent_id)
    if not agent_user or agent_user.role not in ['AGENT', 'BROKER', 'ADMIN']:
        return jsonify({"message": "Invalid agent ID or user not an authorized agent"}), 404

    # 2. Check for existing session (prevent duplicates)
    existing_session = ChatSession.query.filter(
        ChatSession.user_id == user_id,
        ChatSession.agent_id == agent_id,
        ChatSession.property_id == property_id # Optionally check for property context
    ).first()
    
    if existing_session:
        return jsonify({"message": "Session already exists", "session_id": existing_session.id}), 200

    # 3. Create new session
    new_session = ChatSession(
        user_id=user_id,
        agent_id=agent_id,
        property_id=property_id
    )
    db.session.add(new_session)
    db.session.commit()
    
    return jsonify({"message": "Chat session created", "session_id": new_session.id}), 201


# --- MESSAGE RETRIEVAL ENDPOINTS ---

@chat_bp.route("/messages/<int:session_id>", methods=["GET"])
@jwt_required()
def get_messages(session_id):
    """Retrieve the message history for a specific chat session."""
    user_id = get_jwt_identity()
    
    session = ChatSession.query.get_or_404(session_id)
    
    # Authorization: User must be either the user or the agent in the session
    if session.user_id != user_id and session.agent_id != user_id:
        return jsonify({"message": "Forbidden: You are not a participant in this session"}), 403

    # Retrieve all messages for the session, ordered by timestamp
    messages = Message.query.filter_by(session_id=session_id).order_by(Message.timestamp).all()
    
    message_list = [{
        "id": m.id,
        "sender_id": m.sender_id,
        "content": m.content,
        "timestamp": m.timestamp.isoformat(),
        "is_read": m.is_read
    } for m in messages]
    
    return jsonify({
        "session_id": session_id,
        "property_id": session.property_id,
        "messages": message_list
    })
