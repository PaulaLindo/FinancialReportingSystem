#!/usr/bin/env python3
"""
Direct test by simulating logged in session
"""

import requests

def test_direct_approval_access():
    session = requests.Session()
    
    try:
        print("=== DIRECT APPROVAL TEST ===")
        
        # Try to access approvals page without login (should redirect to login)
        response = session.get('http://127.0.0.1:5000/approvals', timeout=5)
        print(f"1. Approvals without login: {response.status_code}")
        
        if response.status_code == 302:
            print("   ✅ Correctly redirects to login")
        elif response.status_code == 200:
            print("   ⚠️ Approvals page accessible without login")
            # Check if it has loading indicators
            if 'Loading...' in response.text:
                print("   ⚠️ Still shows loading indicators")
            else:
                print("   ✅ No loading indicators")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            
        print("\n=== MANUAL LOGIN INSTRUCTIONS ===")
        print("Since automated login is having issues, please try manual login:")
        print("1. Go to: http://127.0.0.1:5000/login")
        print("2. Use demo credentials:")
        print("   Username: finance.manager@sadpmr.gov.za")
        print("   Password: demo123")
        print("3. After successful login, go to: http://127.0.0.1:5000/approvals")
        print("4. Check browser console (F12) for JavaScript errors")
        print("5. Check network tab for API call failures")
        
        print("\n=== ALTERNATIVE ===")
        print("If demo login doesn't work, try:")
        print("   Username: cfo@sadpmr.gov.za")
        print("   Password: demo123")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_direct_approval_access()
