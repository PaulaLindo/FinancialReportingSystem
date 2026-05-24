"""
Role-Based Approval Rules Engine

Implements conditional approval routing based on:
- Amount thresholds
- Document types
- User roles and departments
- Approval SLAs
- Business rules

This ensures proper governance and the four-eyes principle.
"""

from typing import List, Optional, Dict, Tuple
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass

class ApprovalLevel(Enum):
    """Approval authority levels"""
    FINANCE_CLERK = 1
    FINANCE_MANAGER = 2
    CFO = 3
    BOARD = 4
    AUDITOR = 5

class DocumentType(Enum):
    """Financial document types requiring different approval levels"""
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    BUDGET_REPORT = "budget_report"
    FINANCIAL_STATEMENT = "financial_statement"
    TRIAL_BALANCE = "trial_balance"
    ASSET_REGISTER = "asset_register"
    BANK_RECONCILIATION = "bank_reconciliation"
    JOURNAL_ENTRY = "journal_entry"

@dataclass
class ApprovalRequirement:
    """Specifies approval requirements for a document"""
    required_approvers: List[str]  # List of roles required
    escalation_approver: Optional[str]  # Who approves if escalated
    sla_hours: int  # Time limit for approval (in hours)
    require_all_approvals: bool  # True if ALL approvers required
    allow_delegation: bool  # Can this approval be delegated?
    send_notification: bool  # Send notification on submission

@dataclass
class AmountThreshold:
    """Amount-based escalation threshold"""
    min_amount: float
    max_amount: Optional[float]  # None = no upper limit
    required_approver: str  # Role that must approve
    description: str

class ApprovalRulesEngine:
    """
    Centralized approval rules engine for determining workflow requirements
    """

    def __init__(self):
        self.rules = self._initialize_rules()
        self.thresholds = self._initialize_thresholds()
        self.escalation_rules = self._initialize_escalation_rules()

    def _initialize_rules(self) -> Dict[str, ApprovalRequirement]:
        """Initialize base approval rules by document type"""
        return {
            # Balance Sheet - Requires Finance Manager + CFO
            DocumentType.BALANCE_SHEET.value: ApprovalRequirement(
                required_approvers=["FINANCE_MANAGER", "CFO"],
                escalation_approver="CFO",
                sla_hours=24,
                require_all_approvals=True,
                allow_delegation=False,
                send_notification=True
            ),

            # Income Statement - Requires Finance Manager + CFO
            DocumentType.INCOME_STATEMENT.value: ApprovalRequirement(
                required_approvers=["FINANCE_MANAGER", "CFO"],
                escalation_approver="CFO",
                sla_hours=24,
                require_all_approvals=True,
                allow_delegation=False,
                send_notification=True
            ),

            # Budget Report - Requires Finance Manager only
            DocumentType.BUDGET_REPORT.value: ApprovalRequirement(
                required_approvers=["FINANCE_MANAGER"],
                escalation_approver="CFO",
                sla_hours=48,
                require_all_approvals=True,
                allow_delegation=True,
                send_notification=True
            ),

            # Financial Statement - Highest approval requirement
            DocumentType.FINANCIAL_STATEMENT.value: ApprovalRequirement(
                required_approvers=["FINANCE_MANAGER", "CFO", "AUDITOR"],
                escalation_approver="BOARD",
                sla_hours=72,
                require_all_approvals=True,
                allow_delegation=False,
                send_notification=True
            ),

            # Trial Balance - Finance Manager only
            DocumentType.TRIAL_BALANCE.value: ApprovalRequirement(
                required_approvers=["FINANCE_MANAGER"],
                escalation_approver="CFO",
                sla_hours=12,
                require_all_approvals=True,
                allow_delegation=True,
                send_notification=False
            ),

            # Asset Register - Finance Manager
            DocumentType.ASSET_REGISTER.value: ApprovalRequirement(
                required_approvers=["FINANCE_MANAGER"],
                escalation_approver="CFO",
                sla_hours=48,
                require_all_approvals=True,
                allow_delegation=True,
                send_notification=True
            ),

            # Bank Reconciliation - Finance Manager only
            DocumentType.BANK_RECONCILIATION.value: ApprovalRequirement(
                required_approvers=["FINANCE_MANAGER"],
                escalation_approver="CFO",
                sla_hours=24,
                require_all_approvals=True,
                allow_delegation=True,
                send_notification=False
            ),

            # Journal Entry - Depends on amount
            DocumentType.JOURNAL_ENTRY.value: ApprovalRequirement(
                required_approvers=["FINANCE_MANAGER"],
                escalation_approver="CFO",
                sla_hours=4,
                require_all_approvals=True,
                allow_delegation=True,
                send_notification=True
            ),
        }

    def _initialize_thresholds(self) -> Dict[str, List[AmountThreshold]]:
        """Initialize amount-based escalation thresholds"""
        return {
            DocumentType.JOURNAL_ENTRY.value: [
                AmountThreshold(0, 10000, "FINANCE_CLERK", "Standard journal entry"),
                AmountThreshold(10000, 50000, "FINANCE_MANAGER", "Elevated amount"),
                AmountThreshold(50000, 250000, "CFO", "High amount"),
                AmountThreshold(250000, None, "CFO", "Very high amount - CFO required"),
            ],
            DocumentType.BUDGET_REPORT.value: [
                AmountThreshold(0, 100000, "FINANCE_MANAGER", "Standard budget"),
                AmountThreshold(100000, 500000, "CFO", "Elevated budget"),
                AmountThreshold(500000, None, "CFO", "Major budget - CFO required"),
            ],
        }

    def _initialize_escalation_rules(self) -> Dict[str, Tuple[str, str]]:
        """Initialize escalation rules by amount range"""
        return {
            # Escalation: if standard approval takes > X hours, escalate to next level
            "sla_escalation": {
                "threshold_hours": 4,
                "escalate_to": "CFO"
            }
        }

    def get_approval_requirements(
        self,
        document_type: str,
        document_amount: Optional[float] = None,
        department: Optional[str] = None
    ) -> ApprovalRequirement:
        """
        Get approval requirements for a document

        Args:
            document_type: Type of financial document
            document_amount: Amount in document (for threshold-based rules)
            department: Department submitting document

        Returns:
            ApprovalRequirement with all required approvers and settings
        """
        # Get base rule for document type
        if document_type not in self.rules:
            # Default rule if not found
            return ApprovalRequirement(
                required_approvers=["FINANCE_MANAGER", "CFO"],
                escalation_approver="CFO",
                sla_hours=24,
                require_all_approvals=True,
                allow_delegation=False,
                send_notification=True
            )

        base_requirement = self.rules[document_type]

        # Apply amount-based escalation if applicable
        if document_amount is not None and document_type in self.thresholds:
            escalated_approvers = self._apply_amount_escalation(
                document_type, document_amount
            )
            if escalated_approvers:
                base_requirement.required_approvers = escalated_approvers

        return base_requirement

    def _apply_amount_escalation(
        self, document_type: str, amount: float
    ) -> Optional[List[str]]:
        """Apply amount-based escalation rules"""
        if document_type not in self.thresholds:
            return None

        thresholds = self.thresholds[document_type]
        for threshold in thresholds:
            if threshold.min_amount <= amount <= (threshold.max_amount or float('inf')):
                return [threshold.required_approver]

        return None

    def can_approve(
        self, approver_role: str, document_type: str, approval_requirement: ApprovalRequirement
    ) -> bool:
        """
        Check if a user with given role can approve this document

        Args:
            approver_role: Role of the approver
            document_type: Type of document
            approval_requirement: Required approvals

        Returns:
            True if user can approve
        """
        return approver_role in approval_requirement.required_approvers

    def get_approval_chain(
        self, document_type: str, document_amount: Optional[float] = None
    ) -> List[Dict]:
        """
        Get the full approval chain for a document

        Returns:
            List of approval steps with role and order
        """
        requirement = self.get_approval_requirements(document_type, document_amount)

        chain = []
        for i, approver in enumerate(requirement.required_approvers):
            chain.append({
                'step_order': i + 1,
                'required_role': approver,
                'step_name': f"{approver} Approval",
                'allow_delegation': requirement.allow_delegation,
                'sla_hours': requirement.sla_hours
            })

        return chain

    def check_sla_compliance(
        self, submission_time: datetime, approval_time: datetime, document_type: str
    ) -> Tuple[bool, int]:
        """
        Check if approval was within SLA

        Returns:
            (is_compliant, hours_elapsed)
        """
        requirement = self.get_approval_requirements(document_type)
        hours_elapsed = int((approval_time - submission_time).total_seconds() / 3600)
        is_compliant = hours_elapsed <= requirement.sla_hours

        return is_compliant, hours_elapsed

    def is_sla_breached(
        self, submission_time: datetime, document_type: str, threshold_pct: float = 0.8
    ) -> bool:
        """
        Check if SLA is at risk (e.g., at 80% of time limit)

        Args:
            submission_time: When document was submitted
            document_type: Type of document
            threshold_pct: Percentage of SLA elapsed before warning (0.0-1.0)

        Returns:
            True if SLA is at risk
        """
        requirement = self.get_approval_requirements(document_type)
        sla_deadline = submission_time + timedelta(hours=requirement.sla_hours)
        threshold_time = submission_time + timedelta(
            hours=requirement.sla_hours * threshold_pct
        )

        return datetime.now() > threshold_time and datetime.now() < sla_deadline

    def validate_approval_sequence(
        self, approver_role: str, previous_approvers: List[str], requirement: ApprovalRequirement
    ) -> Tuple[bool, str]:
        """
        Validate that approver sequence is correct

        Returns:
            (is_valid, message)
        """
        # Check if this approver is in the required list
        if approver_role not in requirement.required_approvers:
            return False, f"Role {approver_role} not authorized to approve"

        # Check if this approver has already approved
        if approver_role in previous_approvers:
            return False, f"Role {approver_role} has already approved this"

        return True, "Approval is valid"

    def get_delegation_options(
        self, approver_role: str, document_type: str
    ) -> List[str]:
        """
        Get list of roles that can receive delegated approval

        Args:
            approver_role: Role of approver wanting to delegate
            document_type: Type of document

        Returns:
            List of roles that can approve on behalf
        """
        requirement = self.get_approval_requirements(document_type)

        if not requirement.allow_delegation:
            return []

        # Can delegate to users in same role or higher
        delegation_map = {
            "FINANCE_CLERK": ["FINANCE_MANAGER", "CFO"],
            "FINANCE_MANAGER": ["CFO"],
            "CFO": [],
            "AUDITOR": ["CFO"],
        }

        return delegation_map.get(approver_role, [])

    def require_audit_trail_signoff(self, document_type: str) -> bool:
        """Check if document requires audit trail sign-off"""
        audit_required_types = [
            DocumentType.FINANCIAL_STATEMENT.value,
            DocumentType.BALANCE_SHEET.value,
            DocumentType.INCOME_STATEMENT.value,
        ]
        return document_type in audit_required_types

    def get_document_routing_department(
        self, document_type: str, department: Optional[str] = None
    ) -> str:
        """
        Determine which department should route this document

        Args:
            document_type: Type of document
            department: Submitting department

        Returns:
            Department code for routing
        """
        # Route all financial statements through Finance Dept
        return "FINANCE"

    def get_escalation_reason_if_needed(
        self, submitted_time: datetime, document_type: str
    ) -> Optional[str]:
        """
        Check if document should be escalated to higher authority

        Returns:
            Reason for escalation, or None
        """
        if self.is_sla_breached(submitted_time, document_type, threshold_pct=0.9):
            return "SLA breach - document pending > 90% of allowed time"

        return None

    def get_approval_statistics_by_role(self, user_role: str) -> Dict:
        """Get approval statistics for a specific role"""
        return {
            "role": user_role,
            "approver_level": self._get_approver_level(user_role),
            "can_approve_documents": self._get_approvable_documents(user_role),
            "delegation_available": len(self.get_delegation_options(user_role, "")) > 0,
            "audit_authority": user_role in ["CFO", "AUDITOR"]
        }

    def _get_approver_level(self, role: str) -> int:
        """Get numeric approval level for role"""
        levels = {
            "FINANCE_CLERK": 1,
            "FINANCE_MANAGER": 2,
            "CFO": 3,
            "AUDITOR": 5,
            "BOARD": 4,
        }
        return levels.get(role, 0)

    def _get_approvable_documents(self, user_role: str) -> List[str]:
        """Get list of document types this role can approve"""
        approvable = []
        for doc_type, requirement in self.rules.items():
            if user_role in requirement.required_approvers:
                approvable.append(doc_type)
        return approvable


# Global instance
approval_rules_engine = ApprovalRulesEngine()

# Helper functions
def get_approval_requirement_for_document(
    document_type: str, amount: Optional[float] = None
) -> ApprovalRequirement:
    """Convenience function"""
    return approval_rules_engine.get_approval_requirements(document_type, amount)

def can_user_approve(user_role: str, document_type: str) -> bool:
    """Convenience function"""
    requirement = approval_rules_engine.get_approval_requirements(document_type)
    return approval_rules_engine.can_approve(user_role, document_type, requirement)

def get_full_approval_chain(document_type: str, amount: Optional[float] = None) -> List[Dict]:
    """Convenience function"""
    return approval_rules_engine.get_approval_chain(document_type, amount)

if __name__ == "__main__":
    # Example usage
    engine = ApprovalRulesEngine()

    # Get requirements for a document
    requirement = engine.get_approval_requirements("balance_sheet")
    print(f"Balance sheet requires: {requirement.required_approvers}")

    # Get approval chain
    chain = engine.get_approval_chain("income_statement")
    print(f"Income statement chain: {[step['required_role'] for step in chain]}")

    # Check if user can approve
    can_approve = engine.can_approve("CFO", "balance_sheet", requirement)
    print(f"Can CFO approve balance sheet? {can_approve}")

    # Get SLA status
    submitted = datetime.now() - timedelta(hours=20)
    is_compliant, hours = engine.check_sla_compliance(submitted, datetime.now(), "balance_sheet")
    print(f"SLA compliant: {is_compliant}, Hours elapsed: {hours}")
