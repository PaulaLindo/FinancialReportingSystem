#!/usr/bin/env python3
"""
Check available transactions in database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.supabase_auth_models import supabase_auth

def main():
    print("🔍 Checking available transactions...")
    
    try:
        # Initialize Supabase client
        supabase = supabase_auth.client
        
        # Check different transaction tables
        tables_to_check = [
            'financial_statements',
            'balance_sheets', 
            'income_statements',
            'budget_reports',
            'transactions',
            'documents'
        ]
        
        for table in tables_to_check:
            print(f"\n📊 Checking {table} table...")
            try:
                result = supabase.table(table).select('*').limit(5).execute()
                print(f"✅ Found {len(result.data)} records in {table}")
                
                if result.data:
                    for record in result.data[:2]:  # Show first 2
                        print(f"   - ID: {record.get('id')}")
                        print(f"     Type: {record.get('document_type', record.get('type', 'N/A'))}")
                        print(f"     Status: {record.get('status', 'N/A')}")
                        print()
                else:
                    print("   No records found")
                    
            except Exception as e:
                print(f"   ❌ Error accessing {table}: {e}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
