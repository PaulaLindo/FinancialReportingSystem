"""
SADPMR Financial Reporting System - Calculation Transparency Models
Formula transparency and calculation disclosure system for GRAP compliance
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

class CalculationTransparencyModel:
    """Model for providing formula transparency and calculation disclosure"""
    
    def __init__(self):
        self.calculation_registry = self._initialize_calculation_registry()
        self.variable_mappings = self._initialize_variable_mappings()
        
    def _initialize_calculation_registry(self) -> Dict[str, Any]:
        """Initialize registry of all calculations with their formulas"""
        return {
            'carrying_value': {
                'name': 'Carrying Value',
                'description': 'Net book value of an asset after depreciation',
                'formula': 'Asset Cost - Accumulated Depreciation',
                'calculation': 'asset_cost - accumulated_depreciation',
                'variables': [
                    {
                        'name': 'Asset Cost',
                        'description': 'Original purchase cost of the asset',
                        'source': 'Asset Register',
                        'type': 'monetary'
                    },
                    {
                        'name': 'Accumulated Depreciation',
                        'description': 'Total depreciation charged to date',
                        'source': 'Depreciation Schedule',
                        'type': 'monetary'
                    }
                ],
                'grap_reference': 'GRAP 17 - Property, Plant and Equipment',
                'example': {
                    'asset_cost': 100000,
                    'accumulated_depreciation': 25000,
                    'carrying_value': 75000
                }
            },
            'budget_variance': {
                'name': 'Budget Variance',
                'description': 'Difference between actual and budgeted amounts',
                'formula': 'Actual Amount - Budgeted Amount',
                'calculation': 'actual_amount - budgeted_amount',
                'variables': [
                    {
                        'name': 'Actual Amount',
                        'description': 'Actual expenditure or revenue incurred',
                        'source': 'Trial Balance / Actuals',
                        'type': 'monetary'
                    },
                    {
                        'name': 'Budgeted Amount',
                        'description': 'Approved budget for the period',
                        'source': 'Budget Register',
                        'type': 'monetary'
                    }
                ],
                'grap_reference': 'GRAP 24 - Budget Reporting',
                'example': {
                    'actual_amount': 120000,
                    'budgeted_amount': 100000,
                    'budget_variance': 20000
                }
            },
            'depreciation_expense': {
                'name': 'Depreciation Expense',
                'description': 'Periodic depreciation charge for assets',
                'formula': '(Asset Cost - Residual Value) / Useful Life',
                'calculation': '(asset_cost - residual_value) / useful_life',
                'variables': [
                    {
                        'name': 'Asset Cost',
                        'description': 'Original purchase cost of the asset',
                        'source': 'Asset Register',
                        'type': 'monetary'
                    },
                    {
                        'name': 'Residual Value',
                        'description': 'Estimated value at end of useful life',
                        'source': 'Asset Policy',
                        'type': 'monetary'
                    },
                    {
                        'name': 'Useful Life',
                        'description': 'Expected useful life in years',
                        'source': 'Asset Policy / GRAP 17',
                        'type': 'numeric'
                    }
                ],
                'grap_reference': 'GRAP 17 - Depreciation Methods',
                'example': {
                    'asset_cost': 100000,
                    'residual_value': 10000,
                    'useful_life': 10,
                    'depreciation_expense': 9000
                }
            },
            'current_ratio': {
                'name': 'Current Ratio',
                'description': 'Measure of short-term liquidity',
                'formula': 'Current Assets / Current Liabilities',
                'calculation': 'current_assets / current_liabilities',
                'variables': [
                    {
                        'name': 'Current Assets',
                        'description': 'Assets expected to be realized within 12 months',
                        'source': 'Statement of Financial Position',
                        'type': 'monetary'
                    },
                    {
                        'name': 'Current Liabilities',
                        'description': 'Liabilities due within 12 months',
                        'source': 'Statement of Financial Position',
                        'type': 'monetary'
                    }
                ],
                'grap_reference': 'Financial Analysis Ratios',
                'example': {
                    'current_assets': 250000,
                    'current_liabilities': 125000,
                    'current_ratio': 2.0
                }
            },
            'operating_margin': {
                'name': 'Operating Margin',
                'description': 'Profitability from core operations',
                'formula': '(Operating Revenue - Operating Expenses) / Operating Revenue × 100',
                'calculation': '((operating_revenue - operating_expenses) / operating_revenue) * 100',
                'variables': [
                    {
                        'name': 'Operating Revenue',
                        'description': 'Revenue from core operations',
                        'source': 'Statement of Financial Performance',
                        'type': 'monetary'
                    },
                    {
                        'name': 'Operating Expenses',
                        'description': 'Expenses from core operations',
                        'source': 'Statement of Financial Performance',
                        'type': 'monetary'
                    }
                ],
                'grap_reference': 'Financial Analysis Ratios',
                'example': {
                    'operating_revenue': 500000,
                    'operating_expenses': 350000,
                    'operating_margin': 30.0
                }
            },
            'debt_to_equity': {
                'name': 'Debt to Equity Ratio',
                'description': 'Measure of financial leverage',
                'formula': 'Total Liabilities / Net Assets',
                'calculation': 'total_liabilities / net_assets',
                'variables': [
                    {
                        'name': 'Total Liabilities',
                        'description': 'All liability obligations',
                        'source': 'Statement of Financial Position',
                        'type': 'monetary'
                    },
                    {
                        'name': 'Net Assets',
                        'description': 'Total assets minus total liabilities',
                        'source': 'Statement of Financial Position',
                        'type': 'monetary'
                    }
                ],
                'grap_reference': 'Financial Analysis Ratios',
                'example': {
                    'total_liabilities': 200000,
                    'net_assets': 300000,
                    'debt_to_equity': 0.67
                }
            }
        }
    
    def _initialize_variable_mappings(self) -> Dict[str, Any]:
        """Initialize mapping of calculation variables to data sources"""
        return {
            'trial_balance': {
                'actual_amount': 'Net Balance',
                'account_description': 'Account Description',
                'account_code': 'Account Code'
            },
            'budget_data': {
                'budgeted_amount': 'Budget Amount',
                'category': 'Budget Category'
            },
            'asset_register': {
                'asset_cost': 'Purchase Price',
                'accumulated_depreciation': 'Accumulated Depreciation',
                'useful_life': 'Useful Life Years',
                'residual_value': 'Residual Value'
            },
            'financial_statements': {
                'current_assets': 'Current Assets Total',
                'current_liabilities': 'Current Liabilities Total',
                'total_liabilities': 'Total Liabilities',
                'net_assets': 'Net Assets Total',
                'operating_revenue': 'Operating Revenue',
                'operating_expenses': 'Operating Expenses'
            }
        }
    
    def get_calculation_details(self, calculation_type: str) -> Dict[str, Any]:
        """Get detailed formula information for a calculation type"""
        calculation_info = self.calculation_registry.get(calculation_type)
        
        if not calculation_info:
            return {
                'error': f'Calculation type "{calculation_type}" not found',
                'available_calculations': list(self.calculation_registry.keys())
            }
        
        return {
            'calculation_type': calculation_type,
            'calculation_details': calculation_info,
            'retrieved_at': datetime.now().isoformat(),
            'transparency_level': 'FULL'
        }
    
    def calculate_with_transparency(self, calculation_type: str, variables: Dict[str, float]) -> Dict[str, Any]:
        """Perform calculation with full transparency"""
        calculation_info = self.calculation_registry.get(calculation_type)
        
        if not calculation_info:
            return {
                'error': f'Calculation type "{calculation_type}" not found',
                'available_calculations': list(self.calculation_registry.keys())
            }
        
        try:
            # Extract variables needed for calculation
            formula = calculation_info['calculation']
            
            # Create safe evaluation context
            safe_context = {}
            for var in calculation_info['variables']:
                var_name = var['name'].lower().replace(' ', '_')
                if var_name in variables:
                    safe_context[var_name] = variables[var_name]
                else:
                    return {
                        'error': f'Missing variable: {var["name"]}',
                        'required_variables': [v['name'] for v in calculation_info['variables']]
                    }
            
            # Perform calculation (simplified - in production, use proper expression parser)
            result = eval(formula, {"__builtins__": {}}, safe_context)
            
            return {
                'calculation_type': calculation_type,
                'formula': calculation_info['formula'],
                'calculation': calculation_info['calculation'],
                'variables_used': variables,
                'result': result,
                'calculated_at': datetime.now().isoformat(),
                'transparency_disclosure': {
                    'method': calculation_info['description'],
                    'grap_reference': calculation_info['grap_reference'],
                    'variable_sources': [
                        {
                            'variable': var['name'],
                            'value': variables.get(var['name'].lower().replace(' ', '_')),
                            'source': var['source'],
                            'type': var['type']
                        }
                        for var in calculation_info['variables']
                    ]
                }
            }
            
        except Exception as e:
            return {
                'error': f'Calculation failed: {str(e)}',
                'calculation_type': calculation_type,
                'formula': calculation_info['formula'],
                'variables_attempted': variables
            }
    
    def get_all_calculations(self) -> Dict[str, Any]:
        """Get list of all available calculations"""
        return {
            'available_calculations': list(self.calculation_registry.keys()),
            'calculation_count': len(self.calculation_registry),
            'retrieved_at': datetime.now().isoformat(),
            'calculations': {
                calc_type: {
                    'name': info['name'],
                    'description': info['description'],
                    'formula': info['formula'],
                    'grap_reference': info['grap_reference']
                }
                for calc_type, info in self.calculation_registry.items()
            }
        }
    
    def export_calculation_documentation(self, calculation_types: List[str] = None) -> Dict[str, Any]:
        """Export complete calculation documentation"""
        if calculation_types is None:
            calculation_types = list(self.calculation_registry.keys())
        
        documentation = {
            'document_id': f"CALC_DOC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'document_type': 'Calculation Transparency Documentation',
            'grap_compliance': 'FULL',
            'calculations': []
        }
        
        for calc_type in calculation_types:
            if calc_type in self.calculation_registry:
                calc_info = self.calculation_registry[calc_type]
                documentation['calculations'].append({
                    'calculation_type': calc_type,
                    'name': calc_info['name'],
                    'description': calc_info['description'],
                    'formula': calc_info['formula'],
                    'calculation': calc_info['calculation'],
                    'variables': calc_info['variables'],
                    'grap_reference': calc_info['grap_reference'],
                    'example': calc_info['example']
                })
        
        return documentation
    
    def validate_calculation(self, calculation_type: str, variables: Dict[str, float]) -> Dict[str, Any]:
        """Validate calculation inputs before processing"""
        calculation_info = self.calculation_registry.get(calculation_type)
        
        if not calculation_info:
            return {
                'valid': False,
                'error': f'Calculation type "{calculation_type}" not found'
            }
        
        validation_result = {
            'calculation_type': calculation_type,
            'valid': True,
            'warnings': [],
            'errors': [],
            'missing_variables': [],
            'invalid_types': []
        }
        
        # Check required variables
        for var in calculation_info['variables']:
            var_name = var['name'].lower().replace(' ', '_')
            if var_name not in variables:
                validation_result['missing_variables'].append(var['name'])
                validation_result['valid'] = False
        
        # Validate variable types
        for var in calculation_info['variables']:
            var_name = var['name'].lower().replace(' ', '_')
            if var_name in variables:
                value = variables[var_name]
                var_type = var['type']
                
                if var_type == 'monetary' and not isinstance(value, (int, float)):
                    validation_result['invalid_types'].append({
                        'variable': var['name'],
                        'expected_type': 'numeric (monetary)',
                        'actual_type': type(value).__name__
                    })
                    validation_result['valid'] = False
                
                elif var_type == 'numeric' and not isinstance(value, (int, float)):
                    validation_result['invalid_types'].append({
                        'variable': var['name'],
                        'expected_type': 'numeric',
                        'actual_type': type(value).__name__
                    })
                    validation_result['valid'] = False
        
        # Add warnings for unusual values
        for var in calculation_info['variables']:
            var_name = var['name'].lower().replace(' ', '_')
            if var_name in variables:
                value = variables[var_name]
                if var['type'] == 'monetary' and value < 0:
                    validation_result['warnings'].append({
                        'variable': var['name'],
                        'warning': 'Negative monetary value detected'
                    })
                elif var['type'] == 'numeric' and value <= 0:
                    validation_result['warnings'].append({
                        'variable': var['name'],
                        'warning': 'Non-positive numeric value detected'
                    })
        
        return validation_result
