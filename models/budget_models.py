"""
Varydian Financial Reporting System - Budget Management Models
GRAP 24 compliant budget vs actual comparison system
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

class BudgetModel:
    """Budget management model for GRAP 24 compliance"""
    
    def __init__(self):
        self.budget_data = {}
        self.actual_data = {}
        self.variance_data = {}
        
    def create_budget_structure(self, balance_sheet_data: pd.DataFrame) -> Dict[str, Any]:
        """Create budget structure from balance sheet data"""
        budget_structure = {
            'budget_id': f"BUD_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'created_at': datetime.now().isoformat(),
            'fiscal_year': 2026,  # Default fiscal year
            'status': 'draft',
            'original_budget': {},
            'revisions': [],
            'variance_thresholds': {
                'material_variance': 0.05,  # 5% material variance threshold
                'labor_variance': 0.10,   # 10% labor variance threshold
                'other_variance': 0.07     # 7% other variance threshold
            }
        }
        
        # Map balance sheet accounts to budget categories
        for _, row in balance_sheet_data.iterrows():
            account_code = str(row.get('Account Code', ''))
            account_desc = row.get('Account Description', '')
            net_balance = row.get('Net Balance', 0)
            
            if net_balance != 0:
                category = self._categorize_account(account_code, account_desc)
                if category not in budget_structure['original_budget']:
                    budget_structure['original_budget'][category] = 0
                
                budget_structure['original_budget'][category] += abs(net_balance)
        
        return budget_structure
    
    def _categorize_account(self, account_code: str, account_desc: str) -> str:
        """Categorize account for budgeting purposes"""
        account_code = account_code.zfill(4)  # Ensure 4-digit code
        
        # Revenue categories
        if account_code.startswith('4'):
            if 'revenue' in account_desc.lower() or 'income' in account_desc.lower():
                return 'revenue_exchange'
            else:
                return 'revenue_non_exchange'
        
        # Expense categories
        elif account_code.startswith('5'):
            if 'employee' in account_desc.lower() or 'salary' in account_desc.lower() or 'wages' in account_desc.lower():
                return 'expenses_labor'
            elif 'depreci' in account_desc.lower() or 'amort' in account_desc.lower():
                return 'expenses_depreciation'
            else:
                return 'expenses_other'
        
        # Asset categories
        elif account_code.startswith('1'):
            return 'assets_current'
        elif account_code.startswith('2'):
            return 'assets_receivables'
        elif account_code.startswith(('16', '17', '18')):
            return 'assets_non_current'
        
        # Liability categories
        elif account_code.startswith('2'):
            return 'liabilities_current'
        elif account_code.startswith(('23', '24')):
            return 'liabilities_non_current'
        
        # Equity categories
        elif account_code.startswith('3'):
            return 'equity'
        
        return 'other'
    
    def calculate_variance_analysis(self, budget_data: Dict, actual_data: Dict) -> Dict[str, Any]:
        """Calculate variance analysis between budget and actual"""
        variance_analysis = {
            'analysis_id': f"VAR_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'calculated_at': datetime.now().isoformat(),
            'overall_variance': {},
            'category_variances': {},
            'explanations': {},
            'materiality_threshold': 0.05  # 5% materiality threshold
        }
        
        total_budget = sum(budget_data.values())
        total_actual = sum(actual_data.values())
        overall_variance_amount = total_actual - total_budget
        overall_variance_percentage = (overall_variance_amount / total_budget * 100) if total_budget != 0 else 0
        
        variance_analysis['overall_variance'] = {
            'total_budget': total_budget,
            'total_actual': total_actual,
            'variance_amount': overall_variance_amount,
            'variance_percentage': overall_variance_percentage,
            'is_favorable': overall_variance_amount < 0,
            'is_material': abs(overall_variance_percentage) > variance_analysis['materiality_threshold'] * 100
        }
        
        # Calculate category-level variances
        for category in budget_data:
            if category in actual_data:
                budget_amount = budget_data[category]
                actual_amount = actual_data[category]
                variance_amount = actual_amount - budget_amount
                variance_percentage = (variance_amount / budget_amount * 100) if budget_amount != 0 else 0
                
                # Determine materiality and explanation
                is_material = abs(variance_percentage) > self._get_materiality_threshold(category) * 100
                explanation = self._generate_variance_explanation(
                    category, variance_amount, variance_percentage, is_material
                )
                
                variance_analysis['category_variances'][category] = {
                    'budget_amount': budget_amount,
                    'actual_amount': actual_amount,
                    'variance_amount': variance_amount,
                    'variance_percentage': variance_percentage,
                    'is_favorable': variance_amount < 0,
                    'is_material': is_material,
                    'explanation': explanation
                }
        
        return variance_analysis
    
    def _get_materiality_threshold(self, category: str) -> float:
        """Get materiality threshold for category"""
        thresholds = {
            'revenue_exchange': 0.03,      # 3% for revenue
            'revenue_non_exchange': 0.05,  # 5% for non-exchange revenue
            'expenses_labor': 0.10,        # 10% for labor costs
            'expenses_depreciation': 0.15, # 15% for depreciation
            'expenses_other': 0.07,        # 7% for other expenses
            'assets_current': 0.05,          # 5% for current assets
            'assets_non_current': 0.10,      # 10% for non-current assets
            'liabilities_current': 0.05,        # 5% for current liabilities
            'liabilities_non_current': 0.08,  # 8% for non-current liabilities
            'equity': 0.05,                  # 5% for equity
        }
        return thresholds.get(category, 0.05)  # Default 5%
    
    def _generate_variance_explanation(self, category: str, variance_amount: float, 
                                     variance_percentage: float, is_material: bool) -> str:
        """Generate automated variance explanation"""
        if abs(variance_percentage) < 1:
            return "Variance is immaterial and within acceptable tolerance."
        
        if variance_amount > 0:  # Unfavorable variance
            explanations = {
                'revenue_exchange': "Revenue exceeded budget due to increased economic activity.",
                'revenue_non_exchange': "Non-exchange revenue higher than budgeted, possibly due to policy changes.",
                'expenses_labor': "Labor costs exceeded budget, potentially due to overtime or staffing increases.",
                'expenses_depreciation': "Depreciation higher than budgeted, possibly due to asset additions.",
                'expenses_other': "Other expenses exceeded budget, requiring further investigation.",
                'assets_current': "Current assets higher than budgeted, possibly due to cash flow changes.",
                'assets_non_current': "Non-current assets exceeded budget, possibly due to capital expenditures.",
                'liabilities_current': "Current liabilities higher than budgeted, possibly due to increased borrowing.",
                'liabilities_non_current': "Non-current liabilities exceeded budget, possibly due to long-term financing.",
                'equity': "Equity position affected by overall variance."
            }
        else:  # Favorable variance
            explanations = {
                'revenue_exchange': "Revenue below budget, possibly due to economic conditions.",
                'revenue_non_exchange': "Non-exchange revenue lower than budgeted, possibly due to policy changes.",
                'expenses_labor': "Labor costs below budget, possibly due to efficiency gains or staffing reductions.",
                'expenses_depreciation': "Depreciation lower than budgeted, possibly due to asset disposals.",
                'expenses_other': "Other expenses below budget, indicating cost control effectiveness.",
                'assets_current': "Current assets lower than budgeted, possibly due to cash management.",
                'assets_non_current': "Non-current assets lower than budgeted, possibly due to asset disposals.",
                'liabilities_current': "Current liabilities lower than budgeted, possibly due to debt repayment.",
                'liabilities_non_current': "Non-current liabilities lower than budgeted, possibly due to debt restructuring.",
                'equity': "Equity position improved by favorable variance."
            }
        
        return explanations.get(category, "Variance requires manual investigation and explanation.")
    
    def create_budget_revision(self, original_budget: Dict, revision_reason: str, 
                           revised_amounts: Dict[str, float]) -> Dict[str, Any]:
        """Create a budget revision with audit trail"""
        revision = {
            'revision_id': f"REV_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'revision_date': datetime.now().isoformat(),
            'reason': revision_reason,
            'revised_by': 'system',  # In production, this would be user ID
            'original_amounts': original_budget.copy(),
            'revised_amounts': revised_amounts.copy(),
            'changes': {}
        }
        
        # Calculate changes for each category
        for category in original_budget:
            if category in revised_amounts:
                original = original_budget[category]
                revised = revised_amounts[category]
                change = revised - original
                change_percentage = (change / original * 100) if original != 0 else 0
                
                revision['changes'][category] = {
                    'original_amount': original,
                    'revised_amount': revised,
                    'change_amount': change,
                    'change_percentage': change_percentage,
                    'is_increase': change > 0
                }
        
        return revision
    
    def generate_grap24_statement(self, budget_id: str) -> Dict[str, Any]:
        """Generate GRAP 24 compliant Statement of Comparison of Budget and Actual Amounts"""
        if budget_id not in self.budget_storage:
            return {
                'success': False,
                'error': f'Budget {budget_id} not found'
            }
        
        budget_structure = self.budget_storage[budget_id]
        
        if 'actual_data' not in budget_structure:
            return {
                'success': False,
                'error': 'No actual data available for GRAP 24 statement'
            }
        
        grap24_statement = {
            'statement_id': f"GRAP24_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'statement_type': 'Statement of Comparison of Budget and Actual Amounts',
            'grap_reference': 'GRAP 24 - Budget Reporting',
            'fiscal_year': budget_structure.get('fiscal_year', 2026),
            'entity_name': 'Varydian Financial Reporting System',
            'reporting_period': f"Year ended {budget_structure.get('fiscal_year', 2026)}",
            'currency': 'ZAR',
            'amounts_shown_in': 'Thousands of Rand',
            'three_column_comparison': [],
            'variance_analysis': {},
            'compliance_notes': self._get_grap24_compliance_notes()
        }
        
        # Generate three-column comparison for each category
        original_budget = budget_structure['original_budget']
        actual_data = budget_structure['actual_data']
        
        for category in original_budget:
            if category in actual_data:
                original_amount = original_budget[category]
                adjustments = self._calculate_category_adjustments(category, budget_structure)
                final_budget = original_amount + adjustments
                actual_amount = actual_data[category]
                variance = actual_amount - final_budget
                variance_percentage = (variance / final_budget * 100) if final_budget != 0 else 0
                
                comparison_entry = {
                    'category': category,
                    'category_description': self._get_category_description(category),
                    'original_budget': original_amount,
                    'adjustments': adjustments,
                    'adjustment_details': self._get_adjustment_details(category, budget_structure),
                    'final_budget': final_budget,
                    'actual_amount': actual_amount,
                    'variance': variance,
                    'variance_percentage': variance_percentage,
                    'is_favorable': variance < 0,
                    'is_material': abs(variance_percentage) > self._get_materiality_threshold(category) * 100,
                    'grap_classification': self._classify_budget_item(category)
                }
                
                grap24_statement['three_column_comparison'].append(comparison_entry)
        
        # Calculate totals
        totals = self._calculate_grap24_totals(grap24_statement['three_column_comparison'])
        grap24_statement['summary_totals'] = totals
        
        # Generate variance analysis
        grap24_statement['variance_analysis'] = self._create_grap24_variance_analysis(
            grap24_statement['three_column_comparison'], totals
        )
        
        return {
            'success': True,
            'grap24_statement': grap24_statement,
            'message': 'GRAP 24 statement generated successfully'
        }
    
    def _calculate_category_adjustments(self, category: str, budget_structure: Dict) -> float:
        """Calculate total adjustments for a budget category"""
        total_adjustments = 0.0
        
        if 'revisions' in budget_structure:
            for revision in budget_structure['revisions']:
                if category in revision['revised_amounts']:
                    original = revision['original_amounts'].get(category, 0)
                    revised = revision['revised_amounts'][category]
                    adjustment = revised - original
                    total_adjustments += adjustment
        
        return total_adjustments
    
    def _get_adjustment_details(self, category: str, budget_structure: Dict) -> List[Dict]:
        """Get detailed breakdown of adjustments for a category"""
        adjustment_details = []
        
        if 'revisions' in budget_structure:
            for revision in budget_structure['revisions']:
                if category in revision['revised_amounts']:
                    original = revision['original_amounts'].get(category, 0)
                    revised = revision['revised_amounts'][category]
                    adjustment = revised - original
                    
                    detail = {
                        'revision_id': revision['revision_id'],
                        'revision_date': revision['revision_date'],
                        'reason': revision['reason'],
                        'original_amount': original,
                        'revised_amount': revised,
                        'adjustment_amount': adjustment,
                        'is_increase': adjustment > 0
                    }
                    adjustment_details.append(detail)
        
        return adjustment_details
    
    def _get_category_description(self, category: str) -> str:
        """Get descriptive name for budget category"""
        descriptions = {
            'revenue_exchange': 'Revenue from Exchange Transactions',
            'revenue_non_exchange': 'Revenue from Non-Exchange Transactions',
            'expenses_labor': 'Employee Costs',
            'expenses_depreciation': 'Depreciation and Amortisation',
            'expenses_other': 'Other Expenses',
            'assets_current': 'Current Assets',
            'assets_receivables': 'Receivables',
            'assets_non_current': 'Non-Current Assets',
            'liabilities_current': 'Current Liabilities',
            'liabilities_non_current': 'Non-Current Liabilities',
            'equity': 'Net Assets'
        }
        return descriptions.get(category, category.replace('_', ' ').title())
    
    def _classify_budget_item(self, category: str) -> str:
        """Classify budget item according to GRAP 24 requirements"""
        if 'revenue' in category:
            return 'operating_revenue'
        elif 'expenses' in category:
            return 'operating_expense'
        elif 'assets' in category:
            return 'balance_sheet_item'
        elif 'liabilities' in category or 'equity' in category:
            return 'balance_sheet_item'
        else:
            return 'other'
    
    def _calculate_grap24_totals(self, comparison_data: List[Dict]) -> Dict[str, Any]:
        """Calculate totals for GRAP 24 statement"""
        totals = {
            'original_budget_total': sum(item['original_budget'] for item in comparison_data),
            'adjustments_total': sum(item['adjustments'] for item in comparison_data),
            'final_budget_total': sum(item['final_budget'] for item in comparison_data),
            'actual_total': sum(item['actual_amount'] for item in comparison_data),
            'variance_total': sum(item['variance'] for item in comparison_data),
            'favorable_variances': 0,
            'unfavorable_variances': 0,
            'material_variances': 0
        }
        
        for item in comparison_data:
            if item['variance'] < 0:
                totals['favorable_variances'] += abs(item['variance'])
            else:
                totals['unfavorable_variances'] += item['variance']
            
            if item['is_material']:
                totals['material_variances'] += 1
        
        totals['variance_percentage'] = (totals['variance_total'] / totals['final_budget_total'] * 100) if totals['final_budget_total'] != 0 else 0
        
        return totals
    
    def _create_grap24_variance_analysis(self, comparison_data: List[Dict], totals: Dict) -> Dict[str, Any]:
        """Create comprehensive variance analysis for GRAP 24"""
        analysis = {
            'overall_variance': {
                'amount': totals['variance_total'],
                'percentage': totals['variance_percentage'],
                'is_favorable': totals['variance_total'] < 0,
                'materiality_assessment': 'Material' if abs(totals['variance_percentage']) > 5 else 'Immaterial'
            },
            'significant_variances': [],
            'variance_by_category': {},
            'explanations_required': []
        }
        
        # Identify significant variances
        for item in comparison_data:
            if item['is_material']:
                significance = {
                    'category': item['category'],
                    'variance_amount': item['variance'],
                    'variance_percentage': item['variance_percentage'],
                    'impact_assessment': 'High' if abs(item['variance_percentage']) > 10 else 'Medium',
                    'explanation_required': True
                }
                analysis['significant_variances'].append(significance)
                analysis['explanations_required'].append(item['category'])
        
        # Group variances by category type
        for item in comparison_data:
            classification = item['grap_classification']
            if classification not in analysis['variance_by_category']:
                analysis['variance_by_category'][classification] = {
                    'total_variance': 0,
                    'item_count': 0,
                    'material_count': 0
                }
            
            analysis['variance_by_category'][classification]['total_variance'] += item['variance']
            analysis['variance_by_category'][classification]['item_count'] += 1
            if item['is_material']:
                analysis['variance_by_category'][classification]['material_count'] += 1
        
        return analysis
    
    def _get_grap24_compliance_notes(self) -> List[str]:
        """Get GRAP 24 compliance notes and disclosures"""
        return [
            "This statement is prepared in accordance with GRAP 24 requirements",
            "Budget classifications follow the entity's budget structure",
            "Material variances are identified and explained",
            "Adjustments to original budget are disclosed with reasons",
            "Comparative figures are presented for consistency",
            "All amounts are shown in thousands of Rand unless otherwise stated",
            "Variance calculations are based on final budget amounts after adjustments"
        ]
    
    def export_budget_report(self, budget_data: Dict, variance_data: Dict) -> Dict[str, Any]:
        """Export budget vs actual comparison report"""
        report = {
            'report_id': f"BUD_RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'fiscal_year': 2026,
            'report_type': 'budget_vs_actual',
            'executive_summary': self._create_executive_summary(budget_data, variance_data),
            'detailed_analysis': variance_data.get('category_variances', {}),
            'recommendations': self._generate_recommendations(variance_data)
        }
        
        return report
    
    def _create_executive_summary(self, budget_data: Dict, variance_data: Dict) -> Dict[str, Any]:
        """Create executive summary of budget performance"""
        overall = variance_data.get('overall_variance', {})
        
        # Find significant variances
        significant_variances = []
        for category, variance in variance_data.get('category_variances', {}).items():
            if variance.get('is_material', False):
                significant_variances.append({
                    'category': category,
                    'variance_percentage': variance.get('variance_percentage', 0),
                    'explanation': variance.get('explanation', '')
                })
        
        return {
            'total_budget': overall.get('total_budget', 0),
            'total_actual': overall.get('total_actual', 0),
            'total_variance': overall.get('variance_amount', 0),
            'variance_percentage': overall.get('variance_percentage', 0),
            'is_favorable': overall.get('is_favorable', True),
            'significant_variances_count': len(significant_variances),
            'significant_variances': significant_variances[:5],  # Top 5 significant variances
            'material_variances_count': len([v for v in variance_data.get('category_variances', {}).values() if v.get('is_material', False)])
        }
    
    def _generate_recommendations(self, variance_data: Dict) -> List[str]:
        """Generate recommendations based on variance analysis"""
        recommendations = []
        
        overall = variance_data.get('overall_variance', {})
        variance_percentage = abs(overall.get('variance_percentage', 0))
        
        if variance_percentage > 10:
            recommendations.append("Significant variance detected - Management review required")
        elif variance_percentage > 5:
            recommendations.append("Moderate variance - Investigate underlying causes")
        elif variance_percentage < 2:
            recommendations.append("Good budgetary control - Maintain current practices")
        
        # Category-specific recommendations
        for category, variance in variance_data.get('category_variances', {}).items():
            if variance.get('is_material', False):
                if 'expenses' in category:
                    recommendations.append(f"Review {category} controls and implement cost-saving measures")
                elif 'revenue' in category:
                    recommendations.append(f"Analyze {category} trends and adjust forecasting")
        
        return recommendations
