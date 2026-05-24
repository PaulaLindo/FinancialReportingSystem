#!/usr/bin/env python3
"""
Reset and recreate test user with correct password hash
"""

import os
from supabase import create_client
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

def reset_test_user():
    load_dotenv()

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')

    client = create_client(supabase_url, supabase_key)

    try:
        # Delete existing testuser
        delete_result = client.table('users').delete().eq('username', 'testuser').execute()
        print(f'Deleted existing testuser')
        
        # Create new test user with proper hash
        password = 'testpass123'
        password_hash = generate_password_hash(password)
        
        print(f'Generated hash: {password_hash}')
        print(f'Password verification test: {check_password_hash(password_hash, "testpass123")}')
        
        # Insert new user
        new_user = {
            'username': 'testuser',
            'password_hash': password_hash,
            'email': 'test@example.com',
            'role': 'FINANCE_MANAGER',
            'full_name': 'Test User',
            'is_active': True
        }
        
        result = client.table('users').insert(new_user).execute()
        print('New test user created successfully!')
        print('Username: testuser')
        print('Password: testpass123')
        print('Go to: http://127.0.0.1:5000/login')
        
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    reset_test_user()
