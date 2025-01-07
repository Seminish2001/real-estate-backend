from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///properties.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Property model
class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)  # New field for image URLs

# Initialize database
with app.app_context():
    db.create_all()

# Serve the frontend (index.html) at the root URL
@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')

# Fetch all properties with filters
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
            "image_url": property.image_url  # Include image URL in the response
        }
        for property in properties
    ]
    return jsonify(result)

# Add a new property
@app.route('/properties', methods=['POST'])
def add_property():
    data = request.json
    new_property = Property(
        title=data['title'],
        price=data['price'],
        location=data['location'],
        type=data['type'],
        bedrooms=data['bedrooms'],
        size=data['size'],
        image_url=data.get('image_url')  # Accept image URL (optional)
    )
    db.session.add(new_property)
    db.session.commit()
    return jsonify({"message": "Property added successfully!"}), 201

# Delete a property
@app.route('/properties/<int:property_id>', methods=['DELETE'])
def delete_property(property_id):
    property_to_delete = Property.query.get(property_id)
    if not property_to_delete:
        return jsonify({"message": "Property not found!"}), 404
    db.session.delete(property_to_delete)
    db.session.commit()
    return jsonify({"message": "Property deleted successfully!"}), 200

# Update a property
@app.route('/properties/<int:property_id>', methods=['PUT'])
def update_property(property_id):
    property_to_update = Property.query.get(property_id)
    if not property_to_update:
        return jsonify({"message": "Property not found!"}), 404
    data = request.json
    property_to_update.title = data['title']
    property_to_update.price = data['price']
    property_to_update.location = data['location']
    property_to_update.type = data['type']
    property_to_update.bedrooms = data['bedrooms']
    property_to_update.size = data['size']
    property_to_update.image_url = data.get('image_url', property_to_update.image_url)  # Update image URL if provided
    db.session.commit()
    return jsonify({"message": "Property updated successfully!"}), 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
