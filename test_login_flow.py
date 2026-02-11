"""
Test script to verify login functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controllers.routes import app
from models.auth_models import db

def test_login_flow():
    """Test the login flow"""
    print("\n" + "="*70)
    print("TESTING LOGIN FLOW")
    print("="*70)
    
    # Test 1: Verify demo users exist
    print("\n✓ Test 1: Checking demo users...")
    test_credentials = [
        ('cfo@sadpmr.gov.za', 'demo123', 'Sarah Nkosi'),
        ('accountant@sadpmr.gov.za', 'demo123', 'Thabo Mthembu'),
        ('clerk@sadpmr.gov.za', 'demo123', 'Lerato Dlamini'),
        ('auditor@agsa.gov.za', 'demo123', 'AGSA Auditor'),
    ]
    
    for username, password, expected_name in test_credentials:
        user_data = db.verify_password(username, password)
        if user_data:
            print(f"   ✓ {username}: {user_data['full_name']} ({user_data['role']})")
            assert user_data['full_name'] == expected_name, f"Name mismatch for {username}"
            assert user_data['is_active'], f"User {username} is not active"
        else:
            print(f"   ✗ {username}: FAILED TO AUTHENTICATE")
            return False
    
    # Test 2: Verify session configuration
    print("\n✓ Test 2: Checking session configuration...")
    session_config = {
        'PERMANENT_SESSION_LIFETIME': app.config['PERMANENT_SESSION_LIFETIME'],
        'SESSION_COOKIE_SECURE': app.config['SESSION_COOKIE_SECURE'],
        'SESSION_COOKIE_HTTPONLY': app.config['SESSION_COOKIE_HTTPONLY'],
        'SESSION_COOKIE_SAMESITE': app.config['SESSION_COOKIE_SAMESITE'],
        'SESSION_REFRESH_EACH_REQUEST': app.config['SESSION_REFRESH_EACH_REQUEST'],
    }
    
    for key, value in session_config.items():
        print(f"   ✓ {key}: {value}")
    
    # Test 3: Test Flask test client login
    print("\n✓ Test 3: Testing Flask test client login...")
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # Test GET login page
        response = client.get('/login')
        assert response.status_code == 200, f"Login page returned {response.status_code}"
        print("   ✓ GET /login: 200 OK")
        
        # Test POST login with valid credentials
        response = client.post('/login', data={
            'username': 'cfo@sadpmr.gov.za',
            'password': 'demo123'
        }, follow_redirects=True)
        
        # Should redirect to index
        assert response.status_code == 200, f"Login POST returned {response.status_code}"
        print("   ✓ POST /login with valid credentials: Success")
        
        # Check if we can access protected route
        response = client.get('/upload')
        assert response.status_code == 200, f"Protected /upload returned {response.status_code}"
        print("   ✓ Access to protected route /upload: Success")
        
        # Test invalid credentials
        response = client.post('/login', data={
            'username': 'cfo@sadpmr.gov.za',
            'password': 'wrongpassword'
        })
        assert response.status_code == 200, f"Invalid login returned {response.status_code}"
        assert b'Invalid username or password' in response.data, "Error message not shown"
        print("   ✓ POST /login with invalid credentials: Error message shown")
    
    print("\n" + "="*70)
    print("✓ ALL TESTS PASSED - LOGIN FUNCTIONALITY IS WORKING!")
    print("="*70)
    print("\n📍 You can now test the application at: http://localhost:5000")
    print("🔓 Login with: cfo@sadpmr.gov.za / demo123")
    print()
    
    return True

if __name__ == '__main__':
    try:
        success = test_login_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
