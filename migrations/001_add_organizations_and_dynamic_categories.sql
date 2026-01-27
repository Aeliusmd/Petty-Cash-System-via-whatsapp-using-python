-- Migration: Add Organizations table and link Categories to Units (Departments)
-- Created: 2026-01-23
-- Purpose: Support dynamic departments per organization and categories per department

-- =============================================
-- 1. CREATE ORGANIZATIONS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 2. ADD organization_id TO UNITS TABLE
-- =============================================
ALTER TABLE units ADD COLUMN IF NOT EXISTS organization_id INT REFERENCES organizations(id);

-- =============================================
-- 3. ADD unit_id TO CLAIM_CATEGORIES TABLE
-- =============================================
-- Drop unexpected organization_id column if it exists (seems to be a legacy/conflicting column)
-- Drop unexpected organization_id column if it exists (seems to be a legacy/conflicting column)
ALTER TABLE claim_categories DROP COLUMN IF EXISTS organization_id;


ALTER TABLE claim_categories ADD COLUMN IF NOT EXISTS unit_id INT REFERENCES units(id);

-- Drop original global unique constraint on code
ALTER TABLE claim_categories DROP CONSTRAINT IF EXISTS claim_categories_code_key;

-- Add scoped unique constraints
-- 1. Code unique within a unit
CREATE UNIQUE INDEX IF NOT EXISTS idx_claim_categories_code_unit ON claim_categories(code, unit_id) WHERE unit_id IS NOT NULL;
-- 2. Code unique among global categories
CREATE UNIQUE INDEX IF NOT EXISTS idx_claim_categories_code_global ON claim_categories(code) WHERE unit_id IS NULL;

-- =============================================
-- 4. CREATE DEFAULT ORGANIZATION AND ASSIGN ALL EXISTING UNITS
-- =============================================
DO $$
DECLARE
    default_org_id INT;
BEGIN
    -- Check if any organizations exist
    IF NOT EXISTS (SELECT 1 FROM organizations LIMIT 1) THEN
        -- Insert a default organization
        INSERT INTO organizations (code, name, description)
        VALUES ('DEFAULT', 'Default Organization', 'Auto-created default organization')
        RETURNING id INTO default_org_id;
        
        -- Link all existing units to the default organization
        UPDATE units SET organization_id = default_org_id WHERE organization_id IS NULL;
        
        RAISE NOTICE 'Created default organization (ID: %) and linked existing units.', default_org_id;
    END IF;
END;
$$;

-- =============================================
-- 5. MAKE GLOBAL CATEGORIES AVAILABLE TO ALL UNITS
-- =============================================
-- Copy global categories to all units using a single query
INSERT INTO claim_categories (code, name, description, requires_receipt, display_order, unit_id, is_active)
SELECT 
    cc.code, 
    cc.name, 
    cc.description, 
    cc.requires_receipt, 
    cc.display_order, 
    u.id, 
    TRUE
FROM claim_categories cc
CROSS JOIN units u
WHERE cc.unit_id IS NULL
AND NOT EXISTS (
    SELECT 1 FROM claim_categories existing 
    WHERE existing.unit_id = u.id AND existing.code = cc.code
);

-- Delete old global categories
DELETE FROM claim_categories WHERE unit_id IS NULL;

-- =============================================
-- 7. ADD CONSTRAINTS
-- =============================================
-- Now that data is populated, add the foreign key constraints safely
DO $$
BEGIN
    -- Add FK to units if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'units_organization_id_fkey') THEN
        ALTER TABLE units ADD CONSTRAINT units_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES organizations(id);
    END IF;

    -- Add FK to claim_categories if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'claim_categories_unit_id_fkey') THEN
        ALTER TABLE claim_categories ADD CONSTRAINT claim_categories_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES units(id);
    END IF;
END;
$$;

-- =============================================
-- 8. CREATE INDEXES FOR PERFORMANCE
-- =============================================
CREATE INDEX IF NOT EXISTS idx_units_organization ON units(organization_id);
CREATE INDEX IF NOT EXISTS idx_categories_unit ON claim_categories(unit_id);

-- =============================================
-- 9. UPDATE TRIGGERS
-- =============================================
DROP TRIGGER IF EXISTS update_organizations_updated_at ON organizations;
CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

