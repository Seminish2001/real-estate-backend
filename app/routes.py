from flask import Blueprint, render_template, request, jsonify
from app import db
from app.models import Property, Agent

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/properties')
def properties():
    purpose = request.args.get('purpose', 'buy')  # Default to 'buy'
    properties = Property.query.filter_by(purpose=purpose).all()
    return render_template('properties.html', properties=properties, purpose=purpose)

@bp.route('/sell')
def sell():
    return render_template('sell.html')

@bp.route('/agents')
def agents():
    agents = Agent.query.all()
    return render_template('agents.html', agents=agents)

@bp.route('/api/properties', methods=['GET'])
def get_properties():
    location = request.args.get('location')
    purpose = request.args.get('purpose')
    type = request.args.get('type')
    max_price = request.args.get('price', type=float)
    beds = request.args.get('beds', type=int)
    baths = request.args.get('baths', type=int)

    query = Property.query
    if location:
        query = query.filter(Property.location.ilike(f'%{location}%'))
    if purpose:
        query = query.filter_by(purpose=purpose)
    if type:
        query = query.filter_by(type=type)
    if max_price:
        query = query.filter(Property.price <= max_price)
    if beds:
        query = query.filter(Property.beds >= beds)
    if baths:
        query = query.filter(Property.baths >= baths)

    properties = query.all()
    return jsonify({
        'properties': [p.to_dict() for p in properties],
        'count': len(properties)
    })
