"""Initialize Flask app with SQLAlchemy and Flask-Migrate.

Creates a Flask app instance, configures it using 'config.py',
sets up SQLAlchemy for database operations, and configures Flask-Migrate.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


app = Flask(__name__)
from app.config import Config
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes
