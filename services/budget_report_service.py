"""
Budget Report Service
Handles budget report uploads with automatic format detection and variance analysis
"""

import pandas as pd
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from decimal import Decimal

from .financial_document_service import FinancialDocumentService, FinancialDocumentSession
from models.budget_report_models import budget_report_model

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class BudgetReportSession(FinancialDocumentSession):
    """Budget report specific session"""
    document_type: str = "budget_report"
    total_budget: Decimal = Decimal('0.00')
    total_actual: Decimal = Decimal('0.00')
    total_variance: Decimal = Decimal('0.00')
    variance_percentage: Decimal = Decimal('0.00')
    fiscal_year: int = 0
    budget_type: str = ""  # 'operating', 'capital', 'cash'
    department: str = ""
    reporting_period: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = super().to_dict()
        # Convert Decimal to string for JSON serialization
        data['total_budget'] = str(self.total_budget)
        data['total_actual'] = str(self.total_actual)
        data['total_variance'] = str(self.total_variance)
        data['variance_percentage'] = str(self.variance_percentage)
        return data


class BudgetReportService(FinancialDocumentService):
    """Service for handling budget report uploads"""
    
    def __init__(self):
        super().__init__("budget_report")
        self.model = budget_report_model
        
        # Budget report specific column patterns
        self.document_specific_patterns = {
            'budget_amount': [
                r'(?i)budget',
                r'(?i)planned',
                r'(?i)projected',
                r'(?i)estimated',
                r'(?i)forecast',
                r'(?i)target',
                r'(?i)allocation'
            ],
            'actual_amount': [
                r'(?i)actual',
                r'(?i)real',
                r'(?i)spent',
                r'(?i)incurred',
                r'(?i)achieved',
                r'(?i)current'
            ],
            'variance': [
                r'(?i)variance',
                r'(?i)difference',
                r'(?i)deviation',
                r'(?i)var',
                r'(?i)diff',
                r'(?i)delta'
            ],
            'variance_pct': [
                r'(?i)variance\s*%',
                r'(?i)var\s*%',
                r'(?i)percentage',
                r'(?i)pct',
                r'(?i)%\s*var',
                r'(?i)%\s*diff'
            ],
            'department': [
                r'(?i)department',
                r'(?i)dept',
                r'(?i)division',
                r'(?i)unit',
                r'(?i)section',
                r'(?i)cost\s*center'
            ],
            'expense_category': [
                r'(?i)category',
                r'(?i)expense\s*type',
                r'(?i)cost\s*type',
                r'(?i)account',
                r'(?i)line\s*item'
            ]
        }
    
    def get_document_specific_patterns(self) -> Dict[str, List[str]]:
        """Get budget report specific column patterns"""
        return self.document_specific_patterns
    
    def _create_data_row_from_row(self, session_id: str, row_index: int, row: pd.Series, column_mapping: Dict):
        """Create a BudgetReportDataRow from a pandas row"""
        from models.budget_report_models import BudgetReportDataRow
        from decimal import Decimal
        
        # Create raw data dictionary
        raw_data = {str(col): str(val) if pd.notna(val) else '' for col, val in row.items()}
        
        # Process data based on column mappings
        processed_data = {}
        account_code = ''
        account_description = ''
        budget_amount = None
        actual_amount = None
        variance = None
        department = ''
        expense_category = ''
        
        # Extract values based on column mapping
        for field_name, column_name in column_mapping.items():
            if column_name in row.index and pd.notna(row[column_name]):
                value = str(row[column_name]).strip()
                
                if field_name == 'account_code':
                    account_code = value
                    processed_data['account_code'] = value
                elif field_name == 'expense_category':
                    account_description = value
                    expense_category = value
                    processed_data['expense_category'] = value
                elif field_name == 'department':
                    department = value
                    processed_data['department'] = value
                elif field_name == 'budget_amount':
                    try:
                        budget_amount = Decimal(value.replace(',', '').replace('R', '').replace('$', ''))
                        processed_data['budget_amount'] = float(budget_amount)
                    except:
                        pass
                elif field_name == 'actual_amount':
                    try:
                        actual_amount = Decimal(value.replace(',', '').replace('R', '').replace('$', ''))
                        processed_data['actual_amount'] = float(actual_amount)
                    except:
                        pass
                elif field_name == 'variance':
                    try:
                        variance = Decimal(value.replace(',', '').replace('R', '').replace('$', ''))
                        processed_data['variance'] = float(variance)
                    except:
                        pass
                else:
                    processed_data[field_name] = value
        
        # Calculate variance if not provided but we have budget and actual
        if variance is None and budget_amount is not None and actual_amount is not None:
            variance = actual_amount - budget_amount
        
        # Use account_description if not set
        if not account_description:
            account_description = f"Account {account_code}" if account_code else "Unknown Account"
        
        # Create data row
        data_row = BudgetReportDataRow(
            session_id=session_id,
            row_index=row_index,
            raw_data=raw_data,
            processed_data=processed_data,
            account_code=account_code,
            account_description=account_description,
            budget_amount=budget_amount,
            actual_amount=actual_amount,
            variance=variance,
            department=department,
            expense_category=expense_category,
            mapping_status='unmapped',
            validation_status='pending'
        )
        
        return data_row
    
    def validate_document_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate budget report structure"""
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'structure_type': 'unknown',
            'budget_columns': [],
            'actual_columns': [],
            'variance_columns': [],
            'department_columns': []
        }
        
        try:
            # Check minimum required columns
            if len(df.columns) < 2:
                result['errors'].append("Budget report must have at least 2 columns")
                return result
            
            # Detect structure type
            structure_type = self._detect_budget_structure(df)
            result['structure_type'] = structure_type
            
            # Validate based on structure type
            if structure_type == 'budget_vs_actual':
                validation = self._validate_budget_vs_actual_structure(df)
            elif structure_type == 'simple_budget':
                validation = self._validate_simple_budget_structure(df)
            elif structure_type == 'departmental':
                validation = self._validate_departmental_structure(df)
            else:
                validation = self._validate_generic_budget_structure(df)
            
            result.update(validation)
            
            # Check for required financial data
            if not result['budget_columns'] and not result['actual_columns']:
                result['errors'].append("No budget or actual amount columns detected")
            
            # Overall validation
            result['valid'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f"Validation error: {str(e)}")
            result['valid'] = False
        
        return result
    
    def _detect_budget_structure(self, df: pd.DataFrame) -> str:
        """Detect the type of budget structure"""
        columns = [str(col).lower() for col in df.columns]
        
        # Check for budget vs actual structure
        if any('budget' in col for col in columns) and any('actual' in col for col in columns):
            return 'budget_vs_actual'
        
        # Check for departmental structure
        if any('dept' in col or 'department' in col for col in columns):
            return 'departmental'
        
        # Check for simple budget structure
        if any('budget' in col or 'planned' in col or 'projected' in col for col in columns):
            return 'simple_budget'
        
        return 'generic'
    
    def _validate_budget_vs_actual_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate budget vs actual structure"""
        result = {
            'errors': [],
            'warnings': [],
            'budget_columns': [],
            'actual_columns': [],
            'variance_columns': []
        }
        
        # Find budget and actual columns
        for col in df.columns:
            col_lower = str(col).lower()
            if any(pattern in col_lower for pattern in ['budget', 'planned', 'projected', 'estimated']):
                result['budget_columns'].append(col)
            elif any(pattern in col_lower for pattern in ['actual', 'real', 'spent', 'incurred']):
                result['actual_columns'].append(col)
            elif any(pattern in col_lower for pattern in ['variance', 'difference', 'deviation']):
                result['variance_columns'].append(col)
        
        # Validate that we have both budget and actual columns
        if not result['budget_columns']:
            result['errors'].append("No budget columns detected")
        if not result['actual_columns']:
            result['errors'].append("No actual columns detected")
        
        return result
    
    def _validate_simple_budget_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate simple budget structure"""
        result = {
            'errors': [],
            'warnings': [],
            'budget_columns': [],
            'actual_columns': [],
            'variance_columns': []
        }
        
        # Look for budget column
        budget_col = None
        for col in df.columns:
            if any(pattern in str(col).lower() for pattern in ['budget', 'amount', 'total', 'value']):
                budget_col = col
                result['budget_columns'].append(col)
                break
        
        if not budget_col:
            result['errors'].append("No budget column found")
        else:
            # Check if budget column contains numeric data
            try:
                numeric_data = pd.to_numeric(df[budget_col], errors='coerce')
                if numeric_data.isna().all():
                    result['errors'].append(f"Budget column '{budget_col}' contains no numeric data")
            except:
                result['errors'].append(f"Budget column '{budget_col}' cannot be converted to numbers")
        
        return result
    
    def _validate_departmental_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate departmental budget structure"""
        result = {
            'errors': [],
            'warnings': [],
            'budget_columns': [],
            'actual_columns': [],
            'variance_columns': [],
            'department_columns': []
        }
        
        # Find department column
        dept_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if any(pattern in col_lower for pattern in ['department', 'dept', 'division', 'unit']):
                dept_col = col
                result['department_columns'].append(col)
                break
        
        if not dept_col:
            result['errors'].append("No department column found")
        
        # Find budget/actual columns
        for col in df.columns:
            col_lower = str(col).lower()
            if any(pattern in col_lower for pattern in ['budget', 'planned', 'projected']):
                result['budget_columns'].append(col)
            elif any(pattern in col_lower for pattern in ['actual', 'real', 'spent']):
                result['actual_columns'].append(col)
        
        return result
    
    def _validate_generic_budget_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate generic budget structure"""
        result = {
            'errors': [],
            'warnings': [],
            'budget_columns': [],
            'actual_columns': [],
            'variance_columns': []
        }
        
        # Try to identify any numeric columns as budget columns
        for col in df.columns:
            try:
                numeric_data = pd.to_numeric(df[col], errors='coerce')
                if not numeric_data.isna().all():
                    result['budget_columns'].append(col)
            except:
                continue
        
        if not result['budget_columns']:
            result['errors'].append("No numeric columns found for budget amounts")
        else:
            result['warnings'].append("Generic structure detected - manual review recommended")
        
        return result
    
    def create_session(self, file_path: str, user_id: str, filename: str) -> BudgetReportSession:
        """Create budget report specific session"""
        session = BudgetReportSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            document_type="budget_report",
            filename=filename,
            original_filename=filename,
            file_type=filename.split('.')[-1].lower(),
            file_format=filename.split('.')[-1].lower(),
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Try to extract budget information from filename
        self._extract_budget_info(session, filename)
        
        return session
    
    def _extract_budget_info(self, session: BudgetReportSession, filename: str):
        """Extract budget information from filename"""
        filename_lower = filename.lower()
        
        # Detect fiscal year
        year_match = re.search(r'20\d{2}', filename_lower)
        if year_match:
            session.fiscal_year = int(year_match.group())
        
        # Detect budget type
        if any(op in filename_lower for op in ['operating', 'opex', 'expense']):
            session.budget_type = 'operating'
        elif any(cap in filename_lower for cap in ['capital', 'capex', 'investment']):
            session.budget_type = 'capital'
        elif any(cash in filename_lower for cash in ['cash', 'liquidity', 'flow']):
            session.budget_type = 'cash'
        
        # Extract department if present
        dept_patterns = ['finance', 'hr', 'it', 'operations', 'marketing', 'sales', 'admin']
        for dept in dept_patterns:
            if dept in filename_lower:
                session.department = dept.title()
                break
        
        # Extract reporting period
        if session.fiscal_year:
            if any(qtr in filename_lower for qtr in ['q1', 'q2', 'q3', 'q4']):
                qtr_match = re.search(r'q([1-4])', filename_lower)
                if qtr_match:
                    session.reporting_period = f"{session.fiscal_year}-Q{qtr_match.group(1)}"
            else:
                session.reporting_period = f"{session.fiscal_year}"
    
    def _store_session(self, session: BudgetReportSession) -> BudgetReportSession:
        """Store session in database using proper RLS handling"""
        try:
            # Use the new method that handles RLS properly
            return self.create_session_with_user_context("", session.user_id, session.original_filename)
        except Exception as e:
            # Fallback to regular method
            print(f"⚠️ RLS bypass failed, using regular method: {e}")
            model = self.get_model()
            return model.create_session(session)
    
    def get_model(self):
        """Get the budget report model"""
        # This will be created when we create the database models
        from models.budget_report_models import budget_report_model
        return budget_report_model
    
    def create_session_with_user_context(self, file_path: str, user_id: str, filename: str) -> BudgetReportSession:
        """Create budget report session with proper user context for RLS"""
        # Create session object
        session = self.create_session(file_path, user_id, filename)
        
        # Use service role client to bypass RLS for session creation
        try:
            from utils.supabase_client import create_supabase_client_with_rls_bypass
            admin_client = create_supabase_client_with_rls_bypass()
            
            # Insert session using admin client
            data = session.to_dict()
            response = admin_client.table("budget_report_sessions").insert(data).execute()
            
            if response.data:
                session.id = response.data[0]['id']
                return session
            else:
                raise Exception("Failed to create session with admin client")
                
        except Exception as e:
            # Fallback to regular model
            print(f"⚠️ Admin client failed, using regular model: {e}")
            model = self.get_model()
            return model.create_session(session)
    
    def calculate_budget_variance(self, session_id: str) -> Dict[str, Any]:
        """Calculate budget vs actual variance"""
        try:
            model = self.get_model()
            session = model.get_session(session_id)
            
            if not session:
                return {'success': False, 'error': 'Session not found'}
            
            # Get data rows
            data_rows = model.get_data_rows(session_id)
            
            total_budget = Decimal('0.00')
            total_actual = Decimal('0.00')
            
            # Calculate totals based on column mapping
            column_mapping = session.metadata.get('column_mapping', {})
            
            for row in data_rows:
                budget_amount = Decimal('0.00')
                actual_amount = Decimal('0.00')
                
                # Get budget amount
                if 'budget_amount' in column_mapping:
                    budget_amount = Decimal(str(row.get(column_mapping['budget_amount'], '0')))
                
                # Get actual amount
                if 'actual_amount' in column_mapping:
                    actual_amount = Decimal(str(row.get(column_mapping['actual_amount'], '0')))
                
                total_budget += budget_amount
                total_actual += actual_amount
            
            # Calculate variance
            total_variance = total_actual - total_budget
            variance_percentage = (total_variance / total_budget * 100) if total_budget != 0 else Decimal('0.00')
            
            # Update session with calculated values
            session.total_budget = total_budget
            session.total_actual = total_actual
            session.total_variance = total_variance
            session.variance_percentage = variance_percentage
            
            # Save updated session
            model.update_session(session)
            
            return {
                'success': True,
                'total_budget': float(total_budget),
                'total_actual': float(total_actual),
                'total_variance': float(total_variance),
                'variance_percentage': float(variance_percentage),
                'message': f"Budget variance calculated: Budget R{total_budget:,.2f}, Actual R{total_actual:,.2f}, Variance R{total_variance:,.2f} ({variance_percentage:.1f}%)"
            }
            
        except Exception as e:
            logger.error(f"Error calculating budget variance: {str(e)}")
            return {'success': False, 'error': f'Error calculating budget variance: {str(e)}'}
    
    def analyze_budget_performance(self, session_id: str) -> Dict[str, Any]:
        """Analyze budget performance with insights"""
        try:
            variance_result = self.calculate_budget_variance(session_id)
            
            if not variance_result['success']:
                return variance_result
            
            variance_pct = variance_result['variance_percentage']
            
            # Generate performance insights
            insights = []
            
            if abs(variance_pct) <= 5:
                insights.append("Budget performance is excellent - variance within 5%")
                performance_rating = "Excellent"
            elif abs(variance_pct) <= 10:
                insights.append("Budget performance is good - variance within 10%")
                performance_rating = "Good"
            elif abs(variance_pct) <= 20:
                insights.append("Budget performance needs attention - variance over 10%")
                performance_rating = "Needs Attention"
            else:
                insights.append("Budget performance requires immediate review - variance over 20%")
                performance_rating = "Critical"
            
            # Specific insights based on variance direction
            if variance_pct > 0:
                insights.append(f"Over budget by R{variance_result['total_variance']:,.2f}")
            elif variance_pct < 0:
                insights.append(f"Under budget by R{abs(variance_result['total_variance']):,.2f}")
            
            return {
                'success': True,
                'performance_rating': performance_rating,
                'insights': insights,
                **variance_result
            }
            
        except Exception as e:
            logger.error(f"Error analyzing budget performance: {str(e)}")
            return {'success': False, 'error': f'Error analyzing budget performance: {str(e)}'}


# Import regex for budget info extraction
import re

# Global instance
budget_report_service = BudgetReportService()
