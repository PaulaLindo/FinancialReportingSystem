#!/usr/bin/env python3
"""
Create a test user with known password for development
"""

import os
from supabase import create_client
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

def create_test_user():
    load_dotenv()

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')

    if not supabase_url or not supabase_key:
        print("Missing Supabase credentials")
        return False

    # Create password hash using Werkzeug (same as the auth system)
    password = "testpass123"
    password_hash = generate_password_hash(password)

    client = create_client(supabase_url, supabase_key)

    # Create test user with known password
    test_user = {
        'id': str(uuid.uuid4()),
        'username': 'testuser',
        'email': 'test@example.com',
        'password_hash': password_hash,
        'role': 'FINANCE_MANAGER',
        'full_name': 'Test User',
        'is_active': True,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

    try:
        # Check if user already exists
        existing = client.table('users').select('*').eq('username', 'testuser').execute()
        if existing.data:
            print('Test user already exists')
            print('Username: testuser')
            print('Password: testpass123')
            print('Go to: http://127.0.0.1:5000/login')
            return True

        # Insert test user
        result = client.table('users').insert(test_user).execute()
        print('Test user created successfully!')
        print('Username: testuser')
        print('Password: testpass123')
        print('Role: FINANCE_MANAGER')
        print('Go to: http://127.0.0.1:5000/login')
        
        return True
        
    except Exception as e:
        print(f'Error creating test user: {e}')
        return False

if __name__ == "__main__":
    create_test_user()
