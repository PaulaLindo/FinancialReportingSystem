"""
SADPMR Financial Reporting System - Processing State Models
Tracks Balance Sheet processing phases and formula visibility states
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import os

class ProcessingStateModel:
    """Manages Balance Sheet processing states and formula visibility"""
    
    def __init__(self):
        self.processing_db_file = 'data/processing_states.json'
        self.ensure_processing_db_exists()
        
    def ensure_processing_db_exists(self):
        """Initialize processing database if it doesn't exist"""
        os.makedirs(os.path.dirname(self.processing_db_file), exist_ok=True)
        if not os.path.exists(self.processing_db_file):
            self._initialize_empty_db()
    
    def _initialize_empty_db(self):
        """Create empty processing database"""
        empty_db = {
            'processing_states': {},
            'period_status': {},
            'formula_visibility': {}
        }
        with open(self.processing_db_file, 'w') as f:
            json.dump(empty_db, f, indent=2)
    
    def _load_processing_data(self):
        """Load processing data from file"""
        try:
            with open(self.processing_db_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._initialize_empty_db()
            return self._load_processing_data()
    
    def _save_processing_data(self, data):
        """Save processing data to file"""
        with open(self.processing_db_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_processing_state(self, balance_sheet_id: str, period: str, 
                              uploaded_by: str) -> Dict[str, Any]:
        """Create new processing state for uploaded Balance Sheet"""
        processing_state = {
            'balance_sheet_id': balance_sheet_id,
            'period': period,
            'status': 'uploaded',  # uploaded -> mapping -> processing -> review -> finalized
            'uploaded_by': uploaded_by,
            'uploaded_at': datetime.now().isoformat(),
            'mapping_started_at': None,
            'mapping_completed_at': None,
            'processing_started_at': None,
            'processing_completed_at': None,
            'review_started_at': None,
            'finalized_at': None,
            'finalized_by': None,
            'current_reviewer': None,
            'formula_visibility': 'restricted',  # restricted -> draft -> review -> audit
            'mapped_accounts': [],
            'grap_validations': [],
            'formula_breakdowns': {}
        }
        
        # Save to database
        data = self._load_processing_data()
        data['processing_states'][balance_sheet_id] = processing_state
        self._save_processing_data(data)
        
        return processing_state
    
    def update_processing_status(self, balance_sheet_id: str, new_status: str, 
                                user_id: str = None) -> bool:
        """Update processing status and timestamps"""
        data = self._load_processing_data()
        
        if balance_sheet_id not in data['processing_states']:
            return False
        
        state = data['processing_states'][balance_sheet_id]
        old_status = state['status']
        state['status'] = new_status
        
        # Update relevant timestamps
        now = datetime.now().isoformat()
        
        if new_status == 'mapping' and old_status != 'mapping':
            state['mapping_started_at'] = now
            state['formula_visibility'] = 'draft'  # Enable draft formula visibility
        
        elif new_status == 'processing' and old_status != 'processing':
            state['mapping_completed_at'] = now
            state['processing_started_at'] = now
            state['formula_visibility'] = 'review'  # Enable review formula visibility
        
        elif new_status == 'review' and old_status != 'review':
            state['processing_completed_at'] = now
            state['review_started_at'] = now
            state['current_reviewer'] = user_id
            state['formula_visibility'] = 'review'  # Maintain review visibility
        
        elif new_status == 'finalized' and old_status != 'finalized':
            state['finalized_at'] = now
            state['finalized_by'] = user_id
            state['formula_visibility'] = 'audit'  # Switch to audit-only visibility
        
        self._save_processing_data(data)
        return True
    
    def get_processing_state(self, balance_sheet_id: str) -> Optional[Dict[str, Any]]:
        """Get current processing state for Balance Sheet"""
        data = self._load_processing_data()
        return data['processing_states'].get(balance_sheet_id)
    
    def can_view_formulas(self, balance_sheet_id: str, user_role: str, 
                         user_id: str = None) -> Dict[str, Any]:
        """Check if user can view formulas based on processing state and role"""
        state = self.get_processing_state(balance_sheet_id)
        if not state:
            return {'can_view': False, 'reason': 'Balance Sheet not found'}
        
        formula_visibility = state['formula_visibility']
        status = state['status']
        
        # Finance Clerk - never sees formulas
        if user_role == 'FINANCE_CLERK':
            return {'can_view': False, 'reason': 'Finance Clerk does not have formula access'}
        
        # System Admin - never sees formulas
        if user_role == 'SYSTEM_ADMIN':
            return {'can_view': False, 'reason': 'System Admin does not have financial access'}
        
        # Asset Manager - limited access based on processing state
        if user_role == 'ASSET_MANAGER':
            if formula_visibility in ['review', 'audit']:
                return {'can_view': True, 'mode': 'limited', 'reason': 'Asset Manager - Limited access'}
            else:
                return {'can_view': False, 'reason': 'Asset Manager access not available in current phase'}
        
        # Finance Manager - access during review phase
        if user_role == 'FINANCE_MANAGER':
            if formula_visibility in ['draft', 'review', 'audit']:
                if status == 'review' and state.get('current_reviewer') == user_id:
                    return {'can_view': True, 'mode': 'full', 'reason': 'Finance Manager - Active reviewer'}
                elif formula_visibility in ['review', 'audit']:
                    return {'can_view': True, 'mode': 'full', 'reason': 'Finance Manager - Review access'}
                else:
                    return {'can_view': True, 'mode': 'draft', 'reason': 'Finance Manager - Draft access'}
            else:
                return {'can_view': False, 'reason': 'Finance Manager access not available in current phase'}
        
        # CFO - full access during and after processing
        if user_role == 'CFO':
            if formula_visibility in ['draft', 'review', 'audit']:
                return {'can_view': True, 'mode': 'full', 'reason': 'CFO - Full access'}
            else:
                return {'can_view': False, 'reason': 'CFO access not available until mapping phase'}
        
        # Auditor - read-only access after processing
        if user_role == 'AUDITOR':
            if formula_visibility == 'audit':
                return {'can_view': True, 'mode': 'readonly', 'reason': 'Auditor - Read-only audit access'}
            else:
                return {'can_view': False, 'reason': 'Auditor access not available until finalization'}
        
        return {'can_view': False, 'reason': 'Role not recognized for formula access'}
    
    def add_mapped_account(self, balance_sheet_id: str, tb_account: str, 
                          grap_line_item: str, mapped_by: str) -> bool:
        """Add mapped account to processing state"""
        data = self._load_processing_data()
        
        if balance_sheet_id not in data['processing_states']:
            return False
        
        mapping = {
            'tb_account': tb_account,
            'grap_line_item': grap_line_item,
            'mapped_by': mapped_by,
            'mapped_at': datetime.now().isoformat()
        }
        
        data['processing_states'][balance_sheet_id]['mapped_accounts'].append(mapping)
        self._save_processing_data(data)
        return True
    
    def add_grap_validation(self, balance_sheet_id: str, validation_result: Dict[str, Any]) -> bool:
        """Add GRAP validation result"""
        data = self._load_processing_data()
        
        if balance_sheet_id not in data['processing_states']:
            return False
        
        validation = {
            'validation_id': f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'grap_standard': validation_result.get('grap_standard'),
            'line_item': validation_result.get('line_item'),
            'status': validation_result.get('status'),  # pass/fail/warning
            'details': validation_result.get('details'),
            'validated_at': datetime.now().isoformat(),
            'validated_by': validation_result.get('validated_by')
        }
        
        data['processing_states'][balance_sheet_id]['grap_validations'].append(validation)
        self._save_processing_data(data)
        return True
    
    def get_period_status(self, period: str) -> Optional[Dict[str, Any]]:
        """Get overall status for a reporting period"""
        data = self._load_processing_data()
        
        if period not in data['period_status']:
            # Initialize period status
            data['period_status'][period] = {
                'period': period,
                'status': 'open',  # open -> closed -> locked
                'opened_at': datetime.now().isoformat(),
                'closed_at': None,
                'locked_at': None,
                'finalized_balance_sheets': [],
                'audit_access_granted': False
            }
            self._save_processing_data(data)
        
        return data['period_status'][period]
    
    def close_period(self, period: str, closed_by: str) -> bool:
        """Close a reporting period"""
        data = self._load_processing_data()
        
        if period not in data['period_status']:
            return False
        
        data['period_status'][period]['status'] = 'closed'
        data['period_status'][period]['closed_at'] = datetime.now().isoformat()
        data['period_status'][period]['closed_by'] = closed_by
        
        self._save_processing_data(data)
        return True
    
    def lock_period(self, period: str, locked_by: str) -> bool:
        """Lock a reporting period (final)"""
        data = self._load_processing_data()
        
        if period not in data['period_status']:
            return False
        
        data['period_status'][period]['status'] = 'locked'
        data['period_status'][period]['locked_at'] = datetime.now().isoformat()
        data['period_status'][period]['locked_by'] = locked_by
        data['period_status'][period]['audit_access_granted'] = True
        
        # Set all balance sheets in this period to audit mode
        for tb_id, state in data['processing_states'].items():
            if state.get('period') == period:
                state['formula_visibility'] = 'audit'
                state['status'] = 'finalized'
        
        self._save_processing_data(data)
        return True
    
    def get_balance_sheets_by_period(self, period: str) -> List[Dict[str, Any]]:
        """Get all balance sheets for a specific period"""
        data = self._load_processing_data()
        
        balance_sheets = []
        for tb_id, state in data['processing_states'].items():
            if state.get('period') == period:
                state['balance_sheet_id'] = tb_id
                balance_sheets.append(state)
        
        return balance_sheets

# Initialize processing state model
processing_state = ProcessingStateModel()
