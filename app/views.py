from flask import Blueprint, render_template

views = Blueprint("views", __name__)

@views.route("/")
def home():
    return render_template("index.html")

@views.route("/properties")
def properties():
    return render_template("properties.html")

@views.route("/market")
def market():
    return render_template("market.html")

@views.route("/sell")
def sell():
    return render_template("sell.html")

