from app import create_app, db
from flask_migrate import Migrate

app = create_app()

# Automate migrations on startup
with app.app_context():
    Migrate(app, db)  # Initialize migrations
    from flask_migrate import upgrade
    upgrade()  # Apply migrations to create tables

if __name__ == '__main__':
    app.run(debug=True)
