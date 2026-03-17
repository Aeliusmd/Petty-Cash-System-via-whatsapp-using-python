"""
Migration: add multi-level approval tables and backfill data.

Creates:
- approval_policies
- approval_policy_steps
- claim_approval_tasks
- claims.approval_policy_id/current_step_order
- employees.approval_policy_id

Backfill behavior:
- One default policy per department/unit.
- One step in each policy using MANAGER role.
- Existing pending/appealed claims get a PENDING step task.
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

current_file = Path(__file__).resolve()
backend_dir = current_file.parents[3]
sys.path.insert(0, str(backend_dir))

root_dir = backend_dir.parent
env_local = root_dir / ".env.local"
env_default = root_dir / ".env"
if env_local.exists():
    load_dotenv(env_local)
else:
    load_dotenv(env_default)

from app.db.database import db


async def migrate() -> None:
    print("Adding multi-level approval schema...")

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_policies (
            id SERIAL PRIMARY KEY,
            organization_id INT REFERENCES organizations(id) ON DELETE CASCADE,
            unit_id INT NOT NULL REFERENCES units(id) ON DELETE CASCADE,
            name VARCHAR(120) NOT NULL,
            is_default BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_approval_policies_default_per_unit
        ON approval_policies(unit_id)
        WHERE is_default = TRUE
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_approval_policies_org ON approval_policies(organization_id)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_approval_policies_unit ON approval_policies(unit_id)"
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_policy_steps (
            id SERIAL PRIMARY KEY,
            policy_id INT NOT NULL REFERENCES approval_policies(id) ON DELETE CASCADE,
            step_order INT NOT NULL,
            role_type VARCHAR(50) NOT NULL,
            assignee_employee_id INT REFERENCES employees(id),
            is_required BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(policy_id, step_order)
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_policy_steps_policy ON approval_policy_steps(policy_id)"
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS claim_approval_tasks (
            id SERIAL PRIMARY KEY,
            claim_id INT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
            policy_step_id INT NOT NULL REFERENCES approval_policy_steps(id) ON DELETE CASCADE,
            step_order INT NOT NULL,
            assignee_employee_id INT REFERENCES employees(id),
            status VARCHAR(20) NOT NULL DEFAULT 'WAITING'
                CHECK (status IN ('WAITING', 'PENDING', 'APPROVED', 'REJECTED', 'SKIPPED')),
            acted_at TIMESTAMP,
            acted_by INT REFERENCES employees(id),
            comments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(claim_id, step_order)
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_claim_approval_tasks_claim ON claim_approval_tasks(claim_id)"
    )
    await db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_claim_approval_tasks_assignee_status
        ON claim_approval_tasks(assignee_employee_id, status)
        """
    )

    await db.execute(
        "ALTER TABLE claims ADD COLUMN IF NOT EXISTS approval_policy_id INT REFERENCES approval_policies(id)"
    )
    await db.execute(
        "ALTER TABLE claims ADD COLUMN IF NOT EXISTS current_step_order INT"
    )
    await db.execute(
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS approval_policy_id INT"
    )
    await db.execute(
        """
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE employees
                ADD CONSTRAINT fk_employees_approval_policy
                FOREIGN KEY (approval_policy_id) REFERENCES approval_policies(id);
            EXCEPTION WHEN duplicate_object THEN
                NULL;
            END;
        END $$;
        """
    )

    print("Backfilling default department policies...")
    await db.execute(
        """
        INSERT INTO approval_policies (organization_id, unit_id, name, is_default, is_active)
        SELECT DISTINCT
            COALESCE(e.organization_id, u.organization_id) AS organization_id,
            e.unit_id,
            COALESCE(u.name, 'Department') || ' Default Approval',
            TRUE,
            TRUE
        FROM employees e
        LEFT JOIN units u ON u.id = e.unit_id
        WHERE e.unit_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM approval_policies ap
              WHERE ap.unit_id = e.unit_id
                AND ap.is_default = TRUE
          )
        """
    )

    await db.execute(
        """
        INSERT INTO approval_policy_steps (policy_id, step_order, role_type, assignee_employee_id, is_required)
        SELECT ap.id, 1, 'MANAGER', NULL, TRUE
        FROM approval_policies ap
        WHERE NOT EXISTS (
            SELECT 1 FROM approval_policy_steps aps
            WHERE aps.policy_id = ap.id
        )
        """
    )

    print("Linking existing claims to default policies...")
    await db.execute(
        """
        UPDATE claims c
        SET approval_policy_id = ap.id
        FROM employees e
        JOIN approval_policies ap
          ON ap.unit_id = e.unit_id
         AND ap.is_default = TRUE
        WHERE c.employee_id = e.id
          AND c.approval_policy_id IS NULL
        """
    )

    await db.execute(
        """
        UPDATE claims
        SET current_step_order = 1
        WHERE current_step_order IS NULL
          AND approval_policy_id IS NOT NULL
        """
    )

    print("Backfilling tasks for active approval claims...")
    await db.execute(
        """
        INSERT INTO claim_approval_tasks (
            claim_id, policy_step_id, step_order, assignee_employee_id, status
        )
        SELECT
            c.id,
            aps.id,
            1,
            c.manager_id,
            'PENDING'
        FROM claims c
        JOIN claim_statuses cs ON cs.id = c.status_id
        JOIN approval_policy_steps aps
          ON aps.policy_id = c.approval_policy_id
         AND aps.step_order = 1
        WHERE cs.code IN ('PENDING', 'APPEALED')
          AND NOT EXISTS (
              SELECT 1 FROM claim_approval_tasks cat
              WHERE cat.claim_id = c.id
          )
        """
    )

    print("Multi-level approval migration complete")


async def main() -> None:
    await db.connect()
    try:
        await migrate()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
