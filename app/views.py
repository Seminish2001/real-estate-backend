from flask import Blueprint, render_template

views = Blueprint("views", __name__)

@views.route("/")
def home():
    return render_template("index.html")

# Removed /login and /signup routes as they're now handled by modal API calls

@views.route("/for-owners")
def for_owners():
    return render_template("for-owners.html")
