import os
from app import create_app
from app.models import db

# Initialize Flask App
app = create_app()

# Ensure Database Tables Exist
with app.app_context():
    db.create_all()

# Run the Application
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render assigns a dynamic PORT
    app.run(host="0.0.0.0", port=port)
