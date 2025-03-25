from decouple import config

class Config:
    SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here')  # Replace with a secure key in production
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL', default='sqlite:///site.db')  # Use Render's DATABASE_URL or fallback to SQLite
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = config('JWT_SECRET_KEY', default='your-jwt-secret-key-here')  # Replace with a secure key
