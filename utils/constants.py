"""
SADPMR Financial Reporting System - Application Constants
Centralized constants for magic numbers and strings
"""

# File Upload Constants
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
MAX_FILE_SIZE_MB = 16
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# GRAP Mapping Constants
GRAP_MAPPING_VERSION = '2.0'
GRAP_COMPLIANCE_YEAR = 2026

# Financial Statement Categories
ASSET_CODES = ['CA-', 'NCA-']
LIABILITY_CODES = ['CL-', 'NCL-']
EQUITY_CODES = ['NA-']
REVENUE_CODES = ['REV-']
EXPENSE_CODES = ['EXP-']

# PDF Report Constants
PDF_PAGE_SIZE = 'A4'
PDF_MARGIN_TOP_CM = 2.0
PDF_MARGIN_BOTTOM_CM = 2.0
PDF_MARGIN_LEFT_CM = 2.5
PDF_MARGIN_RIGHT_CM = 2.5

# Financial Ratio Benchmarks
RATIO_BENCHMARKS = {
    'current_ratio': {'min': 1.5, 'target': 2.0},
    'debt_to_equity': {'max': 1.0, 'target': 0.5},
    'operating_margin': {'min': 10.0, 'target': 15.0},
    'return_on_assets': {'min': 5.0, 'target': 8.0}
}

# Column Name Mappings
COLUMN_MAPPINGS = {
    'Acc Code': 'Account Code',
    'AccCode': 'Account Code',
    'Account': 'Account Code',
    'Description': 'Account Description',
    'Debit': 'Debit Balance',
    'Credit': 'Credit Balance'
}

# Required Columns
REQUIRED_COLUMNS = ['Account Code', 'Account Description']

# Trial Balance Validation Thresholds
TRIAL_BALANCE_TOLERANCE = 0.01

# HTTP Status Messages
ERROR_MESSAGES = {
    'no_file': 'No file uploaded',
    'no_file_selected': 'No file selected',
    'invalid_file_type': 'Invalid file type',
    'file_not_found': 'File not found',
    'processing_error': 'Processing error',
    'unmapped_accounts': 'Unmapped accounts detected'
}

# Success Messages
SUCCESS_MESSAGES = {
    'file_uploaded': 'Successfully uploaded {row_count} accounts',
    'statements_generated': 'Financial statements generated successfully'
}

# PDF Table Colors
PDF_COLORS = {
    'primary': '#1a237e',
    'secondary': '#283593',
    'success': '#1b5e20',
    'warning': '#e65100',
    'danger': '#c62828',
    'info': '#4a148c',
    'light_blue': '#e3f2fd',
    'light_green': '#e8f5e8',
    'light_red': '#ffebee',
    'light_orange': '#fff3e0',
    'light_purple': '#f3e5f5',
    'light_grey': '#f5f5f5',
    'grey': '#9e9e9e'
}

# PDF Table Styles
TABLE_COLUMN_WIDTHS = {
    'note': 2.0,  # cm
    'description': 12.0,  # cm
    'amount': 3.0  # cm
}

# Session Configuration
SESSION_LIFETIME_HOURS = 1

# Security Configuration
SECRET_KEY_DEFAULT = 'sadpmr-demo-2025-secure-key'
