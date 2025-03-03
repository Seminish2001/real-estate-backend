from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)  # "Landlord", "Agency", "Buyer/Renter"
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # "buy" or "rent"
    property_type = db.Column(db.String(50), nullable=False)  # "apartment", "villa", etc.
    price = db.Column(db.Integer, nullable=False)
    beds = db.Column(db.Integer, nullable=False)
    baths = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Integer, nullable=False)  # in sqft
    image_url = db.Column(db.String(200))  # Cloudinary URL
    lat = db.Column(db.Float)  # For map
    lng = db.Column(db.Float)  # For map
    status = db.Column(db.String(20), default="active")  # "active", "sold"
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class EvaluationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    location = db.Column(db.String(100), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    area = db.Column(db.Integer, nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    estimated_value = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class AlertPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    min_price = db.Column(db.Integer, nullable=False)
    max_price = db.Column(db.Integer, nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="pending")  # "pending", "accepted", "rejected"
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
