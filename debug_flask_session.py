#!/usr/bin/env python3
"""
Debug Flask session configuration and add middleware
"""

import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_debug_app():
    """Create a debug version of the Flask app to identify session issues"""
    
    app = Flask(__name__)
    
    # Copy the same configuration from routes.py
    app.config['SECRET_KEY'] = 'varydian-demo-2025-secure-key-auth-enabled'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['OUTPUT_FOLDER'] = 'outputs'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['DEBUG'] = True
    
    # Add session debugging
    app.config['SESSION_COOKIE_SECURE'] = False  # For localhost
    app.config['SESSION_COOKIE_HTTPONLY'] = False  # For JavaScript access
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Less restrictive
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    
    # Add request logging middleware
    @app.before_request
    def before_request():
        print(f"=== REQUEST DEBUG ===")
        print(f"Method: {request.method}")
        print(f"Path: {request.path}")
        print(f"Headers: {dict(request.headers)}")
        print(f"Cookies: {request.cookies}")
        print(f"Session: {dict(session)}")
        
        # Debug session user
        if 'user_id' in session:
            print(f"Logged in user: {session['user_id']}")
        else:
            print("No user in session")
    
    # Import routes to test
    try:
        from controllers.routes import app as routes_app
        # Copy routes from the main app
        for rule in routes_app.url_map.iter_rules():
            app.add_url_rule(rule)
        print("✅ Routes imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import routes: {e}")
        return None
    
    return app

def test_debug_session():
    print("=== TESTING DEBUG FLASK SESSION ===")
    
    app = create_debug_app()
    
    if app is None:
        print("❌ Failed to create debug app")
        return
    
    # Test with the debug app
    with app.test_client() as client:
        print("\n1. Testing login with debug app...")
        
        # Get login page first
        login_page = client.get('/login')
        print(f"   Login page status: {login_page.status_code}")
        
        # Submit login
        login_response = client.post('/login', data={
            'username': 'finance.manager@sadpmr.gov.za',
            'password': 'demo123'
        })
        print(f"   Login response status: {login_response.status_code}")
        print(f"   Login response headers: {dict(login_response.headers)}")
        
        # Follow redirect if it happens
        if login_response.status_code in [302, 303]:
            redirect_url = login_response.headers.get('Location', '')
            if redirect_url:
                print(f"   Following redirect to: {redirect_url}")
                dashboard = client.get(redirect_url)
                print(f"   Dashboard status: {dashboard.status_code}")
        
        # Test API with session
        print("\n2. Testing API with debug app session...")
        api_response = client.get('/api/current-user')
        print(f"   API status: {api_response.status_code}")
        if api_response.status_code == 200:
            data = api_response.json()
            print(f"   API data: {data}")
        else:
            print(f"   API failed: {api_response.text}")
        
        # Test approvals page
        print("\n3. Testing approvals page...")
        approvals = client.get('/approvals')
        print(f"   Approvals status: {approvals.status_code}")
        if 'Loading...' in approvals.data:
            print("   ⚠️ Still shows loading")
        else:
            print("   ✅ No loading indicators")

if __name__ == "__main__":
    test_debug_session()
