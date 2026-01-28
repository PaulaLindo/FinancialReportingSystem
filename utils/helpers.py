"""
SADPMR Financial Reporting System - Helper Functions
Utility functions for formatting and calculations
"""

import pandas as pd


def format_currency(amount, currency='R'):
    """Format amount as currency string"""
    try:
        if pd.isna(amount) or amount == 0:
            return f"{currency}0.00"
        return f"{currency}{abs(amount):,.2f}"
    except (ValueError, TypeError):
        return f"{currency}0.00"


def calculate_ratios(sofp_data, sofe_data):
    """Calculate additional financial ratios"""
    try:
        # Extract totals
        total_assets = sofp_data['assets']['Amount'].sum()
        current_assets = sofp_data['assets'][
            sofp_data['assets']['GRAP Code'].str.contains('CA-')
        ]['Amount'].sum()
        
        total_liabilities = sofp_data['liabilities']['Amount'].sum()
        current_liabilities = sofp_data['liabilities'][
            sofp_data['liabilities']['GRAP Code'].str.contains('CL-')
        ]['Amount'].sum()
        
        total_revenue = sofe_data['revenue']['Amount'].sum()
        total_expenses = sofe_data['expenses']['Amount'].sum()
        net_assets = sofp_data['net_assets']['Amount'].sum()
        
        # Calculate additional ratios
        ratios = {
            'current_ratio': round(current_assets / current_liabilities, 2) if current_liabilities > 0 else 0,
            'quick_ratio': round((current_assets - sofp_data['assets'][
                sofp_data['assets']['GRAP Code'] == 'CA-004'
            ]['Amount'].sum()) / current_liabilities, 2) if current_liabilities > 0 else 0,
            'debt_to_equity': round(total_liabilities / net_assets, 2) if net_assets > 0 else 0,
            'debt_to_assets': round(total_liabilities / total_assets, 2) if total_assets > 0 else 0,
            'operating_margin': round((total_revenue - total_expenses) / total_revenue * 100, 2) if total_revenue > 0 else 0,
            'return_on_assets': round(sofe_data['surplus'] / total_assets * 100, 2) if total_assets > 0 else 0,
            'return_on_equity': round(sofe_data['surplus'] / net_assets * 100, 2) if net_assets > 0 else 0,
            'asset_turnover': round(total_revenue / total_assets, 2) if total_assets > 0 else 0
        }
        
        return ratios
        
    except Exception as e:
        print(f"Error calculating ratios: {str(e)}")
        return {}


def validate_account_mapping(mapped_df):
    """Validate account mapping results"""
    validation_results = {
        'total_accounts': len(mapped_df),
        'mapped_accounts': 0,
        'unmapped_accounts': 0,
        'unmapped_list': []
    }
    
    if 'grap_code' in mapped_df.columns:
        mapped_accounts = mapped_df[mapped_df['grap_code'].notna()]
        unmapped_accounts = mapped_df[mapped_df['grap_code'].isna()]
        
        validation_results['mapped_accounts'] = len(mapped_accounts)
        validation_results['unmapped_accounts'] = len(unmapped_accounts)
        
        if not unmapped_accounts.empty:
            validation_results['unmapped_list'] = unmapped_accounts[
                ['Account Code', 'Account Description', 'Net Balance']
            ].to_dict('records')
    
    return validation_results


def generate_filename(prefix, extension='pdf'):
    """Generate timestamped filename"""
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{prefix}_{timestamp}.{extension}"


def safe_divide(numerator, denominator, default=0):
    """Safely divide two numbers with default fallback"""
    try:
        if denominator == 0 or pd.isna(denominator):
            return default
        return numerator / denominator
    except (ValueError, TypeError, ZeroDivisionError):
        return default
