from flask import Blueprint, render_template

views = Blueprint("views", __name__)

@views.route("/")
def home():
    return render_template("index.html")

@views.route("/auth")
def auth():
    return render_template("auth.html")

@views.route("/for-owners")
def for_owners():
    return render_template("for-owners.html")
