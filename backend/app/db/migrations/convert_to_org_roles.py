"""
Migration: Convert Global System Roles to Organization-Specific Roles

This migration:
1. For each organization, creates copies of default roles (staff, manager, admin, finance)
2. Copies permissions from global system roles to org-specific copies
3. Updates employees to point to their org's role copies
4. Keeps only super_admin as a true system role

Run with: docker exec -it backend python -m app.db.migrations.convert_to_org_roles
"""
import asyncio
import os
import sys
import traceback

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

try:
    from app.db import db
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)

# Default roles to copy per organization (NOT super_admin)
DEFAULT_ROLES = [
    ('staff', 'Staff', 'Standard employee role'),
    ('manager', 'Manager', 'Team manager with approval rights'),
    ('admin', 'Admin', 'Organization administrator'),
    ('finance', 'Finance', 'Finance officer'),
]

async def migrate_to_org_specific_roles():
    print("🔄 Starting Migration: Global System Roles → Org-Specific Roles...", flush=True)
    
    try:
        await db.connect()
        
        # 1. Get all organizations
        orgs = await db.query("SELECT id, name FROM organizations")
        print(f"📋 Found {len(orgs)} organizations to process", flush=True)
        
        # 2. Get current system roles (except super_admin)
        system_roles = await db.query("""
            SELECT id, code, name, description 
            FROM roles 
            WHERE is_system_role = TRUE 
              AND organization_id IS NULL 
              AND code != 'super_admin'
        """)
        print(f"📋 Found {len(system_roles)} system roles to copy: {[r['code'] for r in system_roles]}", flush=True)
        
        # 3. For each organization, create org-specific copies
        for org in orgs:
            org_id = org['id']
            org_name = org['name']
            print(f"\n🏢 Processing Organization: {org_name} (ID: {org_id})", flush=True)
            
            for role in system_roles:
                await create_org_role_copy(org_id, role)
            
            # 4. Update employees in this org to use new org-specific roles
            await update_org_employees(org_id)
        
        # 5. Deactivate old system roles (except super_admin)
        print("\n🗑️ Marking old system roles as inactive (except super_admin)...", flush=True)
        await db.execute("""
            UPDATE roles 
            SET is_active = FALSE 
            WHERE is_system_role = TRUE 
              AND organization_id IS NULL 
              AND code != 'super_admin'
        """)
        
        print("\n✅ Migration Completed Successfully!", flush=True)
        
    except Exception as e:
        print(f"❌ Migration Failed: {e}", flush=True)
        traceback.print_exc()
    finally:
        await db.close()

async def create_org_role_copy(org_id: int, system_role: dict):
    """Create org-specific copy of a system role with its permissions"""
    
    role_code = system_role['code']
    role_name = system_role['name']
    role_desc = system_role['description']
    system_role_id = system_role['id']
    
    # Check if org already has this role
    existing = await db.query_one("""
        SELECT id FROM roles 
        WHERE code = $1 AND organization_id = $2
    """, role_code, org_id)
    
    if existing:
        print(f"  ⚠️ Role '{role_code}' already exists for org {org_id}, skipping", flush=True)
        return existing['id']
    
    # Create role copy for this org
    new_role_id = await db.fetchval("""
        INSERT INTO roles (code, name, description, organization_id, is_system_role, is_active)
        VALUES ($1, $2, $3, $4, FALSE, TRUE)
        RETURNING id
    """, role_code, role_name, role_desc, org_id)
    
    print(f"  ✅ Created role '{role_code}' (ID: {new_role_id}) for org {org_id}", flush=True)
    
    # Copy permissions from system role
    await db.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT $1, permission_id 
        FROM role_permissions 
        WHERE role_id = $2
        ON CONFLICT DO NOTHING
    """, new_role_id, system_role_id)
    
    perm_count = await db.fetchval("""
        SELECT COUNT(*) FROM role_permissions WHERE role_id = $1
    """, new_role_id)
    print(f"     Copied {perm_count} permissions", flush=True)
    
    return new_role_id

async def update_org_employees(org_id: int):
    """Update employees in an org to use org-specific role copies"""
    
    # Get org-specific roles
    org_roles = await db.query("""
        SELECT id, code FROM roles 
        WHERE organization_id = $1 AND is_active = TRUE
    """, org_id)
    
    org_role_map = {r['code']: r['id'] for r in org_roles}
    
    # Get system roles for mapping
    system_roles = await db.query("""
        SELECT id, code FROM roles 
        WHERE is_system_role = TRUE AND organization_id IS NULL
    """)
    system_role_map = {r['id']: r['code'] for r in system_roles}
    
    # Update employees pointing to system roles
    updated = 0
    for system_role_id, role_code in system_role_map.items():
        if role_code == 'super_admin':
            continue  # Super admin stays as system role
            
        if role_code in org_role_map:
            org_role_id = org_role_map[role_code]
            
            result = await db.execute("""
                UPDATE employees 
                SET role_id = $1 
                WHERE organization_id = $2 AND role_id = $3
            """, org_role_id, org_id, system_role_id)
            
            # Count updated (approximation)
            count = await db.fetchval("""
                SELECT COUNT(*) FROM employees 
                WHERE organization_id = $1 AND role_id = $2
            """, org_id, org_role_id)
            updated += count or 0
    
    print(f"  👥 Updated employees to org-specific roles in org {org_id}", flush=True)


async def seed_roles_for_new_org(org_id: int):
    """
    Utility function to seed default roles when a new organization is created.
    Call this from the organization creation service.
    """
    print(f"🌱 Seeding default roles for organization {org_id}...", flush=True)
    
    # Get system role permissions as template
    system_roles = await db.query("""
        SELECT id, code, name, description 
        FROM roles 
        WHERE is_system_role = TRUE 
          AND organization_id IS NULL 
          AND code != 'super_admin'
          AND is_active = TRUE
    """)
    
    # If no active system roles (they were deactivated), use defaults
    if not system_roles:
        for code, name, desc in DEFAULT_ROLES:
            await create_default_role(org_id, code, name, desc)
    else:
        for role in system_roles:
            await create_org_role_copy(org_id, role)
    
    print(f"✅ Seeded {len(DEFAULT_ROLES)} default roles for org {org_id}", flush=True)


async def create_default_role(org_id: int, code: str, name: str, description: str):
    """Create a default role with standard permissions"""
    
    # Default permission sets
    role_permissions = {
        'staff': [
            'claims.create', 'claims.read.own', 'claims.update.own', 
            'claims.delete.own', 'claims.appeal', 'employees.read.own', 
            'employees.update.own'
        ],
        'manager': [
            'claims.create', 'claims.read.own', 'claims.update.own',
            'claims.read.team', 'claims.approve', 'claims.reject', 
            'dashboard.view.team', 'reports.view', 'employees.read.all'
        ],
        'admin': [
            'claims.read.all', 'claims.update.all', 'claims.delete.all',
            'employees.create', 'employees.read.all', 'employees.update.all',
            'employees.delete', 'employees.activate', 'employees.assign_role',
            'config.view', 'config.manage', 'roles.read', 'roles.create', 
            'roles.update', 'roles.delete', 'audit.view', 'dashboard.view.org'
        ],
        'finance': [
            'claims.read.all', 'claims.export', 'reports.view', 
            'reports.financial', 'audit.view'
        ],
    }
    
    # Create role
    new_role_id = await db.fetchval("""
        INSERT INTO roles (code, name, description, organization_id, is_system_role, is_active)
        VALUES ($1, $2, $3, $4, FALSE, TRUE)
        RETURNING id
    """, code, name, description, org_id)
    
    # Assign permissions
    perm_codes = role_permissions.get(code, [])
    for perm_code in perm_codes:
        perm_id = await db.fetchval("SELECT id FROM permissions WHERE code = $1", perm_code)
        if perm_id:
            await db.execute("""
                INSERT INTO role_permissions (role_id, permission_id) 
                VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, new_role_id, perm_id)
    
    return new_role_id


if __name__ == "__main__":
    asyncio.run(migrate_to_org_specific_roles())
