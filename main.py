from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///properties.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_secret_key_here'  # Replace with a secure key
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Property model
class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Initialize the database
with app.app_context():
    db.create_all()

# Serve the frontend
@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')

# Register a new user
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"message": "Invalid data!"}), 400

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = User(username=data['username'], password=hashed_password)
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except Exception:
        return jsonify({"message": "Username already exists!"}), 409

# User login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"message": "Invalid data!"}), 400

    user = User.query.filter_by(username=data['username']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify({"access_token": access_token}), 200
    return jsonify({"message": "Invalid credentials!"}), 401

# Add a new property (authenticated)
@app.route('/properties', methods=['POST'])
@jwt_required()
def add_property():
    current_user = get_jwt_identity()
    data = request.json
    if not data or 'title' not in data or 'price' not in data:
        return jsonify({"message": "Invalid data!"}), 400

    new_property = Property(
        title=data['title'],
        price=data['price'],
        location=data['location'],
        type=data['type'],
        bedrooms=data['bedrooms'],
        size=data['size'],
        image_url=data.get('image_url'),
        owner_id=current_user
    )
    db.session.add(new_property)
    db.session.commit()
    return jsonify({"message": "Property added successfully!"}), 201

# Fetch all properties with optional filters
@app.route('/properties', methods=['GET'])
def get_properties():
    location = request.args.get('location')
    type_ = request.args.get('type')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    query = Property.query
    if location:
        query = query.filter(Property.location.ilike(f'%{location}%'))
    if type_:
        query = query.filter(Property.type.ilike(f'%{type_}%'))
    if min_price is not None:
        query = query.filter(Property.price >= min_price)
    if max_price is not None:
        query = query.filter(Property.price <= max_price)

    properties = query.all()
    result = [
        {
            "id": property.id,
            "title": property.title,
            "price": property.price,
            "location": property.location,
            "type": property.type,
            "bedrooms": property.bedrooms,
            "size": property.size,
            "image_url": property.image_url,
            "owner_id": property.owner_id
        }
        for property in properties
    ]
    return jsonify(result)

# Update a property (authenticated)
@app.route('/properties/<int:property_id>', methods=['PUT'])
@jwt_required()
def update_property(property_id):
    current_user = get_jwt_identity()
    property_to_update = Property.query.get(property_id)
    if not property_to_update:
        return jsonify({"message": "Property not found!"}), 404
    if property_to_update.owner_id != current_user:
        return jsonify({"message": "Not authorized to update this property!"}), 403

    data = request.json
    property_to_update.title = data['title']
    property_to_update.price = data['price']
    property_to_update.location = data['location']
    property_to_update.type = data['type']
    property_to_update.bedrooms = data['bedrooms']
    property_to_update.size = data['size']
    property_to_update.image_url = data.get('image_url', property_to_update.image_url)
    db.session.commit()
    return jsonify({"message": "Property updated successfully!"}), 200

# Delete a property (authenticated)
@app.route('/properties/<int:property_id>', methods=['DELETE'])
@jwt_required()
def delete_property(property_id):
    current_user = get_jwt_identity()
    property_to_delete = Property.query.get(property_id)
    if not property_to_delete:
        return jsonify({"message": "Property not found!"}), 404
    if property_to_delete.owner_id != current_user:
        return jsonify({"message": "Not authorized to delete this property!"}), 403

    db.session.delete(property_to_delete)
    db.session.commit()
    return jsonify({"message": "Property deleted successfully!"}), 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
