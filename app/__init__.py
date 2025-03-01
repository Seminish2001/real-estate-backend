from flask import Flask
from app.config import Config
from app.models import db, bcrypt
from app.routes import routes
from app.auth_routes import auth_routes
from app.views import views

def create_app():
    app = Flask(__name__, template_folder="../templates")  # Ensure correct path
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)

    app.register_blueprint(routes)
    app.register_blueprint(auth_routes)
    app.register_blueprint(views)

    return app
