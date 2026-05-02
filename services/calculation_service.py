"""
SADPMR Financial Reporting System - Calculation Transparency Service
Service for providing formula transparency and calculation disclosure
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from models.calculation_models import CalculationTransparencyModel

class CalculationService:
    """Service for calculation transparency and formula disclosure"""
    
    def __init__(self):
        self.calculation_model = CalculationTransparencyModel()
        
    def get_calculation_details(self, calculation_type: str) -> Dict[str, Any]:
        """Get detailed formula information for a calculation type"""
        try:
            return self.calculation_model.get_calculation_details(calculation_type)
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get calculation details: {str(e)}'
            }
    
    def calculate_with_transparency(self, calculation_type: str, variables: Dict[str, float]) -> Dict[str, Any]:
        """Perform calculation with full transparency disclosure"""
        try:
            # Validate inputs first
            validation_result = self.calculation_model.validate_calculation(calculation_type, variables)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': 'Validation failed',
                    'validation_details': validation_result
                }
            
            # Perform calculation
            result = self.calculation_model.calculate_with_transparency(calculation_type, variables)
            result['success'] = True
            
            return result
        except Exception as e:
            return {
                'success': False,
                'error': f'Calculation failed: {str(e)}'
            }
    
    def get_all_calculations(self) -> Dict[str, Any]:
        """Get list of all available calculations"""
        try:
            return {
                'success': True,
                'calculations': self.calculation_model.get_all_calculations()
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get calculations: {str(e)}'
            }
    
    def export_calculation_documentation(self, calculation_types: List[str] = None) -> Dict[str, Any]:
        """Export complete calculation documentation"""
        try:
            documentation = self.calculation_model.export_calculation_documentation(calculation_types)
            return {
                'success': True,
                'documentation': documentation
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to export documentation: {str(e)}'
            }
    
    def validate_calculation_inputs(self, calculation_type: str, variables: Dict[str, float]) -> Dict[str, Any]:
        """Validate calculation inputs before processing"""
        try:
            validation_result = self.calculation_model.validate_calculation(calculation_type, variables)
            validation_result['success'] = True
            return validation_result
        except Exception as e:
            return {
                'success': False,
                'error': f'Validation failed: {str(e)}'
            }
