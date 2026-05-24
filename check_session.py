#!/usr/bin/env python3
"""
Check what user ID the Flask session actually contains
"""

import requests

def check_flask_session():
    session = requests.Session()
    
    # Login with demo credentials
    login_data = {'username': 'finance.manager@sadpmr.gov.za', 'password': 'demo123'}
    
    print("=== LOGIN TEST ===")
    login_response = session.post('http://127.0.0.1:5000/login', data=login_data, timeout=5)
    print(f"Login status: {login_response.status_code}")
    
    if login_response.status_code == 302:
        # Follow redirect to get session cookies
        dashboard = session.get('http://127.0.0.1:5000/dashboard', timeout=5)
        print(f"Dashboard status: {dashboard.status_code}")
        
        # Now test current user API to see what Flask thinks the user ID is
        user_api = session.get('http://127.0.0.1:5000/api/current-user', timeout=5)
        print(f"Current user API status: {user_api.status_code}")
        
        if user_api.status_code == 200:
            user_data = user_api.json()
            print(f"Flask session user ID: {user_data.get('data', {}).get('id', 'NOT FOUND')}")
            print(f"Flask session user role: {user_data.get('data', {}).get('role', 'NOT FOUND')}")
        else:
            print("Failed to get current user API")
    else:
        print(f"Login failed with status: {login_response.status_code}")

if __name__ == "__main__":
    check_flask_session()
