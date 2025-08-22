"""
Database initialization script.
Run this to create the necessary database tables before accessing the API.
The application will also automatically initialize the database on startup (in __init__.py).
"""
from app import app, db

def init_db():
    """Create all database tables defined in models.py"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    init_db()
