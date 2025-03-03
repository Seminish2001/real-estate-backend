from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from app.config import Config
from app.models import db, bcrypt
from app.routes import routes
from app.auth_routes import auth_routes
from app.views import views
import logging

def create_app():
    app = Flask(__name__, template_folder="../templates")  # Adjust if templates move
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt = JWTManager(app)
    CORS(app)  # Enable CORS for potential frontend separation

    # Logging for debugging
    logging.basicConfig(level=logging.INFO)
    app.logger.info("Application started")

    # Register blueprints
    app.register_blueprint(routes)
    app.register_blueprint(auth_routes)
    app.register_blueprint(views)

    # Global error handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Unhandled exception: {str(e)}")
        return {"message": f"Server error: {str(e)}"}, 500

    # Initialize database
    with app.app_context():
        db.create_all()

    return app
