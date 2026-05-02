"""
SADPMR Financial Reporting System - Budget Management Service
GRAP 24 compliant budget vs actual comparison service
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
from models.budget_models import BudgetModel

class BudgetService:
    """Service for budget management and variance analysis"""
    
    def __init__(self):
        self.budget_model = BudgetModel()
        self.budget_storage = {}  # In production, this would be database
    
    def create_budget_from_balance_sheet(self, balance_sheet_path: str, 
                                     fiscal_year: int = 2026) -> Dict[str, Any]:
        """Create budget from balance sheet data"""
        try:
            # Import balance sheet
            df = pd.read_excel(balance_sheet_path) if balance_sheet_path.endswith('.xlsx') else pd.read_csv(balance_sheet_path)
            
            # Create budget structure
            budget_structure = self.budget_model.create_budget_structure(df)
            budget_structure['fiscal_year'] = fiscal_year
            
            # Store budget
            budget_id = budget_structure['budget_id']
            self.budget_storage[budget_id] = budget_structure
            
            return {
                'success': True,
                'budget_id': budget_id,
                'budget_data': budget_structure,
                'message': f'Budget created successfully with {len(budget_structure["original_budget"])} categories'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create budget: {str(e)}'
            }
    
    def import_actual_data(self, balance_sheet_path: str, budget_id: str) -> Dict[str, Any]:
        """Import actual data for budget comparison"""
        try:
            # Import balance sheet
            df = pd.read_excel(balance_sheet_path) if balance_sheet_path.endswith('.xlsx') else pd.read_csv(balance_sheet_path)
            
            # Get budget structure
            if budget_id not in self.budget_storage:
                return {
                    'success': False,
                    'error': f'Budget {budget_id} not found'
                }
            
            budget_structure = self.budget_storage[budget_id]
            
            # Extract actual data using same categorization
            actual_data = {}
            for _, row in df.iterrows():
                account_code = str(row.get('Account Code', ''))
                account_desc = row.get('Account Description', '')
                net_balance = row.get('Net Balance', 0)
                
                if net_balance != 0:
                    category = self.budget_model._categorize_account(account_code, account_desc)
                    if category not in actual_data:
                        actual_data[category] = 0
                    actual_data[category] += abs(net_balance)
            
            # Store actual data
            budget_structure['actual_data'] = actual_data
            budget_structure['actual_data_date'] = datetime.now().isoformat()
            
            return {
                'success': True,
                'budget_id': budget_id,
                'actual_data': actual_data,
                'message': f'Actual data imported with {len(actual_data)} categories'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to import actual data: {str(e)}'
            }
    
    def calculate_variance_analysis(self, budget_id: str) -> Dict[str, Any]:
        """Calculate variance analysis between budget and actual"""
        try:
            if budget_id not in self.budget_storage:
                return {
                    'success': False,
                    'error': f'Budget {budget_id} not found'
                }
            
            budget_structure = self.budget_storage[budget_id]
            
            if 'actual_data' not in budget_structure:
                return {
                    'success': False,
                    'error': 'No actual data available for comparison'
                }
            
            # Calculate variance analysis
            variance_analysis = self.budget_model.calculate_variance_analysis(
                budget_structure['original_budget'],
                budget_structure['actual_data']
            )
            
            # Store variance analysis
            budget_structure['variance_analysis'] = variance_analysis
            budget_structure['variance_calculated_date'] = datetime.now().isoformat()
            
            return {
                'success': True,
                'budget_id': budget_id,
                'variance_analysis': variance_analysis,
                'message': 'Variance analysis calculated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to calculate variance analysis: {str(e)}'
            }
    
    def create_budget_revision(self, budget_id: str, revision_reason: str, 
                           revised_amounts: Dict[str, float]) -> Dict[str, Any]:
        """Create a budget revision with audit trail"""
        try:
            if budget_id not in self.budget_storage:
                return {
                    'success': False,
                    'error': f'Budget {budget_id} not found'
                }
            
            budget_structure = self.budget_storage[budget_id]
            original_budget = budget_structure['original_budget']
            
            # Create revision
            revision = self.budget_model.create_budget_revision(
                original_budget, revision_reason, revised_amounts
            )
            
            # Add revision to budget structure
            if 'revisions' not in budget_structure:
                budget_structure['revisions'] = []
            
            budget_structure['revisions'].append(revision)
            budget_structure['last_revised_date'] = datetime.now().isoformat()
            
            # Update original budget if this is a final revision
            if revision_reason.lower().startswith('final'):
                budget_structure['original_budget'] = revised_amounts.copy()
                budget_structure['status'] = 'final'
            
            return {
                'success': True,
                'budget_id': budget_id,
                'revision': revision,
                'message': f'Budget revision {revision["revision_id"]} created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create budget revision: {str(e)}'
            }
    
    def get_budget_summary(self, budget_id: str) -> Dict[str, Any]:
        """Get budget summary for display"""
        try:
            if budget_id not in self.budget_storage:
                return {
                    'success': False,
                    'error': f'Budget {budget_id} not found'
                }
            
            budget_structure = self.budget_storage[budget_id]
            
            summary = {
                'budget_id': budget_id,
                'fiscal_year': budget_structure.get('fiscal_year', 2026),
                'status': budget_structure.get('status', 'draft'),
                'created_at': budget_structure.get('created_at'),
                'total_budget': sum(budget_structure.get('original_budget', {}).values()),
                'categories_count': len(budget_structure.get('original_budget', {})),
                'has_actual_data': 'actual_data' in budget_structure,
                'has_variance_analysis': 'variance_analysis' in budget_structure,
                'revisions_count': len(budget_structure.get('revisions', [])),
                'last_revised_date': budget_structure.get('last_revised_date')
            }
            
            return {
                'success': True,
                'summary': summary
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get budget summary: {str(e)}'
            }
    
    def export_budget_report(self, budget_id: str, format_type: str = 'json') -> Dict[str, Any]:
        """Export budget vs actual comparison report"""
        try:
            if budget_id not in self.budget_storage:
                return {
                    'success': False,
                    'error': f'Budget {budget_id} not found'
                }
            
            budget_structure = self.budget_storage[budget_id]
            
            if 'variance_analysis' not in budget_structure:
                return {
                    'success': False,
                    'error': 'No variance analysis available for export'
                }
            
            # Generate report
            report = self.budget_model.export_budget_report(
                budget_structure['original_budget'],
                budget_structure['variance_analysis']
            )
            
            # Add budget metadata
            report['budget_metadata'] = {
                'budget_id': budget_id,
                'fiscal_year': budget_structure.get('fiscal_year', 2026),
                'status': budget_structure.get('status', 'draft'),
                'created_at': budget_structure.get('created_at'),
                'revisions_count': len(budget_structure.get('revisions', []))
            }
            
            return {
                'success': True,
                'report': report,
                'format': format_type,
                'message': f'Budget report exported in {format_type} format'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to export budget report: {str(e)}'
            }
    
    def list_budgets(self) -> Dict[str, Any]:
        """List all budgets"""
        try:
            budgets = []
            for budget_id, budget_data in self.budget_storage.items():
                summary = {
                    'budget_id': budget_id,
                    'fiscal_year': budget_data.get('fiscal_year', 2026),
                    'status': budget_data.get('status', 'draft'),
                    'created_at': budget_data.get('created_at'),
                    'total_budget': sum(budget_data.get('original_budget', {}).values()),
                    'categories_count': len(budget_data.get('original_budget', {})),
                    'has_actual_data': 'actual_data' in budget_data,
                    'has_variance_analysis': 'variance_analysis' in budget_data,
                    'revisions_count': len(budget_data.get('revisions', []))
                }
                budgets.append(summary)
            
            return {
                'success': True,
                'budgets': budgets,
                'count': len(budgets)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to list budgets: {str(e)}'
            }
    
    def delete_budget(self, budget_id: str) -> Dict[str, Any]:
        """Delete a budget (soft delete with audit trail)"""
        try:
            if budget_id not in self.budget_storage:
                return {
                    'success': False,
                    'error': f'Budget {budget_id} not found'
                }
            
            # Soft delete - mark as deleted but keep for audit trail
            budget_structure = self.budget_storage[budget_id]
            budget_structure['status'] = 'deleted'
            budget_structure['deleted_at'] = datetime.now().isoformat()
            budget_structure['deleted_by'] = 'system'  # In production, this would be user ID
            
            return {
                'success': True,
                'budget_id': budget_id,
                'message': f'Budget {budget_id} marked as deleted'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to delete budget: {str(e)}'
            }
