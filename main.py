from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///properties.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_secret_key_here'  # Replace with a secure key
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Cloudinary Configuration
cloudinary.config(
    cloud_name="dxearodvf",
    api_key="292532466535494",
    api_secret="7C58WhO-JWQsAG8Lze9C5hMfkD4",
    secure=True
)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)  # "Private Owner" or "Real Estate Agency"
    phone = db.Column(db.String(15), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    agency_name = db.Column(db.String(100), nullable=True)
    license_number = db.Column(db.String(50), nullable=True)

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

# Routes to serve templates
@app.route('/')
def serve_homepage():
    homepage_image_url = "https://res.cloudinary.com/dxearodvf/image/upload/v1736524504/jll-future-vision-real-estate-social-1200x628_iiuwf9.jpg"
    return render_template('index.html', homepage_image_url=homepage_image_url)

@app.route('/login')
def serve_login():
    return render_template('login.html')

@app.route('/signup')
def serve_signup():
    return render_template('signup.html')

@app.route('/add-property')
def serve_add_property():
    return render_template('add-property.html')

@app.route('/dashboard')
def serve_dashboard():
    return render_template('dashboard.html')

@app.route('/edit-property/<int:property_id>')
def serve_edit_property(property_id):
    return render_template('edit-property.html', property_id=property_id)

@app.route('/property/<int:property_id>')
def serve_property_details(property_id):
    return render_template('property-details.html', property_id=property_id)

# Register a new user
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    required_fields = ['name', 'email', 'password', 'user_type']

    if not all(field in data and data[field] for field in required_fields):
        return jsonify({"message": "Missing required fields!"}), 400

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = User(
        name=data['name'],
        email=data['email'],
        password=hashed_password,
        user_type=data['user_type'],
        phone=data.get('phone'),
        address=data.get('address'),
        agency_name=data.get('agency_name'),
        license_number=data.get('license_number')
    )
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except Exception:
        return jsonify({"message": "Email already exists!"}), 409

# User login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"message": "Invalid data!"}), 400

    user = User.query.filter_by(email=data['email']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify({"access_token": access_token}), 200
    return jsonify({"message": "Invalid credentials!"}), 401

# Add a new property (authenticated)
@app.route('/properties', methods=['POST'])
@jwt_required()
def add_property():
    current_user = get_jwt_identity()

    # Handle file upload
    image_file = request.files.get('image')
    if not image_file:
        return jsonify({"message": "Image is required!"}), 400

    try:
        upload_result = cloudinary.uploader.upload(image_file)
        image_url = upload_result.get('secure_url')
    except Exception as e:
        return jsonify({"message": f"Image upload failed: {str(e)}"}), 500

    # Save property details
    data = request.form
    new_property = Property(
        title=data['title'],
        price=float(data['price']),
        location=data['location'],
        type=data['type'],
        bedrooms=int(data['bedrooms']),
        size=float(data['size']),
        image_url=image_url,
        owner_id=current_user
    )
    db.session.add(new_property)
    db.session.commit()
    return jsonify({"message": "Property added successfully!"}), 201

# Fetch properties
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
            "size": property.size,
            "image_url": property.image_url
        }
        for property in properties
    ]
    return jsonify(result)

# Fetch a specific property
@app.route('/properties/<int:property_id>', methods=['GET'])
def get_property_details(property_id):
    property = Property.query.get(property_id)
    if not property:
        return jsonify({"message": "Property not found!"}), 404
    return jsonify({
        "id": property.id,
        "title": property.title,
        "price": property.price,
        "location": property.location,
        "type": property.type,
        "bedrooms": property.bedrooms,
        "size": property.size,
        "image_url": property.image_url
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
