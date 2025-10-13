import os
# NEW: Import eventlet and monkey_patch
import eventlet
from app import app, db, socketio

# CRITICAL: Monkey-patch standard Python libraries to be cooperative.
# This must happen before any imports that use standard networking.
eventlet.monkey_patch()

# Import models/events/routes to ensure they are registered
# The mere act of importing registers the blueprints and event handlers.
import models
import chat_events
import auth_routes
import property_routes
import agent_routes
from template_routes import template_bp # Don't forget the new template routes!

if __name__ == "__main__":
    
    with app.app_context():
        print("Ensuring database tables exist...")
        db.create_all() 
        print("Database setup complete.")
        
    port = int(os.getenv("PORT", 5000))
    print(f"Starting server on port {port} using Eventlet...")
    
    # When deployed on Render using the gunicorn start command:
    # gunicorn --worker-class eventlet -w 1 main:app
    # The code below only runs when you execute 'python main.py' locally.
    
    # Run the application using socketio.run, which will use Eventlet
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        # Debug should be False on production environments like Render
        debug=False, 
        allow_unsafe_werkzeug=True 
    )

