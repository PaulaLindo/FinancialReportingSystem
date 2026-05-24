"""
Transactional approval stack (Supabase ``transaction_approvals``).

**Preferred entry from app code:** ``services.approval_facade.approval_facade.transactions``
(same ``TransactionApprovalService`` instance as ``transaction_approval_service`` below).

Use for TX-style flows: create/approve/reject/finalize rows backed by
``transaction_approvals`` and ``approval_actions``, and for reads from the
``pending_approvals`` / ``pending_approvals_by_user`` views.

**Not the same as:**

- ``models.approval_models.ApprovalModel`` — step-based **document** workflows
  (``approval_workflows``, ``approval_steps``, ``audit_logs``), used heavily from
  ``controllers/routes.py``.

- ``services.universal_workflow_service.UniversalWorkflowService.get_pending_approvals`` —
  builds a **session submission queue** (balance sheet / income statement / budget
  sessions by status). That powers ``/api/transactions/pending`` today; it does **not**
  query ``transaction_approvals``.

Routes that call ``/api/transaction/approve`` or ``/api/transaction/reject`` without a
``session_id`` should use ``approval_facade.transactions`` (this service) so transactional
approval I/O stays in one place.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class TransactionApprovalService:
    """Facade over ``SupabaseApprovalModel`` for transactional (TX_*) approvals."""

    def __init__(self) -> None:
        from models.supabase_approval_models import supabase_approval_model

        self._impl = supabase_approval_model

    def create_pending_transaction(
        self,
        creator_id: str,
        transaction_type: str,
        transaction_data: Dict,
        reason: str = "",
    ) -> Dict[str, Any]:
        return self._impl.create_pending_transaction(
            creator_id, transaction_type, transaction_data, reason
        )

    def approve_transaction(
        self,
        approver_id: str,
        transaction_id: str,
        approval_reason: str = "",
    ) -> Dict[str, Any]:
        return self._impl.approve_transaction(
            approver_id, transaction_id, approval_reason
        )

    def reject_transaction(
        self,
        rejecter_id: str,
        transaction_id: str,
        rejection_reason: str,
    ) -> Dict[str, Any]:
        return self._impl.reject_transaction(
            rejecter_id, transaction_id, rejection_reason
        )

    def finalize_transaction(
        self, finalizer_id: str, transaction_id: str
    ) -> Dict[str, Any]:
        return self._impl.finalize_transaction(finalizer_id, transaction_id)

    def get_pending_transactions(
        self, approver_role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return self._impl.get_pending_transactions(approver_role)

    def get_transaction_history(
        self, user_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return self._impl.get_transaction_history(user_id, status)

    def get_approval_statistics(self) -> Dict[str, Any]:
        return self._impl.get_approval_statistics()


transaction_approval_service = TransactionApprovalService()
