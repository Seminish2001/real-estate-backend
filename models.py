import re
from datetime import datetime
from marshmallow import Schema, fields, ValidationError, pre_load

from extensions import db, bcrypt


def slugify(text: str) -> str:
    """Return a URL-friendly slug for the given text."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def safe_get(model, identity):
    """Retrieve a model instance by primary key using SQLAlchemy 2.x APIs."""

    if identity is None:
        return None

    try:
        lookup_id = int(identity)
    except (TypeError, ValueError):
        return None

    return db.session.get(model, lookup_id)


# --- Core Models ---

# UPDATED: User Model with Granular Roles and Agent/Broker Linkage
class User(db.Model):
    """Application user with authentication credentials and defined role."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
    # REQUIRED CHANGE: New definitive 'role' field
    # Options: 'USER' (Buyer/Renter), 'AGENT', 'BROKER', 'ADMIN'
    role = db.Column(db.String(20), default='USER', nullable=False) 
    
    # Link to a dedicated agent profile if the user is an AGENT or BROKER
    # NEW: Fields for personalization and lead routing
    lead_score = db.Column(db.Integer, default=0)
    preferences = db.Column(db.JSON, default={})

    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

    # Relationships
    agent_profile = db.relationship(
        'AgentProfile',
        uselist=False,
        primaryjoin='User.id == AgentProfile.user_id',
        foreign_keys='AgentProfile.user_id',
        backref=db.backref('user', uselist=False),
    )

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)


# UPDATED: Renamed from 'Agent' to 'AgentProfile'
class AgentProfile(db.Model):
    """Dedicated profile for agents and brokers, linked to a User."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, index=True)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    agency = db.Column(db.String(100))
    specialty = db.Column(db.String(100))
    
    # NEW: Advanced fields for monetization and performance
    rating = db.Column(db.Float, default=0.0)
    transaction_history = db.Column(db.Integer, default=0)
    feature_flags = db.Column(db.JSON, default={'tier': 'BASIC'}) # For billing/tiering logic
    
    languages = db.Column(db.String(200))
    location = db.Column(db.String(100))
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


# UPDATED: Property Model with Tiered Logic and AVM/3D Tour fields
class Property(db.Model):
    """Real estate listing with advanced logic fields."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, index=True)
    location = db.Column(db.String(100), nullable=False)
    
    # REQUIRED CHANGE: Tiered Transaction Logic
    purpose = db.Column(db.String(20), nullable=False)  # 'SALE' or 'RENT'
    sale_method = db.Column(db.String(20), default='STANDARD') # 'STANDARD' or 'AUCTION'
    
    # Financial Fields: Price is for SALE, Monthly_Rent for RENT
    price = db.Column(db.Integer, nullable=True)        
    monthly_rent = db.Column(db.Integer, nullable=True) 
    
    property_type = db.Column(db.String(50), nullable=False)
    beds = db.Column(db.Integer, nullable=False)
    baths = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Integer, nullable=False)
    
    # NEW: Advanced Fields
    zestimate_value = db.Column(db.String(100))        
    virtual_tour_url = db.Column(db.String(255))        
    image_url = db.Column(db.String(200)) # Primary thumbnail URL
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    
    # NEW: Default to 'pending' for admin approval
    status = db.Column(db.String(20), default="pending") 
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


# NEW: PropertyImage Model (for multiple images and Image Pipeline data)
class PropertyImage(db.Model):
    """Stores multiple images per property and their processing status."""
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    perceptual_hash = db.Column(db.String(64)) # For duplicate detection
    
    property = db.relationship('Property', backref=db.backref('images', lazy=True))


# NEW: Models for In-App Messaging
class ChatSession(db.Model):
    """Represents a 1-to-1 conversation between a User and an Agent."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Agent is also a User
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=True)
    
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_message_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Message(db.Model):
    """Individual message within a chat session."""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    session = db.relationship('ChatSession', backref=db.backref('messages', lazy=True))

class Appointment(db.Model):
    """Scheduling requests made within a chat session."""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    
    status = db.Column(db.String(20), default='pending') # pending, confirmed, cancelled
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


# --- Existing Models with Minor Updates ---

class EvaluationRequest(db.Model):
    """Request submitted to estimate a property's value."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    location = db.Column(db.String(100), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    area = db.Column(db.Integer, nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    estimated_value = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class AlertPreference(db.Model):
    """Saved search alert settings for a user."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    min_price = db.Column(db.Integer, nullable=False)
    max_price = db.Column(db.Integer, nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class Favorite(db.Model):
    """Mapping of users to properties they like."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class Offer(db.Model):
    """Bid made by a user on a property."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


# --- Schemas ---

class PropertySchema(Schema):
    title = fields.Str(required=True)
    location = fields.Str(required=True)
    
    # UPDATED fields
    purpose = fields.Str(required=True) 
    sale_method = fields.Str(load_default="STANDARD")
    price = fields.Integer(load_default=None)         
    monthly_rent = fields.Integer(load_default=None)  
    virtual_tour_url = fields.Str(load_default=None)
    
    property_type = fields.Str(required=True, data_key="type")
    beds = fields.Integer(required=True)
    baths = fields.Integer(required=True)
    size = fields.Integer(required=True)
    lat = fields.Float(load_default=0)
    lng = fields.Float(load_default=0)

    @pre_load
    def normalize_fields(self, data, **kwargs):
        if "bathrooms" in data and "baths" not in data:
            data["baths"] = data["bathrooms"]
        if "purpose" in data:
            purpose_value = data["purpose"].upper()
            if purpose_value in ["BUY", "SELL"]:
                purpose_value = "SALE"
            elif purpose_value in ["RENT", "LEASE"]:
                purpose_value = "RENT"
            data["purpose"] = purpose_value
        return data


property_schema = PropertySchema()


class AgentProfileSchema(Schema):
    name = fields.Str(required=True)
    email = fields.Email(load_default=None)
    phone = fields.Str(load_default=None)
    agency = fields.Str(load_default=None)
    specialty = fields.Str(load_default=None)
    languages = fields.Str(load_default=None)
    location = fields.Str(load_default=None)
    bio = fields.Str(load_default=None)
    photo_url = fields.Str(load_default=None)

agent_profile_schema = AgentProfileSchema()
