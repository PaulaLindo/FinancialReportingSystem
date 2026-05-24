#!/usr/bin/env python3
"""
Test login and approval page access
"""

import requests

def test_login_and_approval():
    session = requests.Session()

    try:
        # First, get the login page to get any cookies
        login_page = session.get('http://127.0.0.1:5000/login', timeout=5)
        print(f'Login page status: {login_page.status_code}')

        # Then try to login (form data, not JSON)
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

        response = session.post('http://127.0.0.1:5000/login', 
                        data=login_data, 
                        timeout=5)

        print(f'Login POST status: {response.status_code}')
        redirect_location = response.headers.get('Location', 'No redirect')
        print(f'Redirect location: {redirect_location}')

        if response.status_code == 302:
            # Follow redirect to get session cookies
            dashboard = session.get(redirect_location, timeout=5)
            print(f'Dashboard status: {dashboard.status_code}')
            
            # Now test the approval page with the session
            approval_response = session.get('http://127.0.0.1:5000/approvals', timeout=5)
            print(f'Approvals page status: {approval_response.status_code}')
            
            if approval_response.status_code == 200:
                print('SUCCESS: You can now access the approvals page!')
                print('Go to: http://127.0.0.1:5000/approvals in your browser')
                
                # Test API calls with session
                api_response = session.get('http://127.0.0.1:5000/api/transactions/pending', timeout=5)
                print(f'API with session status: {api_response.status_code}')
                
                if api_response.status_code == 200:
                    data = api_response.json()
                    print(f'Workflows data: {len(data.get("data", []))} items')
                else:
                    print('API call failed even with session')
            else:
                print(f'Approvals page error: {approval_response.status_code}')
        else:
            print(f'Login failed: {response.text}')
            
    except Exception as e:
        print(f'Error during test: {e}')

if __name__ == "__main__":
    test_login_and_approval()
