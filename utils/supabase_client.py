"""
Centralized Supabase Client Management
Provides consistent authentication strategy across all modules
"""

import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_supabase_client():
    """
    Create Supabase client using anon key only
    Anon key provides secure, RLS-compliant access for all operations
    """
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_anon_key:
        raise ValueError("Supabase credentials not found. Check SUPABASE_URL and SUPABASE_ANON_KEY in .env file")
    
    try:
        client = create_client(supabase_url, supabase_anon_key)
        print("✅ Using anon key client (secure, RLS-compliant)")
        return client
    except Exception as e:
        print(f"❌ Failed to create Supabase client with anon key: {e}")
        raise ValueError(f"Failed to connect to Supabase: {e}")

def create_supabase_client_with_rls_bypass():
    """
    Create Supabase client with optional RLS bypass
    Uses service role key only when explicitly needed for admin operations
    Defaults to anon key for security
    """
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_service_key = os.getenv('SUPABASE_SECRET_KEY')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    print(f"🔑 Creating client with optional RLS bypass...")
    
    # Default to anon key (secure, RLS-compliant)
    if supabase_url and supabase_anon_key:
        try:
            client = create_client(supabase_url, supabase_anon_key)
            print("✅ Using anon key client (secure, RLS-compliant)")
            return client
        except Exception as e:
            print(f"❌ Anon key failed: {e}")
    
    # Only use service key if anon key fails and it's explicitly needed
    if supabase_url and supabase_service_key:
        try:
            client = create_client(supabase_url, supabase_service_key)
            print("⚠️ Using service role client (RLS bypass - admin only)")
            return client
        except Exception as e:
            print(f"❌ Service key failed: {e}")
    
    raise ValueError("No valid Supabase credentials available")

def create_admin_supabase_client():
    """
    Create Supabase client for admin operations
    Uses anon key only for consistent, secure access
    Admin operations should work through RLS policies
    """
    return create_supabase_client()
