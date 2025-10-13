from flask import Blueprint, render_template
from decouple import config

# Define the blueprint
template_bp = Blueprint('templates', __name__)

@template_bp.route('/')
def index():
    """Renders the main homepage and property search template."""
    # Passes the API key required by base.html and index.html
    google_maps_api_key = config('GOOGLE_MAPS_API_KEY', default='YOUR_FALLBACK_API_KEY')
    return render_template('index.html', google_maps_api_key=google_maps_api_key)

@template_bp.route('/signin.html')
def signin():
    """Renders the sign-in page."""
    return render_template('signin.html')

@template_bp.route('/signup.html')
def signup():
    """Renders the sign-up page."""
    return render_template('signup.html')

@template_bp.route('/property_detail.html')
def property_detail():
    """Renders the single property detail page."""
    # NOTE: The logic for fetching the property ID is handled in the template's JavaScript
    return render_template('property_detail.html')

@template_bp.route('/dashboard-agency.html')
def dashboard_agency():
    """Renders the Agent/Broker dashboard."""
    # NOTE: Authentication/Authorization check is handled in the template's JavaScript
    return render_template('dashboard-agency.html')

@template_bp.route('/dashboard-buyer-renter.html')
def dashboard_buyer_renter():
    """Renders the standard Buyer/Renter dashboard."""
    # NOTE: Authentication check is handled in the template's JavaScript
    return render_template('dashboard-buyer-renter.html')

# Add other necessary template routes here (e.g., /settings.html, /private-agent.html, etc.)
# @template_bp.route('/private-agent.html')
# def private_agent_setup():
#     return render_template('private-agent.html')
