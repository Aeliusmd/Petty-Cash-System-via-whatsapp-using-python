import asyncio
import os
import sys
import traceback
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

try:
    from app.db import db
    from app.config import config
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print(f"Sys Path: {sys.path}")
    traceback.print_exc()
    sys.exit(1)

async def migrate_to_dynamic_rbac():
    print("🔄 Starting Dynamic RBAC System Migration...", flush=True)
    
    try:
        await db.connect()
        
        # 1. Create Tables
        print("📊 Creating database tables...", flush=True)
        await create_tables()
        
        # 2. Seed Permissions
        print("🌱 Seeding permissions...", flush=True)
        await seed_permissions()
        
        # 3. Create System Roles
        print("👑 Creating system roles...", flush=True)
        await create_system_roles()
        
        # 4. Assign Permissions to Roles
        print("🔐 Assigning permissions to roles...", flush=True)
        await assign_system_role_permissions()
        
        # 5. Migrate Employees
        print("👥 Migrating employee records...", flush=True)
        await migrate_employee_roles()
        
        print("✅ RBAC Migration Successfully Completed!", flush=True)
        
    except Exception as e:
        print(f"❌ Migration Failed: {e}", flush=True)
        traceback.print_exc()
    finally:
        await db.close()

async def create_tables():
    """Create roles, permissions, role_permissions tables and update employees"""
    
    queries = [
        # organizations table check (should exist, but good to ensure)
        ("chk_orgs", """
        CREATE TABLE IF NOT EXISTS organizations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            code VARCHAR(20) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """),
        
        # 1. Roles Table
        ("create_roles", """
        CREATE TABLE IF NOT EXISTS roles (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            organization_id INT REFERENCES organizations(id),
            parent_role_id INT REFERENCES roles(id),
            is_system_role BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(code, organization_id)
        );
        """),
        ("idx_roles_org", """CREATE INDEX IF NOT EXISTS idx_roles_org ON roles(organization_id);"""),
        ("idx_roles_code", """CREATE INDEX IF NOT EXISTS idx_roles_code ON roles(code);"""),
        ("idx_roles_parent", """CREATE INDEX IF NOT EXISTS idx_roles_parent ON roles(parent_role_id);"""),
        
        # 2. Permissions Table
        ("create_perms", """
        CREATE TABLE IF NOT EXISTS permissions (
            id SERIAL PRIMARY KEY,
            code VARCHAR(100) UNIQUE NOT NULL,
            resource VARCHAR(50) NOT NULL,
            action VARCHAR(50) NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            category VARCHAR(50),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(resource, action)
        );
        """),
        ("idx_perms_res", """CREATE INDEX IF NOT EXISTS idx_permissions_resource ON permissions(resource);"""),
        ("idx_perms_cat", """CREATE INDEX IF NOT EXISTS idx_permissions_category ON permissions(category);"""),
        
        # 3. Role Permissions Table
        ("create_role_perms", """
        CREATE TABLE IF NOT EXISTS role_permissions (
            id SERIAL PRIMARY KEY,
            role_id INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id INT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(role_id, permission_id)
        );
        """),
        ("idx_rp_role", """CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role_id);"""),
        ("idx_rp_perm", """CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON role_permissions(permission_id);"""),
        
        # 4. Update Employees Table
        ("alter_emp", """
        ALTER TABLE employees 
        ADD COLUMN IF NOT EXISTS role_id INT REFERENCES roles(id);
        """),
        ("idx_emp_role", """CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role_id);""")
    ]
    
    for name, q in queries:
        print(f"  > Executing query: {name}...", flush=True)
        try:
            await db.execute(q)
        except Exception as e:
            print(f"  ❌ Error in query {name}: {e}")
            raise

async def seed_permissions():
    """Insert core system permissions"""
    
    permissions = [
        # Claim Management
        ('claims.create', 'claims', 'create', 'Create Claims', 'Claim Management'),
        ('claims.read.own', 'claims', 'read_own', 'View Own Claims', 'Claim Management'),
        ('claims.read.team', 'claims', 'read_team', 'View Team Claims', 'Claim Management'),
        ('claims.read.all', 'claims', 'read_all', 'View All Claims', 'Claim Management'),
        ('claims.update.own', 'claims', 'update_own', 'Edit Own Claims', 'Claim Management'),
        ('claims.update.all', 'claims', 'update_all', 'Edit Any Claim', 'Claim Management'),
        ('claims.delete.own', 'claims', 'delete_own', 'Delete Own Claims', 'Claim Management'),
        ('claims.delete.all', 'claims', 'delete_all', 'Delete Any Claim', 'Claim Management'),
        ('claims.approve', 'claims', 'approve', 'Approve Claims', 'Claim Management'),
        ('claims.reject', 'claims', 'reject', 'Reject Claims', 'Claim Management'),
        ('claims.appeal', 'claims', 'appeal', 'Appeal Rejected Claims', 'Claim Management'),
        ('claims.export', 'claims', 'export', 'Export Claims Data', 'Claim Management'),
        
        # Employee Management
        ('employees.create', 'employees', 'create', 'Create Employees', 'Employee Management'),
        ('employees.read.own', 'employees', 'read_own', 'View Own Profile', 'Employee Management'),
        ('employees.read.all', 'employees', 'read_all', 'View All Employees', 'Employee Management'),
        ('employees.update.own', 'employees', 'update_own', 'Update Own Profile', 'Employee Management'),
        ('employees.update.all', 'employees', 'update_all', 'Update Any Employee', 'Employee Management'),
        ('employees.delete', 'employees', 'delete', 'Deactivate Employees', 'Employee Management'),
        ('employees.activate', 'employees', 'activate', 'Activate Employees', 'Employee Management'),
        ('employees.assign_role', 'employees', 'assign_role', 'Assign Roles', 'Employee Management'),
        
        # Configuration
        ('config.view', 'config', 'view', 'View Configuration', 'Configuration'),
        ('config.manage', 'config', 'manage', 'Manage Configuration', 'Configuration'),
        
        # Reports
        ('reports.view', 'reports', 'view', 'View Reports', 'Reports'),
        ('reports.financial', 'reports', 'financial', 'View Financial Reports', 'Reports'),
        ('dashboard.view.team', 'dashboard', 'view_team', 'View Team Dashboard', 'Reports'),
        ('dashboard.view.org', 'dashboard', 'view_org', 'View Org Dashboard', 'Reports'),
        
        # Audit
        ('audit.view', 'audit', 'view', 'View Audit Logs', 'Audit'),
        
        # Role Management
        ('roles.create', 'roles', 'create', 'Create Custom Roles', 'Role Management'),
        ('roles.read', 'roles', 'read', 'View Roles', 'Role Management'),
        ('roles.update', 'roles', 'update', 'Update Roles', 'Role Management'),
        ('roles.delete', 'roles', 'delete', 'Delete Custom Roles', 'Role Management'),
        
        # Organization
        ('orgs.manage', 'orgs', 'manage', 'Manage Organizations', 'Organization')
    ]
    
    for code, resource, action, name, category in permissions:
        # Check if exists
        check = "SELECT id FROM permissions WHERE code = $1"
        try:
            exists = await db.query_one(check, code)
            
            if not exists:
                query = """
                    INSERT INTO permissions (code, resource, action, name, category, description)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """
                await db.execute(query, code, resource, action, name, category, name)
        except Exception as e:
            print(f"  ❌ Error seeding permission {code}: {e}")
            raise

async def create_system_roles():
    """Create default system roles"""
    
    system_roles = [
        ('staff', 'Staff', 'Standard employee role'),
        ('manager', 'Manager', 'Team manager with approval rights'),
        ('admin', 'Admin', 'Organization administrator'),
        ('finance', 'Finance', 'Finance officer'),
        ('super_admin', 'Super Admin', 'System administrator')
    ]
    
    for code, name, desc in system_roles:
        # Check if exists (using organization_id IS NULL for system roles)
        check = "SELECT id FROM roles WHERE code = $1 AND organization_id IS NULL"
        try:
            exists = await db.query_one(check, code)
            
            if not exists:
                query = """
                    INSERT INTO roles (code, name, description, is_system_role, organization_id)
                    VALUES ($1, $2, $3, TRUE, NULL)
                """
                await db.execute(query, code, name, desc)
        except Exception as e:
            print(f"  ❌ Error creating role {code}: {e}")
            raise

async def assign_system_role_permissions():
    """Assign default permissions to system roles"""
    
    # Define permission sets
    role_permissions = {
        'staff': [
            'claims.create', 'claims.read.own', 'claims.update.own', 
            'claims.delete.own', 'claims.appeal', 'employees.read.own', 
            'employees.update.own'
        ],
        'manager': [
            # Inherits staff implicitly via code logic, but here we assign explicitly for now
            'claims.create', 'claims.read.own', 'claims.update.own',
            'claims.read.team', 'claims.approve', 'claims.reject', 
            'dashboard.view.team', 'reports.view', 'employees.read.all'
        ],
        'admin': [
            'claims.read.all', 'claims.update.all', 'claims.delete.all',
            'employees.create', 'employees.read.all', 'employees.update.all',
            'employees.delete', 'employees.activate', 'employees.assign_role',
            'config.view', 'config.manage', 'roles.read', 'roles.create', 
            'roles.update', 'audit.view', 'dashboard.view.org'
        ],
        'finance': [
            'claims.read.all', 'claims.export', 'reports.view', 
            'reports.financial', 'audit.view'
        ],
        'super_admin': [
            # Super admin gets EVERYTHING
            'orgs.manage', 'roles.delete'
        ]
    }
    
    # 1. Get all roles
    roles = await db.query("SELECT id, code FROM roles WHERE is_system_role = TRUE")
    role_map = {r['code']: r['id'] for r in roles}
    
    # 2. Get all permissions
    perms = await db.query("SELECT id, code FROM permissions")
    perm_map = {p['code']: p['id'] for p in perms}
    
    for role_code, perm_codes in role_permissions.items():
        if role_code not in role_map:
            continue
            
        role_id = role_map[role_code]
        
        # For super_admin, give ALL permissions
        if role_code == 'super_admin':
            target_perms = list(perm_map.values())
        else:
            target_perms = [perm_map[p] for p in perm_codes if p in perm_map]
            
        for perm_id in target_perms:
            try:
                await db.execute(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    role_id, perm_id
                )
            except Exception as e:
                print(f"  ❌ Error assigning perm {perm_id} to role {role_code}: {e}")
                # Don't iterate validation errors, just print
                pass

async def migrate_employee_roles():
    """Map existing string roles to new Role IDs"""
    
    print("Mapping employees to new roles...", flush=True)
    
    # Get Role IDs
    roles = await db.query("SELECT id, code FROM roles WHERE is_system_role = TRUE")
    role_map = {r['code']: r['id'] for r in roles}
    
    # Update employees
    # Note: 'role' column is the legacy string column
    for role_code, role_id in role_map.items():
        try:
            print(f"  > Migrating role '{role_code}' to ID {role_id}...", flush=True)
            query = """
                UPDATE employees 
                SET role_id = $1 
                WHERE role = $2 AND role_id IS NULL
            """
            await db.execute(query, role_id, role_code)
        except Exception as e:
            print(f"  ❌ Error migrating role {role_code}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(migrate_to_dynamic_rbac())
