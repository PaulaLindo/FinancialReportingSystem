"""
Unified import surface for **approval-related** backend operations.

Use one import in application code::

    from services.approval_facade import approval_facade

Then ``approval_facade.workflow`` (``ApprovalModel`` singleton) and
``approval_facade.transactions`` (``TransactionApprovalService`` singleton).
The facade lazy-loads dependencies to avoid import cycles.

**Attributes**

- ``workflow`` — ``ApprovalModel`` singleton (``models.approval_models``).  
  Step-based **document** approvals: tables ``approval_workflows``, ``approval_steps``,
  ``audit_logs``. Used heavily from ``controllers/routes.py``.

- ``transactions`` — ``TransactionApprovalService`` singleton.  
  **Transactional** four-eyes: ``transaction_approvals``, ``approval_actions``, views such
  as ``pending_approvals``. Use for TX-style approve/reject when there is no document
  ``session_id`` (e.g. universal ``/api/transaction/approve``).

**Not on this facade**

- ``UniversalWorkflowService.get_pending_approvals`` — builds the manager/CFO queue from
  **upload session** rows (balance sheet / income statement / budget) by status, not from
  ``transaction_approvals``. Import from ``services.universal_workflow_service`` when you
  need that behaviour (e.g. ``/api/transactions/pending``).
"""

from __future__ import annotations


class ApprovalFacade:
    """Lazy-loading façade over workflow and transactional approval services."""

    __slots__ = ("_workflow", "_transactions")

    def __init__(self) -> None:
        self._workflow = None
        self._transactions = None

    @property
    def workflow(self):
        """Step-based document approvals (``approval_workflows`` / ``approval_steps``)."""
        if self._workflow is None:
            from models.approval_models import approval_model

            self._workflow = approval_model
        return self._workflow

    @property
    def transactions(self):
        """Transactional approvals (``transaction_approvals`` / ``approval_actions``)."""
        if self._transactions is None:
            from services.transaction_approval_service import transaction_approval_service

            self._transactions = transaction_approval_service
        return self._transactions


approval_facade = ApprovalFacade()
