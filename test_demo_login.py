#!/usr/bin/env python3
"""
Test demo login credentials
"""

import requests

def test_demo_login():
    # Test with demo credentials
    login_data = {
        'username': 'finance.manager@sadpmr.gov.za',
        'password': 'demo123'
    }

    try:
        response = requests.post('http://127.0.0.1:5000/login', 
                               data=login_data, 
                               timeout=5)
        print(f'Login with demo credentials status: {response.status_code}')
        location = response.headers.get('Location', 'None')
        print(f'Location header: {location}')
        
        if response.status_code == 302:
            print('✅ Demo login successful!')
            print('Use these credentials in browser:')
            print('Username: finance.manager@sadpmr.gov.za')
            print('Password: demo123')
        else:
            print(f'❌ Demo login failed: {response.status_code}')
            
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    test_demo_login()
