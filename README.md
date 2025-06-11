# Real Estate Backend

This project is a simple Flask backend for a real estate website. The application provides authentication and basic property management APIs.

## Setup

1. **Python version**: The project requires **Python 3.11+**.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   Alternatively, you can install directly from the project for local
   development:
   ```bash
   pip install -e .
   ```
3. **Environment variables**:
   - `DATABASE_URL` – Database connection string (default: `sqlite:///properties.db`).
   - `JWT_SECRET_KEY` – Secret key used to sign JWT tokens.
   - `GOOGLE_CLIENT_ID` – Client ID for Google OAuth (optional).
   - `GOOGLE_MAPS_API_KEY` – API key for Google Maps (required for map features).
   - `JWT_COOKIE_SECURE` – Set to `True` to transmit JWT cookies over HTTPS only (default `True`).
   - `PORT` – Port for the development server (default: `5000`).

Copy `.env.example` to `.env` and update the values, or export these variables in your shell before running the server.

## Database Setup

Initialize the database tables before starting the server. The scripts rely on
the same environment variables described above (at minimum `DATABASE_URL` and
`JWT_SECRET_KEY`). Use `init_db.py` to create the schema and `seed.py` to add
sample records:

```bash
# Create tables (add --drop to delete existing ones)
python init_db.py --drop

# Populate demo users, properties and agents
python seed.py
```

## Running the Server

Execute the following command:

```bash
python main.py
```

The application will start on `http://localhost:5000` unless a different `PORT` is specified.

## Running Tests

Tests are written with **pytest** and located in the `tests/` directory. Install **all** packages from `requirements.txt` before running the suite:

```bash
pytest
```

If dependencies are missing, pytest may exit with errors such as `ModuleNotFoundError: No module named 'flask'`. Installing the full `requirements.txt` resolves this issue.

The tests use an in-memory SQLite database and cover basic authentication endpoints (signup and signin).

## Authentication

JWT access and refresh tokens are stored as **HttpOnly cookies**. Frontend scripts should not read or write these tokens with `localStorage`. Instead, include `credentials: 'include'` with each `fetch` request so the cookies are sent automatically. When CSRF protection is enabled, pass the `csrf_access_token` cookie value as the `X-CSRF-TOKEN` header on POST/PUT/DELETE requests.


## License

This project is licensed under the [MIT License](LICENSE).
