"""
SADPMR Financial Reporting System - Asset Lifecycle Service
Service for GRAP 17 compliant asset management and depreciation
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
from models.asset_lifecycle_models import AssetLifecycleModel

class AssetLifecycleService:
    """Service for asset lifecycle management and GRAP 17 compliance"""
    
    def __init__(self):
        self.asset_model = AssetLifecycleModel()
        
    def register_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new asset in the asset sub-ledger"""
        try:
            result = self.asset_model.register_asset(asset_data)
            return result
        except Exception as e:
            return {
                'success': False,
                'error': f'Asset registration failed: {str(e)}'
            }
    
    def review_useful_life(self, asset_id: str, new_useful_life: int, 
                          reason: str, user_id: str, effective_date: date = None) -> Dict[str, Any]:
        """Review and update useful life of an asset"""
        try:
            result = self.asset_model.review_useful_life(
                asset_id, new_useful_life, reason, user_id, effective_date
            )
            return result
        except Exception as e:
            return {
                'success': False,
                'error': f'Useful life review failed: {str(e)}'
            }
    
    def get_asset_details(self, asset_id: str) -> Dict[str, Any]:
        """Get complete asset details including depreciation information"""
        try:
            result = self.asset_model.get_asset_details(asset_id)
            return {
                'success': True,
                'asset_details': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get asset details: {str(e)}'
            }
    
    def get_depreciation_history(self, asset_id: str = None) -> Dict[str, Any]:
        """Get depreciation history for assets"""
        try:
            result = self.asset_model.get_depreciation_history(asset_id)
            return {
                'success': True,
                'depreciation_history': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get depreciation history: {str(e)}'
            }
    
    def process_annual_depreciation(self, fiscal_year: int) -> Dict[str, Any]:
        """Process annual depreciation for all assets"""
        try:
            result = self.asset_model.process_annual_depreciation(fiscal_year)
            return {
                'success': True,
                'depreciation_results': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Annual depreciation processing failed: {str(e)}'
            }
    
    def generate_asset_register_report(self) -> Dict[str, Any]:
        """Generate comprehensive asset register report"""
        try:
            report = self.asset_model.generate_asset_register_report()
            return {
                'success': True,
                'asset_register_report': report
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Asset register report generation failed: {str(e)}'
            }
    
    def get_asset_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all assets"""
        try:
            summary = self.asset_model._calculate_asset_summary()
            return {
                'success': True,
                'asset_summary': summary
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get asset summary: {str(e)}'
            }
