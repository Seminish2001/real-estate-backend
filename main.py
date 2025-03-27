from app import app

if __name__ == "__main__":
    # For local development only
    import os
    port = int(os.getenv("PORT", 5000))  # Use PORT env var if set, else default to 5000
    app.run(host="0.0.0.0", port=port, debug=True)
