"""
SADPMR Financial Reporting System - Validation Service
Unified validation for trial balances and data integrity
"""

import pandas as pd
from utils.exceptions import ValidationError, MappingError
from utils.constants import TRIAL_BALANCE_TOLERANCE, ASSET_CODES, LIABILITY_CODES, EQUITY_CODES, REVENUE_CODES, EXPENSE_CODES


class ValidationService:
    """Service for data validation operations"""
    
    @staticmethod
    def validate_trial_balance_integrity(df):
        """Validate trial balance data integrity"""
        errors = []
        warnings = []
        
        # Check for required columns
        missing_columns = ValidationService._check_required_columns(df)
        if missing_columns:
            errors.extend(missing_columns)
        
        # Check for empty account codes
        empty_codes = ValidationService._check_empty_account_codes(df)
        if empty_codes:
            errors.extend(empty_codes)
        
        # Check for duplicate account codes
        duplicates = ValidationService._check_duplicate_codes(df)
        if duplicates:
            warnings.extend(duplicates)
        
        # Check balance calculations
        balance_issues = ValidationService._check_balance_calculations(df)
        if balance_issues:
            warnings.extend(balance_issues)
        
        # Check for negative values
        negative_issues = ValidationService._check_negative_values(df)
        if negative_issues:
            warnings.extend(negative_issues)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'total_accounts': len(df)
        }
    
    @staticmethod
    def validate_grap_mapping(mapped_df):
        """Validate GRAP mapping results"""
        if 'grap_code' not in mapped_df.columns:
            raise MappingError('GRAP code column not found in mapped data')
        
        unmapped_accounts = mapped_df[mapped_df['grap_code'].isna()]
        
        if not unmapped_accounts.empty:
            unmapped_list = unmapped_accounts[
                ['Account Code', 'Account Description', 'Net Balance']
            ].to_dict('records')
            
            raise MappingError(
                f'Found {len(unmapped_accounts)} unmapped accounts',
                account_code=unmapped_list[0]['Account Code'] if unmapped_list else None
            )
        
        return {
            'total_accounts': len(mapped_df),
            'mapped_accounts': len(mapped_df[mapped_df['grap_code'].notna()]),
            'unmapped_accounts': 0
        }
    
    @staticmethod
    def validate_financial_statements(sofp, sofe):
        """Validate generated financial statements"""
        errors = []
        
        # Check SOFP structure
        if not all(key in sofp for key in ['assets', 'liabilities', 'net_assets']):
            errors.append('Statement of Financial Position missing required sections')
        
        # Check SOFE structure
        if not all(key in sofe for key in ['revenue', 'expenses', 'surplus']):
            errors.append('Statement of Financial Performance missing required sections')
        
        # Validate GRAP codes
        ValidationService._validate_grap_codes(sofp['assets'], ASSET_CODES, 'assets')
        ValidationService._validate_grap_codes(sofp['liabilities'], LIABILITY_CODES, 'liabilities')
        ValidationService._validate_grap_codes(sofp['net_assets'], EQUITY_CODES, 'net_assets')
        ValidationService._validate_grap_codes(sofe['revenue'], REVENUE_CODES, 'revenue')
        ValidationService._validate_grap_codes(sofe['expenses'], EXPENSE_CODES, 'expenses')
        
        if errors:
            raise ValidationError('Financial statement validation failed: ' + '; '.join(errors))
        
        return True
    
    @staticmethod
    def _check_required_columns(df):
        """Check for required columns"""
        required_columns = ['Account Code', 'Account Description']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return [f"Missing required columns: {', '.join(missing_columns)}"]
        return []
    
    @staticmethod
    def _check_empty_account_codes(df):
        """Check for empty account codes"""
        if 'Account Code' not in df.columns:
            return []
        
        empty_codes = df[df['Account Code'].isna() | (df['Account Code'] == '')]
        if not empty_codes.empty:
            return [f"Found {len(empty_codes)} rows with empty account codes."]
        return []
    
    @staticmethod
    def _check_duplicate_codes(df):
        """Check for duplicate account codes"""
        if 'Account Code' not in df.columns:
            return []
        
        duplicates = df[df['Account Code'].duplicated(keep=False)]
        if not duplicates.empty:
            return [f"Found {len(duplicates)} duplicate account codes."]
        return []
    
    @staticmethod
    def _check_balance_calculations(df):
        """Check trial balance calculations"""
        warnings = []
        
        if 'Debit Balance' not in df.columns or 'Credit Balance' not in df.columns:
            return warnings
        
        # Check for rows with both debit and credit values
        both_values = df[(df['Debit Balance'] != 0) & (df['Credit Balance'] != 0)]
        if not both_values.empty:
            warnings.append(f"Found {len(both_values)} accounts with both debit and credit balances.")
        
        # Check if trial balance balances
        total_debit = df['Debit Balance'].sum()
        total_credit = df['Credit Balance'].sum()
        
        if abs(total_debit - total_credit) > TRIAL_BALANCE_TOLERANCE:
            warnings.append(
                f"Trial balance doesn't balance: Debit R{total_debit:,.2f} vs Credit R{total_credit:,.2f}"
            )
        
        return warnings
    
    @staticmethod
    def _check_negative_values(df):
        """Check for negative values in unusual places"""
        warnings = []
        
        if 'Debit Balance' in df.columns:
            negative_debits = df[df['Debit Balance'] < 0]
            if not negative_debits.empty:
                warnings.append(f"Found {len(negative_debits)} accounts with negative debit balances.")
        
        if 'Credit Balance' in df.columns:
            negative_credits = df[df['Credit Balance'] < 0]
            if not negative_credits.empty:
                warnings.append(f"Found {len(negative_credits)} accounts with negative credit balances.")
        
        return warnings
    
    @staticmethod
    def _validate_grap_codes(df, valid_codes, section_name):
        """Validate GRAP codes in a section"""
        if 'GRAP Code' not in df.columns:
            return
        
        invalid_codes = df[~df['GRAP Code'].str.startswith(tuple(valid_codes), na=False)]
        if not invalid_codes.empty:
            raise ValidationError(f'Invalid GRAP codes found in {section_name} section')
