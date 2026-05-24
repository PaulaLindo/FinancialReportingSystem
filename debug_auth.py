#!/usr/bin/env python3
"""
Debug Supabase authentication
"""

import os
from models.supabase_auth_models import supabase_auth
from dotenv import load_dotenv

def debug_auth():
    load_dotenv()
    
    print("=== DEBUGGING SUPABASE AUTH ===")
    
    # Test the exact same credentials the browser is using
    test_username = 'finance.manager@sadpmr.gov.za'
    test_password = 'demo123'
    
    print(f"Testing credentials: {test_username} / {test_password}")
    
    try:
        user_data = supabase_auth.verify_password(test_username, test_password)
        
        if user_data:
            print("✅ Password verification SUCCESS!")
            print(f"User ID: {user_data.get('id')}")
            print(f"Username: {user_data.get('username')}")
            print(f"Role: {user_data.get('role')}")
            print(f"Full Name: {user_data.get('full_name')}")
            print(f"Is Active: {user_data.get('is_active')}")
        else:
            print("❌ Password verification FAILED!")
            
    except Exception as e:
        print(f"❌ Auth error: {e}")
    
    # Also test getting user by ID
    if user_data:
        user_id = user_data.get('id')
        print(f"\nTesting get_user_by_id with: {user_id}")
        
        try:
            user_by_id = supabase_auth.get_user_by_id(user_id)
            if user_by_id:
                print("✅ get_user_by_id SUCCESS!")
                print(f"Retrieved user: {user_by_id.get('username')}")
            else:
                print("❌ get_user_by_id FAILED!")
        except Exception as e:
            print(f"❌ get_user_by_id error: {e}")

if __name__ == "__main__":
    debug_auth()
