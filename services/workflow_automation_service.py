"""
Workflow Automation Service
Handles automated state transitions and workflow enforcement for balance sheet submissions
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging

from models.balance_sheet_models import balance_sheet_model, BalanceSheetSession
from models.period_models import period_model, FinancialPeriod, PeriodStatus
from models.supabase_auth_models import supabase_auth
from services.period_management_service import period_management_service

# Set up logging
logger = logging.getLogger(__name__)


class SubmissionStatus(Enum):
    """Submission status enumeration"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESUBMITTED = "resubmitted"


class WorkflowAction(Enum):
    """Workflow action enumeration"""
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    RESUBMIT = "resubmit"
    WITHDRAW = "withdraw"


@dataclass
class WorkflowTransition:
    """Workflow transition data"""
    from_status: str
    to_status: str
    action: str
    allowed_roles: List[str]
    conditions: List[str]
    automated: bool = False


class WorkflowAutomationService:
    """Service for automating workflow state transitions"""
    
    def __init__(self):
        self.balance_sheet_model = balance_sheet_model
        self.period_model = period_model
        self.period_service = period_management_service
        
        # Define workflow transitions
        self.workflow_transitions = {
            SubmissionStatus.DRAFT.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.DRAFT.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['balanced_balance_sheet', 'mapped_accounts', 'valid_period']
                )
            ],
            SubmissionStatus.PENDING_REVIEW.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_REVIEW.value,
                    to_status=SubmissionStatus.APPROVED.value,
                    action=WorkflowAction.APPROVE.value,
                    allowed_roles=['FINANCE_MANAGER', 'CFO'],
                    conditions=['manager_review_complete']
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_REVIEW.value,
                    to_status=SubmissionStatus.REJECTED.value,
                    action=WorkflowAction.REJECT.value,
                    allowed_roles=['FINANCE_MANAGER', 'CFO'],
                    conditions=['rejection_reason']
                )
            ],
            SubmissionStatus.REJECTED.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.REJECTED.value,
                    to_status=SubmissionStatus.RESUBMITTED.value,
                    action=WorkflowAction.RESUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['rejection_addressed', 'valid_period']
                )
            ],
            SubmissionStatus.RESUBMITTED.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.RESUBMITTED.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['balanced_balance_sheet', 'mapped_accounts', 'valid_period']
                )
            ]
        }

    def get_allowed_transitions(self, current_status: str, user_role: str) -> List[WorkflowTransition]:
        """Get allowed workflow transitions for a user"""
        try:
            if current_status not in self.workflow_transitions:
                return []
            
            allowed_transitions = []
            for transition in self.workflow_transitions[current_status]:
                if user_role in transition.allowed_roles:
                    allowed_transitions.append(transition)
            
            return allowed_transitions
            
        except Exception as e:
            logger.error(f"Error getting allowed transitions: {str(e)}")
            return []

    def can_perform_action(self, session_id: str, action: str, user_role: str) -> Tuple[bool, str]:
        """Check if user can perform a workflow action"""
        try:
            # Get current session
            session = self.balance_sheet_model.get_session(session_id)
            if not session:
                return False, "Session not found"
            
            current_status = session.status
            
            # Find matching transition
            allowed_transitions = self.get_allowed_transitions(current_status, user_role)
            matching_transition = None
            
            for transition in allowed_transitions:
                if transition.action == action:
                    matching_transition = transition
                    break
            
            if not matching_transition:
                return False, f"Action '{action}' not allowed for status '{current_status}' and role '{user_role}'"
            
            # Check conditions
            can_transition, condition_message = self._check_transition_conditions(
                session, matching_transition.conditions
            )
            
            if not can_transition:
                return False, condition_message
            
            return True, "Action allowed"
            
        except Exception as e:
            logger.error(f"Error checking action permission: {str(e)}")
            return False, f"Error checking permission: {str(e)}"

    def execute_workflow_action(self, session_id: str, action: str, user_id: str, 
                              action_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a workflow action"""
        try:
            # Get user
            user_data = supabase_auth.get_user_by_id(user_id)
            if not user_data:
                raise Exception("User not found")
            
            user_role = user_data['role']
            
            # Check if action is allowed
            can_perform, message = self.can_perform_action(session_id, action, user_role)
            if not can_perform:
                raise Exception(message)
            
            # Get session
            session = self.balance_sheet_model.get_session(session_id)
            if not session:
                raise Exception("Session not found")
            
            current_status = session.status
            
            # Find target status
            target_status = None
            for transition in self.workflow_transitions.get(current_status, []):
                if transition.action == action and user_role in transition.allowed_roles:
                    target_status = transition.to_status
                    break
            
            if not target_status:
                raise Exception("No valid transition found")
            
            # Execute the action
            result = self._execute_specific_action(
                session, action, target_status, user_id, action_data or {}
            )
            
            logger.info(f"Executed workflow action '{action}' on session {session_id} by user {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing workflow action: {str(e)}")
            raise Exception(f"Failed to execute workflow action: {str(e)}")

    def submit_for_review(self, session_id: str, user_id: str, period_id: Optional[str] = None) -> Dict[str, Any]:
        """Submit balance sheet for manager review"""
        try:
            # Get session
            session = self.balance_sheet_model.get_session(session_id)
            if not session:
                raise Exception("Session not found")
            
            # Validate submission requirements
            validation_result = self._validate_submission_requirements(session, period_id)
            if not validation_result['valid']:
                raise Exception(validation_result['message'])
            
            # Update session status
            updated_session = self.balance_sheet_model.update_session_status(
                session_id, SubmissionStatus.PENDING_REVIEW.value
            )
            
            # Update metadata
            metadata = updated_session.metadata or {}
            metadata.update({
                'submitted_at': datetime.now().isoformat(),
                'submitted_by': user_id,
                'submission_period_id': period_id,
                'workflow_history': metadata.get('workflow_history', []) + [{
                    'action': WorkflowAction.SUBMIT.value,
                    'timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'from_status': session.status,
                    'to_status': SubmissionStatus.PENDING_REVIEW.value
                }]
            })
            
            # Save updated metadata
            self.balance_sheet_model.update_session_metadata(session_id, metadata)
            
            # Record upload for period if provided
            if period_id:
                try:
                    self.period_service.record_upload_for_period(period_id, {
                        'session_id': session_id,
                        'upload_date': datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Failed to record upload for period {period_id}: {str(e)}")
            
            return {
                'success': True,
                'session_id': session_id,
                'new_status': SubmissionStatus.PENDING_REVIEW.value,
                'message': 'Balance Sheet submitted for manager review',
                'submitted_at': metadata['submitted_at']
            }
            
        except Exception as e:
            logger.error(f"Error submitting for review: {str(e)}")
            raise Exception(f"Failed to submit for review: {str(e)}")

    def approve_submission(self, session_id: str, user_id: str, approval_notes: Optional[str] = None) -> Dict[str, Any]:
        """Approve a balance sheet submission"""
        try:
            # Get session
            session = self.balance_sheet_model.get_session(session_id)
            if not session:
                raise Exception("Session not found")
            
            # Update session status
            updated_session = self.balance_sheet_model.update_session_status(
                session_id, SubmissionStatus.APPROVED.value
            )
            
            # Update metadata
            metadata = updated_session.metadata or {}
            metadata.update({
                'approved_at': datetime.now().isoformat(),
                'approved_by': user_id,
                'approval_notes': approval_notes,
                'workflow_history': metadata.get('workflow_history', []) + [{
                    'action': WorkflowAction.APPROVE.value,
                    'timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'from_status': session.status,
                    'to_status': SubmissionStatus.APPROVED.value,
                    'notes': approval_notes
                }]
            })
            
            # Save updated metadata
            self.balance_sheet_model.update_session_metadata(session_id, metadata)
            
            return {
                'success': True,
                'session_id': session_id,
                'new_status': SubmissionStatus.APPROVED.value,
                'message': 'Balance Sheet approved',
                'approved_at': metadata['approved_at']
            }
            
        except Exception as e:
            logger.error(f"Error approving submission: {str(e)}")
            raise Exception(f"Failed to approve submission: {str(e)}")

    def reject_submission(self, session_id: str, user_id: str, rejection_reason: str) -> Dict[str, Any]:
        """Reject a balance sheet submission"""
        try:
            # Get session
            session = self.balance_sheet_model.get_session(session_id)
            if not session:
                raise Exception("Session not found")
            
            if not rejection_reason or rejection_reason.strip() == '':
                raise Exception("Rejection reason is required")
            
            # Update session status
            updated_session = self.balance_sheet_model.update_session_status(
                session_id, SubmissionStatus.REJECTED.value
            )
            
            # Update metadata
            metadata = updated_session.metadata or {}
            metadata.update({
                'rejected_at': datetime.now().isoformat(),
                'rejected_by': user_id,
                'rejection_reason': rejection_reason,
                'workflow_history': metadata.get('workflow_history', []) + [{
                    'action': WorkflowAction.REJECT.value,
                    'timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'from_status': session.status,
                    'to_status': SubmissionStatus.REJECTED.value,
                    'reason': rejection_reason
                }]
            })
            
            # Save updated metadata
            self.balance_sheet_model.update_session_metadata(session_id, metadata)
            
            return {
                'success': True,
                'session_id': session_id,
                'new_status': SubmissionStatus.REJECTED.value,
                'message': 'Balance Sheet rejected',
                'rejected_at': metadata['rejected_at'],
                'rejection_reason': rejection_reason
            }
            
        except Exception as e:
            logger.error(f"Error rejecting submission: {str(e)}")
            raise Exception(f"Failed to reject submission: {str(e)}")

    def resubmit_after_rejection(self, session_id: str, user_id: str, 
                               changes_made: Optional[str] = None) -> Dict[str, Any]:
        """Resubmit a balance sheet after rejection"""
        try:
            # Get session
            session = self.balance_sheet_model.get_session(session_id)
            if not session:
                raise Exception("Session not found")
            
            # Verify session was rejected
            if session.status != SubmissionStatus.REJECTED.value:
                raise Exception("Only rejected submissions can be resubmitted")
            
            # Update session status
            updated_session = self.balance_sheet_model.update_session_status(
                session_id, SubmissionStatus.RESUBMITTED.value
            )
            
            # Update metadata
            metadata = updated_session.metadata or {}
            metadata.update({
                'resubmitted_at': datetime.now().isoformat(),
                'resubmitted_by': user_id,
                'changes_made': changes_made,
                'workflow_history': metadata.get('workflow_history', []) + [{
                    'action': WorkflowAction.RESUBMIT.value,
                    'timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'from_status': session.status,
                    'to_status': SubmissionStatus.RESUBMITTED.value,
                    'changes': changes_made
                }]
            })
            
            # Save updated metadata
            self.balance_sheet_model.update_session_metadata(session_id, metadata)
            
            return {
                'success': True,
                'session_id': session_id,
                'new_status': SubmissionStatus.RESUBMITTED.value,
                'message': 'Balance Sheet resubmitted after rejection',
                'resubmitted_at': metadata['resubmitted_at']
            }
            
        except Exception as e:
            logger.error(f"Error resubmitting after rejection: {str(e)}")
            raise Exception(f"Failed to resubmit: {str(e)}")

    def can_edit_session(self, session_id: str, user_id: str) -> Tuple[bool, str]:
        """Check if a user can edit a session"""
        try:
            # Get session
            session = self.balance_sheet_model.get_session(session_id)
            if not session:
                return False, "Session not found"
            
            # Get user
            user_data = supabase_auth.get_user_by_id(user_id)
            if not user_data:
                return False, "User not found"
            
            user_role = user_data['role']
            
            # Check edit permissions based on status
            if session.status == SubmissionStatus.DRAFT.value:
                # Draft sessions can be edited by creator
                if session.user_id == user_id or user_role in ['FINANCE_MANAGER', 'CFO', 'ADMIN']:
                    return True, "Edit allowed"
                else:
                    return False, "Only creator or managers can edit draft sessions"
            
            elif session.status == SubmissionStatus.REJECTED.value:
                # Rejected sessions can be edited by creator
                if session.user_id == user_id:
                    return True, "Edit allowed for rejected submission"
                else:
                    return False, "Only creator can edit rejected submissions"
            
            elif session.status == SubmissionStatus.RESUBMITTED.value:
                # Resubmitted sessions can be edited by creator
                if session.user_id == user_id:
                    return True, "Edit allowed for resubmitted session"
                else:
                    return False, "Only creator can edit resubmitted sessions"
            
            else:
                # Pending review, approved, or other statuses cannot be edited
                return False, f"Cannot edit session in '{session.status}' status"
                
        except Exception as e:
            logger.error(f"Error checking edit permission: {str(e)}")
            return False, f"Error checking permission: {str(e)}"

    def get_workflow_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get workflow history for a session"""
        try:
            session = self.balance_sheet_model.get_session(session_id)
            if not session:
                return []
            
            metadata = session.metadata or {}
            return metadata.get('workflow_history', [])
            
        except Exception as e:
            logger.error(f"Error getting workflow history: {str(e)}")
            return []

    def _check_transition_conditions(self, session: BalanceSheetSession, 
                                   conditions: List[str]) -> Tuple[bool, str]:
        """Check if transition conditions are met"""
        try:
            for condition in conditions:
                if condition == 'balanced_balance_sheet':
                    # Check if balance sheet is balanced
                    if not self._is_balance_sheet_balanced(session):
                        return False, "Balance Sheet must be balanced (debits = credits)"
                
                elif condition == 'mapped_accounts':
                    # Check if accounts are mapped
                    if not self._has_mapped_accounts(session):
                        return False, "All accounts must be mapped to GRAP categories"
                
                elif condition == 'valid_period':
                    # Check if period is valid and open
                    if not self._has_valid_period(session):
                        return False, "Must be associated with an open period"
                
                elif condition == 'manager_review_complete':
                    # This would be checked during approval action
                    pass
                
                elif condition == 'rejection_reason':
                    # This would be checked during rejection action
                    pass
                
                elif condition == 'rejection_addressed':
                    # Check if rejection has been addressed
                    if not self._rejection_addressed(session):
                        return False, "Rejection issues must be addressed"
            
            return True, "All conditions met"
            
        except Exception as e:
            logger.error(f"Error checking transition conditions: {str(e)}")
            return False, f"Error checking conditions: {str(e)}"

    def _execute_specific_action(self, session: BalanceSheetSession, action: str, 
                              target_status: str, user_id: str, 
                              action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific workflow actions"""
        try:
            if action == WorkflowAction.SUBMIT.value:
                return self.submit_for_review(session.id, user_id, action_data.get('period_id'))
            
            elif action == WorkflowAction.APPROVE.value:
                return self.approve_submission(session.id, user_id, action_data.get('approval_notes'))
            
            elif action == WorkflowAction.REJECT.value:
                return self.reject_submission(session.id, user_id, action_data.get('rejection_reason'))
            
            elif action == WorkflowAction.RESUBMIT.value:
                return self.resubmit_after_rejection(session.id, user_id, action_data.get('changes_made'))
            
            else:
                raise Exception(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Error executing specific action: {str(e)}")
            raise Exception(f"Failed to execute action: {str(e)}")

    def _validate_submission_requirements(self, session: BalanceSheetSession, 
                                         period_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate all requirements for submission"""
        try:
            # Check balanced balance sheet
            if not self._is_balance_sheet_balanced(session):
                return {
                    'valid': False,
                    'message': 'Balance Sheet is not balanced. Total debits must equal total credits.'
                }
            
            # Check mapped accounts
            if not self._has_mapped_accounts(session):
                return {
                    'valid': False,
                    'message': 'Not all accounts are mapped to GRAP categories. Please complete the mapping.'
                }
            
            # Check valid period
            if period_id:
                can_upload, message = self.period_service.validate_upload_for_period(period_id)
                if not can_upload:
                    return {
                        'valid': False,
                        'message': f'Period validation failed: {message}'
                    }
            
            return {
                'valid': True,
                'message': 'All submission requirements met'
            }
            
        except Exception as e:
            logger.error(f"Error validating submission requirements: {str(e)}")
            return {
                'valid': False,
                'message': f'Validation error: {str(e)}'
            }

    def _is_balance_sheet_balanced(self, session: BalanceSheetSession) -> bool:
        """Check if balance sheet is balanced"""
        try:
            # Get balance sheet data
            data_rows = self.balance_sheet_model.get_session_data(session.id)
            
            if not data_rows:
                return False
            
            total_debits = 0.0
            total_credits = 0.0
            
            for row in data_rows:
                try:
                    debit = float(row.get('debit_balance', 0) or 0)
                    credit = float(row.get('credit_balance', 0) or 0)
                    total_debits += debit
                    total_credits += credit
                except (ValueError, TypeError):
                    continue
            
            # Allow small rounding differences
            return abs(total_debits - total_credits) < 0.01
            
        except Exception as e:
            logger.error(f"Error checking balance sheet balance: {str(e)}")
            return False

    def _has_mapped_accounts(self, session: BalanceSheetSession) -> bool:
        """Check if accounts are mapped"""
        try:
            # Check processing results for mapped accounts
            metadata = session.metadata or {}
            processing_results = metadata.get('processing_results', {})
            
            mapped_count = processing_results.get('mapped_accounts', 0)
            total_count = processing_results.get('total_accounts', 0)
            
            return total_count > 0 and mapped_count >= total_count
            
        except Exception as e:
            logger.error(f"Error checking mapped accounts: {str(e)}")
            return False

    def _has_valid_period(self, session: BalanceSheetSession) -> bool:
        """Check if session has valid period"""
        try:
            metadata = session.metadata or {}
            period_id = metadata.get('period_id')
            
            if not period_id:
                return False
            
            period = self.period_model.get_period(period_id)
            if not period:
                return False
            
            return period.status == PeriodStatus.OPEN.value
            
        except Exception as e:
            logger.error(f"Error checking valid period: {str(e)}")
            return False

    def _rejection_addressed(self, session: BalanceSheetSession) -> bool:
        """Check if rejection issues have been addressed"""
        try:
            metadata = session.metadata or {}
            
            # Check if there was a rejection
            if not metadata.get('rejection_reason'):
                return True  # No rejection to address
            
            # Check if changes were made after rejection
            resubmitted_at = metadata.get('resubmitted_at')
            if resubmitted_at:
                return True
            
            # Check if changes were documented
            changes_made = metadata.get('changes_made')
            if changes_made and changes_made.strip():
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking rejection addressed: {str(e)}")
            return False


# Create global workflow automation service instance
workflow_automation_service = WorkflowAutomationService()
