#!/usr/bin/env python3
"""
Test password verification directly
"""

import os
from models.supabase_auth_models import supabase_auth
from dotenv import load_dotenv

def test_password_verification():
    load_dotenv()
    
    try:
        # Test password verification directly
        user_data = supabase_auth.verify_password('testuser', 'testpass123')
        
        if user_data:
            print('Password verification SUCCESS!')
            print(f'User: {user_data.get("username", "N/A")}')
            print(f'Role: {user_data.get("role", "N/A")}')
            print(f'Active: {user_data.get("is_active", False)}')
        else:
            print('Password verification FAILED!')
            
            # Check if user exists at all
            user_info = supabase_auth.get_user_by_username('testuser')
            if user_info:
                print('User exists but password verification failed')
                print('This might indicate a password hashing mismatch')
            else:
                print('User does not exist in database')
                
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    test_password_verification()
