"""
Approval policy model helpers for multi-level approvals.
"""

from typing import Dict, Any, List, Optional

from app.db.database import db


class ApprovalPolicy:
    @staticmethod
    async def list_by_unit(unit_id: int) -> List[Dict[str, Any]]:
        return await db.query(
            """
            SELECT *
            FROM approval_policies
            WHERE unit_id = $1
            ORDER BY is_default DESC, created_at ASC
            """,
            unit_id,
        )

    @staticmethod
    async def get_by_id(policy_id: int) -> Optional[Dict[str, Any]]:
        return await db.query_one("SELECT * FROM approval_policies WHERE id = $1", policy_id)

    @staticmethod
    async def get_steps(policy_id: int) -> List[Dict[str, Any]]:
        return await db.query(
            """
            SELECT aps.*,
                   e.name AS assignee_name
            FROM approval_policy_steps aps
            LEFT JOIN employees e ON e.id = aps.assignee_employee_id
            WHERE aps.policy_id = $1
            ORDER BY aps.step_order ASC
            """,
            policy_id,
        )

    @staticmethod
    async def upsert_default_policy(
        organization_id: int,
        unit_id: int,
        name: str,
    ) -> Dict[str, Any]:
        existing = await db.query_one(
            """
            SELECT *
            FROM approval_policies
            WHERE unit_id = $1 AND is_default = TRUE
            LIMIT 1
            """,
            unit_id,
        )
        if existing:
            updated = await db.query(
                """
                UPDATE approval_policies
                SET name = $1,
                    is_active = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $2
                RETURNING *
                """,
                name,
                existing["id"],
            )
            return updated[0]

        created = await db.query(
            """
            INSERT INTO approval_policies (organization_id, unit_id, name, is_default, is_active)
            VALUES ($1, $2, $3, TRUE, TRUE)
            RETURNING *
            """,
            organization_id,
            unit_id,
            name,
        )
        return created[0]

    @staticmethod
    async def replace_steps(policy_id: int, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        await db.query("DELETE FROM approval_policy_steps WHERE policy_id = $1", policy_id)
        for step in steps:
            await db.query(
                """
                INSERT INTO approval_policy_steps (
                    policy_id, step_order, role_type, assignee_employee_id, is_required
                ) VALUES ($1, $2, $3, $4, $5)
                """,
                policy_id,
                step["step_order"],
                step["role_type"],
                step.get("assignee_employee_id"),
                step.get("is_required", True),
            )
        return await ApprovalPolicy.get_steps(policy_id)

    @staticmethod
    async def resolve_for_employee(employee_id: int) -> Optional[Dict[str, Any]]:
        # Employee override first
        override = await db.query_one(
            """
            SELECT ap.*
            FROM employees e
            JOIN approval_policies ap ON ap.id = e.approval_policy_id
            WHERE e.id = $1 AND ap.is_active = TRUE
            """,
            employee_id,
        )
        if override:
            return override

        # Department default fallback
        return await db.query_one(
            """
            SELECT ap.*
            FROM employees e
            JOIN approval_policies ap ON ap.unit_id = e.unit_id
            WHERE e.id = $1 AND ap.is_default = TRUE AND ap.is_active = TRUE
            ORDER BY ap.created_at ASC
            LIMIT 1
            """,
            employee_id,
        )

    @staticmethod
    async def resolve_step_assignee(step: Dict[str, Any], claimant_id: int) -> Optional[int]:
        # Explicit user override on the step has top priority
        if step.get("assignee_employee_id"):
            return step["assignee_employee_id"]

        role_type = (step.get("role_type") or "").strip().lower()

        # Supervisor/manager route resolves to claimant's direct manager first.
        if role_type in {"manager", "supervisor", "line_manager"}:
            manager_id = await db.fetchval(
                "SELECT manager_id FROM employees WHERE id = $1",
                claimant_id,
            )
            if manager_id:
                return manager_id
            # No direct manager — fall through to role-based lookup below
            print(f"ℹ️ No direct manager for employee {claimant_id}, "
                  f"falling through to role-based lookup for '{role_type}'")

        # Role-based assignment in same organization.
        # Prefer role_id matching first, then legacy role text.
        claimant = await db.query_one(
            "SELECT organization_id, unit_id FROM employees WHERE id = $1",
            claimant_id,
        )
        if not claimant:
            return None

        assignee = await db.query_one(
            """
            SELECT e.id
            FROM employees e
            LEFT JOIN roles r ON r.id = e.role_id
            WHERE e.is_active = TRUE
              AND e.organization_id = $1
              AND (
                    LOWER(COALESCE(r.code, '')) = $2
                 OR LOWER(COALESCE(e.role, '')) = $2
              )
            ORDER BY e.id ASC
            LIMIT 1
            """,
            claimant.get("organization_id"),
            role_type,
        )
        return assignee["id"] if assignee else None
