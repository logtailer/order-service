
import os
import subprocess
import sys
from app import app, db

# Initialize the database using migrations if they exist
with app.app_context():
    try:
        # Try to run migrations first (preferred method)
        from flask_migrate import upgrade
        upgrade()
        print("Database migrations applied successfully!")
    except Exception as e:
        print(f"Warning: Could not apply migrations: {e}")
        # Fallback to create_all() if migrations fail
        db.create_all()
        print("Database tables created using create_all()")

if __name__ == '__main__':
    host = os.environ.get('HOST', 'localhost')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host=host, port=port, debug=debug)
