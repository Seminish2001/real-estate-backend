from flask import Flask
from flask_jwt_extended import JWTManager
from app.config import Config
from app.models import db, bcrypt
from app.routes import routes
from app.auth_routes import auth_routes
from app.views import views

def create_app():
    app = Flask(__name__, template_folder="../templates")  # Ensure correct path if using templates
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt = JWTManager(app)

    # Register blueprints
    app.register_blueprint(routes)
    app.register_blueprint(auth_routes)
    app.register_blueprint(views)

    return app
