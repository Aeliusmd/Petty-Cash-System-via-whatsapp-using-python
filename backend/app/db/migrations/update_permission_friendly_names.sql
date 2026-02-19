-- Migration: Update permission names and descriptions to plain English
-- Run this once on the live database to make permission names friendly for non-technical users.

-- ═══════════════════════════════════════════
-- CLAIMS  (page: All Claims / My Claims)
-- ═══════════════════════════════════════════
UPDATE permissions SET name = 'Submit Claims',          description = 'Can submit new petty cash claims'                          WHERE code = 'claims.create';
UPDATE permissions SET name = 'View Own Claims',        description = 'Can see their own claims only'                              WHERE code = 'claims.read.own';
UPDATE permissions SET name = 'View Team Claims',       description = 'Can see claims from their team members'                    WHERE code = 'claims.read.team';
UPDATE permissions SET name = 'View All Claims',        description = 'Can see every claim in the organisation'                   WHERE code = 'claims.read.all';
UPDATE permissions SET name = 'Edit Own Claims',        description = 'Can edit their own pending claims'                         WHERE code = 'claims.update.own';
UPDATE permissions SET name = 'Edit Any Claim',         description = 'Can edit any claim in the organisation'                    WHERE code = 'claims.update.all';
UPDATE permissions SET name = 'Delete Own Claims',      description = 'Can delete their own pending claims'                       WHERE code = 'claims.delete.own';
UPDATE permissions SET name = 'Delete Any Claim',       description = 'Can delete any claim in the organisation'                  WHERE code = 'claims.delete.all';
UPDATE permissions SET name = 'Approve Claims',         description = 'Can approve pending claims'                                WHERE code = 'claims.approve';
UPDATE permissions SET name = 'Reject Claims',          description = 'Can reject pending claims'                                 WHERE code = 'claims.reject';
UPDATE permissions SET name = 'Appeal Rejection',       description = 'Can appeal a rejected claim'                               WHERE code = 'claims.appeal';
UPDATE permissions SET name = 'Export Claims',          description = 'Can download / export claim reports'                       WHERE code = 'claims.export';

-- ═══════════════════════════════════════════
-- EMPLOYEES  (page: Employees)
-- ═══════════════════════════════════════════
UPDATE permissions SET name = 'Add Employees',          description = 'Can add new employees to the organisation'                 WHERE code = 'employees.create';
UPDATE permissions SET name = 'View Own Profile',       description = 'Can view their own employee profile'                       WHERE code = 'employees.read.own';
UPDATE permissions SET name = 'View All Employees',     description = 'Can see the full employee list'                            WHERE code = 'employees.read.all';
UPDATE permissions SET name = 'Edit Own Profile',       description = 'Can update their own employee profile'                     WHERE code = 'employees.update.own';
UPDATE permissions SET name = 'Edit Any Employee',      description = 'Can update any employee''s details'                        WHERE code = 'employees.update.all';
UPDATE permissions SET name = 'Deactivate Employees',   description = 'Can deactivate (soft-delete) an employee account'          WHERE code = 'employees.delete';
UPDATE permissions SET name = 'Reactivate Employees',   description = 'Can reactivate a deactivated employee account'             WHERE code = 'employees.activate';
UPDATE permissions SET name = 'Assign Roles',           description = 'Can change which role an employee has'                     WHERE code = 'employees.assign_role';

-- ═══════════════════════════════════════════
-- SETTINGS  (page: Settings – Departments & Categories)
-- ═══════════════════════════════════════════
UPDATE permissions SET name = 'View Settings',          description = 'Can view departments and claim categories'                 WHERE code = 'config.view';
UPDATE permissions SET name = 'Manage Settings',        description = 'Can add, edit and delete departments and claim categories' WHERE code = 'config.manage';

-- ═══════════════════════════════════════════
-- REPORTS & DASHBOARD
-- ═══════════════════════════════════════════
UPDATE permissions SET name = 'View Reports',           description = 'Can view standard claim reports'                           WHERE code = 'reports.view';
UPDATE permissions SET name = 'View Financial Reports', description = 'Can view financial / payment summary reports'              WHERE code = 'reports.financial';
UPDATE permissions SET name = 'View Team Dashboard',    description = 'Can see the dashboard for their team'                      WHERE code = 'dashboard.view.team';
UPDATE permissions SET name = 'View Organisation Dashboard', description = 'Can see the organisation-wide dashboard'             WHERE code = 'dashboard.view.org';

-- ═══════════════════════════════════════════
-- AUDIT LOGS  (page: Audit Logs)
-- ═══════════════════════════════════════════
UPDATE permissions SET name = 'View Audit Logs',        description = 'Can see the activity and change history logs'              WHERE code = 'audit.view';

-- ═══════════════════════════════════════════
-- ROLES  (page: Roles)
-- ═══════════════════════════════════════════
UPDATE permissions SET name = 'View Roles',             description = 'Can see the list of roles and their permissions'           WHERE code = 'roles.read';
UPDATE permissions SET name = 'Create Roles',           description = 'Can create new custom roles'                               WHERE code = 'roles.create';
UPDATE permissions SET name = 'Edit Roles',             description = 'Can edit existing roles and their permissions'             WHERE code = 'roles.update';
UPDATE permissions SET name = 'Delete Roles',           description = 'Can permanently delete a custom role'                     WHERE code = 'roles.delete';

-- ═══════════════════════════════════════════
-- CATEGORY LABELS (make them page-friendly in the UI)
-- ═══════════════════════════════════════════
UPDATE permissions SET category = 'Claims'          WHERE category = 'Claim Management';
UPDATE permissions SET category = 'Employees'       WHERE category = 'Employee Management';
UPDATE permissions SET category = 'Settings'        WHERE category = 'Configuration';
UPDATE permissions SET category = 'Roles'           WHERE category = 'Role Management';
UPDATE permissions SET category = 'Reports'         WHERE category IS NULL AND resource IN ('reports','dashboard');
