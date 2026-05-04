"""
Create proper Excel test files for multi-document system testing
"""

import pandas as pd
import os

def create_budget_report_balanced():
    """Create balanced budget report Excel file"""
    data = [
        ['DEPT-001', 'Salaries - Finance', 'Finance', 500000, 480000, -20000, -4.0],
        ['DEPT-002', 'Office Supplies', 'Finance', 25000, 26000, 1000, 4.0],
        ['DEPT-003', 'Software Licenses', 'Finance', 75000, 75000, 0, 0.0],
        ['DEPT-004', 'Training & Development', 'Finance', 30000, 28000, -2000, -6.7],
        ['DEPT-005', 'Travel Expenses', 'Finance', 40000, 42000, 2000, 5.0],
        ['DEPT-006', 'Marketing Campaigns', 'Marketing', 150000, 160000, 10000, 6.7],
        ['DEPT-007', 'Advertising', 'Marketing', 80000, 75000, -5000, -6.3],
        ['DEPT-008', 'Events & Sponsorships', 'Marketing', 45000, 48000, 3000, 6.7],
        ['DEPT-009', 'Equipment Maintenance', 'Operations', 60000, 55000, -5000, -8.3],
        ['DEPT-010', 'Utilities', 'Operations', 35000, 36000, 1000, 2.9],
        ['DEPT-011', 'Rent & Lease', 'Operations', 120000, 120000, 0, 0.0],
        ['DEPT-012', 'Insurance', 'Operations', 45000, 45000, 0, 0.0],
        ['DEPT-013', 'Professional Services', 'Admin', 30000, 32000, 2000, 6.7],
        ['DEPT-014', 'Legal Fees', 'Admin', 20000, 18000, -2000, -10.0],
        ['DEPT-015', 'Consulting Services', 'Admin', 40000, 42000, 2000, 5.0],
        ['DEPT-016', 'IT Infrastructure', 'IT', 80000, 85000, 5000, 6.3],
        ['DEPT-017', 'Cybersecurity', 'IT', 35000, 35000, 0, 0.0],
        ['DEPT-018', 'Data Backup & Recovery', 'IT', 15000, 14000, -1000, -6.7],
        ['DEPT-019', 'Research & Development', 'R&D', 200000, 190000, -10000, -5.0],
        ['DEPT-020', 'Prototype Development', 'R&D', 80000, 85000, 5000, 6.3],
        ['TOTAL', 'All Departments', 'ALL', 1500000, 1485000, -15000, -1.0]
    ]
    
    df = pd.DataFrame(data, columns=[
        'Account Code', 'Account Description', 'Department', 
        'Budget Amount', 'Actual Amount', 'Variance', 'Variance %'
    ])
    
    filepath = 'financial_documents/budget_reports/budget_report_balanced_excel.xlsx'
    df.to_excel(filepath, index=False)
    print(f"✅ Created balanced budget report: {filepath}")

def create_budget_report_unbalanced():
    """Create unbalanced budget report Excel file"""
    data = [
        ['DEPT-001', 'Salaries - Finance', 'Finance', 500000, 520000, 20000, 4.0],
        ['DEPT-002', 'Office Supplies', 'Finance', 25000, 28000, 3000, 12.0],
        ['DEPT-003', 'Software Licenses', 'Finance', 75000, 75000, 0, 0.0],
        ['DEPT-004', 'Training & Development', 'Finance', 30000, 35000, 5000, 16.7],
        ['DEPT-005', 'Travel Expenses', 'Finance', 40000, 45000, 5000, 12.5],
        ['DEPT-006', 'Marketing Campaigns', 'Marketing', 150000, 140000, -10000, -6.7],
        ['DEPT-007', 'Advertising', 'Marketing', 80000, 70000, -10000, -12.5],
        ['DEPT-008', 'Events & Sponsorships', 'Marketing', 45000, 50000, 5000, 11.1],
        ['DEPT-009', 'Equipment Maintenance', 'Operations', 60000, 65000, 5000, 8.3],
        ['DEPT-010', 'Utilities', 'Operations', 35000, 40000, 5000, 14.3],
        ['DEPT-011', 'Rent & Lease', 'Operations', 120000, 125000, 5000, 4.2],
        ['DEPT-012', 'Insurance', 'Operations', 45000, 45000, 0, 0.0],
        ['DEPT-013', 'Professional Services', 'Admin', 30000, 35000, 5000, 16.7],
        ['DEPT-014', 'Legal Fees', 'Admin', 20000, 25000, 5000, 25.0],
        ['DEPT-015', 'Consulting Services', 'Admin', 40000, 38000, -2000, -5.0],
        ['DEPT-016', 'IT Infrastructure', 'IT', 80000, 90000, 10000, 12.5],
        ['DEPT-017', 'Cybersecurity', 'IT', 35000, 40000, 5000, 14.3],
        ['DEPT-018', 'Data Backup & Recovery', 'IT', 15000, 18000, 3000, 20.0],
        ['DEPT-019', 'Research & Development', 'R&D', 200000, 180000, -20000, -10.0],
        ['DEPT-020', 'Prototype Development', 'R&D', 80000, 95000, 15000, 18.8],
        ['TOTAL', 'All Departments', 'ALL', 1500000, 1595000, 95000, 6.3]
    ]
    
    df = pd.DataFrame(data, columns=[
        'Account Code', 'Account Description', 'Department', 
        'Budget Amount', 'Actual Amount', 'Variance', 'Variance %'
    ])
    
    filepath = 'financial_documents/budget_reports/budget_report_unbalanced_excel.xlsx'
    df.to_excel(filepath, index=False)
    print(f"✅ Created unbalanced budget report: {filepath}")

def create_income_statement_balanced():
    """Create balanced income statement Excel file"""
    data = [
        ['REV-001', 'Consulting Services Revenue', 'Revenue', 250000, '2025-Q1'],
        ['REV-002', 'Training Revenue', 'Revenue', 150000, '2025-Q1'],
        ['REV-003', 'Software Licensing Revenue', 'Revenue', 180000, '2025-Q1'],
        ['REV-004', 'Maintenance Contracts Revenue', 'Revenue', 120000, '2025-Q1'],
        ['REV-005', 'Professional Services Revenue', 'Revenue', 200000, '2025-Q1'],
        ['REV-006', 'Support Services Revenue', 'Revenue', 80000, '2025-Q1'],
        ['EXP-001', 'Salaries & Wages', 'Expenses', 180000, '2025-Q1'],
        ['EXP-002', 'Employee Benefits', 'Expenses', 45000, '2025-Q1'],
        ['EXP-003', 'Office Rent', 'Expenses', 60000, '2025-Q1'],
        ['EXP-004', 'Utilities', 'Expenses', 15000, '2025-Q1'],
        ['EXP-005', 'Software Subscriptions', 'Expenses', 25000, '2025-Q1'],
        ['EXP-006', 'Marketing Expenses', 'Expenses', 35000, '2025-Q1'],
        ['EXP-007', 'Travel Expenses', 'Expenses', 20000, '2025-Q1'],
        ['EXP-008', 'Professional Fees', 'Expenses', 30000, '2025-Q1'],
        ['EXP-009', 'Insurance', 'Expenses', 12000, '2025-Q1'],
        ['EXP-010', 'Depreciation', 'Expenses', 18000, '2025-Q1'],
        ['EXP-011', 'Interest Expense', 'Expenses', 8000, '2025-Q1'],
        ['EXP-012', 'Taxes & Licenses', 'Expenses', 15000, '2025-Q1'],
        ['TOTAL', 'Total Operations', 'Summary', 980000, '2025-Q1'],
        ['NET_INCOME', 'Net Income', 'Summary', 220000, '2025-Q1']
    ]
    
    df = pd.DataFrame(data, columns=[
        'Account Code', 'Account Description', 'Category', 'Amount', 'Period'
    ])
    
    filepath = 'financial_documents/income_statements/income_statement_balanced_excel.xlsx'
    df.to_excel(filepath, index=False)
    print(f"✅ Created balanced income statement: {filepath}")

def create_income_statement_unbalanced():
    """Create unbalanced income statement Excel file"""
    data = [
        ['REV-001', 'Consulting Services Revenue', 'Revenue', 250000, '2025-Q1'],
        ['REV-002', 'Training Revenue', 'Revenue', 150000, '2025-Q1'],
        ['REV-003', 'Software Licensing Revenue', 'Revenue', 180000, '2025-Q1'],
        ['REV-004', 'Maintenance Contracts Revenue', 'Revenue', 120000, '2025-Q1'],
        ['REV-005', 'Professional Services Revenue', 'Revenue', 200000, '2025-Q1'],
        ['REV-006', 'Support Services Revenue', 'Revenue', 80000, '2025-Q1'],
        ['EXP-001', 'Salaries & Wages', 'Expenses', 220000, '2025-Q1'],
        ['EXP-002', 'Employee Benefits', 'Expenses', 55000, '2025-Q1'],
        ['EXP-003', 'Office Rent', 'Expenses', 75000, '2025-Q1'],
        ['EXP-004', 'Utilities', 'Expenses', 20000, '2025-Q1'],
        ['EXP-005', 'Software Subscriptions', 'Expenses', 35000, '2025-Q1'],
        ['EXP-006', 'Marketing Expenses', 'Expenses', 45000, '2025-Q1'],
        ['EXP-007', 'Travel Expenses', 'Expenses', 30000, '2025-Q1'],
        ['EXP-008', 'Professional Fees', 'Expenses', 40000, '2025-Q1'],
        ['EXP-009', 'Insurance', 'Expenses', 15000, '2025-Q1'],
        ['EXP-010', 'Depreciation', 'Expenses', 25000, '2025-Q1'],
        ['EXP-011', 'Interest Expense', 'Expenses', 12000, '2025-Q1'],
        ['EXP-012', 'Taxes & Licenses', 'Expenses', 20000, '2025-Q1'],
        ['TOTAL', 'Total Operations', 'Summary', 1165000, '2025-Q1'],
        ['NET_LOSS', 'Net Loss', 'Summary', -35000, '2025-Q1']
    ]
    
    df = pd.DataFrame(data, columns=[
        'Account Code', 'Account Description', 'Category', 'Amount', 'Period'
    ])
    
    filepath = 'financial_documents/income_statements/income_statement_unbalanced_excel.xlsx'
    df.to_excel(filepath, index=False)
    print(f"✅ Created unbalanced income statement: {filepath}")

if __name__ == '__main__':
    print("🔧 Creating proper Excel test files for multi-document system...")
    
    # Create directories if they don't exist
    os.makedirs('financial_documents/budget_reports', exist_ok=True)
    os.makedirs('financial_documents/income_statements', exist_ok=True)
    
    # Create all test files
    create_budget_report_balanced()
    create_budget_report_unbalanced()
    create_income_statement_balanced()
    create_income_statement_unbalanced()
    
    print("\n🎉 All test files created successfully!")
    print("\n📊 Test Files Available:")
    print("  Budget Reports:")
    print("    - budget_report_balanced_excel.xlsx (1% under budget)")
    print("    - budget_report_unbalanced_excel.xlsx (6.3% over budget)")
    print("  Income Statements:")
    print("    - income_statement_balanced_excel.xlsx (R 220K profit)")
    print("    - income_statement_unbalanced_excel.xlsx (R 35K loss)")
    print("  CSV Files:")
    print("    - budget_report_balanced_proper.csv")
    print("    - income_statement_balanced_proper.csv")
    print("\n🚀 Ready for testing at http://localhost:5000/upload")
