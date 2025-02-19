from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from app.config import Config
from app.models import db, bcrypt
from app.routes import routes
from app.auth_routes import auth_routes
from app.views import views

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    JWTManager(app)

    app.register_blueprint(routes)
    app.register_blueprint(auth_routes)
    app.register_blueprint(views)

    return app
