"""
SADPMR Financial Reporting System - Application Runner
Development server startup script
"""

import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_APP'] = 'app.py'

# Import and run the application
from app import app

if __name__ == '__main__':
    print("🚀 Starting SADPMR Financial Reporting System...")
    print("📊 Access the application at: http://localhost:5000")
    print("📁 Upload directory: ./uploads")
    print("📄 Output directory: ./outputs")
    print("-" * 50)
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        use_reloader=True
    )
