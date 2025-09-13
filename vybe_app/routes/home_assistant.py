"""
Home Assistant Routes
====================
Flask routes for Home Assistant UI pages
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from vybe_app.api.home_assistant_api import home_assistant_bp, ha_connection

# Create the main routes blueprint
home_assistant_routes = Blueprint('home_assistant_routes', __name__, url_prefix='/home-assistant')


@home_assistant_routes.route('/')
def home_assistant_dashboard():
    """Home Assistant dashboard page"""
    return render_template('home_assistant/dashboard.html', 
                         title="Home Assistant - Vybe AI",
                         connection_status=ha_connection)


@home_assistant_routes.route('/settings')
def home_assistant_settings():
    """Home Assistant settings page"""
    return render_template('home_assistant/settings.html',
                         title="Home Assistant Settings - Vybe AI",
                         connection_status=ha_connection)


@home_assistant_routes.route('/devices')
def home_assistant_devices():
    """Home Assistant devices page"""
    return render_template('home_assistant/devices.html',
                         title="Home Assistant Devices - Vybe AI", 
                         connection_status=ha_connection,
                         devices=ha_connection.get('devices', []))


# Register both blueprints in the main app
def register_home_assistant_blueprints(app):
    """Register all Home Assistant blueprints with the Flask app"""
    app.register_blueprint(home_assistant_bp)  # API routes
    app.register_blueprint(home_assistant_routes)  # UI routes
