import os
from app import app, db, socketio # Import the core app and socketio instances

# Import models to ensure they are registered with SQLAlchemy before db.create_all()
import models
# Import chat events to register the websocket handlers
import chat_events
# Import route blueprints to register the HTTP endpoints
import auth_routes
import property_routes
import agent_routes

if __name__ == "__main__":
    
    with app.app_context():
        print("Ensuring database tables exist...")
        # This will create all tables defined in models.py
        db.create_all() 
        print("Database setup complete.")
        
    port = int(os.getenv("PORT", 5000))
    print(f"Starting server on port {port}...")
    
    # Run the application using socketio.run, NOT app.run
    # This is required to host the WebSockets server
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        debug=True, 
        # allow_unsafe_werkzeug is often needed for modern Flask development
        allow_unsafe_werkzeug=True 
    )
