"""
SADPMR GRAP Mapping Engine
Phase 2: Enhanced Financial Statement Generation with PDF Export
"""

import pandas as pd
import numpy as np
from datetime import datetime
from utils.constants import (
    COLUMN_MAPPINGS, 
    ASSET_CODES, 
    LIABILITY_CODES, 
    EQUITY_CODES, 
    REVENUE_CODES, 
    EXPENSE_CODES
)
class GRAPMappingEngine:
    """Core GRAP mapping engine for financial statement generation"""
    
    def __init__(self):
        self.mapping_schema = self._load_mapping_schema()
        self.grap_line_items = self._load_grap_structure()
        
    def _load_mapping_schema(self):
        """Load account to GRAP mapping schema"""
        mapping = {
            # Assets
            '1000': {'grap_code': 'CA-001', 'grap_item': 'Cash and Cash Equivalents'},
            '1100': {'grap_code': 'CA-001', 'grap_item': 'Cash and Cash Equivalents'},
            '1200': {'grap_code': 'CA-002', 'grap_item': 'Receivables from Exchange Transactions'},
            '1210': {'grap_code': 'CA-002', 'grap_item': 'Receivables from Exchange Transactions'},
            '1250': {'grap_code': 'CA-002', 'grap_item': 'Receivables from Exchange Transactions'},
            '1300': {'grap_code': 'CA-004', 'grap_item': 'Inventories'},
            '1400': {'grap_code': 'CA-003', 'grap_item': 'Receivables from Non-Exchange Transactions'},
            '1500': {'grap_code': 'CA-005', 'grap_item': 'Prepayments'},
            '1600': {'grap_code': 'NCA-001', 'grap_item': 'Property, Plant and Equipment'},
            '1700': {'grap_code': 'NCA-002', 'grap_item': 'Intangible Assets'},
            '1800': {'grap_code': 'NCA-003', 'grap_item': 'Investments'},
            
            # Liabilities
            '2000': {'grap_code': 'CL-001', 'grap_item': 'Payables from Exchange Transactions'},
            '2100': {'grap_code': 'CL-002', 'grap_item': 'Employee Benefit Obligations (Current)'},
            '2200': {'grap_code': 'CL-003', 'grap_item': 'Provisions (Current)'},
            '2300': {'grap_code': 'NCL-001', 'grap_item': 'Employee Benefit Obligations (Non-Current)'},
            '2400': {'grap_code': 'NCL-002', 'grap_item': 'Provisions (Non-Current)'},
            
            # Equity
            '3000': {'grap_code': 'NA-001', 'grap_item': 'Accumulated Surplus/(Deficit)'},
            
            # Revenue
            '4000': {'grap_code': 'REV-002', 'grap_item': 'Revenue from Non-Exchange Transactions'},
            '4100': {'grap_code': 'REV-001', 'grap_item': 'Revenue from Exchange Transactions'},
            '4200': {'grap_code': 'REV-001', 'grap_item': 'Revenue from Exchange Transactions'},
            
            # Expenses
            '5000': {'grap_code': 'EXP-001', 'grap_item': 'Employee Costs'},
            '5100': {'grap_code': 'EXP-001', 'grap_item': 'Employee Costs'},
            '5200': {'grap_code': 'EXP-001', 'grap_item': 'Employee Costs'},
            '6000': {'grap_code': 'EXP-003', 'grap_item': 'General Expenses'},
            '6100': {'grap_code': 'EXP-002', 'grap_item': 'Depreciation and Amortisation'},
            '6200': {'grap_code': 'EXP-004', 'grap_item': 'Finance Costs'},
            '6300': {'grap_code': 'EXP-003', 'grap_item': 'General Expenses'},
        }
        return pd.DataFrame.from_dict(mapping, orient='index').reset_index()
    
    def _load_grap_structure(self):
        """Load GRAP financial statement structure"""
        return {
            'SOFP_ASSETS': ['CA-001', 'CA-002', 'CA-003', 'CA-004', 'CA-005', 
                           'NCA-001', 'NCA-002', 'NCA-003'],
            'SOFP_LIABILITIES': ['CL-001', 'CL-002', 'CL-003', 
                                'NCL-001', 'NCL-002', 'NCL-003'],
            'SOFP_NET_ASSETS': ['NA-001'],
            'SOFE_REVENUE': ['REV-001', 'REV-002'],
            'SOFE_EXPENSES': ['EXP-001', 'EXP-002', 'EXP-003', 'EXP-004']
        }
    
    def import_trial_balance(self, file_path):
        """Import and validate trial balance from Excel/CSV"""
        df = pd.read_excel(file_path) if file_path.endswith('.xlsx') else pd.read_csv(file_path)
        
        # Standardize column names
        df.columns = df.columns.str.strip()
        
        # Debug: Print actual column names
        print(f"Actual columns in file: {list(df.columns)}")
        
        # Check if this looks like a trial balance file
        required_keywords = ['account', 'debit', 'credit', 'balance']
        column_str = ' '.join(df.columns).lower()
        
        if not any(keyword in column_str for keyword in required_keywords):
            raise ValueError(f"This doesn't appear to be a trial balance file. Expected columns like 'Account Code', 'Account Description', 'Debit Balance', 'Credit Balance'. Found columns: {list(df.columns)}. Please upload a proper trial balance file.")
        
        # Handle column name variations - only rename if source column exists and target doesn't
        for source_col, target_col in COLUMN_MAPPINGS.items():
            if source_col in df.columns and target_col not in df.columns:
                df.rename(columns={source_col: target_col}, inplace=True)
        
        print(f"Columns after mapping: {list(df.columns)}")
        
        # Calculate net balance
        if 'Net Balance' not in df.columns:
            if 'Debit Balance' in df.columns and 'Credit Balance' in df.columns:
                df['Net Balance'] = df['Debit Balance'] - df['Credit Balance']
            else:
                available_cols = [col for col in df.columns if 'debit' in col.lower() or 'credit' in col.lower()]
                raise ValueError(f"Required columns 'Debit Balance' and 'Credit Balance' not found. Available columns: {list(df.columns)}. Similar columns: {available_cols}")
        
        return df
    
    def map_to_grap(self, trial_balance_df):
        """Map trial balance accounts to GRAP line items"""
        trial_balance_df['Account Code'] = trial_balance_df['Account Code'].astype(str)
        self.mapping_schema['index'] = self.mapping_schema['index'].astype(str)
        
        mapped_df = pd.merge(
            trial_balance_df,
            self.mapping_schema,
            left_on='Account Code',
            right_on='index',
            how='left'
        )
        
        return mapped_df
    
    def generate_statement_of_financial_position(self, mapped_df):
        """Generate Statement of Financial Position (Balance Sheet)"""
        sofp = mapped_df.groupby(['grap_code', 'grap_item'])['Net Balance'].sum().reset_index()
        sofp.columns = ['GRAP Code', 'Line Item', 'Amount']
        
        # Separate components
        assets = sofp[sofp['GRAP Code'].str.startswith(tuple(ASSET_CODES), na=False)].copy()
        liabilities = sofp[sofp['GRAP Code'].str.startswith(tuple(LIABILITY_CODES), na=False)].copy()
        net_assets = sofp[sofp['GRAP Code'].str.startswith(tuple(EQUITY_CODES), na=False)].copy()
        
        # Convert to positive values for presentation
        liabilities['Amount'] = liabilities['Amount'].abs()
        net_assets['Amount'] = net_assets['Amount'].abs()
        
        return {'assets': assets, 'liabilities': liabilities, 'net_assets': net_assets}
    
    def generate_statement_of_performance(self, mapped_df):
        """Generate Statement of Financial Performance (Income Statement)"""
        sofe = mapped_df.groupby(['grap_code', 'grap_item'])['Net Balance'].sum().reset_index()
        sofe.columns = ['GRAP Code', 'Line Item', 'Amount']
        
        # Separate revenue and expenses
        revenue = sofe[sofe['GRAP Code'].str.startswith(tuple(REVENUE_CODES), na=False)].copy()
        expenses = sofe[sofe['GRAP Code'].str.startswith(tuple(EXPENSE_CODES), na=False)].copy()
        
        revenue['Amount'] = revenue['Amount'].abs()
        
        # Calculate surplus/deficit
        total_revenue = revenue['Amount'].sum()
        total_expenses = expenses['Amount'].sum()
        surplus_deficit = total_revenue - total_expenses
        
        return {'revenue': revenue, 'expenses': expenses, 'surplus': surplus_deficit}
    
    def calculate_ratios(self, sofp, sofe):
        """Calculate key financial ratios"""
        # Extract totals
        total_assets = sofp['assets']['Amount'].sum()
        current_assets = sofp['assets'][
            sofp['assets']['GRAP Code'].str.startswith(tuple(['CA-']), na=False)
        ]['Amount'].sum()
        
        total_liabilities = sofp['liabilities']['Amount'].sum()
        current_liabilities = sofp['liabilities'][
            sofp['liabilities']['GRAP Code'].str.startswith(tuple(['CL-']), na=False)
        ]['Amount'].sum()
        
        total_revenue = sofe['revenue']['Amount'].sum()
        total_expenses = sofe['expenses']['Amount'].sum()
        net_assets = sofp['net_assets']['Amount'].sum()
        
        # Calculate ratios with error handling
        ratios = {
            'current_ratio': round(current_assets / current_liabilities, 2) if current_liabilities > 0 else 0,
            'debt_to_equity': round(total_liabilities / net_assets, 2) if net_assets > 0 else 0,
            'operating_margin': round((total_revenue - total_expenses) / total_revenue * 100, 2) if total_revenue > 0 else 0,
            'return_on_assets': round(sofe['surplus'] / total_assets * 100, 2) if total_assets > 0 else 0
        }
        
        return ratios
    
    def generate_cash_flow_statement(self, sofp, sofe, mapped_df):
        """Generate Cash Flow Statement using Indirect Method"""
        # Indirect method: Start with surplus/deficit, add back non-cash items
        net_surplus = sofe['surplus']
        
        # Non-cash items
        depreciation = sofe['expenses'][
            sofe['expenses']['GRAP Code'] == 'EXP-002'
        ]['Amount'].sum() if len(sofe['expenses']) > 0 else 0
        
        # Working capital changes (simplified)
        receivables_change = mapped_df[mapped_df['grap_code'].str.startswith('CA-00', na=False)]['Net Balance'].sum()
        payables_change = mapped_df[mapped_df['grap_code'].str.startswith('CL-00', na=False)]['Net Balance'].sum()
        
        # Operating cash flow
        operating_cash = net_surplus + depreciation - (receivables_change - payables_change)
        
        # Investing activities (simplified)
        ppe_changes = mapped_df[mapped_df['grap_code'] == 'NCA-001']['Net Balance'].sum()
        investing_cash = -abs(ppe_changes) if ppe_changes < 0 else 0
        
        # Financing activities (simplified)
        borrowing_changes = mapped_df[mapped_df['grap_code'].str.startswith('NCL-', na=False)]['Net Balance'].sum()
        financing_cash = borrowing_changes
        
        # Net cash movement
        net_cash_movement = operating_cash + investing_cash + financing_cash
        
        # Structure for presentation
        cash_flow_data = {
            'operating': [
                {'Line Item': 'Net Surplus/(Deficit)', 'Amount': net_surplus},
                {'Line Item': 'Add: Depreciation & Amortisation', 'Amount': depreciation},
                {'Line Item': 'Changes in Working Capital', 'Amount': -(receivables_change - payables_change)},
                {'Line Item': 'Net Cash from Operating Activities', 'Amount': operating_cash}
            ],
            'investing': [
                {'Line Item': 'Capital Expenditure', 'Amount': investing_cash},
                {'Line Item': 'Net Cash from Investing Activities', 'Amount': investing_cash}
            ],
            'financing': [
                {'Line Item': 'Borrowing Activities', 'Amount': financing_cash},
                {'Line Item': 'Net Cash from Financing Activities', 'Amount': financing_cash}
            ],
            'net_movement': net_cash_movement
        }
        
        return cash_flow_data


def generate_pdf_report(results, output_path):
    """Generate PDF financial report - wrapper function"""
    from services.pdf_service import PDFService
    service = PDFService()
    return service.generate_financial_statements_pdf(results, output_path)
