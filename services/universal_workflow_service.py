"""
Universal Workflow Service
Handles workflow automation for all financial document types (Balance Sheets, Income Statements, Budget Reports)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

from models.balance_sheet_models import balance_sheet_model
from models.supabase_auth_models import supabase_auth
from services.period_management_service import period_management_service

# Set up logging
logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Document type enumeration"""
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    BUDGET_REPORT = "budget_report"


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
    document_types: List[str]  # Which document types this applies to
    automated: bool = False


class UniversalWorkflowService:
    """Service for automating workflow state transitions for all document types"""
    
    def __init__(self):
        self.period_service = period_management_service
        
        # Define workflow transitions for all document types
        self.workflow_transitions = {
            SubmissionStatus.DRAFT.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.DRAFT.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['valid_document_structure', 'mapped_accounts', 'valid_period'],
                    document_types=[DocumentType.BALANCE_SHEET.value, DocumentType.INCOME_STATEMENT.value, DocumentType.BUDGET_REPORT.value]
                )
            ],
            SubmissionStatus.PENDING_REVIEW.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_REVIEW.value,
                    to_status=SubmissionStatus.APPROVED.value,
                    action=WorkflowAction.APPROVE.value,
                    allowed_roles=['FINANCE_MANAGER', 'CFO'],
                    conditions=['manager_review_complete'],
                    document_types=[DocumentType.BALANCE_SHEET.value, DocumentType.INCOME_STATEMENT.value, DocumentType.BUDGET_REPORT.value]
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_REVIEW.value,
                    to_status=SubmissionStatus.REJECTED.value,
                    action=WorkflowAction.REJECT.value,
                    allowed_roles=['FINANCE_MANAGER', 'CFO'],
                    conditions=['rejection_reason'],
                    document_types=[DocumentType.BALANCE_SHEET.value, DocumentType.INCOME_STATEMENT.value, DocumentType.BUDGET_REPORT.value]
                )
            ],
            SubmissionStatus.REJECTED.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.REJECTED.value,
                    to_status=SubmissionStatus.RESUBMITTED.value,
                    action=WorkflowAction.RESUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['rejection_addressed', 'valid_period'],
                    document_types=[DocumentType.BALANCE_SHEET.value, DocumentType.INCOME_STATEMENT.value, DocumentType.BUDGET_REPORT.value]
                )
            ],
            SubmissionStatus.RESUBMITTED.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.RESUBMITTED.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['valid_document_structure', 'mapped_accounts', 'valid_period'],
                    document_types=[DocumentType.BALANCE_SHEET.value, DocumentType.INCOME_STATEMENT.value, DocumentType.BUDGET_REPORT.value]
                )
            ]
        }
        
        # Document-specific validation conditions
        self.document_conditions = {
            DocumentType.BALANCE_SHEET.value: {
                'valid_document_structure': self._validate_balance_sheet_structure,
                'mapped_accounts': self._check_balance_sheet_mapping,
                'valid_period': self._check_valid_period
            },
            DocumentType.INCOME_STATEMENT.value: {
                'valid_document_structure': self._validate_income_statement_structure,
                'mapped_accounts': self._check_income_statement_mapping,
                'valid_period': self._check_valid_period
            },
            DocumentType.BUDGET_REPORT.value: {
                'valid_document_structure': self._validate_budget_report_structure,
                'mapped_accounts': self._check_budget_report_mapping,
                'valid_period': self._check_valid_period
            }
        }
    
    def submit_for_review(self, document_type: str, session_id: str, user_id: str, notes: str = "", mapped_data: List[Dict] = None) -> Dict[str, Any]:
        """
        Submit document for review - universal method for all document types
        """
        try:
            logger.info(f"🔄 Submitting {document_type} for review: {session_id}")
            
            # Validate document type
            if document_type not in [dt.value for dt in DocumentType]:
                return {
                    'success': False,
                    'error': f'Invalid document type: {document_type}'
                }
            
            # Get appropriate model
            model = self._get_model_for_document_type(document_type)
            if not model:
                return {
                    'success': False,
                    'error': f'No model found for document type: {document_type}'
                }
            
            # Get session
            session = model.get_session(session_id)
            if not session:
                return {
                    'success': False,
                    'error': f'Session {session_id} not found'
                }
            
            # Check current status
            if session.status != SubmissionStatus.DRAFT.value:
                return {
                    'success': False,
                    'error': f'Document must be in DRAFT status to submit. Current status: {session.status}'
                }
            
            # Validate user role
            user_data = supabase_auth.get_user_by_id(user_id)
            if not user_data:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            # Check workflow transition
            transition = self._get_workflow_transition(
                SubmissionStatus.DRAFT.value,
                WorkflowAction.SUBMIT.value,
                document_type,
                user_data['role']
            )
            
            if not transition:
                return {
                    'success': False,
                    'error': f'Workflow transition not allowed for user role: {user_data["role"]}'
                }
            
            # Validate conditions
            condition_results = self._validate_workflow_conditions(
                document_type, session, transition.conditions
            )
            
            if not condition_results['all_passed']:
                return {
                    'success': False,
                    'error': f'Workflow conditions not met: {condition_results["failed_conditions"]}'
                }
            
            # Update session status
            session.status = SubmissionStatus.PENDING_REVIEW.value
            session.updated_at = datetime.now()
            session.metadata['submitted_at'] = datetime.now().isoformat()
            session.metadata['submitted_by'] = user_id
            session.metadata['submission_notes'] = notes
            session.processing_log.append(f"Submitted for review by {user_data.get('email', user_id)} at {datetime.now()}")
            
            # Store mapped data if provided
            if mapped_data:
                session.metadata['mapped_data'] = mapped_data
                session.metadata['mapping_completed_at'] = datetime.now().isoformat()
                session.metadata['total_mapped_accounts'] = len(mapped_data)
                session.processing_log.append(f"Stored {len(mapped_data)} mapped accounts")
            
            # Save updated session
            updated_session = model.update_session(session)
            
            # Create workflow record
            workflow_record = self._create_workflow_record(
                document_type, session_id, user_id, 
                SubmissionStatus.DRAFT.value,
                SubmissionStatus.PENDING_REVIEW.value,
                WorkflowAction.SUBMIT.value,
                notes
            )
            
            logger.info(f"✅ {document_type} submitted for review successfully")
            
            return {
                'success': True,
                'session_id': session_id,
                'submission_id': session_id,  # Use session_id as submission_id for compatibility
                'document_type': document_type,
                'new_status': SubmissionStatus.PENDING_REVIEW.value,
                'workflow_record': workflow_record,
                'message': f'{document_type.replace("_", " ").title()} submitted for review successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error submitting {document_type} for review: {str(e)}")
            return {
                'success': False,
                'error': f'Error submitting {document_type} for review: {str(e)}'
            }
    
    def approve_document(self, document_type: str, session_id: str, user_id: str, notes: str = "") -> Dict[str, Any]:
        """Approve document - universal method for all document types"""
        try:
            logger.info(f"✅ Approving {document_type}: {session_id}")
            
            # Get appropriate model and session
            model = self._get_model_for_document_type(document_type)
            session = model.get_session(session_id)
            
            if not session:
                return {'success': False, 'error': 'Session not found'}
            
            # Check current status
            if session.status != SubmissionStatus.PENDING_REVIEW.value:
                return {
                    'success': False,
                    'error': f'Document must be in PENDING_REVIEW status to approve'
                }
            
            # Validate user role
            user = supabase_auth.get_user(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Update session status
            session.status = SubmissionStatus.APPROVED.value
            session.updated_at = datetime.now()
            session.metadata['approved_at'] = datetime.now().isoformat()
            session.metadata['approved_by'] = user_id
            session.metadata['approval_notes'] = notes
            session.processing_log.append(f"Approved by {user.email} at {datetime.now()}")
            
            # Save updated session
            updated_session = model.update_session(session)
            
            # Create workflow record
            workflow_record = self._create_workflow_record(
                document_type, session_id, user_id,
                SubmissionStatus.PENDING_REVIEW.value,
                SubmissionStatus.APPROVED.value,
                WorkflowAction.APPROVE.value,
                notes
            )
            
            return {
                'success': True,
                'session_id': session_id,
                'document_type': document_type,
                'new_status': SubmissionStatus.APPROVED.value,
                'workflow_record': workflow_record,
                'message': f'{document_type.replace("_", " ").title()} approved successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error approving {document_type}: {str(e)}")
            return {'success': False, 'error': f'Error approving {document_type}: {str(e)}'}
    
    def reject_document(self, document_type: str, session_id: str, user_id: str, reason: str) -> Dict[str, Any]:
        """Reject document - universal method for all document types"""
        try:
            logger.info(f"❌ Rejecting {document_type}: {session_id}")
            
            # Get appropriate model and session
            model = self._get_model_for_document_type(document_type)
            session = model.get_session(session_id)
            
            if not session:
                return {'success': False, 'error': 'Session not found'}
            
            # Check current status
            if session.status != SubmissionStatus.PENDING_REVIEW.value:
                return {
                    'success': False,
                    'error': f'Document must be in PENDING_REVIEW status to reject'
                }
            
            # Validate user role
            user = supabase_auth.get_user(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Update session status
            session.status = SubmissionStatus.REJECTED.value
            session.updated_at = datetime.now()
            session.metadata['rejected_at'] = datetime.now().isoformat()
            session.metadata['rejected_by'] = user_id
            session.metadata['rejection_reason'] = reason
            session.processing_log.append(f"Rejected by {user.email} at {datetime.now()}. Reason: {reason}")
            
            # Save updated session
            updated_session = model.update_session(session)
            
            # Create workflow record
            workflow_record = self._create_workflow_record(
                document_type, session_id, user_id,
                SubmissionStatus.PENDING_REVIEW.value,
                SubmissionStatus.REJECTED.value,
                WorkflowAction.REJECT.value,
                reason
            )
            
            return {
                'success': True,
                'session_id': session_id,
                'document_type': document_type,
                'new_status': SubmissionStatus.REJECTED.value,
                'workflow_record': workflow_record,
                'message': f'{document_type.replace("_", " ").title()} rejected successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error rejecting {document_type}: {str(e)}")
            return {'success': False, 'error': f'Error rejecting {document_type}: {str(e)}'}
    
    def get_user_submissions(self, user_id: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """Get all submissions for a user, optionally filtered by document type"""
        try:
            submissions = []
            
            # Get submissions from all document types
            document_types = [dt.value for dt in DocumentType]
            if document_type:
                document_types = [document_type]
            
            for doc_type in document_types:
                model = self._get_model_for_document_type(doc_type)
                if model:
                    sessions = model.get_user_sessions(user_id, limit=50)
                    for session in sessions:
                        submissions.append({
                            'session_id': session.id,
                            'document_type': session.document_type,
                            'filename': session.filename,
                            'status': session.status,
                            'created_at': session.created_at,
                            'updated_at': session.updated_at,
                            'total_rows': session.total_rows,
                            'total_columns': session.total_columns,
                            'metadata': session.metadata
                        })
            
            # Sort by creation date (newest first)
            submissions.sort(key=lambda x: x['created_at'], reverse=True)
            
            return {
                'success': True,
                'submissions': submissions,
                'total_count': len(submissions)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting user submissions: {str(e)}")
            return {'success': False, 'error': f'Error getting user submissions: {str(e)}'}
    
    def get_pending_approvals(self, user_id: str) -> Dict[str, Any]:
        """Get all pending approvals for a manager/CFO"""
        try:
            user = supabase_auth.get_user(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Check if user has approval permissions
            if user.role not in ['FINANCE_MANAGER', 'CFO']:
                return {'success': False, 'error': 'User does not have approval permissions'}
            
            pending_approvals = []
            
            # Get pending submissions from all document types
            for doc_type in [dt.value for dt in DocumentType]:
                model = self._get_model_for_document_type(doc_type)
                if model:
                    sessions = model.get_sessions_by_status(SubmissionStatus.PENDING_REVIEW.value, limit=100)
                    for session in sessions:
                        pending_approvals.append({
                            'session_id': session.id,
                            'document_type': session.document_type,
                            'filename': session.filename,
                            'submitted_by': session.metadata.get('submitted_by', ''),
                            'submitted_at': session.metadata.get('submitted_at', ''),
                            'total_rows': session.total_rows,
                            'metadata': session.metadata
                        })
            
            # Sort by submission date (oldest first)
            pending_approvals.sort(key=lambda x: x['submitted_at'])
            
            return {
                'success': True,
                'pending_approvals': pending_approvals,
                'total_count': len(pending_approvals)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting pending approvals: {str(e)}")
            return {'success': False, 'error': f'Error getting pending approvals: {str(e)}'}
    
    def _get_model_for_document_type(self, document_type: str):
        """Get the appropriate model for a document type"""
        try:
            if document_type == DocumentType.BALANCE_SHEET.value:
                from models.balance_sheet_models import balance_sheet_model
                return balance_sheet_model
            elif document_type == DocumentType.INCOME_STATEMENT.value:
                from models.income_statement_models import income_statement_model
                return income_statement_model
            elif document_type == DocumentType.BUDGET_REPORT.value:
                from models.budget_report_models import budget_report_model
                return budget_report_model
            else:
                return None
        except ImportError:
            logger.warning(f"Model not yet implemented for document type: {document_type}")
            return None
    
    def _get_workflow_transition(self, from_status: str, action: str, document_type: str, user_role: str) -> Optional[WorkflowTransition]:
        """Get workflow transition for given parameters"""
        transitions = self.workflow_transitions.get(from_status, [])
        
        for transition in transitions:
            if (transition.action == action and 
                document_type in transition.document_types and 
                user_role in transition.allowed_roles):
                return transition
        
        return None
    
    def _validate_workflow_conditions(self, document_type: str, session, conditions: List[str]) -> Dict[str, Any]:
        """Validate workflow conditions for a document"""
        results = {
            'all_passed': True,
            'failed_conditions': [],
            'condition_results': {}
        }
        
        doc_conditions = self.document_conditions.get(document_type, {})
        
        for condition in conditions:
            if condition in doc_conditions:
                try:
                    condition_func = doc_conditions[condition]
                    condition_result = condition_func(session)
                    results['condition_results'][condition] = condition_result
                    
                    if not condition_result.get('passed', False):
                        results['all_passed'] = False
                        results['failed_conditions'].append(condition)
                        
                except Exception as e:
                    logger.error(f"Error validating condition {condition}: {str(e)}")
                    results['all_passed'] = False
                    results['failed_conditions'].append(f"{condition} (validation error)")
        
        return results
    
    def _create_workflow_record(self, document_type: str, session_id: str, user_id: str,
                              from_status: str, to_status: str, action: str, notes: str) -> Dict[str, Any]:
        """Create a workflow record"""
        return {
            'id': str(uuid.uuid4()),
            'document_type': document_type,
            'session_id': session_id,
            'user_id': user_id,
            'from_status': from_status,
            'to_status': to_status,
            'action': action,
            'notes': notes,
            'timestamp': datetime.now().isoformat()
        }
    
    # Document-specific validation methods
    def _validate_balance_sheet_structure(self, session) -> Dict[str, Any]:
        """Validate balance sheet structure"""
        validation_result = session.metadata.get('validation_result', {})
        return {'passed': validation_result.get('valid', False)}
    
    def _validate_income_statement_structure(self, session) -> Dict[str, Any]:
        """Validate income statement structure"""
        validation_result = session.metadata.get('validation_result', {})
        # If no validation result, assume valid for existing sessions
        if not validation_result:
            return {'passed': True}
        return {'passed': validation_result.get('valid', False)}
    
    def _validate_budget_report_structure(self, session) -> Dict[str, Any]:
        """Validate budget report structure"""
        validation_result = session.metadata.get('validation_result', {})
        # If no validation result, assume valid for existing sessions
        if not validation_result:
            return {'passed': True}
        return {'passed': validation_result.get('valid', False)}
    
    def _check_balance_sheet_mapping(self, session) -> Dict[str, Any]:
        """Check if balance sheet has GRAP mapping"""
        has_mapping = bool(session.metadata.get('grap_mapping'))
        return {'passed': has_mapping}
    
    def _check_income_statement_mapping(self, session) -> Dict[str, Any]:
        """Check if income statement has GRAP mapping"""
        has_mapping = bool(session.metadata.get('grap_mapping'))
        # Also check for mapped_accounts as fallback
        if not has_mapping:
            has_mapping = bool(session.metadata.get('mapped_accounts'))
        return {'passed': has_mapping}
    
    def _check_budget_report_mapping(self, session) -> Dict[str, Any]:
        """Check if budget report has GRAP mapping"""
        has_mapping = bool(session.metadata.get('grap_mapping'))
        # Also check for mapped_accounts as fallback
        if not has_mapping:
            has_mapping = bool(session.metadata.get('mapped_accounts'))
        return {'passed': has_mapping}
    
    def _check_valid_period(self, session) -> Dict[str, Any]:
        """Check if document has a valid financial period"""
        # This would integrate with the period management service
        return {'passed': True}  # Simplified for now


# Import required modules
import uuid
