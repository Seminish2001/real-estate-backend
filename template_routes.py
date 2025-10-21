from flask import Blueprint, abort, render_template
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from decouple import config

from models import User, safe_get

# Define the blueprint
template_bp = Blueprint('templates', __name__)


def _current_user(optional: bool = False):
    try:
        verify_jwt_in_request(optional=optional)
    except Exception:
        if optional:
            return None
        raise

    user_id = get_jwt_identity()
    if not user_id:
        return None
    return safe_get(User, user_id)


@template_bp.route('/')
def index():
    """Renders the main homepage and property search template."""
    google_maps_api_key = config('GOOGLE_MAPS_API_KEY', default='YOUR_FALLBACK_API_KEY')
    return render_template('index.html', google_maps_api_key=google_maps_api_key)


@template_bp.route('/about')
def about():
    return render_template('about.html')


@template_bp.route('/contact')
def contact():
    return render_template('contact.html')


@template_bp.route('/diy-sell')
def diy_sell():
    return render_template('diy-sell.html')


@template_bp.route('/instant-offer')
def instant_offer():
    return render_template('instant-offer.html')


@template_bp.route('/join-as-agent')
def join_as_agent():
    return render_template('join-as-agent.html')


@template_bp.route('/private-agent')
def private_agent():
    return render_template('private-agent.html')

@template_bp.route('/list/private-agent')
def private_agent_legacy():
    return render_template('private-agent.html')


@template_bp.route('/reset-password')
def reset_password():
    return render_template('reset-password.html')


@template_bp.route('/mortgage')
def mortgage():
    return render_template('mortgage.html')


@template_bp.route('/admin')
def admin_dashboard():
    user = _current_user(optional=True)
    if not user or not (user.role == 'ADMIN' or getattr(user, 'is_admin', False)):
        abort(403)
    return render_template('admin.html', user=user)


_DASHBOARD_TEMPLATES = {
    'landlord': ('dashboard-landlord.html', {'LANDLORD', 'AGENT', 'BROKER', 'ADMIN'}),
    'buyer-renter': ('dashboard-buyer-renter.html', {'USER'}),
    'agency': ('dashboard-agency.html', {'AGENT', 'BROKER', 'ADMIN'}),
}


@template_bp.route('/dashboard/<string:dashboard_slug>')
def dashboards(dashboard_slug: str):
    entry = _DASHBOARD_TEMPLATES.get(dashboard_slug)
    if not entry:
        abort(404)

    template_name, allowed_roles = entry
    user = _current_user(optional=False)
    if not user or user.role not in allowed_roles:
        abort(403)

    return render_template(template_name)


@template_bp.route('/property_detail.html')
def property_detail():
    """Renders the single property detail page."""
    return render_template('property_detail.html')


@template_bp.route('/dashboard-agency.html')
def dashboard_agency():
    """Renders the Agent/Broker dashboard."""
    return render_template('dashboard-agency.html')


@template_bp.route('/dashboard-buyer-renter.html')
def dashboard_buyer_renter():
    """Renders the standard Buyer/Renter dashboard."""
    return render_template('dashboard-buyer-renter.html')
