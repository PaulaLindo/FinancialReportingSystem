"""
Income Statement Service
Handles income statement uploads with automatic format detection and GRAP mapping
"""

import pandas as pd
import uuid
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from decimal import Decimal

from .financial_document_service import FinancialDocumentService, FinancialDocumentSession
from models.income_statement_models import income_statement_model

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class IncomeStatementSession(FinancialDocumentSession):
    """Income statement specific session"""
    document_type: str = "income_statement"
    total_revenue: Decimal = Decimal('0.00')
    total_expenses: Decimal = Decimal('0.00')
    net_income: Decimal = Decimal('0.00')
    gross_profit: Decimal = Decimal('0.00')
    operating_income: Decimal = Decimal('0.00')
    fiscal_year: int = 0
    reporting_period: str = ""  # e.g., "2025-Q1", "2025-03"
    statement_type: str = "monthly"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = super().to_dict()
        # Convert Decimal to string for JSON serialization
        data['total_revenue'] = str(self.total_revenue)
        data['total_expenses'] = str(self.total_expenses)
        data['net_income'] = str(self.net_income)
        data['gross_profit'] = str(self.gross_profit)
        data['operating_income'] = str(self.operating_income)
        return data


class IncomeStatementService(FinancialDocumentService):
    """Service for handling income statement uploads"""
    
    def __init__(self):
        super().__init__("income_statement")
        self.model = income_statement_model
        
        # Income statement specific column patterns
        self.document_specific_patterns = {
            'revenue': [
                r'(?i)revenue',
                r'(?i)income',
                r'(?i)sales',
                r'(?i)turnover',
                r'(?i)fees\s*earned',
                r'(?i)service\s*revenue',
                r'(?i)operating\s*revenue'
            ],
            'expenses': [
                r'(?i)expenses?',
                r'(?i)costs?',
                r'(?i)expenditure',
                r'(?i)operating\s*expenses?',
                r'(?i)administrative',
                r'(?i)salaries',
                r'(?i)wages',
                r'(?i)rent',
                r'(?i)utilities',
                r'(?i)depreciation',
                r'(?i)amortization'
            ],
            'amount': [
                r'(?i)amount',
                r'(?i)value',
                r'(?i)total',
                r'(?i)balance',
                r'(?i)figure',
                r'(?i)rand',
                r'(?i)zar',
                r'(?i)r\s*'
            ],
            'period': [
                r'(?i)period',
                r'(?i)month',
                r'(?i)quarter',
                r'(?i)year',
                r'(?i)fiscal\s*year',
                r'(?i)reporting\s*period'
            ],
            'category': [
                r'(?i)category',
                r'(?i)type',
                r'(?i)classification',
                r'(?i)group',
                r'(?i)section',
                r'(?i)account\s*type'
            ]
        }
    
    def get_document_specific_patterns(self) -> Dict[str, List[str]]:
        """Get income statement specific column patterns"""
        return self.document_specific_patterns
    
    def _create_data_row_from_row(self, session_id: str, row_index: int, row: pd.Series, column_mapping: Dict):
        """Create an IncomeStatementDataRow from a pandas row"""
        from models.income_statement_models import IncomeStatementDataRow
        from decimal import Decimal
        
        # Create raw data dictionary
        raw_data = {str(col): str(val) if pd.notna(val) else '' for col, val in row.items()}
        
        # Process data based on column mappings
        processed_data = {}
        account_code = ''
        account_description = ''
        amount = None
        category = ''
        period = ''
        
        # Extract values based on column mapping
        for field_name, column_name in column_mapping.items():
            if column_name in row.index and pd.notna(row[column_name]):
                value = str(row[column_name]).strip()
                
                if field_name == 'account_code':
                    account_code = value
                    processed_data['account_code'] = value
                elif field_name == 'category':
                    account_description = value
                    category = value
                    processed_data['category'] = value
                elif field_name == 'revenue':
                    # For income statements, revenue accounts have credit balance
                    try:
                        amount = Decimal(value.replace(',', '').replace('R', '').replace('$', ''))
                        processed_data['revenue'] = float(amount)
                    except:
                        pass
                elif field_name == 'expenses':
                    # For income statements, expense accounts have debit balance
                    try:
                        amount = Decimal(value.replace(',', '').replace('R', '').replace('$', ''))
                        processed_data['expenses'] = float(amount)
                    except:
                        pass
                elif field_name == 'amount':
                    try:
                        amount = Decimal(value.replace(',', '').replace('R', '').replace('$', ''))
                        processed_data['amount'] = float(amount)
                    except:
                        pass
                elif field_name == 'period':
                    period = value
                    processed_data['period'] = value
                else:
                    processed_data[field_name] = value
        
        # Use account_description if not set
        if not account_description:
            account_description = f"Account {account_code}" if account_code else "Unknown Account"
        
        # Determine debit and credit balance based on category and amount
        debit_balance = None
        credit_balance = None
        
        if amount is not None:
            # Revenue accounts typically have credit balances
            if category and any(term in category.lower() for term in ['revenue', 'income', 'sales', 'fees']):
                credit_balance = amount
                debit_balance = Decimal('0')
            # Expense accounts typically have debit balances
            else:
                debit_balance = amount
                credit_balance = Decimal('0')
        
        # Create data row
        data_row = IncomeStatementDataRow(
            session_id=session_id,
            row_index=row_index,
            raw_data=raw_data,
            processed_data=processed_data,
            account_code=account_code,
            account_description=account_description,
            debit_balance=debit_balance,
            credit_balance=credit_balance,
            net_balance=credit_balance - debit_balance if credit_balance and debit_balance else amount,
            category=category,
            period=period,
            mapping_status='unmapped',
            validation_status='pending'
        )
        
        return data_row
    
    def validate_document_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate income statement structure"""
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'structure_type': 'unknown',
            'revenue_columns': [],
            'expense_columns': [],
            'amount_columns': []
        }
        
        try:
            # Check minimum required columns
            if len(df.columns) < 2:
                result['errors'].append("Income statement must have at least 2 columns")
                return result
            
            # Detect structure type
            structure_type = self._detect_income_statement_structure(df)
            result['structure_type'] = structure_type
            
            # Validate based on structure type
            if structure_type == 'simple':
                validation = self._validate_simple_structure(df)
            elif structure_type == 'detailed':
                validation = self._validate_detailed_structure(df)
            elif structure_type == 'categorized':
                validation = self._validate_categorized_structure(df)
            else:
                validation = self._validate_generic_structure(df)
            
            result.update(validation)
            
            # Check for required financial data
            if not result['revenue_columns'] and not result['expense_columns']:
                result['errors'].append("No revenue or expense columns detected")
            
            # Overall validation
            result['valid'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f"Validation error: {str(e)}")
            result['valid'] = False
        
        return result
    
    def _detect_income_statement_structure(self, df: pd.DataFrame) -> str:
        """Detect the type of income statement structure"""
        columns = [str(col).lower() for col in df.columns]
        
        # Check for categorized structure (Category | Account | Amount)
        if any('category' in col or 'type' in col for col in columns):
            return 'categorized'
        
        # Check for detailed structure (Account Description | Revenue | Expenses)
        if any('revenue' in col for col in columns) and any('expense' in col for col in columns):
            return 'detailed'
        
        # Check for simple structure (Account | Amount | Type)
        if any('amount' in col for col in columns) and len(columns) >= 2:
            return 'simple'
        
        return 'generic'
    
    def _validate_simple_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate simple income statement structure"""
        result = {
            'errors': [],
            'warnings': [],
            'revenue_columns': [],
            'expense_columns': [],
            'amount_columns': []
        }
        
        # Look for amount column
        amount_col = None
        for col in df.columns:
            if any(pattern in str(col).lower() for pattern in ['amount', 'total', 'value', 'balance']):
                amount_col = col
                result['amount_columns'].append(col)
                break
        
        if not amount_col:
            result['errors'].append("No amount column found")
        else:
            # Check if amount column contains numeric data
            try:
                numeric_data = pd.to_numeric(df[amount_col], errors='coerce')
                if numeric_data.isna().all():
                    result['errors'].append(f"Amount column '{amount_col}' contains no numeric data")
            except:
                result['errors'].append(f"Amount column '{amount_col}' cannot be converted to numbers")
        
        return result
    
    def _validate_detailed_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate detailed income statement structure"""
        result = {
            'errors': [],
            'warnings': [],
            'revenue_columns': [],
            'expense_columns': [],
            'amount_columns': []
        }
        
        # Find revenue and expense columns
        for col in df.columns:
            col_lower = str(col).lower()
            if any(pattern in col_lower for pattern in ['revenue', 'income', 'sales']):
                result['revenue_columns'].append(col)
            elif any(pattern in col_lower for pattern in ['expense', 'cost', 'expenditure']):
                result['expense_columns'].append(col)
        
        # Validate that we have both revenue and expense columns
        if not result['revenue_columns']:
            result['warnings'].append("No revenue columns detected")
        if not result['expense_columns']:
            result['warnings'].append("No expense columns detected")
        
        return result
    
    def _validate_categorized_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate categorized income statement structure"""
        result = {
            'errors': [],
            'warnings': [],
            'revenue_columns': [],
            'expense_columns': [],
            'amount_columns': []
        }
        
        # Look for category and amount columns
        category_col = None
        amount_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if any(pattern in col_lower for pattern in ['category', 'type', 'classification']):
                category_col = col
            elif any(pattern in col_lower for pattern in ['amount', 'total', 'value']):
                amount_col = col
                result['amount_columns'].append(col)
        
        if not category_col:
            result['errors'].append("No category column found")
        if not amount_col:
            result['errors'].append("No amount column found")
        
        return result
    
    def _validate_generic_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate generic income statement structure"""
        result = {
            'errors': [],
            'warnings': [],
            'revenue_columns': [],
            'expense_columns': [],
            'amount_columns': []
        }
        
        # Try to identify any numeric columns as amount columns
        for col in df.columns:
            try:
                numeric_data = pd.to_numeric(df[col], errors='coerce')
                if not numeric_data.isna().all():
                    result['amount_columns'].append(col)
            except:
                continue
        
        if not result['amount_columns']:
            result['errors'].append("No numeric columns found for amounts")
        else:
            result['warnings'].append("Generic structure detected - manual review recommended")
        
        return result
    
    def create_session(self, file_path: str, user_id: str, filename: str) -> IncomeStatementSession:
        """Create income statement specific session"""
        session = IncomeStatementSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            document_type="income_statement",
            filename=filename,
            original_filename=filename,
            file_type=filename.split('.')[-1].lower(),
            file_format=filename.split('.')[-1].lower(),
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Try to extract period information from filename
        self._extract_period_info(session, filename)
        
        return session
    
    def _extract_period_info(self, session: IncomeStatementSession, filename: str):
        """Extract period information from filename"""
        filename_lower = filename.lower()
        
        # Detect fiscal year
        year_match = re.search(r'20\d{2}', filename_lower)
        if year_match:
            session.fiscal_year = int(year_match.group())
        
        # Detect period type
        if any(qtr in filename_lower for qtr in ['q1', 'q2', 'q3', 'q4']):
            session.period_type = 'quarterly'
        elif any(month in filename_lower for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
            session.period_type = 'monthly'
        elif 'annual' in filename_lower or 'yearly' in filename_lower:
            session.period_type = 'annual'
        
        # Extract reporting period
        if session.fiscal_year:
            if session.period_type == 'quarterly':
                qtr_match = re.search(r'q([1-4])', filename_lower)
                if qtr_match:
                    session.reporting_period = f"{session.fiscal_year}-Q{qtr_match.group(1)}"
            elif session.period_type == 'monthly':
                # Try to extract month
                months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                for i, month in enumerate(months, 1):
                    if month in filename_lower:
                        session.reporting_period = f"{session.fiscal_year}-{i:02d}"
                        break
                else:
                    session.reporting_period = f"{session.fiscal_year}"
            else:
                session.reporting_period = f"{session.fiscal_year}"
    
    def get_model(self):
        """Get the income statement model"""
        # This will be created when we create the database models
        from models.income_statement_models import income_statement_model
        return income_statement_model
    
    def create_session_with_user_context(self, file_path: str, user_id: str, filename: str) -> IncomeStatementSession:
        """Create income statement session with proper user context for RLS"""
        # Create session object
        session = self.create_session(file_path, user_id, filename)
        
        # Use regular model - the RLS policies should be fixed to work with Flask auth
        model = self.get_model()
        return model.create_session(session)
    
    def _store_session(self, session: IncomeStatementSession) -> IncomeStatementSession:
        """Store session in database using proper RLS handling"""
        try:
            # Use the new method that handles RLS properly
            return self.create_session_with_user_context("", session.user_id, session.original_filename)
        except Exception as e:
            # Fallback to regular method
            print(f"⚠️ RLS bypass failed, using regular method: {e}")
            model = self.get_model()
            return model.create_session(session)
    
    def calculate_financial_summary(self, session_id: str) -> Dict[str, Any]:
        """Calculate revenue, expenses, and net income"""
        try:
            model = self.get_model()
            session = model.get_session(session_id)
            
            if not session:
                return {'success': False, 'error': 'Session not found'}
            
            # Get data rows
            data_rows = model.get_data_rows(session_id)
            
            revenue_total = Decimal('0.00')
            expense_total = Decimal('0.00')
            
            # Calculate totals based on column mapping
            column_mapping = session.metadata.get('column_mapping', {})
            
            for row in data_rows:
                if 'amount' in column_mapping:
                    amount = Decimal(str(row.get(column_mapping['amount'], '0')))
                    
                    # Determine if this is revenue or expense
                    account_desc = str(row.get(column_mapping.get('account_desc', ''), '')).lower()
                    
                    if any(rev in account_desc for rev in ['revenue', 'income', 'sales', 'fee']):
                        revenue_total += amount
                    else:
                        expense_total += amount
            
            net_income = revenue_total - expense_total
            
            # Update session with calculated values
            session.revenue_total = revenue_total
            session.expense_total = expense_total
            session.net_income = net_income
            
            # Save updated session
            model.update_session(session)
            
            return {
                'success': True,
                'revenue_total': float(revenue_total),
                'expense_total': float(expense_total),
                'net_income': float(net_income),
                'message': f"Financial summary calculated: Revenue R{revenue_total:,.2f}, Expenses R{expense_total:,.2f}, Net Income R{net_income:,.2f}"
            }
            
        except Exception as e:
            logger.error(f"Error calculating financial summary: {str(e)}")
            return {'success': False, 'error': f'Error calculating financial summary: {str(e)}'}


# Import regex for period extraction
import re

# Global instance
income_statement_service = IncomeStatementService()
