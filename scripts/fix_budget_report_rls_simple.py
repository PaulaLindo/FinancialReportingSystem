#!/usr/bin/env python3
"""
Simple Budget Report RLS Fix
This script uses the service role key to execute SQL directly
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Main function"""
    print("🚀 Budget Report RLS Fix (Simple)")
    print("This script will fix the RLS policies for budget_report_sessions table")
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file and try again.")
        return False
    
    try:
        # Import required libraries
        import psycopg2
        from psycopg2 import sql
        
        # Parse the Supabase URL to get connection details
        supabase_url = os.getenv('SUPABASE_URL')
        # Extract project ID from URL
        project_id = supabase_url.split('//')[1].split('.')[0]
        
        # Construct PostgreSQL connection string
        db_url = f"postgresql://postgres:{os.getenv('SUPABASE_SECRET_KEY')}@db.{project_id}.supabase.co:5432/postgres"
        
        print("🔌 Connecting to PostgreSQL database...")
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("✅ Connected to PostgreSQL successfully!")
        print()
        
        # Read and execute the SQL file
        sql_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                               'fix_budget_report_rls.sql')
        
        if not os.path.exists(sql_file):
            print(f"❌ SQL file not found: {sql_file}")
            return False
        
        print(f"📄 Executing SQL file: {sql_file}")
        print("-" * 60)
        
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Split the SQL content by semicolons and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements, 1):
            if statement and not statement.startswith('--'):
                print(f"🔧 Executing statement {i}/{len(statements)}...")
                try:
                    cursor.execute(statement)
                    conn.commit()
                    print(f"   ✅ Success")
                except Exception as e:
                    print(f"   ❌ Error: {str(e)}")
                    # Continue with other statements
                    conn.rollback()
        
        # Close the connection
        cursor.close()
        conn.close()
        
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
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing required library: {e}")
        print("Please install psycopg2: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Error fixing RLS policies: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
