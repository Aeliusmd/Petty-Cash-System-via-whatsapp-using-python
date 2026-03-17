"""
Basic regression tests for multi-level approval workflow.

Run:
    python -m unittest backend.tests.test_multi_approval_flow
"""

import unittest
from unittest.mock import AsyncMock, patch

from app.models.approval import ApprovalPolicy
from app.models.claim import Claim


class TestMultiApprovalFlow(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_step_assignee_prefers_explicit_user(self):
        step = {"role_type": "FINANCE", "assignee_employee_id": 88}
        assignee = await ApprovalPolicy.resolve_step_assignee(step=step, claimant_id=10)
        self.assertEqual(assignee, 88)

    async def test_approve_step_rejects_non_assignee(self):
        claim = Claim({"id": 5, "employee_id": 2, "manager_id": 7})
        current_task = {"id": 11, "step_order": 1, "assignee_employee_id": 99}

        with patch.object(Claim, "find_by_id", AsyncMock(return_value=claim)):
            with patch.object(Claim, "get_current_pending_task", AsyncMock(return_value=current_task)):
                with self.assertRaises(PermissionError):
                    await Claim.approve_step(claim_id=5, approver_id=7)

    async def test_reject_step_rejects_non_assignee(self):
        claim = Claim({"id": 8, "employee_id": 3, "manager_id": 4})
        current_task = {"id": 15, "step_order": 2, "assignee_employee_id": 12}

        with patch.object(Claim, "find_by_id", AsyncMock(return_value=claim)):
            with patch.object(Claim, "get_current_pending_task", AsyncMock(return_value=current_task)):
                with self.assertRaises(PermissionError):
                    await Claim.reject_step(claim_id=8, approver_id=4, reason="invalid")

    async def test_approve_step_activates_next_task(self):
        claim = Claim({"id": 9, "employee_id": 3, "manager_id": 4})
        current_task = {"id": 31, "step_order": 1, "assignee_employee_id": 4}
        next_task = {"id": 32, "step_order": 2, "assignee_employee_id": 6}
        updated_claim = Claim({"id": 9, "status_code": "PENDING"})

        with patch.object(Claim, "find_by_id", AsyncMock(side_effect=[claim, updated_claim])):
            with patch.object(Claim, "get_current_pending_task", AsyncMock(return_value=current_task)):
                with patch("app.models.claim.db.query_one", AsyncMock(return_value=next_task)):
                    with patch("app.models.claim.db.query", AsyncMock(return_value=[])):
                        result = await Claim.approve_step(claim_id=9, approver_id=4)

        self.assertFalse(result["is_final"])
        self.assertEqual(result["next_assignee_id"], 6)
        self.assertEqual(result["approved_step"], 1)


if __name__ == "__main__":
    unittest.main()
