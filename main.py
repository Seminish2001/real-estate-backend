import os
import eventlet
# CRITICAL: Monkey-patch standard Python libraries to be cooperative.
# This must happen before importing the Flask app, extensions, or routes.
eventlet.monkey_patch()

# --- Now, and only now, import the core Flask/DB objects ---
# The code in app.py now runs AFTER the patch is complete.
from app import app, db, socketio 

# --- Import modules containing Blueprints/Event Handlers/Models ---
# The mere act of importing these files registers the blueprints and event handlers.
import models
import chat_events
import auth_routes
import property_routes
import agent_routes
from template_routes import template_bp

if __name__ == "__main__":
    
    # 1. Run database setup within the app context
    with app.app_context():
        print("Ensuring database tables exist...")
        db.create_all() 
        print("Database setup complete.")
        
    port = int(os.getenv("PORT", 5000))
    print(f"Starting server on port {port} using Eventlet...")
    
    # 2. Run the application via socketio.run
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        # Debug should be False on production (Render)
        debug=False, 
        allow_unsafe_werkzeug=True 
    )
