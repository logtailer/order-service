
"""Module for configuration settings.
- loads environment variables using dotenv
- sets up various configuration parameters for the Flask app.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    if os.environ.get('FLASK_ENV') == 'testing':
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///orders.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
