"""
SADPMR Financial Reporting System - Validators
Data validation functions for trial balances and file formats
"""

import pandas as pd
import os
from utils.constants import ALLOWED_EXTENSIONS, COLUMN_MAPPINGS, REQUIRED_COLUMNS, TRIAL_BALANCE_TOLERANCE


def validate_file_format(filepath):
    """Validate uploaded file format and structure"""
    try:
        # Check file extension
        if not any(filepath.lower().endswith(f'.{ext}') for ext in ALLOWED_EXTENSIONS):
            return False, f"Invalid file format. Please upload {', '.join(ALLOWED_EXTENSIONS).upper()} files."
        
        # Try to read the file
        if filepath.lower().endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)
        
        # Check if DataFrame is empty
        if df.empty:
            return False, "The uploaded file is empty."
        
        # Check minimum required columns
        available_columns = [col.strip() for col in df.columns]
        
        # Apply column mapping
        df.columns = [COLUMN_MAPPINGS.get(col.strip(), col.strip()) for col in df.columns]
        
        # Check for required columns after mapping
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"
        
        # Check if we have financial data
        if 'Debit Balance' not in df.columns and 'Credit Balance' not in df.columns:
            return False, "File must contain either Debit Balance or Credit Balance columns."
        
        return True, "File format is valid."
        
    except Exception as e:
        return False, f"Error reading file: {str(e)}"


def validate_trial_balance(df):
    """Validate trial balance data integrity"""
    errors = []
    warnings = []
    
    # Check for required columns
    required_columns = ['Account Code', 'Account Description']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Check for empty account codes
    if 'Account Code' in df.columns:
        empty_codes = df[df['Account Code'].isna() | (df['Account Code'] == '')]
        if not empty_codes.empty:
            errors.append(f"Found {len(empty_codes)} rows with empty account codes.")
    
    # Check for duplicate account codes
    if 'Account Code' in df.columns:
        duplicates = df[df['Account Code'].duplicated(keep=False)]
        if not duplicates.empty:
            warnings.append(f"Found {len(duplicates)} duplicate account codes.")
    
    # Check balance calculations
    if 'Debit Balance' in df.columns and 'Credit Balance' in df.columns:
        # Check for rows with both debit and credit values
        both_values = df[(df['Debit Balance'] != 0) & (df['Credit Balance'] != 0)]
        if not both_values.empty:
            warnings.append(f"Found {len(both_values)} accounts with both debit and credit balances.")
        
        # Check if trial balance balances
        total_debit = df['Debit Balance'].sum()
        total_credit = df['Credit Balance'].sum()
        
        if abs(total_debit - total_credit) > TRIAL_BALANCE_TOLERANCE:
            warnings.append(f"Trial balance doesn't balance: Debit R{total_debit:,.2f} vs Credit R{total_credit:,.2f}")
    
    # Check for negative values in unusual places
    if 'Debit Balance' in df.columns:
        negative_debits = df[df['Debit Balance'] < 0]
        if not negative_debits.empty:
            warnings.append(f"Found {len(negative_debits)} accounts with negative debit balances.")
    
    if 'Credit Balance' in df.columns:
        negative_credits = df[df['Credit Balance'] < 0]
        if not negative_credits.empty:
            warnings.append(f"Found {len(negative_credits)} accounts with negative credit balances.")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'total_accounts': len(df)
    }
