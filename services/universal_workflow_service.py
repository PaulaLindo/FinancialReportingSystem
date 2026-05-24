"""
Universal Workflow Service
Handles workflow automation for all financial document types (Balance Sheets, Income Statements, Budget Reports)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import logging
import uuid

from models.balance_sheet_models import balance_sheet_model
from models.supabase_auth_models import supabase_auth
from services.period_management_service import period_management_service
from utils.constants import ClerkWorkflowMessages
from utils.session_workflow import mark_session_committed_metadata

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
    PENDING_CFO = "pending_cfo"
    APPROVED_BY_MANAGER = "approved_by_manager"
    REJECTED_BY_MANAGER = "rejected_by_manager"
    REJECTED_BY_CFO = "rejected_by_cfo"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESUBMITTED = "resubmitted"


# Document types that require Finance Manager sign-off before CFO final approval
CFO_GATE_DOCUMENT_TYPES = frozenset({
    DocumentType.BALANCE_SHEET.value,
    DocumentType.INCOME_STATEMENT.value,
    DocumentType.BUDGET_REPORT.value,
})

# Statuses from which a Finance Clerk may submit for manager review
CLERK_SUBMIT_FROM_STATUSES = frozenset({
    SubmissionStatus.DRAFT.value,
    "uploaded",
    "processing",
    "mapped",
    "validated",
    SubmissionStatus.RESUBMITTED.value,
    SubmissionStatus.REJECTED_BY_MANAGER.value,
    SubmissionStatus.REJECTED_BY_CFO.value,
    SubmissionStatus.REJECTED.value,
})

# CFO queue: new manager-approved label and legacy pending_cfo
CFO_PENDING_STATUSES = frozenset({
    SubmissionStatus.APPROVED_BY_MANAGER.value,
    SubmissionStatus.PENDING_CFO.value,
})

# Map DB session statuses to workflow transition keys
WORKFLOW_STATUS_ALIASES = {
    "uploaded": SubmissionStatus.DRAFT.value,
    "processing": SubmissionStatus.DRAFT.value,
    "mapped": SubmissionStatus.DRAFT.value,
    "validated": SubmissionStatus.DRAFT.value,
}


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
                    document_types=[DocumentType.BALANCE_SHEET.value, DocumentType.INCOME_STATEMENT.value]
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.DRAFT.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['valid_document_structure', 'mapped_accounts', 'valid_period', 'grap24_variance_explanations'],
                    document_types=[DocumentType.BUDGET_REPORT.value]
                )
            ],
            SubmissionStatus.PENDING_REVIEW.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_REVIEW.value,
                    to_status=SubmissionStatus.APPROVED_BY_MANAGER.value,
                    action=WorkflowAction.APPROVE.value,
                    allowed_roles=['FINANCE_MANAGER'],
                    conditions=['manager_review_complete'],
                    document_types=[
                        DocumentType.BALANCE_SHEET.value,
                        DocumentType.INCOME_STATEMENT.value,
                    ],
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_REVIEW.value,
                    to_status=SubmissionStatus.APPROVED_BY_MANAGER.value,
                    action=WorkflowAction.APPROVE.value,
                    allowed_roles=['FINANCE_MANAGER'],
                    conditions=['manager_review_complete', 'grap24_variance_explanations'],
                    document_types=[DocumentType.BUDGET_REPORT.value],
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_REVIEW.value,
                    to_status=SubmissionStatus.REJECTED_BY_MANAGER.value,
                    action=WorkflowAction.REJECT.value,
                    allowed_roles=['FINANCE_MANAGER'],
                    conditions=['rejection_reason'],
                    document_types=list(CFO_GATE_DOCUMENT_TYPES),
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_REVIEW.value,
                    to_status=SubmissionStatus.REJECTED.value,
                    action=WorkflowAction.REJECT.value,
                    allowed_roles=['CFO'],
                    conditions=['rejection_reason'],
                    document_types=list(CFO_GATE_DOCUMENT_TYPES),
                ),
            ],
            SubmissionStatus.APPROVED_BY_MANAGER.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.APPROVED_BY_MANAGER.value,
                    to_status=SubmissionStatus.APPROVED.value,
                    action=WorkflowAction.APPROVE.value,
                    allowed_roles=['CFO'],
                    conditions=[
                        'manager_review_complete',
                        'manager_approved',
                        'grap_statement_compliance',
                    ],
                    document_types=[
                        DocumentType.BALANCE_SHEET.value,
                        DocumentType.INCOME_STATEMENT.value,
                    ],
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.APPROVED_BY_MANAGER.value,
                    to_status=SubmissionStatus.APPROVED.value,
                    action=WorkflowAction.APPROVE.value,
                    allowed_roles=['CFO'],
                    conditions=[
                        'manager_review_complete',
                        'manager_approved',
                        'grap24_variance_explanations',
                    ],
                    document_types=[DocumentType.BUDGET_REPORT.value],
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.APPROVED_BY_MANAGER.value,
                    to_status=SubmissionStatus.REJECTED.value,
                    action=WorkflowAction.REJECT.value,
                    allowed_roles=['CFO'],
                    conditions=['rejection_reason'],
                    document_types=list(CFO_GATE_DOCUMENT_TYPES),
                ),
            ],
            SubmissionStatus.PENDING_CFO.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_CFO.value,
                    to_status=SubmissionStatus.APPROVED.value,
                    action=WorkflowAction.APPROVE.value,
                    allowed_roles=['CFO'],
                    conditions=[
                        'manager_review_complete',
                        'manager_approved',
                        'grap_statement_compliance',
                    ],
                    document_types=[
                        DocumentType.BALANCE_SHEET.value,
                        DocumentType.INCOME_STATEMENT.value,
                    ],
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_CFO.value,
                    to_status=SubmissionStatus.APPROVED.value,
                    action=WorkflowAction.APPROVE.value,
                    allowed_roles=['CFO'],
                    conditions=[
                        'manager_review_complete',
                        'manager_approved',
                        'grap24_variance_explanations',
                    ],
                    document_types=[DocumentType.BUDGET_REPORT.value],
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.PENDING_CFO.value,
                    to_status=SubmissionStatus.REJECTED.value,
                    action=WorkflowAction.REJECT.value,
                    allowed_roles=['CFO'],
                    conditions=['rejection_reason'],
                    document_types=list(CFO_GATE_DOCUMENT_TYPES),
                ),
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
            SubmissionStatus.REJECTED_BY_MANAGER.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.REJECTED_BY_MANAGER.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['rejection_addressed', 'valid_period', 'mapped_accounts'],
                    document_types=[DocumentType.BALANCE_SHEET.value, DocumentType.INCOME_STATEMENT.value]
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.REJECTED_BY_MANAGER.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['rejection_addressed', 'valid_period', 'mapped_accounts', 'grap24_variance_explanations'],
                    document_types=[DocumentType.BUDGET_REPORT.value]
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.REJECTED_BY_MANAGER.value,
                    to_status=SubmissionStatus.RESUBMITTED.value,
                    action=WorkflowAction.RESUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['rejection_addressed', 'valid_period'],
                    document_types=list(CFO_GATE_DOCUMENT_TYPES),
                ),
            ],
            SubmissionStatus.REJECTED_BY_CFO.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.REJECTED_BY_CFO.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['rejection_addressed', 'valid_period', 'mapped_accounts'],
                    document_types=[DocumentType.BALANCE_SHEET.value, DocumentType.INCOME_STATEMENT.value]
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.REJECTED_BY_CFO.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['rejection_addressed', 'valid_period', 'mapped_accounts', 'grap24_variance_explanations'],
                    document_types=[DocumentType.BUDGET_REPORT.value]
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.REJECTED_BY_CFO.value,
                    to_status=SubmissionStatus.RESUBMITTED.value,
                    action=WorkflowAction.RESUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['rejection_addressed', 'valid_period'],
                    document_types=list(CFO_GATE_DOCUMENT_TYPES),
                ),
            ],
            SubmissionStatus.RESUBMITTED.value: [
                WorkflowTransition(
                    from_status=SubmissionStatus.RESUBMITTED.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['valid_document_structure', 'mapped_accounts', 'valid_period'],
                    document_types=[DocumentType.BALANCE_SHEET.value, DocumentType.INCOME_STATEMENT.value]
                ),
                WorkflowTransition(
                    from_status=SubmissionStatus.RESUBMITTED.value,
                    to_status=SubmissionStatus.PENDING_REVIEW.value,
                    action=WorkflowAction.SUBMIT.value,
                    allowed_roles=['FINANCE_CLERK'],
                    conditions=['valid_document_structure', 'mapped_accounts', 'valid_period', 'grap24_variance_explanations'],
                    document_types=[DocumentType.BUDGET_REPORT.value]
                )
            ]
        }
        
        # Document-specific validation conditions
        self.document_conditions = {
            DocumentType.BALANCE_SHEET.value: {
                'valid_document_structure': self._validate_balance_sheet_structure,
                'mapped_accounts': self._check_balance_sheet_mapping,
                'valid_period': self._check_valid_period,
                'grap_statement_compliance': self._check_grap_statement_compliance,
                'manager_review_complete': self._manager_review_complete,
                'manager_approved': self._manager_approved,
                'rejection_reason': self._rejection_reason_condition,
                'rejection_addressed': self._rejection_addressed,
            },
            DocumentType.INCOME_STATEMENT.value: {
                'valid_document_structure': self._validate_income_statement_structure,
                'mapped_accounts': self._check_income_statement_mapping,
                'valid_period': self._check_valid_period,
                'grap_statement_compliance': self._check_grap_statement_compliance,
                'manager_review_complete': self._manager_review_complete,
                'manager_approved': self._manager_approved,
                'rejection_reason': self._rejection_reason_condition,
                'rejection_addressed': self._rejection_addressed,
            },
            DocumentType.BUDGET_REPORT.value: {
                'valid_document_structure': self._validate_budget_report_structure,
                'mapped_accounts': self._check_budget_report_mapping,
                'valid_period': self._check_valid_period,
                'grap24_variance_explanations': self._check_grap24_variance_explanations,
                'manager_review_complete': self._manager_review_complete,
                'manager_approved': self._manager_approved,
                'rejection_reason': self._rejection_reason_condition,
                'rejection_addressed': self._rejection_addressed,
            }
        }
    
    def submit_for_review(
        self,
        document_type: str,
        session_id: str,
        user_id: str,
        notes: str = "",
        mapped_data: List[Dict] = None,
        clerk_correction_note: str = "",
    ) -> Dict[str, Any]:
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
            
            if session.status in (
                SubmissionStatus.PENDING_REVIEW.value,
                SubmissionStatus.PENDING_CFO.value,
                SubmissionStatus.APPROVED_BY_MANAGER.value,
                SubmissionStatus.APPROVED.value,
            ):
                return {
                    'success': False,
                    'error': f'Document is already submitted or approved. Current status: {session.status}',
                }

            if session.status not in CLERK_SUBMIT_FROM_STATUSES:
                return {
                    'success': False,
                    'error': (
                        f'Document cannot be submitted in its current state. '
                        f'Current status: {session.status}'
                    ),
                }

            from utils.period_lock import check_session_period_unlocked
            allowed, lock_err = check_session_period_unlocked(session)
            if not allowed:
                return {'success': False, 'error': lock_err}

            prior_status = session.status
            correction_note = (clerk_correction_note or notes or '').strip()
            from utils.session_workflow import CLERK_ACTIONABLE_REJECTION_STATUSES

            if prior_status in CLERK_ACTIONABLE_REJECTION_STATUSES:
                if not correction_note:
                    return {
                        'success': False,
                        'error': 'A mandatory clerk correction note is required before resubmitting.',
                    }
                if str(session.user_id) != str(user_id):
                    return {
                        'success': False,
                        'error': 'Only the submitting clerk can resubmit this correction.',
                    }

            # Validate user role
            user_data = supabase_auth.get_user_by_id(user_id)
            if not user_data:
                return {
                    'success': False,
                    'error': 'User not found'
                }

            workflow_from_status = WORKFLOW_STATUS_ALIASES.get(
                session.status, session.status
            )

            if session.metadata is None:
                session.metadata = {}

            # Persist clerk mapping payload before workflow checks
            if mapped_data:
                session.metadata["mapped_data"] = mapped_data
                session.metadata["mapped_accounts"] = mapped_data
                session.metadata["grap_mapping"] = True
                session.metadata["document_type"] = document_type
                session.metadata["total_mapped_accounts"] = len(mapped_data)

            if prior_status in CLERK_ACTIONABLE_REJECTION_STATUSES:
                session.metadata["clerk_correction_note"] = correction_note
                session.metadata["changes_made"] = correction_note

            # Check workflow transition
            transition = self._get_workflow_transition(
                workflow_from_status,
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
                messages = []
                for key in condition_results.get("failed_conditions") or []:
                    cr = (condition_results.get("condition_results") or {}).get(key) or {}
                    if cr.get("message"):
                        messages.append(str(cr["message"]))
                detail = "; ".join(messages) if messages else ", ".join(
                    condition_results.get("failed_conditions") or []
                )
                return {
                    'success': False,
                    'error': f'Workflow conditions not met: {detail}',
                }
            
            # Update session status (DB column aliased via balance_sheet_models; workflow in metadata)
            session.status = SubmissionStatus.PENDING_REVIEW.value
            session.updated_at = datetime.now()
            if session.metadata is None:
                session.metadata = {}
            session.metadata = mark_session_committed_metadata(session.metadata)
            session.metadata['workflow_status'] = SubmissionStatus.PENDING_REVIEW.value
            session.metadata['submitted_at'] = datetime.now().isoformat()
            session.metadata['submitted_by'] = user_id
            session.metadata['submission_notes'] = notes
            if prior_status in CLERK_ACTIONABLE_REJECTION_STATUSES:
                from services.workflow_timeline_service import append_timeline_event

                session.metadata.pop('rejection_reason', None)
                mapped_count = len(mapped_data) if mapped_data else session.metadata.get('total_mapped_accounts', 0)
                res_hist = session.metadata.get('resubmission_history')
                if not isinstance(res_hist, list):
                    res_hist = []
                res_entry = {
                    'at': datetime.now().isoformat(),
                    'by': user_id,
                    'clerk_correction_note': correction_note,
                    'prior_status': prior_status,
                    'mapped_accounts_count': mapped_count,
                    'changes_summary': f'Resubmitted with {mapped_count} mapped account(s) after correction.',
                }
                res_hist.append(res_entry)
                session.metadata['resubmission_history'] = res_hist[-50:]
                session.metadata['clerk_correction_note'] = correction_note
                session.metadata['last_resubmitted_at'] = res_entry['at']
                session.metadata['last_resubmitted_by'] = user_id
                append_timeline_event(
                    session.metadata,
                    {
                        'type': 'clerk_resubmission',
                        'at': res_entry['at'],
                        'label': 'Clerk correction and resubmission',
                        'detail': correction_note,
                        'changes_summary': res_entry['changes_summary'],
                        'actor_id': user_id,
                    },
                )
            elif not session.metadata.get('first_submitted_at'):
                from services.workflow_timeline_service import append_timeline_event

                session.metadata['first_submitted_at'] = session.metadata['submitted_at']
                append_timeline_event(
                    session.metadata,
                    {
                        'type': 'clerk_submission',
                        'at': session.metadata['submitted_at'],
                        'label': 'Clerk original submission',
                        'detail': (notes or '').strip() or None,
                        'actor_id': user_id,
                    },
                )
            if not isinstance(session.processing_log, list):
                session.processing_log = list(session.processing_log or [])
            log_msg = (
                f"Resubmitted after rejection by {user_data.get('email', user_id)} at {datetime.now()}. "
                f"Note: {correction_note[:500]}"
                if prior_status in CLERK_ACTIONABLE_REJECTION_STATUSES
                else f"Submitted for review by {user_data.get('email', user_id)} at {datetime.now()}"
            )
            session.processing_log.append(log_msg)
            
            # Store mapped data if provided
            if mapped_data:
                session.metadata['mapped_data'] = mapped_data
                session.metadata['mapping_completed_at'] = datetime.now().isoformat()
                session.metadata['total_mapped_accounts'] = len(mapped_data)
                if not isinstance(session.processing_log, list):
                    session.processing_log = list(session.processing_log or [])
                session.processing_log.append(f"Stored {len(mapped_data)} mapped accounts")
            
            # Save updated session
            updated_session = model.update_session(session)
            
            # Create workflow record
            workflow_record = self._create_workflow_record(
                document_type, session_id, user_id,
                prior_status,
                SubmissionStatus.PENDING_REVIEW.value,
                WorkflowAction.SUBMIT.value,
                notes
            )
            
            # Create audit trail record for submission
            try:
                from models.audit_models import AuditTrailModel
                audit_model = AuditTrailModel()
                
                # Create a readable transaction ID for the audit trail
                transaction_id = f"{document_type.upper()[:3]}-{session_id[-8:].upper()}"
                
                audit_model.log_transaction_creation(
                    transaction_id=transaction_id,
                    creator_id=user_id,
                    transaction_data={
                        'document_type': document_type,
                        'session_id': session_id,
                        'submitted_at': datetime.now().isoformat()
                    },
                    reason=f"Submitted {document_type} for review"
                )
                
                logger.info(f"✅ Created audit trail record for submission {transaction_id}")
                
            except Exception as audit_error:
                logger.warning(f"⚠️ Could not create audit trail record for submission: {audit_error}")
                # Don't fail the submission if audit creation fails
            
            try:
                from services.cleanup_service import CleanupService
                CleanupService().cleanup_user_ephemeral_sessions(
                    user_id, keep_session_id=session_id
                )
            except Exception as cleanup_err:
                logger.warning(f"Could not clean up other staging sessions: {cleanup_err}")

            try:
                from services.inbox_service import notify_submission_pending_review

                sent = notify_submission_pending_review(
                    session_id=session_id,
                    document_type=document_type,
                    submitter_id=user_id,
                    submitter_name=user_data.get("full_name") or "",
                )
                logger.info(
                    "FM inbox: %s notification(s) for %s session %s",
                    sent,
                    document_type,
                    session_id,
                )
            except Exception as notify_err:
                logger.warning(
                    "Could not send submission inbox notifications for %s: %s",
                    document_type,
                    notify_err,
                    exc_info=True,
                )

            try:
                from services.approval_rules_engine import get_approval_requirement_for_document

                req = get_approval_requirement_for_document(document_type)
                if session.metadata is None:
                    session.metadata = {}
                session.metadata["approval_requirements"] = {
                    "required_approvers": list(req.required_approvers),
                    "sla_hours": req.sla_hours,
                }
                model.update_session(session)
            except Exception as meta_err:
                logger.warning(
                    "Could not persist approval_requirements for %s: %s",
                    document_type,
                    meta_err,
                )

            logger.info(f"✅ {document_type} submitted for review successfully")
            
            from utils.grap_standards_scope import (
                standard_label_for_document,
                submit_success_message,
            )

            return {
                'success': True,
                'session_id': session_id,
                'submission_id': session_id,  # Use session_id as submission_id for compatibility
                'document_type': document_type,
                'new_status': SubmissionStatus.PENDING_REVIEW.value,
                'workflow_record': workflow_record,
                'grap_standard': standard_label_for_document(document_type),
                'message': submit_success_message(document_type),
            }

        except Exception as e:
            logger.error(f"❌ Error submitting {document_type} for review: {str(e)}")
            return {
                'success': False,
                'error': f'Error submitting {document_type} for review: {str(e)}'
            }
    
    def approve_document(self, document_type: str, session_id: str, user_id: str, notes: str = "") -> Dict[str, Any]:
        """Approve document - Finance Manager forwards to CFO or CFO final-approves."""
        try:
            logger.info(f"✅ Approving {document_type}: {session_id}")

            model = self._get_model_for_document_type(document_type)
            session = model.get_session(session_id) if model else None

            if not session:
                return {'success': False, 'error': 'Session not found'}

            user = supabase_auth.get_user_by_id(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}

            role = user.get('role')
            from utils.session_workflow import effective_workflow_status

            current = effective_workflow_status(session)

            if document_type not in CFO_GATE_DOCUMENT_TYPES:
                return {'success': False, 'error': f'Unsupported document type for approval workflow: {document_type}'}

            if current == SubmissionStatus.PENDING_REVIEW.value:
                if role != 'FINANCE_MANAGER':
                    return {
                        'success': False,
                        'error': 'Only the Finance Manager can approve at this stage (forwards submission to CFO)',
                    }
                transition = self._get_workflow_transition(
                    current, WorkflowAction.APPROVE.value, document_type, role
                )
                if not transition:
                    return {'success': False, 'error': 'Workflow transition not allowed'}
                cond = self._validate_workflow_conditions(document_type, session, transition.conditions)
                if not cond['all_passed']:
                    return {
                        'success': False,
                        'error': self._format_condition_failure(cond),
                        'failed_conditions': cond.get('failed_conditions'),
                        'condition_results': cond.get('condition_results'),
                    }
                new_status = SubmissionStatus.APPROVED_BY_MANAGER.value
                if session.metadata is None:
                    session.metadata = {}
                session.metadata['workflow_status'] = new_status
                session.status = self._db_status_for_workflow(document_type, new_status)
                session.updated_at = datetime.now()
                session.metadata['manager_approval'] = {
                    'at': datetime.now().isoformat(),
                    'by': user_id,
                    'notes': notes or '',
                }
                session.metadata['forwarded_to_cfo_at'] = datetime.now().isoformat()
                self._append_approval_signature(session.metadata, user_id, role)
                session.processing_log.append(
                    f"Approved by Finance Manager ({user.get('email', user_id)}) at {datetime.now()}"
                )
                model.update_session(session)
                workflow_record = self._create_workflow_record(
                    document_type, session_id, user_id,
                    SubmissionStatus.PENDING_REVIEW.value,
                    new_status,
                    WorkflowAction.APPROVE.value,
                    notes,
                )
                try:
                    from services.inbox_service import notify_forwarded_to_cfo

                    notify_forwarded_to_cfo(
                        session_id=session_id,
                        document_type=document_type,
                        manager_id=user_id,
                    )
                except Exception as notify_err:
                    logger.warning("Inbox notify CFO failed: %s", notify_err)
                return {
                    'success': True,
                    'session_id': session_id,
                    'document_type': document_type,
                    'new_status': new_status,
                    'workflow_record': workflow_record,
                    'approval_signatures': session.metadata.get('approval_signatures', []),
                    'approval_signature': session.metadata.get('approval_signatures', []),
                    'message': 'Submission approved by Finance Manager and forwarded to CFO',
                }

            if current in CFO_PENDING_STATUSES:
                if role != 'CFO':
                    return {'success': False, 'error': 'Only the CFO can final-approve at this stage'}
                transition = self._get_workflow_transition(
                    current, WorkflowAction.APPROVE.value, document_type, role
                )
                if not transition:
                    return {'success': False, 'error': 'Workflow transition not allowed'}
                cond = self._validate_workflow_conditions(document_type, session, transition.conditions)
                if not cond['all_passed']:
                    return {
                        'success': False,
                        'error': self._format_condition_failure(cond),
                        'failed_conditions': cond.get('failed_conditions'),
                        'condition_results': cond.get('condition_results'),
                    }

                from utils.period_lock import attach_period_to_session_metadata
                from utils.period_lock import find_period_id_for_finalization

                period_id = find_period_id_for_finalization(session)
                if not period_id:
                    return {
                        'success': False,
                        'error': (
                            'Cannot finalize: this submission is not linked to a reporting period. '
                            'Ensure a financial period was selected on upload, or ask your system '
                            'administrator to link the submission to an open reporting period.'
                        ),
                        'code': 'period_id_unresolved',
                    }

                try:
                    locked_period = self.period_service.lock_period(period_id, user_id)
                    locked_period_name = locked_period.name
                except Exception as lock_err:
                    logger.error(f"Failed to lock period {period_id} in database: {lock_err}")
                    return {
                        'success': False,
                        'error': (
                            'Cannot finalize: the reporting period could not be locked in the database. '
                            'Confirm Supabase CFO migrations are applied and SUPABASE_SECRET_KEY is configured, '
                            'then try again or contact your system administrator.'
                        ),
                        'code': 'period_lock_db_sync_failed',
                        'period_id': period_id,
                    }

                attach_period_to_session_metadata(session, period_id)

                new_status = SubmissionStatus.APPROVED.value
                session.status = new_status
                session.updated_at = datetime.now()
                if session.metadata is None:
                    session.metadata = {}
                session.metadata.pop('workflow_status', None)
                session.metadata['approved_at'] = datetime.now().isoformat()
                session.metadata['approved_by'] = user_id
                session.metadata['approval_notes'] = notes
                session.metadata['cfo_approval'] = {
                    'at': datetime.now().isoformat(),
                    'by': user_id,
                    'notes': notes or '',
                }
                self._append_approval_signature(session.metadata, user_id, role)
                session.processing_log.append(f"Final approved by CFO {user.get('email', user_id)} at {datetime.now()}")

                session.metadata['period_locked'] = True
                session.metadata['period_locked_at'] = datetime.now().isoformat()
                session.metadata['period_id'] = period_id
                session.metadata['period_lock_db_synced'] = True
                session.metadata['period_name'] = locked_period_name
                session.processing_log.append(
                    f"Reporting period locked: {locked_period_name or period_id} at {datetime.now()}"
                )

                model.update_session(session)
                workflow_record = self._create_workflow_record(
                    document_type, session_id, user_id,
                    current,
                    new_status,
                    WorkflowAction.APPROVE.value,
                    notes,
                )
                try:
                    from models.audit_models import AuditTrailModel

                    audit_model = AuditTrailModel()
                    transaction_id = f"{document_type.upper()[:3]}-{session_id[-8:].upper()}"
                    audit_model.log_transaction_approval(
                        transaction_id=transaction_id,
                        approver_id=user_id,
                        approval_reason=notes or f"CFO approved {document_type}",
                    )
                except Exception as audit_error:
                    logger.warning(f"Could not create audit trail for CFO approval: {audit_error}")

                try:
                    from services.inbox_service import notify_submitter_final_approval

                    submitter_id = (session.metadata or {}).get("submitted_by") or session.user_id
                    notify_submitter_final_approval(
                        submitter_id,
                        session_id=session_id,
                        document_type=document_type,
                        approver_id=user_id,
                    )
                except Exception as notify_err:
                    logger.warning("Inbox notify submitter failed: %s", notify_err)

                return {
                    'success': True,
                    'session_id': session_id,
                    'document_type': document_type,
                    'new_status': new_status,
                    'workflow_record': workflow_record,
                    'period_locked': True,
                    'period_name': locked_period_name,
                    'period_lock_db_synced': True,
                    'message': f'{document_type.replace("_", " ").title()} final approval completed',
                }

            return {
                'success': False,
                'error': f'Document cannot be approved in status: {current}',
            }

        except Exception as e:
            logger.error(f"❌ Error approving {document_type}: {str(e)}")
            return {'success': False, 'error': f'Error approving {document_type}: {str(e)}'}

    def reject_document(self, document_type: str, session_id: str, user_id: str, reason: str) -> Dict[str, Any]:
        """Reject document - Finance Manager from pending_review; CFO from pending_cfo or pending_review."""
        try:
            logger.info(f"❌ Rejecting {document_type}: {session_id}")

            model = self._get_model_for_document_type(document_type)
            session = model.get_session(session_id) if model else None

            if not session:
                return {'success': False, 'error': 'Session not found'}

            if not (reason or '').strip():
                return {'success': False, 'error': 'Rejection reason is required'}

            user = supabase_auth.get_user_by_id(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}

            role = user.get('role')
            from utils.session_workflow import effective_workflow_status

            current = effective_workflow_status(session)

            if document_type not in CFO_GATE_DOCUMENT_TYPES:
                return {'success': False, 'error': f'Unsupported document type: {document_type}'}

            new_status = SubmissionStatus.REJECTED.value
            if current == SubmissionStatus.PENDING_REVIEW.value:
                if role != 'FINANCE_MANAGER':
                    return {'success': False, 'error': 'Only the Finance Manager can reject at pending review'}
                new_status = SubmissionStatus.REJECTED_BY_MANAGER.value
            elif current in CFO_PENDING_STATUSES:
                if role != 'CFO':
                    return {'success': False, 'error': 'Only the CFO can reject a submission pending CFO approval'}
                new_status = SubmissionStatus.REJECTED_BY_CFO.value
            else:
                return {
                    'success': False,
                    'error': f'Document must be pending review or pending CFO to reject. Current: {current}',
                }

            transition = self._get_workflow_transition(
                current, WorkflowAction.REJECT.value, document_type, role
            )
            if not transition:
                return {'success': False, 'error': 'Workflow transition not allowed for rejection'}

            previous_status = current
            reason = (reason or '').strip()

            snapshot = self._capture_rejection_snapshot(session, document_type, previous_status)

            if session.metadata is None:
                session.metadata = {}
            # Per-account reviewer threads invalidated on any rejection return-to-clerk
            session.metadata.pop('line_item_comments', None)

            if previous_status in CFO_PENDING_STATUSES and new_status == SubmissionStatus.REJECTED.value:
                self._clear_forward_approvals_on_cfo_rejection(session.metadata)

            hist = session.metadata.get('rejection_history')
            if not isinstance(hist, list):
                hist = []
            hist.append({
                'at': datetime.now().isoformat(),
                'by': user_id,
                'reason': reason,
                'snapshot': snapshot,
                'new_status': new_status,
                'prior_status': previous_status,
                'rejector_role': role,
            })
            session.metadata['rejection_history'] = hist[-50:]

            from services.workflow_timeline_service import append_timeline_event

            reject_label = (
                'Rejected by Finance Manager'
                if new_status == SubmissionStatus.REJECTED_BY_MANAGER.value
                else 'Rejected by CFO' if role == 'CFO' else 'Submission rejected'
            )
            append_timeline_event(
                session.metadata,
                {
                    'type': 'rejection',
                    'at': datetime.now().isoformat(),
                    'label': reject_label,
                    'detail': reason,
                    'actor_id': user_id,
                    'actor_role': role,
                    'prior_status': previous_status,
                },
            )

            session.status = new_status
            session.updated_at = datetime.now()

            if new_status in (
                SubmissionStatus.REJECTED_BY_MANAGER.value,
                SubmissionStatus.REJECTED_BY_CFO.value,
            ):
                session.metadata['workflow_status'] = new_status
            else:
                session.metadata.pop('workflow_status', None)
            session.metadata['rejected_at'] = datetime.now().isoformat()
            session.metadata['rejected_by'] = user_id
            session.metadata['rejection_reason'] = reason
            session.metadata['rejection_snapshot'] = snapshot
            if new_status == SubmissionStatus.REJECTED_BY_MANAGER.value:
                session.metadata['manager_rejection'] = {
                    'at': datetime.now().isoformat(),
                    'by': user_id,
                    'reason': reason,
                }
            elif new_status == SubmissionStatus.REJECTED_BY_CFO.value:
                session.metadata['cfo_rejection'] = {
                    'at': datetime.now().isoformat(),
                    'by': user_id,
                    'reason': reason,
                }

            submitter_uid = getattr(session, 'user_id', None)
            if submitter_uid:
                session.metadata['last_rejection_target_user_id'] = str(submitter_uid)

            self._enqueue_clerk_rejection_alert(session.metadata, reason, user_id, new_status)

            session.processing_log.append(
                f"Rejected by {user.get('email', user_id)} at {datetime.now()}. Reason: {reason}"
            )

            model.update_session(session)

            workflow_record = self._create_workflow_record(
                document_type, session_id, user_id,
                previous_status,
                new_status,
                WorkflowAction.REJECT.value,
                reason,
            )

            try:
                from models.audit_models import AuditTrailModel

                transaction_id = f"{document_type.upper()[:3]}-{session_id[-8:].upper()}"
                audit_model = AuditTrailModel()
                audit_model.log_transaction_rejection(
                    transaction_id=transaction_id,
                    rejecter_id=user_id,
                    rejection_data={
                        'session_id': session_id,
                        'document_type': document_type,
                        'reason': reason,
                        'prior_status': previous_status,
                        'new_status': new_status,
                        'snapshot': snapshot,
                        'rejector_role': role,
                        'workflow_record_id': workflow_record.get('id'),
                    },
                )
            except Exception as audit_error:
                logger.warning(f'Could not create audit rejection record: {audit_error}')

            try:
                from services.inbox_service import notify_submitter_of_rejection

                notify_submitter_of_rejection(
                    str(submitter_uid) if submitter_uid else None,
                    session_id=session_id,
                    document_type=document_type,
                    reason=reason,
                    rejector_id=user_id,
                    new_status=new_status,
                )
            except Exception as inbox_err:
                logger.warning("Could not create inbox rejection notification: %s", inbox_err)

            return {
                'success': True,
                'session_id': session_id,
                'document_type': document_type,
                'new_status': new_status,
                'workflow_record': workflow_record,
                'message': (
                    'Submission rejected by Finance Manager — returned to clerk for correction'
                    if new_status == SubmissionStatus.REJECTED_BY_MANAGER.value
                    else f'{document_type.replace("_", " ").title()} rejected successfully'
                ),
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
    
    def process_approval(self, session_id: str, user_id: str, action: str, reason: str = '') -> Dict[str, Any]:
        """Process approval or rejection using the same rules as approve_document / reject_document."""
        try:
            session = None
            document_type = None

            for doc_type in [dt.value for dt in DocumentType]:
                temp_model = self._get_model_for_document_type(doc_type)
                if temp_model:
                    temp_session = temp_model.get_session(session_id)
                    if temp_session:
                        session = temp_session
                        document_type = doc_type
                        break

            if not session:
                return {'success': False, 'error': f'Session {session_id} not found'}

            user_data = supabase_auth.get_user_by_id(user_id)
            if not user_data:
                return {'success': False, 'error': 'User not found'}

            if user_data.get('role') not in ['FINANCE_MANAGER', 'CFO']:
                return {'success': False, 'error': 'User does not have approval permissions'}

            if action == 'approve':
                result = self.approve_document(document_type, session_id, user_id, reason or '')
                if not result.get('success'):
                    return result
                return {
                    'success': True,
                    'message': result.get('message', 'Document approved successfully'),
                    'session_id': session_id,
                    'document_type': document_type,
                    'status': result.get('new_status', session.status),
                }

            if action == 'reject':
                result = self.reject_document(document_type, session_id, user_id, reason or '')
                if not result.get('success'):
                    return result
                return {
                    'success': True,
                    'message': result.get('message', 'Document rejected successfully'),
                    'session_id': session_id,
                    'document_type': document_type,
                    'status': SubmissionStatus.REJECTED.value,
                }

            return {'success': False, 'error': f'Invalid action: {action}'}

        except Exception as e:
            logger.error(f"❌ Error processing approval: {str(e)}")
            return {'success': False, 'error': f'Error processing approval: {str(e)}'}
    
    def get_pending_approvals(
        self,
        user_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Pending queue from **upload sessions** by effective workflow status.

        Finance Manager sees ``pending_review``; CFO sees ``pending_cfo`` and
        ``approved_by_manager``. Scans balance sheet, income statement, and budget
        tables so no document type is dropped when another type has many recent rows.
        """
        try:
            user = supabase_auth.get_user_by_id(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}

            if user.get('role') not in ['FINANCE_MANAGER', 'CFO']:
                return {'success': False, 'error': 'User does not have approval permissions'}

            role = user.get('role')
            safe_limit = max(1, min(int(limit or 50), 200))
            safe_offset = max(0, int(offset or 0))

            if role == 'FINANCE_MANAGER':
                want_statuses = frozenset({SubmissionStatus.PENDING_REVIEW.value})
            else:
                want_statuses = CFO_PENDING_STATUSES

            from utils.session_workflow import (
                effective_workflow_status,
                session_submitted_for_review,
            )

            pending_approvals: List[Dict[str, Any]] = []
            seen_ids: set = set()
            fetch_cap = max(safe_limit * 15, 500)

            for doc_type in (
                DocumentType.BALANCE_SHEET.value,
                DocumentType.INCOME_STATEMENT.value,
                DocumentType.BUDGET_REPORT.value,
            ):
                model = self._get_model_for_document_type(doc_type)
                if not model or not getattr(model, 'client', None):
                    continue

                table = getattr(model, 'table_name', None)
                if not table and doc_type == DocumentType.BALANCE_SHEET.value:
                    table = 'balance_sheet_sessions'
                if not table:
                    continue

                try:
                    result = (
                        model.client.table(table)
                        .select('*')
                        .order('updated_at', desc=True)
                        .limit(fetch_cap)
                        .execute()
                    )
                except Exception as exc:
                    logger.warning('Pending queue fetch failed for %s: %s', doc_type, exc)
                    continue

                for raw in result.data or []:
                    try:
                        if doc_type == DocumentType.BALANCE_SHEET.value:
                            from models.balance_sheet_models import _balance_sheet_session_from_row

                            session = _balance_sheet_session_from_row(raw)
                        elif doc_type == DocumentType.INCOME_STATEMENT.value:
                            from models.income_statement_models import income_statement_session_from_row

                            session = income_statement_session_from_row(raw)
                        else:
                            from models.budget_report_models import budget_report_session_from_row

                            session = budget_report_session_from_row(raw)
                    except Exception:
                        continue

                    sid = getattr(session, 'id', None)
                    if not sid or sid in seen_ids:
                        continue
                    if not session_submitted_for_review(session):
                        continue

                    eff = effective_workflow_status(session)
                    if eff not in want_statuses:
                        continue

                    seen_ids.add(sid)
                    submitted_by_id = session.user_id
                    submitted_by_user = supabase_auth.get_user_by_id(submitted_by_id)
                    submitted_by_name = (
                        submitted_by_user.get('full_name', 'Unknown User')
                        if submitted_by_user
                        else 'Unknown User'
                    )

                    created_raw = getattr(session, 'created_at', None)
                    if hasattr(created_raw, 'isoformat'):
                        created_at = created_raw.isoformat()
                    elif created_raw:
                        created_at = str(created_raw)
                    else:
                        created_at = ''

                    md = session.metadata or {}
                    pending_approvals.append({
                        'session_id': session.id,
                        'document_type': getattr(session, 'document_type', None) or doc_type,
                        'filename': session.filename,
                        'status': eff,
                        'user_id': session.user_id,
                        'submitted_by': submitted_by_name,
                        'submitted_by_id': submitted_by_id,
                        'submitted_at': md.get('submitted_at', ''),
                        'created_at': created_at,
                        'total_rows': session.total_rows,
                        'total_columns': session.total_columns,
                        'period_name': md.get('period_name') or md.get('period') or md.get('reporting_period'),
                        'metadata': md,
                    })

            pending_approvals.sort(key=lambda x: x['submitted_at'] or x['created_at'])
            total = len(pending_approvals)
            page = pending_approvals[safe_offset : safe_offset + safe_limit]

            return {
                'success': True,
                'pending_approvals': page,
                'total_count': total,
                'limit': safe_limit,
                'offset': safe_offset,
                'has_more': safe_offset + safe_limit < total,
            }

        except Exception as e:
            logger.error(f"❌ Error getting pending approvals: {str(e)}")
            return {'success': False, 'error': f'Error getting pending approvals: {str(e)}'}
    
    @staticmethod
    def _append_approval_signature(metadata: Dict[str, Any], user_id: str, role: str) -> None:
        """Append approver user id to metadata approval_signatures (audit trail)."""
        signatures = metadata.get('approval_signatures')
        if not isinstance(signatures, list):
            signatures = []
        entry = {
            'user_id': user_id,
            'role': role,
            'at': datetime.now().isoformat(),
        }
        if not any(
            s.get('user_id') == user_id and s.get('role') == role for s in signatures if isinstance(s, dict)
        ):
            signatures.append(entry)
        metadata['approval_signatures'] = signatures

    def _capture_rejection_snapshot(
        self, session, document_type: str, previous_status: str
    ) -> Dict[str, Any]:
        """Point-in-time snapshot for audit / integrity (keep payload bounded)."""
        md = getattr(session, 'metadata', None) or {}
        unmapped_ct = 0
        rows_sampled = 0
        gm = md.get('grap_mapping')
        if isinstance(gm, dict):
            mdata = gm.get('mapping_data')
            if isinstance(mdata, list):
                rows_sampled = min(len(mdata), 500)
                for row in mdata[:500]:
                    if not isinstance(row, dict):
                        continue
                    gc = row.get('grap_code') or row.get('mapped_to_grap')
                    if row.get('mapping_status') == 'unmapped' or not (gc and str(gc).strip()):
                        unmapped_ct += 1
        return {
            'captured_at': datetime.now().isoformat(),
            'document_type': document_type,
            'session_id': getattr(session, 'id', None),
            'status_before_rejection': previous_status,
            'filename': getattr(session, 'filename', None) or getattr(session, 'original_filename', None),
            'estimated_unmapped_accounts': unmapped_ct,
            'mapping_rows_sampled': rows_sampled,
            'total_upload_rows': getattr(session, 'total_rows', None),
            'mapped_accounts_count': md.get('mapped_accounts_count') or md.get('mapped_accounts'),
        }

    @staticmethod
    def _clear_forward_approvals_on_cfo_rejection(metadata: Dict[str, Any]) -> None:
        """
        CFO rejection must reset prior manager/CFO forward markers so the clerk
        resubmission cannot inherit stale signatures.
        """
        for key in (
            'manager_approval',
            'forwarded_to_cfo_at',
            'cfo_approval',
            'approval_signatures',
            'approved_at',
            'approved_by',
            'approval_notes',
            'workflow_status',
        ):
            metadata.pop(key, None)

    @staticmethod
    def _enqueue_clerk_rejection_alert(
        metadata: Dict[str, Any], reason: str, rejector_id: str, new_status: str
    ) -> None:
        alerts = metadata.get('pending_clerk_alerts')
        if not isinstance(alerts, list):
            alerts = []
        alerts.append(
            {
                'type': 'rejection',
                'severity': 'high',
                'at': datetime.now().isoformat(),
                'rejector_id': rejector_id,
                'summary': (reason or '')[:2000],
                'new_status': new_status,
            }
        )
        metadata['pending_clerk_alerts'] = alerts[-25:]

    def collect_settled_history_sessions(
        self,
        statuses: List[str],
        *,
        limit: int = 100,
        user_filter: str = '',
    ) -> List[Dict[str, Any]]:
        """
        FM/CFO history: match by effective workflow status (metadata) as well as DB status.
        Budget and income tables often store workflow in metadata while status stays mapped/validated.
        """
        from datetime import timezone
        from utils.session_workflow import (
            effective_workflow_status,
            parse_iso_datetime,
            session_matches_settled_status,
        )

        want = [str(s).strip().lower() for s in statuses if str(s).strip()]
        if not want:
            return []

        rows_out: List[Dict[str, Any]] = []
        seen_ids: set = set()
        fetch_cap = max(limit * 8, 200)

        for doc_type in (
            DocumentType.BALANCE_SHEET.value,
            DocumentType.INCOME_STATEMENT.value,
            DocumentType.BUDGET_REPORT.value,
        ):
            model = self._get_model_for_document_type(doc_type)
            if not model or not getattr(model, 'client', None):
                continue

            table = getattr(model, 'table_name', None)
            if not table and doc_type == DocumentType.BALANCE_SHEET.value:
                table = 'balance_sheet_sessions'
            if not table:
                continue

            try:
                result = (
                    model.client.table(table)
                    .select('*')
                    .order('updated_at', desc=True)
                    .limit(fetch_cap)
                    .execute()
                )
            except Exception as exc:
                logger.warning('History fetch failed for %s: %s', doc_type, exc)
                continue

            for raw in result.data or []:
                try:
                    if doc_type == DocumentType.BALANCE_SHEET.value:
                        from models.balance_sheet_models import _balance_sheet_session_from_row

                        session = _balance_sheet_session_from_row(raw)
                    elif doc_type == DocumentType.INCOME_STATEMENT.value:
                        session = self._income_session_from_row(raw)
                    else:
                        session = self._budget_session_from_row(raw)
                except Exception:
                    continue

                sid = getattr(session, 'id', None)
                if not sid or sid in seen_ids:
                    continue
                if user_filter and str(getattr(session, 'user_id', '')) != str(user_filter):
                    continue

                if not any(session_matches_settled_status(session, s) for s in want):
                    continue

                seen_ids.add(sid)
                eff = effective_workflow_status(session)
                rows_out.append({
                    'session': session,
                    'document_type': doc_type,
                    'display_status': eff or getattr(session, 'status', ''),
                })
                if len(rows_out) >= limit:
                    break
            if len(rows_out) >= limit:
                break

        _epoch = datetime.min.replace(tzinfo=timezone.utc)

        def _history_ts(sess: Any) -> datetime:
            ts = parse_iso_datetime(getattr(sess, 'updated_at', None)) or parse_iso_datetime(
                getattr(sess, 'created_at', None)
            )
            return ts or _epoch

        rows_out.sort(key=lambda r: _history_ts(r['session']), reverse=True)
        return rows_out[:limit]

    @staticmethod
    def _income_session_from_row(session_data: Dict[str, Any]):
        from decimal import Decimal
        from models.income_statement_models import IncomeStatementSession

        return IncomeStatementSession(
            id=session_data['id'],
            user_id=session_data['user_id'],
            document_type=session_data.get('document_type', 'income_statement'),
            filename=session_data.get('filename', ''),
            original_filename=session_data.get('original_filename', ''),
            file_type=session_data.get('file_type', 'unknown'),
            file_format=session_data.get('file_format', 'unknown'),
            status=session_data.get('status', 'draft'),
            total_rows=session_data.get('total_rows', 0),
            total_columns=session_data.get('total_columns', 0),
            file_size_bytes=session_data.get('file_size_bytes', 0),
            checksum_md5=session_data.get('checksum_md5', ''),
            created_at=session_data.get('created_at'),
            updated_at=session_data.get('updated_at'),
            processed_at=session_data.get('processed_at'),
            metadata=session_data.get('metadata') or {},
            processing_log=session_data.get('processing_log') or [],
            validation_results=session_data.get('validation_results') or {},
            total_revenue=Decimal(str(session_data.get('total_revenue', '0.00'))),
            total_expenses=Decimal(str(session_data.get('total_expenses', '0.00'))),
            net_income=Decimal(str(session_data.get('net_income', '0.00'))),
            gross_profit=Decimal(str(session_data.get('gross_profit', '0.00'))),
            operating_income=Decimal(str(session_data.get('operating_income', '0.00'))),
            fiscal_year=session_data.get('fiscal_year', 0),
            reporting_period=session_data.get('reporting_period', ''),
            statement_type=session_data.get('statement_type', 'monthly'),
        )

    @staticmethod
    def _budget_session_from_row(session_data: Dict[str, Any]):
        from decimal import Decimal
        from models.budget_report_models import BudgetReportSession

        return BudgetReportSession(
            id=session_data['id'],
            user_id=session_data['user_id'],
            document_type=session_data.get('document_type', 'budget_report'),
            filename=session_data.get('filename', ''),
            original_filename=session_data.get('original_filename', ''),
            file_type=session_data.get('file_type', 'unknown'),
            file_format=session_data.get('file_format', 'unknown'),
            status=session_data.get('status', 'draft'),
            total_rows=session_data.get('total_rows', 0),
            total_columns=session_data.get('total_columns', 0),
            file_size_bytes=session_data.get('file_size_bytes', 0),
            checksum_md5=session_data.get('checksum_md5', ''),
            created_at=session_data.get('created_at'),
            updated_at=session_data.get('updated_at'),
            processed_at=session_data.get('processed_at'),
            metadata=session_data.get('metadata') or {},
            processing_log=session_data.get('processing_log') or [],
            validation_results=session_data.get('validation_results') or {},
            total_budget=Decimal(str(session_data.get('total_budget', '0.00'))),
            total_actual=Decimal(str(session_data.get('total_actual', '0.00'))),
            total_variance=Decimal(str(session_data.get('total_variance', '0.00'))),
            variance_percentage=Decimal(str(session_data.get('variance_percentage', '0.00'))),
            fiscal_year=session_data.get('fiscal_year', 0),
            budget_type=session_data.get('budget_type', ''),
            department=session_data.get('department', ''),
            reporting_period=session_data.get('reporting_period', ''),
        )

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

    @staticmethod
    def _db_status_for_workflow(document_type: str, workflow_status: str) -> str:
        """Map app workflow labels to DB-safe status values per document table."""
        if document_type == DocumentType.BALANCE_SHEET.value:
            from models.balance_sheet_models import _normalize_balance_sheet_session_status_for_db

            return _normalize_balance_sheet_session_status_for_db(workflow_status)

        aliases = {
            SubmissionStatus.PENDING_REVIEW.value: 'mapped',
            SubmissionStatus.PENDING_CFO.value: 'validated',
            SubmissionStatus.APPROVED_BY_MANAGER.value: 'validated',
            SubmissionStatus.REJECTED_BY_MANAGER.value: 'rejected',
            SubmissionStatus.REJECTED_BY_CFO.value: 'rejected',
            SubmissionStatus.APPROVED.value: 'approved',
            SubmissionStatus.REJECTED.value: 'rejected',
            SubmissionStatus.RESUBMITTED.value: 'uploaded',
        }
        if workflow_status in (
            'uploaded',
            'processing',
            'mapped',
            'validated',
            'approved',
            'rejected',
            'archived',
            'draft',
        ):
            return workflow_status
        return aliases.get(workflow_status, 'validated')
    
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

    @staticmethod
    def _format_condition_failure(cond: Dict[str, Any]) -> str:
        messages = []
        for key in cond.get('failed_conditions') or []:
            cr = (cond.get('condition_results') or {}).get(key) or {}
            if cr.get('message'):
                messages.append(str(cr['message']))
        if messages:
            return '; '.join(messages)
        failed = cond.get('failed_conditions') or []
        return f'Workflow conditions not met: {failed}'

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
        """GRAP 1 SFP: structure, mapping, and accounting equation."""
        return self._grap_compliance_result(session, DocumentType.BALANCE_SHEET.value)

    def _validate_income_statement_structure(self, session) -> Dict[str, Any]:
        """GRAP 1 performance: structure, mapping, revenue/expense totals."""
        return self._grap_compliance_result(session, DocumentType.INCOME_STATEMENT.value)

    def _grap_compliance_result(self, session, document_type: str) -> Dict[str, Any]:
        from services.grap_compliance_service import run_session_grap_compliance

        out = run_session_grap_compliance(session, document_type)
        if out.get("report") and session.metadata is not None:
            session.metadata["validation_result"] = out["report"]
            session.metadata["grap_compliance_report"] = out["report"]
        return {
            "passed": out.get("passed", False),
            "message": out.get("message"),
        }

    def _check_grap_statement_compliance(self, session) -> Dict[str, Any]:
        """Balance sheet / income statement GRAP 1 checks (not GRAP 24)."""
        from utils.period_lock import infer_document_type_from_session

        doc_type = (session.metadata or {}).get("document_type")
        if not doc_type:
            doc_type = infer_document_type_from_session(getattr(session, "id", "") or "")
        if not doc_type:
            return {"passed": False, "message": "Could not determine document type for GRAP compliance"}
        from utils.grap_standards_scope import statement_compliance_applies_to

        if not statement_compliance_applies_to(doc_type):
            return {"passed": True}
        return self._grap_compliance_result(session, doc_type)
    
    def _validate_budget_report_structure(self, session) -> Dict[str, Any]:
        """Validate budget report structure"""
        validation_result = session.metadata.get('validation_result', {})
        # If no validation result, assume valid for existing sessions
        if not validation_result:
            return {'passed': True}
        return {'passed': validation_result.get('valid', False)}
    
    def _check_balance_sheet_mapping(self, session) -> Dict[str, Any]:
        """Check if balance sheet has GRAP mapping"""
        md = session.metadata or {}
        has_mapping = bool(
            md.get("grap_mapping")
            or md.get("mapped_data")
            or md.get("mapped_accounts")
        )
        return {
            'passed': has_mapping,
            'message': None if has_mapping else 'Complete GRAP account mapping before submitting',
        }
    
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

    def _manager_review_complete(self, session) -> Dict[str, Any]:
        """Gate for approve transitions; extend with business rules if needed."""
        return {'passed': True}

    def _manager_approved(self, session) -> Dict[str, Any]:
        """CFO final approve requires prior Finance Manager approval."""
        from utils.session_workflow import effective_workflow_status

        md = session.metadata or {}
        manager = md.get('manager_approval') or {}
        eff = effective_workflow_status(session)
        in_cfo_queue = eff in CFO_PENDING_STATUSES
        passed = bool(manager.get('at')) and in_cfo_queue
        return {
            'passed': passed,
            'message': None if passed else 'Finance Manager approval is required before CFO finalization',
        }

    def _rejection_reason_condition(self, session) -> Dict[str, Any]:
        """Rejection reason is validated on the request path; condition always passes here."""
        return {'passed': True}

    def _rejection_addressed(self, session) -> Dict[str, Any]:
        """Resubmit from rejected state requires a clerk correction note on the request."""
        md = session.metadata or {}
        from utils.session_workflow import CLERK_ACTIONABLE_REJECTION_STATUSES, effective_workflow_status

        st = effective_workflow_status(session)
        if st not in CLERK_ACTIONABLE_REJECTION_STATUSES:
            return {'passed': True}
        note = (md.get('clerk_correction_note') or md.get('changes_made') or '').strip()
        if note:
            return {'passed': True}
        if isinstance(md.get('resubmission_history'), list) and md['resubmission_history']:
            last = md['resubmission_history'][-1]
            if isinstance(last, dict) and (last.get('clerk_correction_note') or '').strip():
                return {'passed': True}
        return {
            'passed': False,
            'message': 'Enter a mandatory clerk correction note before resubmitting.',
        }

    def _check_valid_period(self, session) -> Dict[str, Any]:
        """Reject submit/resubmit when the linked reporting period is locked."""
        from utils.period_lock import check_session_period_unlocked
        allowed, message = check_session_period_unlocked(session)
        return {'passed': allowed, 'message': message or None}

    def _check_grap24_variance_explanations(self, session) -> Dict[str, Any]:
        """
        GRAP 24 (budget vs actual only): mandatory variance narrative when |variance/budget| > 10%.
        Not applicable to balance sheet or income statement — see utils.grap24_scope.
        """
        from utils.grap24_scope import grap24_applies_to

        doc_type = (session.metadata or {}).get("document_type")
        if doc_type and not grap24_applies_to(doc_type):
            return {"passed": True}

        from services.budget_variance_service import (
            get_variance_explanations_from_metadata,
            validate_variance_explanations,
        )
        from models.budget_report_models import budget_report_model

        rows_raw = budget_report_model.get_data_rows(session.id)
        budget_rows = []
        for r in rows_raw:
            budget_rows.append({
                'row_index': r.row_index,
                'account_code': r.account_code,
                'account_description': r.account_description,
                'budget_amount': float(r.budget_amount),
                'actual_amount': float(r.actual_amount),
                'variance': float(r.variance),
                'is_total_row': r.is_total_row,
                'is_subtotal_row': r.is_subtotal_row,
            })
        explanations = get_variance_explanations_from_metadata(session.metadata)
        passed, missing, _required = validate_variance_explanations(budget_rows, explanations)
        if passed:
            return {'passed': True}
        return {
            'passed': False,
            'message': (
                'GRAP 24: variance explanation required for line items exceeding 10%: '
                + ', '.join(missing[:8])
                + ('…' if len(missing) > 8 else '')
            ),
        }

    def batch_approve(
        self,
        items: List[Dict[str, str]],
        user_id: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Approve multiple sessions; continues on per-item failure."""
        results = []
        succeeded = 0
        for item in items or []:
            document_type = (item or {}).get("document_type")
            session_id = (item or {}).get("session_id")
            if not document_type or not session_id:
                results.append({
                    "session_id": session_id,
                    "document_type": document_type,
                    "success": False,
                    "error": "document_type and session_id required",
                })
                continue
            outcome = self.approve_document(
                document_type=document_type,
                session_id=session_id,
                user_id=user_id,
                notes=notes,
            )
            results.append({
                "session_id": session_id,
                "document_type": document_type,
                **outcome,
            })
            if outcome.get("success"):
                succeeded += 1
        total = len(results)
        return {
            "success": succeeded > 0 and succeeded == total,
            "partial": 0 < succeeded < total,
            "approved_count": succeeded,
            "total": total,
            "results": results,
        }


