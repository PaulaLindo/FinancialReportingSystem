"""
Varydian Financial Reporting System - Main Application Entry Point
Flask Web Application for GRAP Financial Statement Generation
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main application from controllers (using auth-enabled version)
from controllers.routes import app

# Import and register universal routes for multi-document support
from controllers.routes_universal import register_universal_routes
register_universal_routes(app)

if __name__ == '__main__':
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
