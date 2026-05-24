"""
Varydian Financial Reporting System - Main Application Entry Point
Flask Web Application for GRAP Financial Statement Generation
"""
from services.approval_rules_engine import approval_rules_engine

import os
import sys

# Try to load environment variables from .env file (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available in production, use environment variables directly
    pass

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main application from controllers (using auth-enabled version)
from controllers.routes import app

# Import and register universal routes for multi-document support
try:
    from controllers.routes_universal import register_universal_routes
    register_universal_routes(app)
except ImportError as e:
    print(f"Warning: Could not register universal routes: {e}")

try:
    from controllers.routes_export import register_export_routes

    register_export_routes(app)
except ImportError as e:
    print(f"Warning: Could not register export routes: {e}")

try:
    from controllers.routes_certificate import register_certificate_routes

    register_certificate_routes(app)
except ImportError as e:
    print(f"Warning: Could not register certificate routes: {e}")

try:
    from controllers.routes_finance_manager import register_finance_manager_routes
    register_finance_manager_routes(app)
except ImportError as e:
    print(f"Warning: Could not register finance manager routes: {e}")

try:
    from controllers.routes_inbox import register_inbox_routes

    register_inbox_routes(app)
except ImportError as e:
    print(f"Warning: Could not register inbox routes: {e}")

try:
    from controllers.routes_system import register_system_routes

    register_system_routes(app)
except ImportError as e:
    print(f"Warning: Could not register system routes: {e}")

try:
    from utils.period_lock_guard import register_period_lock_middleware

    register_period_lock_middleware(app)
except ImportError as e:
    print(f"Warning: Could not register period lock middleware: {e}")

# Vercel expects a WSGI handler
def handler(environ, start_response):
    """WSGI handler for Vercel"""
    return app(environ, start_response)

if __name__ == '__main__':
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
