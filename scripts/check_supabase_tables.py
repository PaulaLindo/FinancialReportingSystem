#!/usr/bin/env python3
"""
Check Current Tables in Supabase Database
This script will list all tables currently in the database to help us plan the migration from trial_balance to balance_sheet terminology.
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client
from models.supabase_auth_models import supabase_auth

def check_database_tables():
    """Check what tables currently exist in the Supabase database"""
    
    print("🔍 Checking Supabase Database Tables...")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
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
            supabase_key=os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        
        print("✅ Connected to Supabase successfully!")
        print()
        
        # Get all tables using information_schema
        print("📊 Fetching table information...")
        print("-" * 60)
        
        # Query to get all tables
        tables_query = """
        SELECT 
            table_name,
            table_type
        FROM 
            information_schema.tables
        WHERE 
            table_schema = 'public'
        ORDER BY 
            table_name;
        """
        
        result = supabase.rpc('execute_sql', {'query': tables_query}).execute()
        
        if result.data:
            print(f"Found {len(result.data)} tables in the database:")
            print()
            
            # Categorize tables
            trial_balance_tables = []
            balance_sheet_tables = []
            other_tables = []
            
            for table in result.data:
                table_name = table['table_name']
                table_type = table['table_type']
                
                if 'trial_balance' in table_name.lower():
                    trial_balance_tables.append(table_name)
                elif 'balance_sheet' in table_name.lower():
                    balance_sheet_tables.append(table_name)
                else:
                    other_tables.append(table_name)
            
            # Display tables by category
            if trial_balance_tables:
                print("🔴 TRIAL BALANCE TABLES (Need Migration):")
                for table in trial_balance_tables:
                    print(f"   - {table['table_name']} ({table['table_type']})")
                print()
            
            if balance_sheet_tables:
                print("🟢 BALANCE SHEET TABLES (Already Updated):")
                for table in balance_sheet_tables:
                    print(f"   - {table['table_name']} ({table['table_type']})")
                print()
            
            if other_tables:
                print("⚪ OTHER TABLES:")
                for table in other_tables:
                    print(f"   - {table['table_name']} ({table['table_type']})")
                print()
            
            # Show detailed table info for trial_balance tables
            if trial_balance_tables:
                print("🔍 Detailed Analysis of Trial Balance Tables:")
                print("-" * 60)
                
                for table in trial_balance_tables:
                    table_name = table['table_name']
                    print(f"\n📋 Table: {table_name}")
                    
                    # Get column information
                    columns_query = f"""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM 
                        information_schema.columns
                    WHERE 
                        table_schema = 'public' AND table_name = '{table_name}'
                    ORDER BY 
                        ordinal_position;
                    """
                    
                    try:
                        columns_result = supabase.rpc('execute_sql', {'query': columns_query}).execute()
                        
                        if columns_result.data:
                            print(f"   Columns ({len(columns_result.data)}):")
                            for col in columns_result.data:
                                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                                default_val = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                                print(f"   - {col['column_name']}: {col['data_type']} {nullable} {default_val}")
                        else:
                            print("   (No columns found)")
                    except Exception as col_error:
                        print(f"   ❌ Error getting columns: {str(col_error)}")
                    
                    # Check if table has data
                    try:
                        count_query = f"SELECT COUNT(*) as row_count FROM {table_name};"
                        count_result = supabase.rpc('execute_sql', {'query': count_query}).execute()
                        
                        if count_result.data:
                            row_count = count_result.data[0]['row_count']
                            print(f"   📊 Rows: {row_count}")
                            
                            if row_count > 0:
                                print(f"   ⚠️  WARNING: This table contains {row_count} rows that need migration!")
                        else:
                            print(f"   ✅ Table is empty")
                    except Exception as count_error:
                        print(f"   ❌ Error checking row count: {str(count_error)}")
                        
                except Exception as table_error:
                    print(f"   ❌ Error analyzing table {table_name}: {str(table_error)}")
            
            # Generate migration recommendations
            print("\n🎯 MIGRATION RECOMMENDATIONS:")
            print("=" * 60)
            
            if trial_balance_tables:
                print("📋 Tables that need to be renamed/updated:")
                for table in trial_balance_tables:
                    new_name = table['table_name'].replace('trial_balance', 'balance_sheet')
                    print(f"   - {table['table_name']} → {new_name}")
                print()
                
                print("📝 Recommended Actions:")
                print("   1. Create new balance_sheet tables with the same structure")
                print("   2. Migrate data from trial_balance tables to balance_sheet tables")
                print("   3. Update any views, functions, or stored procedures")
                print("   4. Drop old trial_balance tables (after backup)")
                print("   5. Update application code to use new table names")
                print("   6. Test the migration thoroughly")
                print()
                print("⚠️  IMPORTANT: Always backup your database before making structural changes!")
            else:
                print("✅ All tables already use balance_sheet terminology!")
                print("   No database migration required.")
            
        else:
            print("❌ No tables found in the database")
            print("   This might indicate:")
            print("   - Database connection issues")
            print("   - Empty database")
            print("   - Permission issues")
        
        print("\n" + "=" * 60)
        print("✅ Database check completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database tables: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Please check your Supabase configuration and try again.")
        return False

def main():
    """Main function"""
    print("🚀 Supabase Table Checker")
    print("This script will check what tables exist in your Supabase database")
    print("and help plan the migration from trial_balance to balance_sheet terminology.")
    print()
    
    success = check_database_tables()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
