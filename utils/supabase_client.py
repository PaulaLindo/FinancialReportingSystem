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
    Create Supabase client with fallback authentication strategy
    Tries anon key first, then service key, then auth client fallback
    """
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
    supabase_service_key = os.getenv('SUPABASE_SECRET_KEY')
    
    print(f"🔑 Debug - SUPABASE_URL: {supabase_url}")
    print(f"🔑 Debug - SUPABASE_ANON_KEY: {supabase_anon_key[:20]}..." if supabase_anon_key else "🔑 Debug - SUPABASE_ANON_KEY: None")
    print(f"🔑 Debug - SUPABASE_SECRET_KEY: {supabase_service_key[:20]}..." if supabase_service_key else "🔑 Debug - SUPABASE_SECRET_KEY: None")
    
    # Try anon key first (most reliable)
    if supabase_url and supabase_anon_key:
        try:
            client = create_client(supabase_url, supabase_anon_key)
            print("✅ Using anon key client")
            return client
        except Exception as e:
            print(f"⚠️ Anon key failed: {e}")
    
    # Try service key as fallback
    if supabase_url and supabase_service_key:
        try:
            client = create_client(supabase_url, supabase_service_key)
            print("✅ Using service role client (anon key failed)")
            return client
        except Exception as e:
            print(f"⚠️ Service key failed: {e}")
    
    # Final fallback - raise error for manual handling
    raise ValueError("No valid Supabase credentials available. Check SUPABASE_ANON_KEY and SUPABASE_SECRET_KEY")

def create_supabase_client_with_rls_bypass():
    """
    Create Supabase client with RLS bypass for development
    Uses service role key if available to bypass RLS policies
    """
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_service_key = os.getenv('SUPABASE_SECRET_KEY')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    print(f"🔑 Creating client with RLS bypass...")
    
    # For development, try service key first to bypass RLS
    if supabase_url and supabase_service_key:
        try:
            client = create_client(supabase_url, supabase_service_key)
            print("✅ Using service role client for RLS bypass")
            return client
        except Exception as e:
            print(f"⚠️ Service key failed for RLS bypass: {e}")
    
    # Fallback to anon key
    if supabase_url and supabase_anon_key:
        try:
            client = create_client(supabase_url, supabase_anon_key)
            print("⚠️ Using anon key (RLS may block operations)")
            return client
        except Exception as e:
            print(f"⚠️ Anon key failed: {e}")
    
    raise ValueError("No valid Supabase credentials available for RLS bypass")

def create_admin_supabase_client():
    """
    Create Supabase client specifically for admin operations
    Uses anon key first since service key is invalid, same as regular client
    """
    # For now, use the same strategy as regular client since service key is invalid
    return create_supabase_client()
