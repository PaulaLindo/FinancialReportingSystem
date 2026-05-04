"""
Varydian Financial Reporting System - Main Application Entry Point
Flask Web Application for GRAP Financial Statement Generation
"""

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

# Vercel expects a WSGI handler
def handler(environ, start_response):
    """WSGI handler for Vercel"""
    return app(environ, start_response)

if __name__ == '__main__':
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
