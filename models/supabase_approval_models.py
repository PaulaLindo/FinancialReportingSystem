"""
SADPMR Financial Reporting System - Supabase Approval Models
Four-Eyes approval workflow using Supabase database
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from supabase import create_client
import os
import json

class SupabaseApprovalModel:
    """Four-Eyes approval workflow for financial transactions using Supabase"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.client = create_client(self.supabase_url, self.supabase_key)
    
    def _get_required_approvals(self, transaction_type: str) -> List[str]:
        """Get required approval roles based on transaction type"""
        approval_matrix = {
            'journal_entry': ['FINANCE_MANAGER', 'CFO'],
            'asset_impairment': ['ASSET_MANAGER', 'FINANCE_MANAGER', 'CFO'],
            'budget_adjustment': ['FINANCE_MANAGER', 'CFO'],
            'financial_statement': ['CFO'],
            'asset_disposal': ['ASSET_MANAGER', 'FINANCE_MANAGER', 'CFO']
        }
        return approval_matrix.get(transaction_type, ['FINANCE_MANAGER', 'CFO'])
    
    def _map_legacy_role(self, role: str) -> str:
        """Map legacy roles to new roles for demo compatibility"""
        legacy_mapping = {
            'ACCOUNTANT': 'FINANCE_MANAGER',
            'CLERK': 'FINANCE_CLERK',
            'AUDITOR': 'AUDITOR',
            'CFO': 'CFO',
        }
        return legacy_mapping.get(role, role)
    
    def _get_user_role(self, user_id: str) -> str:
        """Get user role from ID"""
        try:
            from models.supabase_auth_models import supabase_auth
            user_data = supabase_auth.get_user_by_id(user_id)
            return user_data['role'] if user_data else 'UNKNOWN'
        except:
            return 'UNKNOWN'
    
    def _get_user_name(self, user_id: str) -> str:
        """Get user name from ID"""
        try:
            from models.supabase_auth_models import supabase_auth
            user_data = supabase_auth.get_user_by_id(user_id)
            return user_data['full_name'] if user_data else f"User {user_id}"
        except:
            return f"User {user_id}"
    
    def create_pending_transaction(self, creator_id: str, transaction_type: str, 
                                transaction_data: Dict, reason: str = '') -> Dict[str, Any]:
        """Create a transaction requiring approval"""
        try:
            transaction_id = f"TX_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            transaction_record = {
                'transaction_id': transaction_id,
                'transaction_type': transaction_type,
                'creator_id': creator_id,
                'transaction_data': transaction_data,
                'reason': reason,
                'status': 'pending_approval',
                'required_approvals': self._get_required_approvals(transaction_type),
                'current_approvals': [],
                'rejections': [],
                'created_at': datetime.now().isoformat()
            }
            
            result = self.client.table('transaction_approvals').insert(transaction_record).execute()
            
            if result.data:
                # Log creation action
                self._log_approval_action(
                    transaction_id, 'create', creator_id, 
                    self._get_user_role(creator_id),
                    transaction_data, reason
                )
                
                return {
                    'success': True,
                    'transaction': result.data[0],
                    'message': f'Transaction {transaction_id} created and requires approval'
                }
            else:
                return {'success': False, 'error': 'Failed to create transaction'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _log_approval_action(self, transaction_id: str, action_type: str, user_id: str,
                            user_role: str, action_data: Dict = None, reason: str = '',
                            ip_address: str = '127.0.0.1', user_agent: str = 'Web Browser'):
        """Log approval action"""
        try:
            action_record = {
                'transaction_id': transaction_id,
                'action_type': action_type,
                'user_id': user_id,
                'user_role': user_role,
                'action_data': action_data or {},
                'reason': reason,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'created_at': datetime.now().isoformat()
            }
            
            self.client.table('approval_actions').insert(action_record).execute()
            
        except Exception as e:
            pass
    
    def approve_transaction(self, approver_id: str, transaction_id: str, 
                          approval_reason: str) -> Dict[str, Any]:
        """Add approval to transaction"""
        try:
            # Get transaction details
            result = self.client.table('transaction_approvals').select('*').eq('transaction_id', transaction_id).execute()
            
            if not result.data:
                return {'success': False, 'error': 'Transaction not found'}
            
            transaction = result.data[0]
            
            # Check if approver has required role
            approver_role = self._map_legacy_role(self._get_user_role(approver_id))
            if approver_role not in transaction['required_approvals']:
                return {'success': False, 'error': 'Insufficient approval privileges'}
            
            # Check if already approved by this role
            for approval in transaction['current_approvals']:
                if approval.get('approver_role') == approver_role:
                    return {'success': False, 'error': 'Transaction already approved by this role'}
            
            # Call Supabase function to add approval
            func_result = self.client.rpc('add_approval', {
                'p_transaction_id': transaction_id,
                'p_user_id': approver_id,
                'p_user_role': approver_role,
                'p_reason': approval_reason
            }).execute()
            
            if func_result.data:
                # Get updated transaction
                updated_result = self.client.table('transaction_approvals').select('*').eq('transaction_id', transaction_id).execute()
                updated_transaction = updated_result.data[0] if updated_result.data else transaction
                
                return {
                    'success': True,
                    'transaction': updated_transaction,
                    'message': f'Transaction approved by {approver_role}',
                    'fully_approved': updated_transaction['status'] == 'approved'
                }
            else:
                return {'success': False, 'error': 'Failed to add approval'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def reject_transaction(self, rejecter_id: str, transaction_id: str, 
                         rejection_reason: str) -> Dict[str, Any]:
        """Reject a transaction"""
        try:
            # Get transaction
            result = self.client.table('transaction_approvals').select('*').eq('transaction_id', transaction_id).execute()
            
            if not result.data:
                return {'success': False, 'error': 'Transaction not found or already processed'}
            
            transaction = result.data[0]
            
            # Add rejection
            rejection_data = {
                'rejecter_id': rejecter_id,
                'rejecter_name': self._get_user_name(rejecter_id),
                'rejecter_role': self._get_user_role(rejecter_id),
                'rejected_at': datetime.now().isoformat(),
                'reason': rejection_reason
            }
            
            # Update transaction
            updated_rejections = transaction['rejections'] + [rejection_data]
            
            update_result = self.client.table('transaction_approvals').update({
                'rejections': updated_rejections,
                'status': 'rejected'
            }).eq('transaction_id', transaction_id).execute()
            
            if update_result.data:
                # Log rejection action
                self._log_approval_action(
                    transaction_id, 'reject', rejecter_id,
                    self._get_user_role(rejecter_id),
                    rejection_data, rejection_reason
                )
                
                return {
                    'success': True,
                    'transaction': update_result.data[0],
                    'message': 'Transaction rejected'
                }
            else:
                return {'success': False, 'error': 'Failed to reject transaction'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def finalize_transaction(self, finalizer_id: str, transaction_id: str) -> Dict[str, Any]:
        """Finalize an approved transaction (CFO only)"""
        try:
            # Get transaction
            result = self.client.table('transaction_approvals').select('*').eq('transaction_id', transaction_id).execute()
            
            if not result.data:
                return {'success': False, 'error': 'Approved transaction not found'}
            
            transaction = result.data[0]
            
            # Check if finalizer is CFO
            finalizer_role = self._get_user_role(finalizer_id)
            if finalizer_role != 'CFO':
                return {'success': False, 'error': 'Only CFO can finalize transactions'}
            
            # Check if transaction is approved
            if transaction['status'] != 'approved':
                return {'success': False, 'error': 'Only approved transactions can be finalized'}
            
            # Finalize transaction
            update_result = self.client.table('transaction_approvals').update({
                'status': 'finalized',
                'finalized_at': datetime.now().isoformat(),
                'finalized_by': finalizer_id
            }).eq('transaction_id', transaction_id).execute()
            
            if update_result.data:
                # Log finalization action
                self._log_approval_action(
                    transaction_id, 'finalize', finalizer_id,
                    finalizer_role,
                    {'finalized_at': datetime.now().isoformat()},
                    'Transaction finalized by CFO'
                )
                
                return {
                    'success': True,
                    'transaction': update_result.data[0],
                    'message': 'Transaction finalized successfully'
                }
            else:
                return {'success': False, 'error': 'Failed to finalize transaction'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_pending_transactions(self, approver_role: str = None) -> List[Dict[str, Any]]:
        """Get pending transactions, optionally filtered by approver role"""
        try:
            query = self.client.table('pending_approvals').select('*')
            
            if approver_role:
                # Map legacy role to new role for compatibility
                mapped_role = self._map_legacy_role(approver_role)
                
                # Filter transactions that require this role's approval
                # This would need to be enhanced with proper filtering in Supabase
                result = query.execute()
                pending = result.data if result.data else []
                
                # Filter client-side for now
                filtered = []
                for tx in pending:
                    if mapped_role in tx['required_approvals']:
                        # Check if not already approved by this role
                        already_approved = False
                        for approval in tx.get('current_approvals', []):
                            if approval.get('approver_role') == mapped_role:
                                already_approved = True
                                break
                        if not already_approved:
                            filtered.append(tx)
                return filtered
            else:
                result = query.execute()
                return result.data if result.data else []
                
        except Exception as e:
            print(f"Error getting pending transactions: {e}")
            return []
    
    def get_transaction_history(self, user_id: str = None, status: str = None) -> List[Dict[str, Any]]:
        """Get transaction history with optional filters"""
        try:
            query = self.client.table('transaction_approvals').select('*')
            
            if user_id:
                query = query.eq('creator_id', user_id)
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('created_at', desc=True).execute()
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting transaction history: {e}")
            return []
    
    def get_approval_statistics(self) -> Dict[str, Any]:
        """Get approval workflow statistics"""
        try:
            # Get all transactions
            result = self.client.table('transaction_approvals').select('*').execute()
            transactions = result.data if result.data else []
            
            stats = {
                'pending_count': 0,
                'approved_count': 0,
                'rejected_count': 0,
                'finalized_count': 0,
                'total_transactions': len(transactions),
                'approval_rate': 0,
                'rejection_rate': 0,
                'finalization_rate': 0,
                'pending_by_type': {}
            }
            
            # Calculate statistics
            for tx in transactions:
                status = tx['status']
                if status == 'pending_approval':
                    stats['pending_count'] += 1
                elif status == 'approved':
                    stats['approved_count'] += 1
                elif status == 'rejected':
                    stats['rejected_count'] += 1
                elif status == 'finalized':
                    stats['finalized_count'] += 1
                
                # Pending transactions by type
                if status == 'pending_approval':
                    tx_type = tx['transaction_type']
                    stats['pending_by_type'][tx_type] = stats['pending_by_type'].get(tx_type, 0) + 1
            
            # Calculate rates
            total_processed = stats['approved_count'] + stats['rejected_count']
            if total_processed > 0:
                stats['approval_rate'] = (stats['approved_count'] / total_processed) * 100
                stats['rejection_rate'] = (stats['rejected_count'] / total_processed) * 100
            
            if stats['approved_count'] > 0:
                stats['finalization_rate'] = (stats['finalized_count'] / stats['approved_count']) * 100
            
            return stats
            
        except Exception as e:
            print(f"Error getting approval statistics: {e}")
            return {}

# Initialize the approval model
supabase_approval_model = SupabaseApprovalModel()
