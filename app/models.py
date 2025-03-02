from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)  # "Private Owner", "Real Estate Agency", "Buyer/Renter"

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

class EvaluationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Optional for logged-in users
    location = db.Column(db.String(100), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)  # e.g., apartment, villa
    area = db.Column(db.Integer, nullable=False)  # in square meters
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(50), nullable=False)  # e.g., new, good
    estimated_value = db.Column(db.String(100))  # e.g., "€300,000 - €350,000"
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class AlertPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Optional for logged-in users
    email = db.Column(db.String(100), nullable=False)  # For notifications
    purpose = db.Column(db.String(20), nullable=False)  # buy or rent
    location = db.Column(db.String(100), nullable=False)
    min_price = db.Column(db.Integer, nullable=False)
    max_price = db.Column(db.Integer, nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, instant
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
