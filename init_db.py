import argparse
from app import app, db


def init_db(drop=False):
    with app.app_context():
        if drop:
            db.drop_all()
        db.create_all()
        print("Database tables created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the database.")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating new ones.",
    )
    args = parser.parse_args()
    init_db(drop=args.drop)
