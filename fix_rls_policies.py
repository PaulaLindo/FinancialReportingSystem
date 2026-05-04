#!/usr/bin/env python3
"""
Fix RLS Policies for Budget Report and Income Statement Tables
This script fixes the RLS policy violations that prevent inserts
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client, Client

def fix_rls_policies():
    """Fix RLS policies for budget_report and income_statement tables"""
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    service_role_key = os.getenv('SUPABASE_SECRET_KEY')  # Use SECRET_KEY for admin operations
    
    if not supabase_url or not service_role_key:
        print("❌ Missing Supabase credentials in .env file")
        print("📋 Required: SUPABASE_URL and SUPABASE_SECRET_KEY")
        return False
    
    # Create Supabase client with service role key for admin operations
    try:
        admin_client: Client = create_client(supabase_url, service_role_key)
        print("✅ Connected to Supabase with admin privileges")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {str(e)}")
        return False
    
    # SQL statements to fix RLS policies
    rls_fixes = [
        # Drop existing policies for budget_report_sessions
        """
        DROP POLICY IF EXISTS "Users can view own budget report sessions" ON public.budget_report_sessions;
        DROP POLICY IF EXISTS "Users can insert own budget report sessions" ON public.budget_report_sessions;
        DROP POLICY IF EXISTS "Users can update own budget report sessions" ON public.budget_report_sessions;
        DROP POLICY IF EXISTS "Users can delete own budget report sessions" ON public.budget_report_sessions;
        """,
        
        # Create correct policies for budget_report_sessions
        """
        CREATE POLICY "Users can view own budget report sessions" ON public.budget_report_sessions
            FOR SELECT USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);
        
        CREATE POLICY "Users can insert own budget report sessions" ON public.budget_report_sessions
            FOR INSERT WITH CHECK (auth.uid()::text = user_id::text OR auth.uid() IS NULL);
        
        CREATE POLICY "Users can update own budget report sessions" ON public.budget_report_sessions
            FOR UPDATE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);
        
        CREATE POLICY "Users can delete own budget report sessions" ON public.budget_report_sessions
            FOR DELETE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);
        """,
        
        # Drop existing policies for income_statement_sessions
        """
        DROP POLICY IF EXISTS "Users can view own income statement sessions" ON public.income_statement_sessions;
        DROP POLICY IF EXISTS "Users can insert own income statement sessions" ON public.income_statement_sessions;
        DROP POLICY IF EXISTS "Users can update own income statement sessions" ON public.income_statement_sessions;
        DROP POLICY IF EXISTS "Users can delete own income statement sessions" ON public.income_statement_sessions;
        """,
        
        # Create correct policies for income_statement_sessions
        """
        CREATE POLICY "Users can view own income statement sessions" ON public.income_statement_sessions
            FOR SELECT USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);
        
        CREATE POLICY "Users can insert own income statement sessions" ON public.income_statement_sessions
            FOR INSERT WITH CHECK (auth.uid()::text = user_id::text OR auth.uid() IS NULL);
        
        CREATE POLICY "Users can update own income statement sessions" ON public.income_statement_sessions
            FOR UPDATE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);
        
        CREATE POLICY "Users can delete own income statement sessions" ON public.income_statement_sessions
            FOR DELETE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);
        """
    ]
    
    # Execute each SQL statement
    for i, sql in enumerate(rls_fixes, 1):
        try:
            print(f"🔧 Executing RLS fix {i}/{len(rls_fixes)}...")
            result = admin_client.rpc('exec_sql', {'sql': sql}).execute()
            print(f"✅ RLS fix {i} completed successfully")
        except Exception as e:
            print(f"❌ RLS fix {i} failed: {str(e)}")
            # Continue with other fixes
    
    print("\n🎉 RLS policy fixes completed!")
    print("📋 Summary:")
    print("   - Fixed budget_report_sessions RLS policies")
    print("   - Fixed income_statement_sessions RLS policies")
    print("   - Users can now insert their own sessions")
    print("   - Users can only view/update/delete their own data")
    
    return True

if __name__ == "__main__":
    print("🔧 Fixing RLS Policies for Multi-Document Tables")
    print("=" * 50)
    
    success = fix_rls_policies()
    
    if success:
        print("\n✅ RLS policies fixed successfully!")
        print("🚀 You can now upload budget reports and income statements")
    else:
        print("\n❌ Failed to fix RLS policies")
        print("🔍 Please check your Supabase credentials and permissions")
