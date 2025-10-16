import os
import eventlet

# CRITICAL FIX: 1. Patch Eventlet BEFORE anything else runs from other modules.
eventlet.monkey_patch()

# --- 2. Import the core Flask/DB objects ---
# 'db' is now an unattached SQLAlchemy object from app.py
from app import app, db, socketio 

# --- 3. Initialize the DB object with the app ---
# This associates the 'db' object with 'app' explicitly.
with app.app_context():
    db.init_app(app) 

# --- 4. Import models/events/routes ---
# These are imported AFTER db.init_app(app) so that when they reference 'db', 
# the association is complete, eliminating circular import issues.
import models 
import chat_events
import auth_routes
import property_routes
import agent_routes
from template_routes import template_bp

if __name__ == "__main__":
    
    # Database setup must happen inside an app context (which we already established)
    with app.app_context():
        print("Ensuring database tables exist...")
        # The database connection failure happens HERE:
        db.create_all() 
        print("Database setup complete.")
        
    port = int(os.getenv("PORT", 5000))
    print(f"Starting server on port {port} using Eventlet...")
    
    # Run the application via socketio.run
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        debug=False, 
        allow_unsafe_werkzeug=True 
    )

