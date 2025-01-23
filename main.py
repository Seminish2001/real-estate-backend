from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies
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
    return render_template('index.html')

@app.route('/login')
def serve_login():
    return render_template('login.html')

@app.route('/signup')
def serve_signup():
    return render_template('signup.html')

@app.route('/dashboard')
def serve_dashboard():
    return render_template('dashboard.html')

@app.route('/manage-properties')
def serve_manage_properties():
    properties = Property.query.all()
    return render_template('manage-properties.html', properties=properties)

@app.route('/clients')
def serve_manage_clients():
    return render_template('clients.html')

@app.route('/reports')
def serve_reports():
    return render_template('reports.html')

@app.route('/settings')
def serve_account_settings():
    return render_template('account-settings.html')

@app.route('/support')
def serve_support():
    return render_template('support.html')

@app.route('/properties-page')
def serve_properties_page():
    properties = Property.query.all()
    return render_template('properties.html', properties=properties)

@app.route('/logout', methods=['POST'])
def logout():
    response = jsonify({"message": "Successfully logged out!"})
    unset_jwt_cookies(response)
    return response

# Register a new user
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    required_fields = ['name', 'email', 'password', 'user_type']
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({"message": "Missing required fields!"}), 400
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = User(name=data['name'], email=data['email'], password=hashed_password, user_type=data['user_type'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully!"}), 201

# User login
@app.route('/login', methods=['POST'])
def login_user():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify({"access_token": access_token}), 200
    return jsonify({"message": "Invalid credentials!"}), 401

# Fetch properties
@app.route('/properties')
def serve_properties_page():
    properties = Property.query.all()
    return render_template('properties.html', properties=properties)
    
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

