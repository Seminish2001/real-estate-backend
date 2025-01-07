from flask import Flask, jsonify, request
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

# Initialize database
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return "Welcome to Your Real Estate Platform!"

@app.route('/properties', methods=['GET'])
def get_properties():
    properties = Property.query.all()
    result = [
        {
            "id": property.id,
            "title": property.title,
            "price": property.price,
            "location": property.location,
            "type": property.type,
            "bedrooms": property.bedrooms,
            "size": property.size
        }
        for property in properties
    ]
    return jsonify(result)

@app.route('/properties', methods=['POST'])
def add_property():
    data = request.json
    new_property = Property(
        title=data['title'],
        price=data['price'],
        location=data['location'],
        type=data['type'],
        bedrooms=data['bedrooms'],
        size=data['size']
    )
    db.session.add(new_property)
    db.session.commit()
    return jsonify({"message": "Property added successfully!"}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
