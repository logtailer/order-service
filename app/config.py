
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
        # PostgreSQL Connection Settings
        DB_USER = os.environ.get('DB_USER', 'postgres')
        DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
        DB_HOST = os.environ.get('DB_HOST', 'localhost')
        DB_PORT = os.environ.get('DB_PORT', '5432')
        DB_NAME = os.environ.get('DB_NAME', 'orderdb')
        
        # Build connection string from components or use DATABASE_URL if provided
        postgres_uri = os.environ.get('DATABASE_URL')
        if not postgres_uri:
            postgres_uri = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        
        # SQLite fallback for local development without Docker
        sqlite_uri = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///orders.db')
        
        # If DATABASE_URL starts with postgres://, update it to postgresql:// (needed for SQLAlchemy 1.4+)
        if postgres_uri and postgres_uri.startswith('postgres://'):
            postgres_uri = postgres_uri.replace('postgres://', 'postgresql://', 1)
            
        SQLALCHEMY_DATABASE_URI = postgres_uri or sqlite_uri
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
