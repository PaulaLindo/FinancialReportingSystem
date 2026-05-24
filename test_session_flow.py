#!/usr/bin/env python3
"""
Test the complete Flask session flow
"""

import requests
from urllib.parse import urlparse

def test_session_flow():
    print("=== TESTING FLASK SESSION FLOW ===")
    
    session = requests.Session()
    
    # Step 1: Get login page to get any session cookies
    print("1. Getting login page...")
    login_page = session.get('http://127.0.0.1:5000/login', timeout=5)
    print(f"   Login page status: {login_page.status_code}")
    print(f"   Cookies before login: {session.cookies}")
    
    # Step 2: Submit login form
    print("\n2. Submitting login form...")
    login_data = {
        'username': 'finance.manager@sadpmr.gov.za',
        'password': 'demo123'
    }
    
    login_response = session.post('http://127.0.0.1:5000/login', 
                             data=login_data, 
                             timeout=5,
                             allow_redirects=True)
    
    print(f"   Login response status: {login_response.status_code}")
    print(f"   Login response headers: {dict(login_response.headers)}")
    print(f"   Cookies after login: {session.cookies}")
    
    # Step 3: Follow redirect if it happens
    if login_response.status_code in [302, 303]:
        redirect_url = login_response.headers.get('Location', '')
        if redirect_url:
            print(f"   Following redirect to: {redirect_url}")
            dashboard = session.get(redirect_url, timeout=5)
            print(f"   Dashboard status: {dashboard.status_code}")
            print(f"   Dashboard cookies: {session.cookies}")
    
    # Step 4: Test API with session
    print("\n4. Testing API with session...")
    api_response = session.get('http://127.0.0.1:5000/api/current-user', timeout=5)
    print(f"   API status: {api_response.status_code}")
    
    if api_response.status_code == 200:
        user_data = api_response.json()
        print(f"   API user data: {user_data}")
    else:
        print(f"   API failed: {api_response.text}")
    
    # Step 5: Test approvals page
    print("\n5. Testing approvals page...")
    approvals = session.get('http://127.0.0.1:5000/approvals', timeout=5)
    print(f"   Approvals page status: {approvals.status_code}")
    
    if approvals.status_code == 200:
        if 'Loading...' in approvals.text:
            print("   ⚠️ Still shows loading indicators")
        else:
            print("   ✅ No loading indicators")
    else:
        print(f"   Approvals failed: {approvals.status_code}")

if __name__ == "__main__":
    test_session_flow()
