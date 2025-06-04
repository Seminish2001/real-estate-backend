# Real Estate Backend

This project is a simple Flask backend for a real estate website. The application provides authentication and basic property management APIs.

## Setup

1. **Python version**: The project requires **Python 3.11+**.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment variables**:
   - `DATABASE_URL` – Database connection string (default: `sqlite:///properties.db`).
   - `JWT_SECRET_KEY` – Secret key used to sign JWT tokens.
   - `GOOGLE_CLIENT_ID` – Client ID for Google OAuth (optional).
   - `PORT` – Port for the development server (default: `5000`).

You can create a `.env` file or export these variables in your shell before running the server.

## Running the Server

Execute the following command:

```bash
python main.py
```

The application will start on `http://localhost:5000` unless a different `PORT` is specified.

## Running Tests

Tests are written with **pytest** and located in the `tests/` directory. Run them with:

```bash
pytest
```

The tests use an in-memory SQLite database and cover basic authentication endpoints (signup and signin).

