import os
from datetime import timedelta
from decouple import config

class Config:
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL', default='sqlite:///properties.db')  # Render sets DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = config('JWT_SECRET_KEY', default='default_secret_key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = True  # Hardcoded for production
    JWT_COOKIE_CSRF_PROTECT = True  # Hardcoded for production

    # Hardcoded Cloudinary credentials (temporary)
    CLOUDINARY_CLOUD_NAME = 'dxearodvf'
    CLOUDINARY_API_KEY = '292532466535494'
    CLOUDINARY_API_SECRET = '7C58WhO-JWQsAG8Lze9C5hMfkD4'

    if JWT_SECRET_KEY == 'default_secret_key':
        print("WARNING: Using default JWT_SECRET_KEY. Set this in production!")
