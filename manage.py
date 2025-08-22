#!/usr/bin/env python3
"""
Manage database migrations for the Order Service.

Usage:
  python manage.py db init      # Initialize migrations repository
  python manage.py db migrate   # Generate migration
  python manage.py db upgrade   # Apply migrations
  python manage.py db --help    # Show Flask-Migrate help
"""
import os
from flask_migrate import Migrate, MigrateCommand
from flask.cli import FlaskGroup

from app import app, db

cli = FlaskGroup(app)

if __name__ == '__main__':
    cli()
