#!/usr/bin/env python3
"""
Simple test to check if approval page works with session
"""

import requests

def test_approval_page():
    print("=== APPROVAL PAGE ACCESS TEST ===")
    print("1. Testing direct API access (should fail without session):")
    
    try:
        # Test without session (should fail)
        response = requests.get('http://127.0.0.1:5000/api/transactions/pending', timeout=5)
        print(f"   Direct API: {response.status_code}")
        
        if response.status_code == 401:
            print("   ✅ Correctly requires authentication")
        else:
            print("   ❌ Unexpected - should require authentication")
            
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n2. Testing with browser session simulation:")
    print("   To test the approval page properly:")
    print("   1. Open browser and go to: http://127.0.0.1:5000/login")
    print("   2. Login with: username=testuser, password=testpass123")
    print("   3. Then go to: http://127.0.0.1:5000/approvals")
    print("   4. Check browser console for any JavaScript errors")
    print("   5. Check network tab for API calls")
    
    print("\n=== TROUBLESHOOTING ===")
    print("If you still see 'Loading...':")
    print("- Check browser console (F12) for JavaScript errors")
    print("- Check network tab for failed API calls")
    print("- Make sure you're logged in properly")
    print("- Try refreshing the page after login")
    
    print("\n=== ALTERNATIVE ===")
    print("If login doesn't work, try existing users:")
    print("- Username: finance.manager@example.com")
    print("- Password: (check with your team or try password reset)")

if __name__ == "__main__":
    test_approval_page()
