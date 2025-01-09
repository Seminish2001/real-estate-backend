from flask import Flask, jsonify, request, send_from_directory, render_template
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
    cloud_name="dxearodvf",  # Replace with your Cloudinary cloud name
    api_key="292532466535494",  # Replace with your Cloudinary API key
    api_secret="your_api_secret",  # Replace with your Cloudinary API secret
    secure=True
)

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

# Serve frontend files
@app.route('/')
def serve_homepage():
    return send_from_directory('.', 'index.html')

@app.route('/login')
def serve_login():
    return send_from_directory('.', 'login.html')

@app.route('/signup')
def serve_signup():
    return send_from_directory('.', 'signup.html')

@app.route('/add-property')
def serve_add_property():
    return send_from_directory('.', 'add-property.html')

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory('.', 'dashboard.html')

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

    # Handle file upload
    image_file = request.files.get('image')
    if not image_file:
        return jsonify({"message": "Image is required!"}), 400

    try:
        upload_result = cloudinary.uploader.upload(image_file)
        image_url = upload_result.get('secure_url')

        # Apply auto-formatting and resizing
        optimized_image_url, _ = cloudinary_url(
            upload_result['public_id'],
            fetch_format="auto",
            quality="auto",
            width=500,
            height=500,
            crop="auto",
            gravity="auto"
        )
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
        image_url=optimized_image_url,
        owner_id=current_user
    )
    db.session.add(new_property)
    db.session.commit()
    return jsonify({"message": "Property added successfully!", "image_url": optimized_image_url}), 201

# Edit a property (authenticated)
@app.route('/properties/<int:property_id>', methods=['PUT'])
@jwt_required()
def update_property(property_id):
    current_user = get_jwt_identity()
    property_to_update = Property.query.get(property_id)

    if not property_to_update:
        return jsonify({"message": "Property not found!"}), 404
    if property_to_update.owner_id != current_user:
        return jsonify({"message": "Not authorized to update this property!"}), 403

    data = request.form
    property_to_update.title = data['title']
    property_to_update.price = float(data['price'])
    property_to_update.location = data['location']
    property_to_update.type = data['type']
    property_to_update.bedrooms = int(data['bedrooms'])
    property_to_update.size = float(data['size'])

    image_file = request.files.get('image')
    if image_file:
        upload_result = cloudinary.uploader.upload(image_file)
        property_to_update.image_url = upload_result.get('secure_url')

    db.session.commit()
    return jsonify({"message": "Property updated successfully!"}), 200

# Fetch all properties
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

# Fetch a specific property by ID
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
