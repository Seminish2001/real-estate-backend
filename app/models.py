from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)  # e.g., 'agency', 'landlord', 'agent', 'buyer-renter'
    properties = db.relationship('Property', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'user_type': self.user_type
        }

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    beds = db.Column(db.Integer, nullable=False)
    baths = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Integer, nullable=False)  # in square feet
    image_url = db.Column(db.String(200))
    purpose = db.Column(db.String(10), nullable=False)  # 'buy' or 'rent'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'price': self.price,
            'location': self.location,
            'beds': self.beds,
            'baths': self.baths,
            'size': self.size,
            'image_url': self.image_url,
            'purpose': self.purpose,
            'user_id': self.user_id
        }

class Agent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    agency = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(50))  # e.g., 'buying', 'selling', 'renting'
    sales = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    reviews = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(200))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'agency': self.agency,
            'location': self.location,
            'specialty': self.specialty,
            'sales': self.sales,
            'rating': self.rating,
            'reviews': self.reviews,
            'image_url': self.image_url
        }
