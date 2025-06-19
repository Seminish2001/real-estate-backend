from app import app, db

"""Entry point for running the development server.

The database tables are automatically created on startup if they do not
already exist. This avoids "no such table" errors when using the sign in or
sign up routes for the first time.
"""

if __name__ == "__main__":
    import os
    # Always ensure tables exist so authentication routes work on first run
    with app.app_context():
        db.create_all()

    port = int(os.getenv("PORT", 5000))  # Use PORT env var if set, else default to 5000
    app.run(host="0.0.0.0", port=port, debug=True)
