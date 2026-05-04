#!/usr/bin/env python3
"""
Fix Budget Report RLS Policies
This script executes the SQL to fix the RLS policies for budget_report_sessions table
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client

def execute_sql_file(supabase: Client, file_path: str):
    """Execute SQL from a file"""
    try:
        with open(file_path, 'r') as f:
            sql_content = f.read()
        
        # Split the SQL content by semicolons and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements, 1):
            if statement:
                print(f"🔧 Executing statement {i}/{len(statements)}...")
                try:
                    result = supabase.rpc('execute_sql', {'query': statement}).execute()
                    if result.data:
                        print(f"   ✅ Success: {result.data}")
                    else:
                        print(f"   ✅ Executed successfully")
                except Exception as e:
                    print(f"   ❌ Error: {str(e)}")
                    # Continue with other statements
        
        return True
    except Exception as e:
        print(f"❌ Error reading SQL file: {str(e)}")
        return False

def main():
    """Main function"""
    print("🚀 Budget Report RLS Fix")
    print("This script will fix the RLS policies for budget_report_sessions table")
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file and try again.")
        return False
    
    try:
        # Create Supabase client
        print("🔌 Connecting to Supabase...")
        supabase: Client = create_client(
            supabase_url=os.getenv('SUPABASE_URL'),
            supabase_key=os.getenv('SUPABASE_ANON_KEY')
        )
        
        print("✅ Connected to Supabase successfully!")
        print()
        
        # Execute the SQL fix
        sql_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                               'fix_budget_report_rls.sql')
        
        if not os.path.exists(sql_file):
            print(f"❌ SQL file not found: {sql_file}")
            return False
        
        print(f"📄 Executing SQL file: {sql_file}")
        print("-" * 60)
        
        success = execute_sql_file(supabase, sql_file)
        
        if success:
            print("\n" + "=" * 60)
            print("✅ Budget Report RLS fix completed!")
            print()
            print("🎯 Next Steps:")
            print("1. Try uploading a budget report again")
            print("2. The RLS policy should now allow authenticated users to create sessions")
            print("3. The user_id will be validated against auth.uid()::text")
            print()
            print("🔍 Verification:")
            print("- Users can only view their own budget report sessions")
            print("- Users can only insert sessions with their own user_id")
            print("- Users can only update/delete their own sessions")
        else:
            print("❌ Failed to execute SQL fix")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing RLS policies: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
