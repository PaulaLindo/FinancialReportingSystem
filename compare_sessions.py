#!/usr/bin/env python3
"""
Compare automated vs browser session API calls
"""

import requests
import json

def compare_sessions():
    print("=== COMPARING SESSIONS ===")
    
    # Test 1: Direct API call (like our automated test)
    print("\n1. Direct API call (no session):")
    direct_response = requests.get('http://127.0.0.1:5000/api/transactions/pending', timeout=5)
    print(f"   Status: {direct_response.status_code}")
    if direct_response.status_code == 200:
        data = direct_response.json()
        print(f"   Data: {json.dumps(data, indent=2)}")
    
    # Test 2: Simulate browser session with the exact same cookies
    print("\n2. Simulated browser session:")
    
    # Use the exact session cookie from our previous test
    session_cookie = "session=.eJwtjrEOgjAURX_FvJmSUooik8SgcYDBuDcPeQUSWkihDhr_XUxYz8nJvR9QEzmDluwC2eI8BaD9MCiLhiCDR4f1uCuXjkztIQA3Dn98uVV5dS5UmVf5tbivws_kVN-sLkkwTjmmTErNmUy4YEcuJKtFjBGnPUUHvQXbiO4t2ieF6w1syZ1mbCbjwnZ8hW-E7w_DCTO_.agN8dw.OEwiGfKa6uvPQVIQIbt3tgSe4JE"
    
    session = requests.Session()
    session.cookies.set('session', session_cookie)
    
    browser_response = session.get('http://127.0.0.1:5000/api/transactions/pending', timeout=5)
    print(f"   Status: {browser_response.status_code}")
    if browser_response.status_code == 200:
        data = browser_response.json()
        print(f"   Data: {json.dumps(data, indent=2)}")
        
        # Compare the results
        if direct_response.status_code == browser_response.status_code:
            direct_data = direct_response.json()
            browser_data = browser_response.json()
            if direct_data == browser_data:
                print("   ✅ API responses are IDENTICAL")
            else:
                print("   ❌ API responses are DIFFERENT")
                print(f"   Direct count: {direct_data.get('count', 'N/A')}")
                print(f"   Browser count: {browser_data.get('count', 'N/A')}")
        else:
            print("   ❌ Cannot compare - different status codes")

if __name__ == "__main__":
    compare_sessions()
