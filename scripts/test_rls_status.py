#!/usr/bin/env python3
"""
Test RLS Status and Provide Clear Instructions
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils.supabase_client import create_supabase_client

def test_rls_status():
    """Test if RLS is blocking operations"""
    print("🔧 Testing RLS Status")
    print("=" * 50)
    
    try:
        client = create_supabase_client()
        print("✅ Connected to Supabase with anon key")
        
        # Test if we can read from trial_balance_sessions
        try:
            result = client.table('trial_balance_sessions').select('count').execute()
            print(f"✅ Can read trial_balance_sessions: {result.data}")
        except Exception as e:
            print(f"❌ Cannot read trial_balance_sessions: {e}")
        
        # Test if we can insert into trial_balance_sessions
        try:
            import uuid
            test_data = {
                'user_id': str(uuid.uuid4()),  # Proper UUID format
                'filename': 'test-filename',
                'status': 'test',
                'total_rows': 0,
                'total_columns': 0,
                'file_size_bytes': 0,
                'file_type': 'test',
                'file_format': 'test'
            }
            result = client.table('trial_balance_sessions').insert(test_data).execute()
            print(f"✅ Can insert into trial_balance_sessions: {result.data}")
            
            # Clean up test data
            if result.data:
                client.table('trial_balance_sessions').delete().eq('user_id', 'test-user-id').execute()
                print("✅ Cleaned up test data")
                
        except Exception as e:
            print(f"❌ Cannot insert into trial_balance_sessions: {e}")
            if '42501' in str(e):
                print("🚨 This is an RLS policy error!")
                print("📝 To fix this, you need to:")
                print("   1. Go to your Supabase dashboard")
                print("   2. Navigate to SQL Editor")
                print("   3. Run the SQL commands in scripts/disable_rls_dev.sql")
                print("   4. Or manually disable RLS on the tables")
        
    except Exception as e:
        print(f"❌ Failed to connect: {e}")

def main():
    """Main function"""
    test_rls_status()
    
    print("\n📋 Quick Fix Instructions:")
    print("=" * 50)
    print("1. Open Supabase Dashboard")
    print("2. Go to SQL Editor")
    print("3. Copy and paste the contents of scripts/disable_rls_dev.sql")
    print("4. Run the SQL commands")
    print("5. Try uploading a file again")
    
    print("\n🔗 SQL File Location:")
    print("   scripts/disable_rls_dev.sql")
    
    print("\n⚠️  Note: This disables RLS for development only!")
    print("   For production, you'll need valid service role keys")

if __name__ == "__main__":
    main()
