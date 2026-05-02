#!/usr/bin/env python3
"""
Database Table Checker with Available Keys
Check what tables exist using the available Supabase keys
"""

import os
from dotenv import load_dotenv

def check_database_with_anon_key():
    """Check database using ANON key (limited permissions)"""
    print("🔍 Checking Database Tables with Available Keys...")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    
    # Check available keys
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
    supabase_secret_key = os.getenv('SUPABASE_SECRET_KEY')
    
    print(f"SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Missing'}")
    print(f"SUPABASE_ANON_KEY: {'✅ Set' if supabase_anon_key else '❌ Missing'}")
    print(f"SUPABASE_SECRET_KEY: {'✅ Set' if supabase_secret_key else '❌ Missing (commented out)'}")
    
    if not supabase_url or not supabase_anon_key:
        print("\n❌ Missing required environment variables")
        return False
    
    try:
        from supabase import create_client
        print("\n✅ Supabase client imported")
        
        # Use ANON key for basic connection
        key_to_use = supabase_anon_key
        key_type = "ANON"
        
        if supabase_secret_key and not supabase_secret_key.startswith('#'):
            key_to_use = supabase_secret_key
            key_type = "SERVICE_ROLE"
        
        print(f"🔑 Using {key_type} key for connection...")
        
        supabase = create_client(supabase_url, key_to_use)
        print("✅ Supabase client created")
        
        # Try to check some common tables that might exist
        print("\n🔍 Checking for common tables...")
        
        # List of tables we expect to find
        expected_tables = [
            'balance_sheet_sessions',
            'balance_sheet_columns', 
            'balance_sheet_data',
            'trial_balance_sessions',
            'trial_balance_columns',
            'trial_balance_data',
            'users',
            'grap_chart_of_accounts',
            'mapping_rules'
        ]
        
        found_tables = []
        missing_tables = []
        
        for table_name in expected_tables:
            try:
                # Try to select from the table (this will test if it exists)
                result = supabase.table(table_name).select('count', count='exact').execute()
                
                if result.data is not None:
                    count = result.count if hasattr(result, 'count') else 'unknown'
                    found_tables.append((table_name, count))
                    print(f"✅ {table_name}: Found ({count} rows)")
                else:
                    missing_tables.append(table_name)
                    print(f"❌ {table_name}: Not found or no access")
                    
            except Exception as e:
                missing_tables.append(table_name)
                error_msg = str(e).lower()
                if 'permission denied' in error_msg or 'does not exist' in error_msg:
                    print(f"❌ {table_name}: Not found or no access")
                else:
                    print(f"❌ {table_name}: Error - {str(e)[:50]}...")
        
        print("\n" + "=" * 60)
        print("📊 SUMMARY:")
        print(f"✅ Found tables: {len(found_tables)}")
        print(f"❌ Missing tables: {len(missing_tables)}")
        
        if found_tables:
            print("\n🟢 FOUND TABLES:")
            for table_name, count in found_tables:
                if 'trial_balance' in table_name.lower():
                    print(f"   🔴 {table_name}: {count} rows (NEEDS MIGRATION)")
                elif 'balance_sheet' in table_name.lower():
                    print(f"   🟢 {table_name}: {count} rows (ALREADY UPDATED)")
                else:
                    print(f"   ⚪ {table_name}: {count} rows")
        
        if missing_tables:
            print("\n🔴 MISSING TABLES:")
            for table_name in missing_tables:
                print(f"   - {table_name}")
        
        # Migration recommendations
        print("\n🎯 MIGRATION ANALYSIS:")
        trial_balance_found = any('trial_balance' in t[0].lower() for t in found_tables)
        balance_sheet_found = any('balance_sheet' in t[0].lower() for t in found_tables)
        
        if trial_balance_found and not balance_sheet_found:
            print("📋 STATUS: Need to migrate from trial_balance to balance_sheet")
            print("🔧 ACTION: Create balance_sheet tables and migrate data")
        elif balance_sheet_found and not trial_balance_found:
            print("✅ STATUS: Migration appears complete")
            print("🔧 ACTION: No database changes needed")
        elif trial_balance_found and balance_sheet_found:
            print("⚠️  STATUS: Both table types exist")
            print("🔧 ACTION: Need to migrate data and drop old tables")
        else:
            print("❓ STATUS: No relevant tables found")
            print("🔧 ACTION: May need to create initial database schema")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install supabase package: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    check_database_with_anon_key()
