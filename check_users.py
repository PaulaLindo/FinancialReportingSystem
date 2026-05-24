#!/usr/bin/env python3
"""
Check users in database
"""

import os
from supabase import create_client
from dotenv import load_dotenv

def check_users():
    load_dotenv()

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')

    if not supabase_url or not supabase_key:
        print("Missing Supabase credentials")
        return

    client = create_client(supabase_url, supabase_key)

    try:
        # Check if there are any users
        users_result = client.table('users').select('*').limit(5).execute()
        print(f'Users in database: {len(users_result.data)}')
        
        if users_result.data:
            for user in users_result.data:
                username = user.get('username', 'N/A')
                role = user.get('role', 'N/A')
                email = user.get('email', 'N/A')
                print(f'User: {username} - Role: {role} - Email: {email}')
        else:
            print('No users found in database')
            print('You need to create a test user or login first')
        
        # Check if there's a simple test user we can use
        test_user = client.table('users').select('*').eq('username', 'admin').execute()
        if test_user.data:
            print('\nTest user found: username=admin')
        else:
            print('\nNo admin user found. You may need to register first.')
            
    except Exception as e:
        print(f'Error checking users: {e}')

if __name__ == "__main__":
    check_users()
