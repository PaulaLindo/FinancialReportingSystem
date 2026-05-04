"""
Varydian Financial Reporting System - Four-Eyes Approval Workflow Models
Transaction approval system implementing Segregation of Duties
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import os

class TransactionApprovalModel:
    """Four-Eyes approval workflow for financial transactions"""
    
    def __init__(self):
        self.approval_db_file = 'data/approvals.json'
        self.ensure_approval_db_exists()
        
    def ensure_approval_db_exists(self):
        """Initialize approval database if it doesn't exist"""
        os.makedirs(os.path.dirname(self.approval_db_file), exist_ok=True)
        if not os.path.exists(self.approval_db_file):
            self._initialize_empty_db()
    
    def _initialize_empty_db(self):
        """Create empty approval database"""
        empty_db = {
            'pending_transactions': [],
            'approved_transactions': [],
            'rejected_transactions': [],
            'finalized_transactions': []
        }
        with open(self.approval_db_file, 'w') as f:
            json.dump(empty_db, f, indent=2)
    
    def _load_approval_data(self):
        """Load approval data from file"""
        try:
            with open(self.approval_db_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._initialize_empty_db()
            return self._load_approval_data()
    
    def _save_approval_data(self, data):
        """Save approval data to file"""
        with open(self.approval_db_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_pending_transaction(self, creator_id: str, transaction_type: str, 
                                transaction_data: Dict, reason: str = '') -> Dict[str, Any]:
        """Create a transaction requiring approval"""
        transaction = {
            'transaction_id': f"TX_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'transaction_type': transaction_type,  # 'journal_entry', 'asset_impairment', 'budget_adjustment'
            'creator_id': creator_id,
            'creator_name': self._get_user_name(creator_id),
            'transaction_data': transaction_data,
            'reason': reason,
            'status': 'pending_approval',
            'created_at': datetime.now().isoformat(),
            'required_approvals': self._get_required_approvals(transaction_type),
            'current_approvals': [],
            'rejections': [],
            'finalized_at': None,
            'finalized_by': None
        }
        
        # Save to pending transactions
        data = self._load_approval_data()
        data['pending_transactions'].append(transaction)
        self._save_approval_data(data)
        
        return transaction
    
    def _get_required_approvals(self, transaction_type: str) -> List[str]:
        """Get required approval roles based on transaction type"""
        approval_matrix = {
            'journal_entry': ['FINANCE_MANAGER', 'CFO'],
            'asset_impairment': ['ASSET_MANAGER', 'FINANCE_MANAGER', 'CFO'],
            'budget_adjustment': ['FINANCE_MANAGER', 'CFO'],
            'financial_statement': ['CFO'],  # Only CFO needs to approve final statements
            'asset_disposal': ['ASSET_MANAGER', 'FINANCE_MANAGER', 'CFO']
        }
        return approval_matrix.get(transaction_type, ['FINANCE_MANAGER', 'CFO'])
    
    def _map_legacy_role(self, role: str) -> str:
        """Map legacy roles to new roles for demo compatibility"""
        legacy_mapping = {
            'ACCOUNTANT': 'FINANCE_MANAGER',  # Accountant acts as Finance Manager
            'CLERK': 'FINANCE_CLERK',  # Clerk acts as Finance Clerk
            'AUDITOR': 'AUDITOR',  # Auditor stays the same
            'CFO': 'CFO',  # CFO stays the same
        }
        return legacy_mapping.get(role, role)
    
    def _get_user_name(self, user_id: str) -> str:
        """Get user name from ID"""
        try:
            from models.supabase_auth_models import supabase_auth
            user_data = supabase_auth.get_user_by_id(user_id)
            return user_data['full_name'] if user_data else f"User {user_id}"
        except:
            return f"User {user_id}"
    
    def approve_submission(self, submission_id: str, approver_id: str, approver_role: str, approval_notes: str = '') -> bool:
        """Approve a submission"""
        try:
            data = self._load_approval_data()
            
            # Create approval record
            approval_record = {
                'submission_id': submission_id,
                'approver_id': approver_id,
                'approver_role': approver_role,
                'approved_at': datetime.now().isoformat(),
                'approval_notes': approval_notes,
                'status': 'approved'
            }
            
            # Add to approved transactions
            data['approved_transactions'].append(approval_record)
            
            # Remove from pending if exists
            data['pending_transactions'] = [tx for tx in data['pending_transactions'] if tx.get('submission_id') != submission_id]
            
            self._save_approval_data(data)
            return True
            
        except Exception as e:
            print(f"Error approving submission: {str(e)}")
            return False
    
    def reject_submission(self, submission_id: str, rejecter_id: str, rejecter_role: str, rejection_reason: str) -> bool:
        """Reject a submission"""
        try:
            data = self._load_approval_data()
            
            # Create rejection record
            rejection_record = {
                'submission_id': submission_id,
                'rejecter_id': rejecter_id,
                'rejecter_role': rejecter_role,
                'rejected_at': datetime.now().isoformat(),
                'rejection_reason': rejection_reason,
                'status': 'rejected'
            }
            
            # Add to rejected transactions
            data['rejected_transactions'].append(rejection_record)
            
            # Remove from pending if exists
            data['pending_transactions'] = [tx for tx in data['pending_transactions'] if tx.get('submission_id') != submission_id]
            
            self._save_approval_data(data)
            return True
            
        except Exception as e:
            print(f"Error rejecting submission: {str(e)}")
            return False

    def approve_transaction(self, approver_id: str, transaction_id: str, 
                          approval_reason: str) -> Dict[str, Any]:
        """Add approval to transaction"""
        data = self._load_approval_data()
        
        # Find transaction in pending
        transaction = None
        for tx in data['pending_transactions']:
            if tx['transaction_id'] == transaction_id:
                transaction = tx
                break
        
        if not transaction:
            return {'success': False, 'error': 'Transaction not found or already processed'}
        
        # Check if approver has required role
        approver_role = self._map_legacy_role(self._get_user_role(approver_id))
        if approver_role not in transaction['required_approvals']:
            return {'success': False, 'error': 'Insufficient approval privileges'}
        
        # Check if already approved by this role
        for approval in transaction['current_approvals']:
            if approval['approver_role'] == approver_role:
                return {'success': False, 'error': 'Transaction already approved by this role'}
        
        # Add approval
        approval = {
            'approver_id': approver_id,
            'approver_name': self._get_user_name(approver_id),
            'approver_role': approver_role,
            'approved_at': datetime.now().isoformat(),
            'reason': approval_reason
        }
        
        transaction['current_approvals'].append(approval)
        
        # Check if all required approvals obtained
        if len(transaction['current_approvals']) >= len(transaction['required_approvals']):
            transaction['status'] = 'approved'
            # Move to approved transactions
            data['pending_transactions'].remove(transaction)
            data['approved_transactions'].append(transaction)
        
        self._save_approval_data(data)
        
        return {
            'success': True,
            'transaction': transaction,
            'message': f'Transaction approved by {approver_role}',
            'fully_approved': transaction['status'] == 'approved'
        }
    
    def reject_transaction(self, rejecter_id: str, transaction_id: str, 
                         rejection_reason: str) -> Dict[str, Any]:
        """Reject a transaction"""
        data = self._load_approval_data()
        
        # Find transaction in pending
        transaction = None
        for tx in data['pending_transactions']:
            if tx['transaction_id'] == transaction_id:
                transaction = tx
                break
        
        if not transaction:
            return {'success': False, 'error': 'Transaction not found or already processed'}
        
        # Add rejection
        rejection = {
            'rejecter_id': rejecter_id,
            'rejecter_name': self._get_user_name(rejecter_id),
            'rejecter_role': self._get_user_role(rejecter_id),
            'rejected_at': datetime.now().isoformat(),
            'reason': rejection_reason
        }
        
        transaction['rejections'].append(rejection)
        transaction['status'] = 'rejected'
        
        # Move to rejected transactions
        data['pending_transactions'].remove(transaction)
        data['rejected_transactions'].append(transaction)
        
        self._save_approval_data(data)
        
        return {
            'success': True,
            'transaction': transaction,
            'message': 'Transaction rejected'
        }
    
    def finalize_transaction(self, finalizer_id: str, transaction_id: str) -> Dict[str, Any]:
        """Finalize an approved transaction (CFO only)"""
        data = self._load_approval_data()
        
        # Find transaction in approved
        transaction = None
        for tx in data['approved_transactions']:
            if tx['transaction_id'] == transaction_id:
                transaction = tx
                break
        
        if not transaction:
            return {'success': False, 'error': 'Approved transaction not found'}
        
        # Check if finalizer is CFO
        finalizer_role = self._get_user_role(finalizer_id)
        if finalizer_role != 'CFO':
            return {'success': False, 'error': 'Only CFO can finalize transactions'}
        
        # Finalize transaction
        transaction['status'] = 'finalized'
        transaction['finalized_at'] = datetime.now().isoformat()
        transaction['finalized_by'] = finalizer_id
        transaction['finalizer_name'] = self._get_user_name(finalizer_id)
        
        # Move to finalized transactions
        data['approved_transactions'].remove(transaction)
        data['finalized_transactions'].append(transaction)
        
        self._save_approval_data(data)
        
        return {
            'success': True,
            'transaction': transaction,
            'message': 'Transaction finalized successfully'
        }
    
    def _get_user_role(self, user_id: str) -> str:
        """Get user role from ID"""
        try:
            from models.supabase_auth_models import supabase_auth
            user_data = supabase_auth.get_user_by_id(user_id)
            return user_data['role'] if user_data else 'UNKNOWN'
        except:
            return 'UNKNOWN'
    
    def get_pending_transactions(self, approver_role: str = None) -> List[Dict[str, Any]]:
        """Get pending transactions, optionally filtered by approver role"""
        data = self._load_approval_data()
        pending = data['pending_transactions']
        
        if approver_role:
            # Map legacy role to new role for compatibility
            mapped_role = self._map_legacy_role(approver_role)
            
            # Filter transactions that require this role's approval
            filtered = []
            for tx in pending:
                if mapped_role in tx['required_approvals']:
                    # Check if not already approved by this role
                    already_approved = False
                    for approval in tx['current_approvals']:
                        if approval['approver_role'] == mapped_role:
                            already_approved = True
                            break
                    if not already_approved:
                        filtered.append(tx)
            return filtered
        
        return pending
    
    def get_transaction_history(self, user_id: str = None, status: str = None) -> List[Dict[str, Any]]:
        """Get transaction history with optional filters"""
        data = self._load_approval_data()
        all_transactions = (
            data['pending_transactions'] + 
            data['approved_transactions'] + 
            data['rejected_transactions'] + 
            data['finalized_transactions']
        )
        
        # Filter by user ID (creator or approver)
        if user_id:
            filtered = []
            for tx in all_transactions:
                if tx['creator_id'] == user_id:
                    filtered.append(tx)
                else:
                    # Check if user participated in approvals
                    for approval in tx.get('current_approvals', []):
                        if approval['approver_id'] == user_id:
                            filtered.append(tx)
                            break
                    for rejection in tx.get('rejections', []):
                        if rejection['rejecter_id'] == user_id:
                            filtered.append(tx)
                            break
            all_transactions = filtered
        
        # Filter by status
        if status:
            all_transactions = [tx for tx in all_transactions if tx['status'] == status]
        
        # Sort by creation date (newest first)
        all_transactions.sort(key=lambda x: x['created_at'], reverse=True)
        
        return all_transactions
    
    def get_approval_statistics(self) -> Dict[str, Any]:
        """Get approval workflow statistics"""
        data = self._load_approval_data()
        
        stats = {
            'pending_count': len(data['pending_transactions']),
            'approved_count': len(data['approved_transactions']),
            'rejected_count': len(data['rejected_transactions']),
            'finalized_count': len(data['finalized_transactions']),
            'total_transactions': sum([
                len(data['pending_transactions']),
                len(data['approved_transactions']),
                len(data['rejected_transactions']),
                len(data['finalized_transactions'])
            ]),
            'approval_rate': 0,
            'rejection_rate': 0,
            'finalization_rate': 0,
            'pending_by_type': {},
            'avg_approval_time': 0
        }
        
        # Calculate rates
        total_processed = stats['approved_count'] + stats['rejected_count']
        if total_processed > 0:
            stats['approval_rate'] = (stats['approved_count'] / total_processed) * 100
            stats['rejection_rate'] = (stats['rejected_count'] / total_processed) * 100
        
        if stats['approved_count'] > 0:
            stats['finalization_rate'] = (stats['finalized_count'] / stats['approved_count']) * 100
        
        # Pending transactions by type
        for tx in data['pending_transactions']:
            tx_type = tx['transaction_type']
            stats['pending_by_type'][tx_type] = stats['pending_by_type'].get(tx_type, 0) + 1
        
        return stats


# Initialize the approval model
approval_model = TransactionApprovalModel()
