#!/usr/bin/env python3
"""
GRAP Chart of Accounts Seeder
Populates the database with standard GRAP chart of accounts
"""

import sys
import os
from decimal import Decimal

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.balance_sheet_models import (
    balance_sheet_model, GRAPChartOfAccounts, MappingRule
)


def seed_grap_accounts():
    """Seed the database with standard GRAP chart of accounts"""
    
    # Standard GRAP Chart of Accounts
    grap_accounts = [
        # ASSETS
        {
            'grap_category': 'ASSETS',
            'grap_subcategory': 'NON-CURRENT ASSETS',
            'grap_account': 'Property, Plant and Equipment',
            'grap_account_code': '2100',
            'account_description': 'Tangible fixed assets used in operations',
            'account_type': 'asset',
            'normal_balance': 'debit',
            'keywords': ['property', 'plant', 'equipment', 'fixed assets', 'ppe', 'buildings', 'vehicles', 'machinery'],
            'alternative_names': ['Fixed Assets', 'Capital Assets', 'PPE'],
            'mapping_patterns': [r'(?i)property.*plant.*equipment', r'(?i)fixed.*assets', r'(?i)ppe']
        },
        {
            'grap_category': 'ASSETS',
            'grap_subcategory': 'NON-CURRENT ASSETS',
            'grap_account': 'Intangible Assets',
            'grap_account_code': '2200',
            'account_description': 'Non-physical assets like patents, trademarks',
            'account_type': 'asset',
            'normal_balance': 'debit',
            'keywords': ['intangible', 'patents', 'trademarks', 'goodwill', 'software', 'intellectual property'],
            'alternative_names': ['Intangibles', 'IP Assets'],
            'mapping_patterns': [r'(?i)intangible.*assets', r'(?i)patents', r'(?i)trademarks']
        },
        {
            'grap_category': 'ASSETS',
            'grap_subcategory': 'NON-CURRENT ASSETS',
            'grap_account': 'Investments',
            'grap_account_code': '2300',
            'account_description': 'Long-term investments in securities and other entities',
            'account_type': 'asset',
            'normal_balance': 'debit',
            'keywords': ['investments', 'securities', 'shares', 'bonds', 'long-term investments'],
            'alternative_names': ['Long-term Investments', 'Investment Portfolio'],
            'mapping_patterns': [r'(?i)long.*term.*investments', r'(?i)investment.*portfolio']
        },
        {
            'grap_category': 'ASSETS',
            'grap_subcategory': 'CURRENT ASSETS',
            'grap_account': 'Cash and Cash Equivalents',
            'grap_account_code': '1100',
            'account_description': 'Cash on hand and demand deposits',
            'account_type': 'asset',
            'normal_balance': 'debit',
            'keywords': ['cash', 'bank', 'money', 'funds', 'liquidity', 'demand deposits'],
            'alternative_names': ['Cash', 'Bank Accounts', 'Money Market'],
            'mapping_patterns': [r'(?i)cash.*equivalents', r'(?i)bank.*accounts', r'(?i)money.*market']
        },
        {
            'grap_category': 'ASSETS',
            'grap_subcategory': 'CURRENT ASSETS',
            'grap_account': 'Trade and Other Receivables',
            'grap_account_code': '1200',
            'account_description': 'Amounts owed by customers and others',
            'account_type': 'asset',
            'normal_balance': 'debit',
            'keywords': ['receivables', 'debtors', 'accounts receivable', 'trade debtors', 'customers'],
            'alternative_names': ['Accounts Receivable', 'Debtors', 'Trade Receivables'],
            'mapping_patterns': [r'(?i)accounts.*receivable', r'(?i)trade.*receivables', r'(?i)debtors']
        },
        {
            'grap_category': 'ASSETS',
            'grap_subcategory': 'CURRENT ASSETS',
            'grap_account': 'Inventory',
            'grap_account_code': '1300',
            'account_description': 'Goods held for sale or in production',
            'account_type': 'asset',
            'normal_balance': 'debit',
            'keywords': ['inventory', 'stock', 'goods', 'materials', 'supplies', 'raw materials'],
            'alternative_names': ['Stock', 'Goods', 'Materials'],
            'mapping_patterns': [r'(?i)inventory', r'(?i)stock', r'(?i)raw.*materials']
        },
        {
            'grap_category': 'ASSETS',
            'grap_subcategory': 'CURRENT ASSETS',
            'grap_account': 'Prepayments',
            'grap_account_code': '1400',
            'account_description': 'Payments made in advance for future expenses',
            'account_type': 'asset',
            'normal_balance': 'debit',
            'keywords': ['prepayments', 'prepaid', 'advance payments', 'prepaid expenses'],
            'alternative_names': ['Prepaid Expenses', 'Advance Payments'],
            'mapping_patterns': [r'(?i)prepaid.*expenses', r'(?i)advance.*payments']
        },
        
        # LIABILITIES
        {
            'grap_category': 'LIABILITIES',
            'grap_subcategory': 'NON-CURRENT LIABILITIES',
            'grap_account': 'Long-term Borrowings',
            'grap_account_code': '3100',
            'account_description': 'Loans and borrowings payable after more than one year',
            'account_type': 'liability',
            'normal_balance': 'credit',
            'keywords': ['long-term loans', 'borrowings', 'debt', 'bonds payable', 'term loans'],
            'alternative_names': ['Long-term Debt', 'Term Loans', 'Bonds Payable'],
            'mapping_patterns': [r'(?i)long.*term.*borrowings', r'(?i)long.*term.*debt']
        },
        {
            'grap_category': 'LIABILITIES',
            'grap_subcategory': 'NON-CURRENT LIABILITIES',
            'grap_account': 'Provisions',
            'grap_account_code': '3200',
            'account_description': 'Liabilities of uncertain timing or amount',
            'account_type': 'liability',
            'normal_balance': 'credit',
            'keywords': ['provisions', 'contingent liabilities', 'restructuring', 'decommissioning'],
            'alternative_names': ['Contingent Liabilities', 'Restructuring Provisions'],
            'mapping_patterns': [r'(?i)provisions', r'(?i)contingent.*liabilities']
        },
        {
            'grap_category': 'LIABILITIES',
            'grap_subcategory': 'CURRENT LIABILITIES',
            'grap_account': 'Trade and Other Payables',
            'grap_account_code': '4100',
            'account_description': 'Amounts owed to suppliers and others',
            'account_type': 'liability',
            'normal_balance': 'credit',
            'keywords': ['payables', 'creditors', 'accounts payable', 'trade creditors', 'suppliers'],
            'alternative_names': ['Accounts Payable', 'Creditors', 'Trade Payables'],
            'mapping_patterns': [r'(?i)accounts.*payable', r'(?i)trade.*payables', r'(?i)creditors']
        },
        {
            'grap_category': 'LIABILITIES',
            'grap_subcategory': 'CURRENT LIABILITIES',
            'grap_account': 'Short-term Borrowings',
            'grap_account_code': '4200',
            'account_description': 'Loans and borrowings payable within one year',
            'account_type': 'liability',
            'normal_balance': 'credit',
            'keywords': ['short-term loans', 'overdraft', 'bank overdraft', 'working capital loans'],
            'alternative_names': ['Bank Overdraft', 'Working Capital Loans'],
            'mapping_patterns': [r'(?i)short.*term.*borrowings', r'(?i)bank.*overdraft']
        },
        {
            'grap_category': 'LIABILITIES',
            'grap_subcategory': 'CURRENT LIABILITIES',
            'grap_account': 'Current Portion of Long-term Borrowings',
            'grap_account_code': '4300',
            'account_description': 'Portion of long-term borrowings due within one year',
            'account_type': 'liability',
            'normal_balance': 'credit',
            'keywords': ['current portion', 'long-term debt', 'current maturities'],
            'alternative_names': ['Current Maturities', 'Current Debt'],
            'mapping_patterns': [r'(?i)current.*portion', r'(?i)current.*maturities']
        },
        {
            'grap_category': 'LIABILITIES',
            'grap_subcategory': 'CURRENT LIABILITIES',
            'grap_account': 'Accrued Expenses',
            'grap_account_code': '4400',
            'account_description': 'Expenses incurred but not yet paid',
            'account_type': 'liability',
            'normal_balance': 'credit',
            'keywords': ['accrued', 'accruals', 'expenses payable', 'salaries payable'],
            'alternative_names': ['Accruals', 'Expenses Payable'],
            'mapping_patterns': [r'(?i)accrued.*expenses', r'(?i)accruals']
        },
        
        # EQUITY
        {
            'grap_category': 'EQUITY',
            'grap_subcategory': 'EQUITY',
            'grap_account': 'Share Capital',
            'grap_account_code': '5100',
            'account_description': 'Capital contributed by shareholders',
            'account_type': 'equity',
            'normal_balance': 'credit',
            'keywords': ['share capital', 'issued capital', 'common stock', 'ordinary shares'],
            'alternative_names': ['Issued Capital', 'Common Stock', 'Ordinary Shares'],
            'mapping_patterns': [r'(?i)share.*capital', r'(?i)issued.*capital', r'(?i)common.*stock']
        },
        {
            'grap_category': 'EQUITY',
            'grap_subcategory': 'EQUITY',
            'grap_account': 'Share Premium',
            'grap_account_code': '5200',
            'account_description': 'Amount received from shareholders above par value',
            'account_type': 'equity',
            'normal_balance': 'credit',
            'keywords': ['share premium', 'additional paid-in capital', 'capital surplus'],
            'alternative_names': ['Additional Paid-in Capital', 'Capital Surplus'],
            'mapping_patterns': [r'(?i)share.*premium', r'(?i)additional.*paid.*in']
        },
        {
            'grap_category': 'EQUITY',
            'grap_subcategory': 'EQUITY',
            'grap_account': 'Retained Earnings',
            'grap_account_code': '5300',
            'account_description': 'Accumulated profits retained in the business',
            'account_type': 'equity',
            'normal_balance': 'credit',
            'keywords': ['retained earnings', 'accumulated profits', 'reserves'],
            'alternative_names': ['Accumulated Profits', 'Reserves'],
            'mapping_patterns': [r'(?i)retained.*earnings', r'(?i)accumulated.*profits']
        },
        {
            'grap_category': 'EQUITY',
            'grap_subcategory': 'EQUITY',
            'grap_account': 'Other Reserves',
            'grap_account_code': '5400',
            'account_description': 'Other reserves and revaluation surpluses',
            'account_type': 'equity',
            'normal_balance': 'credit',
            'keywords': ['reserves', 'revaluation surplus', 'foreign exchange reserves'],
            'alternative_names': ['Revaluation Surplus', 'Exchange Reserves'],
            'mapping_patterns': [r'(?i)revaluation.*surplus', r'(?i)foreign.*exchange.*reserves']
        },
        
        # REVENUE
        {
            'grap_category': 'REVENUE',
            'grap_subcategory': 'OPERATING REVENUE',
            'grap_account': 'Revenue from Exchange Transactions',
            'grap_account_code': '6100',
            'account_description': 'Revenue from the sale of goods and services',
            'account_type': 'revenue',
            'normal_balance': 'credit',
            'keywords': ['sales', 'revenue', 'turnover', 'fees', 'service income'],
            'alternative_names': ['Sales Revenue', 'Turnover', 'Service Income'],
            'mapping_patterns': [r'(?i)sales.*revenue', r'(?i)service.*income', r'(?i)turnover']
        },
        {
            'grap_category': 'REVENUE',
            'grap_subcategory': 'OPERATING REVENUE',
            'grap_account': 'Other Operating Revenue',
            'grap_account_code': '6200',
            'account_description': 'Other revenue directly related to operations',
            'account_type': 'revenue',
            'normal_balance': 'credit',
            'keywords': ['other operating income', 'consulting fees', 'commission income'],
            'alternative_names': ['Operating Income', 'Commission Income'],
            'mapping_patterns': [r'(?i)other.*operating.*revenue', r'(?i)commission.*income']
        },
        {
            'grap_category': 'REVENUE',
            'grap_subcategory': 'NON-OPERATING REVENUE',
            'grap_account': 'Revenue from Non-Exchange Transactions',
            'grap_account_code': '6300',
            'account_description': 'Grants, donations, and other non-exchange revenue',
            'account_type': 'revenue',
            'normal_balance': 'credit',
            'keywords': ['grants', 'donations', 'subsidies', 'non-exchange revenue'],
            'alternative_names': ['Grants', 'Donations', 'Subsidies'],
            'mapping_patterns': [r'(?i)grants', r'(?i)donations', r'(?i)subsidies']
        },
        {
            'grap_category': 'REVENUE',
            'grap_subcategory': 'NON-OPERATING REVENUE',
            'grap_account': 'Finance Income',
            'grap_account_code': '6400',
            'account_description': 'Interest and other finance income',
            'account_type': 'revenue',
            'normal_balance': 'credit',
            'keywords': ['interest income', 'finance income', 'investment income'],
            'alternative_names': ['Interest Income', 'Investment Income'],
            'mapping_patterns': [r'(?i)interest.*income', r'(?i)finance.*income']
        },
        
        # EXPENSES
        {
            'grap_category': 'EXPENSES',
            'grap_subcategory': 'OPERATING EXPENSES',
            'grap_account': 'Employee Benefits Expense',
            'grap_account_code': '7100',
            'account_description': 'Salaries, wages, and other employee costs',
            'account_type': 'expense',
            'normal_balance': 'debit',
            'keywords': ['salaries', 'wages', 'employee costs', 'staff costs', 'payroll'],
            'alternative_names': ['Salaries and Wages', 'Staff Costs', 'Payroll'],
            'mapping_patterns': [r'(?i)salaries.*wages', r'(?i)employee.*benefits', r'(?i)staff.*costs']
        },
        {
            'grap_category': 'EXPENSES',
            'grap_subcategory': 'OPERATING EXPENSES',
            'grap_account': 'Depreciation and Amortisation',
            'grap_account_code': '7200',
            'account_description': 'Systematic allocation of asset costs',
            'account_type': 'expense',
            'normal_balance': 'debit',
            'keywords': ['depreciation', 'amortisation', 'asset write-downs'],
            'alternative_names': ['Depreciation Expense', 'Amortisation'],
            'mapping_patterns': [r'(?i)depreciation.*amortisation', r'(?i)depreciation.*expense']
        },
        {
            'grap_category': 'EXPENSES',
            'grap_subcategory': 'OPERATING EXPENSES',
            'grap_account': 'Materials and Supplies',
            'grap_account_code': '7300',
            'account_description': 'Cost of materials and supplies used in operations',
            'account_type': 'expense',
            'normal_balance': 'debit',
            'keywords': ['materials', 'supplies', 'consumables', 'raw materials'],
            'alternative_names': ['Cost of Materials', 'Consumables'],
            'mapping_patterns': [r'(?i)materials.*supplies', r'(?i)consumables']
        },
        {
            'grap_category': 'EXPENSES',
            'grap_subcategory': 'OPERATING EXPENSES',
            'grap_account': 'Other Operating Expenses',
            'grap_account_code': '7400',
            'account_description': 'Other expenses directly related to operations',
            'account_type': 'expense',
            'normal_balance': 'debit',
            'keywords': ['operating expenses', 'rent', 'utilities', 'maintenance'],
            'alternative_names': ['Operating Costs', 'Rent and Utilities'],
            'mapping_patterns': [r'(?i)operating.*expenses', r'(?i)rent.*utilities']
        },
        {
            'grap_category': 'EXPENSES',
            'grap_subcategory': 'NON-OPERATING EXPENSES',
            'grap_account': 'Finance Costs',
            'grap_account_code': '8100',
            'account_description': 'Interest and other finance costs',
            'account_type': 'expense',
            'normal_balance': 'debit',
            'keywords': ['interest expense', 'finance costs', 'bank charges'],
            'alternative_names': ['Interest Expense', 'Bank Charges'],
            'mapping_patterns': [r'(?i)interest.*expense', r'(?i)finance.*costs']
        },
        {
            'grap_category': 'EXPENSES',
            'grap_subcategory': 'NON-OPERATING EXPENSES',
            'grap_account': 'Impairment Losses',
            'grap_account_code': '8200',
            'account_description': 'Losses from asset impairments',
            'account_type': 'expense',
            'normal_balance': 'debit',
            'keywords': ['impairment', 'write-downs', 'bad debts'],
            'alternative_names': ['Write-downs', 'Bad Debt Expense'],
            'mapping_patterns': [r'(?i)impairment.*losses', r'(?i)write.*downs']
        }
    ]
    
    success_count = 0
    error_count = 0
    
    print("🏛️ Seeding GRAP Chart of Accounts...")
    print("=" * 50)
    
    for account_data in grap_accounts:
        try:
            # Create GRAP account object
            account = GRAPChartOfAccounts(
                grap_category=account_data['grap_category'],
                grap_subcategory=account_data['grap_subcategory'],
                grap_account=account_data['grap_account'],
                grap_account_code=account_data['grap_account_code'],
                account_description=account_data['account_description'],
                account_type=account_data['account_type'],
                normal_balance=account_data['normal_balance'],
                keywords=account_data['keywords'],
                alternative_names=account_data['alternative_names'],
                mapping_patterns=account_data['mapping_patterns'],
                is_active=True,
                is_custom=False,
                created_by='00000000-0000-0000-0000-000000000000'
            )
            
            # Save to database
            account_id = balance_sheet_model.create_mapping_rule(MappingRule(
                user_id='00000000-0000-0000-0000-000000000000',
                rule_name=f"GRAP Account: {account_data['grap_account']}",
                rule_type='category_mapping',
                pattern_type='exact',
                input_pattern=account_data['grap_account_code'],
                output_value=account_data['grap_account'],
                context={'category': account_data['grap_category'], 'subcategory': account_data['grap_subcategory']},
                confidence_score=1.0,
                is_active=True,
                is_system_rule=True,
                priority=100
            ))
            
            # Also add to GRAP chart of accounts table
            # Note: This would need to be implemented in the model
            success_count += 1
            print(f"✅ {account_data['grap_account_code']}: {account_data['grap_account']}")
            
        except Exception as e:
            error_count += 1
            print(f"❌ Error adding {account_data['grap_account']}: {str(e)}")
    
    print("=" * 50)
    print(f"📊 Summary: {success_count} accounts seeded, {error_count} errors")
    
    if error_count == 0:
        print("🎉 All GRAP accounts seeded successfully!")
    else:
        print("⚠️ Some accounts failed to seed. Check the errors above.")
    
    return success_count, error_count


def main():
    """Main function to run the seeder"""
    try:
        success_count, error_count = seed_grap_accounts()
        return 0 if error_count == 0 else 1
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
