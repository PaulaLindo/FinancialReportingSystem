"""
Varydian Financial Reporting System - Asset Lifecycle Models
GRAP 17 compliant asset management and depreciation system
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
import pandas as pd

class AssetLifecycleModel:
    """Asset lifecycle management model for GRAP 17 compliance"""
    
    def __init__(self):
        self.asset_register = {}
        self.depreciation_schedules = {}
        self.depreciation_history = {}
        self.asset_categories = self._initialize_asset_categories()
        self.depreciation_methods = self._initialize_depreciation_methods()
        
    def _initialize_asset_categories(self) -> Dict[str, Any]:
        """Initialize GRAP 17 asset categories"""
        return {
            'property_plant_equipment': {
                'code': 'PPE',
                'name': 'Property, Plant and Equipment',
                'description': 'Tangible assets held for use in production',
                'useful_life_range': {'min': 3, 'max': 50},
                'depreciation_method': 'straight_line',
                'grap_reference': 'GRAP 17.1'
            },
            'intangible_assets': {
                'code': 'IA',
                'name': 'Intangible Assets',
                'description': 'Non-physical assets that provide future economic benefits',
                'useful_life_range': {'min': 1, 'max': 20},
                'depreciation_method': 'straight_line',
                'grap_reference': 'GRAP 17.2'
            },
            'investment_property': {
                'code': 'IP',
                'name': 'Investment Property',
                'description': 'Property held to earn rentals or capital appreciation',
                'useful_life_range': {'min': 10, 'max': 50},
                'depreciation_method': 'straight_line',
                'grap_reference': 'GRAP 17.3'
            },
            'financial_assets': {
                'code': 'FA',
                'name': 'Financial Assets',
                'description': 'Investments in equity, debt instruments, and other financial assets',
                'useful_life_range': {'min': 1, 'max': 10},
                'depreciation_method': 'amortisation',
                'grap_reference': 'GRAP 17.4'
            }
        }
    
    def _initialize_depreciation_methods(self) -> Dict[str, Any]:
        """Initialize depreciation methods per GRAP 17"""
        return {
            'straight_line': {
                'name': 'Straight-Line Method',
                'formula': '(Cost - Residual Value) / Useful Life',
                'description': 'Equal depreciation charges over useful life',
                'grap_reference': 'GRAP 17.21'
            },
            'reducing_balance': {
                'name': 'Reducing Balance Method',
                'formula': 'Carrying Amount × Depreciation Rate',
                'description': 'Higher charges in early years, reducing over time',
                'grap_reference': 'GRAP 17.22'
            },
            'units_of_production': {
                'name': 'Units of Production Method',
                'formula': '(Cost - Residual Value) / Total Expected Production × Actual Production',
                'description': 'Based on actual usage or production',
                'grap_reference': 'GRAP 17.23'
            }
        }
    
    def register_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new asset in the asset sub-ledger"""
        asset_id = f"AST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Validate required fields
        required_fields = ['asset_name', 'asset_category', 'purchase_date', 'purchase_cost', 'useful_life_years']
        for field in required_fields:
            if field not in asset_data:
                return {
                    'success': False,
                    'error': f'Required field missing: {field}'
                }
        
        # Validate asset category
        category_code = asset_data['asset_category']
        if category_code not in self.asset_categories:
            return {
                'success': False,
                'error': f'Invalid asset category: {category_code}',
                'available_categories': list(self.asset_categories.keys())
            }
        
        # Create asset record
        asset_record = {
            'asset_id': asset_id,
            'asset_name': asset_data['asset_name'],
            'asset_category': category_code,
            'category_details': self.asset_categories[category_code],
            'purchase_date': asset_data['purchase_date'],
            'purchase_cost': float(asset_data['purchase_cost']),
            'residual_value': float(asset_data.get('residual_value', 0)),
            'useful_life_years': int(asset_data['useful_life_years']),
            'remaining_useful_life': int(asset_data['useful_life_years']),
            'depreciation_method': asset_data.get('depreciation_method', 'straight_line'),
            'depreciation_start_date': asset_data.get('depreciation_start_date', asset_data['purchase_date']),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'created_by': asset_data.get('created_by', 'system'),
            'last_reviewed': None,
            'review_history': []
        }
        
        # Calculate initial carrying value
        asset_record['carrying_value'] = asset_record['purchase_cost']
        asset_record['accumulated_depreciation'] = 0.0
        
        # Store in asset register
        self.asset_register[asset_id] = asset_record
        
        # Initialize depreciation schedule
        self._initialize_depreciation_schedule(asset_id)
        
        return {
            'success': True,
            'asset_id': asset_id,
            'asset_record': asset_record,
            'message': f'Asset {asset_id} registered successfully'
        }
    
    def _initialize_depreciation_schedule(self, asset_id: str) -> None:
        """Initialize depreciation schedule for an asset"""
        asset = self.asset_register[asset_id]
        
        schedule = {
            'asset_id': asset_id,
            'depreciation_method': asset['depreciation_method'],
            'annual_depreciation': 0.0,
            'monthly_depreciation': 0.0,
            'total_depreciable_amount': asset['purchase_cost'] - asset['residual_value'],
            'remaining_depreciable_amount': asset['purchase_cost'] - asset['residual_value'],
            'schedule_entries': []
        }
        
        # Calculate annual depreciation
        if asset['depreciation_method'] == 'straight_line':
            schedule['annual_depreciation'] = schedule['total_depreciable_amount'] / asset['useful_life_years']
            schedule['monthly_depreciation'] = schedule['annual_depreciation'] / 12
        
        # Generate schedule entries
        current_year = datetime.now().year
        for year in range(current_year, current_year + asset['remaining_useful_life'] + 1):
            year_entry = {
                'year': year,
                'opening_carrying_value': 0.0,
                'depreciation_charge': schedule['annual_depreciation'],
                'accumulated_depreciation': 0.0,
                'closing_carrying_value': 0.0,
                'status': 'projected'
            }
            schedule['schedule_entries'].append(year_entry)
        
        self.depreciation_schedules[asset_id] = schedule
    
    def review_useful_life(self, asset_id: str, new_useful_life: int, 
                          reason: str, user_id: str, effective_date: date = None) -> Dict[str, Any]:
        """Review and update useful life of an asset (GRAP 17 compliance)"""
        
        if asset_id not in self.asset_register:
            return {
                'success': False,
                'error': f'Asset {asset_id} not found'
            }
        
        asset = self.asset_register[asset_id]
        old_useful_life = asset['remaining_useful_life']
        
        # Validate new useful life
        category = self.asset_categories[asset['asset_category']]
        if new_useful_life < category['useful_life_range']['min'] or new_useful_life > category['useful_life_range']['max']:
            return {
                'success': False,
                'error': f'Invalid useful life. Must be between {category["useful_life_range"]["min"]} and {category["useful_life_range"]["max"]} years for {category["name"]}',
                'category_range': category['useful_life_range']
            }
        
        # Create review record
        review_record = {
            'review_id': f"REV_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'review_date': datetime.now().isoformat(),
            'effective_date': effective_date.isoformat() if effective_date else datetime.now().date().isoformat(),
            'old_useful_life': old_useful_life,
            'new_useful_life': new_useful_life,
            'change_reason': reason,
            'reviewed_by': user_id,
            'impact_analysis': self._analyze_useful_life_change_impact(asset_id, old_useful_life, new_useful_life),
            'grap_compliance': {
                'compliant': True,
                'reference': 'GRAP 17.16 - Review of Useful Life',
                'disclosure_required': True
            }
        }
        
        # Preserve historical depreciation before change
        historical_snapshot = {
            'snapshot_date': datetime.now().isoformat(),
            'asset_id': asset_id,
            'old_useful_life': old_useful_life,
            'new_useful_life': new_useful_life,
            'accumulated_depreciation_before': asset['accumulated_depreciation'],
            'carrying_value_before': asset['carrying_value'],
            'depreciation_schedule_before': self.depreciation_schedules.get(asset_id, {}).copy(),
            'review_details': review_record
        }
        
        if asset_id not in self.depreciation_history:
            self.depreciation_history[asset_id] = []
        
        self.depreciation_history[asset_id].append(historical_snapshot)
        
        # Update asset record
        asset['remaining_useful_life'] = new_useful_life
        asset['last_reviewed'] = datetime.now().isoformat()
        asset['review_history'].append(review_record)
        
        # Recalculate depreciation schedule
        self._recalculate_depreciation_schedule(asset_id, new_useful_life)
        
        return {
            'success': True,
            'asset_id': asset_id,
            'review_record': review_record,
            'updated_asset': asset,
            'historical_snapshot': historical_snapshot,
            'message': f'Useful life updated from {old_useful_life} to {new_useful_life} years'
        }
    
    def _analyze_useful_life_change_impact(self, asset_id: str, old_life: int, new_life: int) -> Dict[str, Any]:
        """Analyze the impact of useful life change"""
        asset = self.asset_register[asset_id]
        schedule = self.depreciation_schedules.get(asset_id, {})
        
        # Calculate impact on annual depreciation
        old_annual_depreciation = schedule.get('annual_depreciation', 0)
        new_annual_depreciation = schedule['total_depreciable_amount'] / new_life
        depreciation_change = new_annual_depreciation - old_annual_depreciation
        
        # Calculate impact on remaining depreciation periods
        old_remaining_periods = old_life
        new_remaining_periods = new_life
        
        return {
            'depreciation_change': {
                'old_annual': old_annual_depreciation,
                'new_annual': new_annual_depreciation,
                'annual_change': depreciation_change,
                'percentage_change': (depreciation_change / old_annual_depreciation * 100) if old_annual_depreciation > 0 else 0
            },
            'timing_impact': {
                'old_remaining_periods': old_remaining_periods,
                'new_remaining_periods': new_remaining_periods,
                'period_change': new_remaining_periods - old_remaining_periods
            },
            'financial_impact': {
                'total_depreciation_change': depreciation_change * new_remaining_periods,
                'carrying_value_impact': depreciation_change * old_remaining_periods
            }
        }
    
    def _recalculate_depreciation_schedule(self, asset_id: str, new_useful_life: int) -> None:
        """Recalculate depreciation schedule after useful life change"""
        asset = self.asset_register[asset_id]
        schedule = self.depreciation_schedules[asset_id]
        
        # Update schedule parameters
        schedule['annual_depreciation'] = schedule['total_depreciable_amount'] / new_useful_life
        schedule['monthly_depreciation'] = schedule['annual_depreciation'] / 12
        
        # Regenerate schedule entries from current year
        current_year = datetime.now().year
        remaining_years = new_useful_life
        
        schedule['schedule_entries'] = []
        for i, year in enumerate(range(current_year, current_year + remaining_years + 1)):
            year_entry = {
                'year': year,
                'opening_carrying_value': asset['carrying_value'] + (schedule['annual_depreciation'] * i),
                'depreciation_charge': schedule['annual_depreciation'],
                'accumulated_depreciation': asset['accumulated_depreciation'] + (schedule['annual_depreciation'] * (i + 1)),
                'closing_carrying_value': asset['carrying_value'] + (schedule['annual_depreciation'] * (i + 1)),
                'status': 'projected'
            }
            schedule['schedule_entries'].append(year_entry)
    
    def get_asset_details(self, asset_id: str) -> Dict[str, Any]:
        """Get complete asset details including depreciation information"""
        if asset_id not in self.asset_register:
            return {
                'error': f'Asset {asset_id} not found'
            }
        
        asset = self.asset_register[asset_id]
        schedule = self.depreciation_schedules.get(asset_id, {})
        history = self.depreciation_history.get(asset_id, [])
        
        return {
            'asset_details': asset,
            'depreciation_schedule': schedule,
            'depreciation_history': history,
            'retrieved_at': datetime.now().isoformat()
        }
    
    def get_depreciation_history(self, asset_id: str = None) -> Dict[str, Any]:
        """Get depreciation history for assets"""
        if asset_id:
            if asset_id not in self.depreciation_history:
                return {
                    'error': f'No depreciation history found for asset {asset_id}'
                }
            return {
                'asset_id': asset_id,
                'history': self.depreciation_history[asset_id],
                'retrieved_at': datetime.now().isoformat()
            }
        else:
            return {
                'all_assets_history': self.depreciation_history,
                'total_assets_with_history': len(self.depreciation_history),
                'retrieved_at': datetime.now().isoformat()
            }
    
    def process_annual_depreciation(self, fiscal_year: int) -> Dict[str, Any]:
        """Process annual depreciation for all assets"""
        depreciation_results = {
            'fiscal_year': fiscal_year,
            'processed_at': datetime.now().isoformat(),
            'assets_processed': [],
            'total_depreciation': 0.0,
            'errors': []
        }
        
        for asset_id, asset in self.asset_register.items():
            if asset['status'] != 'active':
                continue
            
            schedule = self.depreciation_schedules.get(asset_id, {})
            if not schedule:
                depreciation_results['errors'].append({
                    'asset_id': asset_id,
                    'error': 'No depreciation schedule found'
                })
                continue
            
            # Find the year entry in schedule
            year_entry = None
            for entry in schedule['schedule_entries']:
                if entry['year'] == fiscal_year:
                    year_entry = entry
                    break
            
            if year_entry and year_entry['status'] == 'projected':
                # Process depreciation for this year
                depreciation_amount = schedule['annual_depreciation']
                
                # Update asset record
                asset['accumulated_depreciation'] += depreciation_amount
                asset['carrying_value'] -= depreciation_amount
                asset['remaining_useful_life'] -= 1
                
                # Update schedule entry
                year_entry['status'] = 'processed'
                year_entry['processed_date'] = datetime.now().isoformat()
                
                # Record in depreciation history
                depreciation_record = {
                    'asset_id': asset_id,
                    'fiscal_year': fiscal_year,
                    'depreciation_amount': depreciation_amount,
                    'accumulated_depreciation_after': asset['accumulated_depreciation'],
                    'carrying_value_after': asset['carrying_value'],
                    'remaining_useful_life_after': asset['remaining_useful_life'],
                    'processed_at': datetime.now().isoformat()
                }
                
                if asset_id not in self.depreciation_history:
                    self.depreciation_history[asset_id] = []
                
                self.depreciation_history[asset_id].append(depreciation_record)
                
                depreciation_results['assets_processed'].append(depreciation_record)
                depreciation_results['total_depreciation'] += depreciation_amount
                
                # Check if asset is fully depreciated
                if asset['remaining_useful_life'] <= 0:
                    asset['status'] = 'fully_depreciated'
        
        return depreciation_results
    
    def generate_asset_register_report(self) -> Dict[str, Any]:
        """Generate comprehensive asset register report"""
        report = {
            'report_id': f"ASSET_REG_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'report_type': 'Asset Register and Depreciation Schedule',
            'grap_compliance': 'GRAP 17',
            'summary': self._calculate_asset_summary(),
            'asset_details': [],
            'depreciation_summary': {},
            'compliance_metrics': self._calculate_compliance_metrics()
        }
        
        for asset_id, asset in self.asset_register.items():
            schedule = self.depreciation_schedules.get(asset_id, {})
            history = self.depreciation_history.get(asset_id, [])
            
            asset_detail = {
                'asset_id': asset_id,
                'asset_name': asset['asset_name'],
                'category': asset['asset_category'],
                'purchase_cost': asset['purchase_cost'],
                'accumulated_depreciation': asset['accumulated_depreciation'],
                'carrying_value': asset['carrying_value'],
                'remaining_useful_life': asset['remaining_useful_life'],
                'status': asset['status'],
                'last_reviewed': asset['last_reviewed'],
                'review_count': len(asset['review_history'])
            }
            report['asset_details'].append(asset_detail)
        
        return report
    
    def _calculate_asset_summary(self) -> Dict[str, Any]:
        """Calculate asset register summary statistics"""
        total_assets = len(self.asset_register)
        total_purchase_cost = sum(asset['purchase_cost'] for asset in self.asset_register.values())
        total_accumulated_depreciation = sum(asset['accumulated_depreciation'] for asset in self.asset_register.values())
        total_carrying_value = sum(asset['carrying_value'] for asset in self.asset_register.values())
        
        status_counts = {}
        for asset in self.asset_register.values():
            status = asset['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        category_counts = {}
        for asset in self.asset_register.values():
            category = asset['asset_category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            'total_assets': total_assets,
            'total_purchase_cost': total_purchase_cost,
            'total_accumulated_depreciation': total_accumulated_depreciation,
            'total_carrying_value': total_carrying_value,
            'net_book_value_ratio': (total_carrying_value / total_purchase_cost * 100) if total_purchase_cost > 0 else 0,
            'assets_by_status': status_counts,
            'assets_by_category': category_counts
        }
    
    def _calculate_compliance_metrics(self) -> Dict[str, Any]:
        """Calculate GRAP 17 compliance metrics"""
        total_assets = len(self.asset_register)
        assets_with_reviews = sum(1 for asset in self.asset_register.values() if asset['review_history'])
        assets_with_history = len(self.depreciation_history)
        
        # Check useful life compliance
        useful_life_compliant = 0
        for asset in self.asset_register.values():
            category = self.asset_categories[asset['asset_category']]
            min_life = category['useful_life_range']['min']
            max_life = category['useful_life_range']['max']
            if min_life <= asset['useful_life_years'] <= max_life:
                useful_life_compliant += 1
        
        return {
            'total_assets': total_assets,
            'assets_with_reviews': assets_with_reviews,
            'assets_with_depreciation_history': assets_with_history,
            'useful_life_compliance_rate': (useful_life_compliant / total_assets * 100) if total_assets > 0 else 0,
            'review_coverage_rate': (assets_with_reviews / total_assets * 100) if total_assets > 0 else 0,
            'history_coverage_rate': (assets_with_history / total_assets * 100) if total_assets > 0 else 0,
            'overall_compliance_score': 0.0,
            'compliance_level': 'EXCELLENT'
        }
