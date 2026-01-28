"""
SADPMR Financial Reporting System - Main Application Entry Point
Flask Web Application for GRAP Financial Statement Generation
"""

import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main application from controllers
from controllers.routes import app

if __name__ == '__main__':
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
