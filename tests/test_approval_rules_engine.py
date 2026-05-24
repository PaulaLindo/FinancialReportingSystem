import unittest

from services.approval_rules_engine import (
    approval_rules_engine,
    can_user_approve,
    get_approval_requirement_for_document,
    get_full_approval_chain,
)


class ApprovalRulesEngineTests(unittest.TestCase):
    def test_balance_sheet_requires_manager_and_cfo(self):
        req = get_approval_requirement_for_document("balance_sheet")
        self.assertIn("FINANCE_MANAGER", req.required_approvers)
        self.assertIn("CFO", req.required_approvers)

    def test_cfo_can_approve_balance_sheet(self):
        self.assertTrue(can_user_approve("CFO", "balance_sheet"))

    def test_clerk_cannot_approve_balance_sheet(self):
        self.assertFalse(can_user_approve("FINANCE_CLERK", "balance_sheet"))

    def test_approval_chain_has_steps(self):
        chain = get_full_approval_chain("income_statement")
        self.assertGreaterEqual(len(chain), 1)
        roles = {step.get("required_role") for step in chain}
        self.assertTrue(roles & {"FINANCE_MANAGER", "CFO"})

    def test_sla_hours_positive(self):
        req = approval_rules_engine.get_approval_requirements("budget_report")
        self.assertGreater(req.sla_hours, 0)


if __name__ == "__main__":
    unittest.main()
