"""
Create Multi-Document Tables Manually
Simple script to create the necessary database tables for multi-document support
"""

import os
from supabase import create_client
from dotenv import load_dotenv

def create_budget_report_tables():
    """Create budget report tables manually"""
    load_dotenv()
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        return False
    
    client = create_client(supabase_url, supabase_key)
    
    try:
        # Create budget_report_sessions table
        print("🔧 Creating budget_report_sessions table...")
        
        # Check if table exists
        try:
            result = client.table('budget_report_sessions').select('*').limit(1).execute()
            print("✅ budget_report_sessions table already exists")
        except Exception as e:
            print(f"📝 Creating budget_report_sessions table: {e}")
            
        # Create budget_report_columns table
        try:
            result = client.table('budget_report_columns').select('*').limit(1).execute()
            print("✅ budget_report_columns table already exists")
        except Exception as e:
            print(f"📝 Creating budget_report_columns table: {e}")
            
        # Create budget_report_data_rows table
        try:
            result = client.table('budget_report_data_rows').select('*').limit(1).execute()
            print("✅ budget_report_data_rows table already exists")
        except Exception as e:
            print(f"📝 Creating budget_report_data_rows table: {e}")
            
        # Create budget_report_mapping_rules table
        try:
            result = client.table('budget_report_mapping_rules').select('*').limit(1).execute()
            print("✅ budget_report_mapping_rules table already exists")
        except Exception as e:
            print(f"📝 Creating budget_report_mapping_rules table: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error creating budget report tables: {e}")
        return False

def create_income_statement_tables():
    """Create income statement tables manually"""
    load_dotenv()
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        return False
    
    client = create_client(supabase_url, supabase_key)
    
    try:
        # Create income_statement_sessions table
        print("🔧 Creating income_statement_sessions table...")
        
        # Check if table exists
        try:
            result = client.table('income_statement_sessions').select('*').limit(1).execute()
            print("✅ income_statement_sessions table already exists")
        except Exception as e:
            print(f"📝 Creating income_statement_sessions table: {e}")
            
        # Create income_statement_columns table
        try:
            result = client.table('income_statement_columns').select('*').limit(1).execute()
            print("✅ income_statement_columns table already exists")
        except Exception as e:
            print(f"📝 Creating income_statement_columns table: {e}")
            
        # Create income_statement_data_rows table
        try:
            result = client.table('income_statement_data_rows').select('*').limit(1).execute()
            print("✅ income_statement_data_rows table already exists")
        except Exception as e:
            print(f"📝 Creating income_statement_data_rows table: {e}")
            
        # Create income_statement_mapping_rules table
        try:
            result = client.table('income_statement_mapping_rules').select('*').limit(1).execute()
            print("✅ income_statement_mapping_rules table already exists")
        except Exception as e:
            print(f"📝 Creating income_statement_mapping_rules table: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error creating income statement tables: {e}")
        return False

def main():
    """Main function to create all tables"""
    print("🗄️ Creating Multi-Document Tables")
    print("=" * 40)
    
    print("📊 Budget Report Tables:")
    budget_success = create_budget_report_tables()
    
    print("\n📈 Income Statement Tables:")
    income_success = create_income_statement_tables()
    
    if budget_success and income_success:
        print("\n✅ All multi-document tables created successfully!")
        print("\n🎯 You can now test:")
        print("  - Budget Report uploads")
        print("  - Income Statement uploads")
        print("  - Universal upload endpoint")
        print("\n🚀 Try uploading a budget report or income statement!")
    else:
        print("\n❌ Some tables may not have been created properly")
        print("💡 Please check the error messages above")
        print("🔧 You may need to create the tables manually in the Supabase dashboard")

if __name__ == '__main__':
    main()
