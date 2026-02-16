
"""Module for configuration settings.
- loads environment variables using dotenv
- sets up various configuration parameters for the Flask app.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    if os.environ.get('FLASK_ENV') == 'testing':
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    else:
        # PostgreSQL is preferred for production, with SQLite as fallback for development
        postgres_uri = os.environ.get('DATABASE_URL')
        sqlite_uri = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///orders.db')
        
        # If DATABASE_URL starts with postgres://, update it to postgresql:// (needed for SQLAlchemy 1.4+)
        if postgres_uri and postgres_uri.startswith('postgres://'):
            postgres_uri = postgres_uri.replace('postgres://', 'postgresql://', 1)
            
        SQLALCHEMY_DATABASE_URI = postgres_uri or sqlite_uri
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
