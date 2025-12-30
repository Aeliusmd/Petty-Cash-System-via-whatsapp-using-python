-- Petty Cash Management System - Database Schema
-- PostgreSQL 14+
-- Run this script to create all tables

-- =============================================
-- MASTER DATA TABLES
-- =============================================

-- Employee Grades (A, B, C, etc.)
CREATE TABLE IF NOT EXISTS grades (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Organizational Units / Departments
CREATE TABLE IF NOT EXISTS units (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Locations
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Claim Categories (Batta, Fuel, Accommodation, Sundry)
CREATE TABLE IF NOT EXISTS claim_categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    requires_receipt BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Claim Statuses
CREATE TABLE IF NOT EXISTS claim_statuses (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    display_order INT DEFAULT 0
);

-- =============================================
-- EMPLOYEE MANAGEMENT
-- =============================================

-- Employees Table
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    employee_code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    whatsapp_chat_id VARCHAR(50),
    email VARCHAR(100),
    grade_id INT REFERENCES grades(id),
    unit_id INT REFERENCES units(id),
    location_id INT REFERENCES locations(id),
    manager_id INT REFERENCES employees(id),
    role VARCHAR(20) DEFAULT 'staff' CHECK (role IN ('staff', 'manager', 'admin', 'finance')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for phone number lookups
CREATE INDEX IF NOT EXISTS idx_employees_phone ON employees(phone_number);
CREATE INDEX IF NOT EXISTS idx_employees_chat_id ON employees(whatsapp_chat_id);

-- =============================================
-- RULES ENGINE
-- =============================================

-- Batta Rates (Grade × Location)
CREATE TABLE IF NOT EXISTS batta_rates (
    id SERIAL PRIMARY KEY,
    grade_id INT NOT NULL REFERENCES grades(id),
    location_id INT NOT NULL REFERENCES locations(id),
    rate_per_day DECIMAL(10,2) NOT NULL,
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(grade_id, location_id, effective_from)
);

-- Category Caps (Max limits per category)
CREATE TABLE IF NOT EXISTS category_caps (
    id SERIAL PRIMARY KEY,
    category_id INT NOT NULL REFERENCES claim_categories(id),
    grade_id INT REFERENCES grades(id), -- NULL means all grades
    max_amount DECIMAL(10,2) NOT NULL,
    period VARCHAR(20) DEFAULT 'monthly' CHECK (period IN ('daily', 'weekly', 'monthly', 'yearly')),
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- CLAIMS & APPROVALS
-- =============================================

-- Claims Table
CREATE TABLE IF NOT EXISTS claims (
    id SERIAL PRIMARY KEY,
    claim_number VARCHAR(20) UNIQUE NOT NULL,
    employee_id INT NOT NULL REFERENCES employees(id),
    category_id INT NOT NULL REFERENCES claim_categories(id),
    location_id INT REFERENCES locations(id),
    status_id INT NOT NULL REFERENCES claim_statuses(id),
    claim_type VARCHAR(20) DEFAULT 'outright' CHECK (claim_type IN ('bill', 'outright')),
    claim_date DATE NOT NULL DEFAULT CURRENT_DATE,
    duration_days INT DEFAULT 1,
    user_amount DECIMAL(10,2),
    system_amount DECIMAL(10,2),
    final_amount DECIMAL(10,2),
    description TEXT,
    manager_id INT REFERENCES employees(id),
    approved_by INT REFERENCES employees(id),
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    appeal_count INT DEFAULT 0,
    is_exception BOOLEAN DEFAULT FALSE,
    exception_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for claim lookups
CREATE INDEX IF NOT EXISTS idx_claims_employee ON claims(employee_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status_id);
CREATE INDEX IF NOT EXISTS idx_claims_manager ON claims(manager_id);
CREATE INDEX IF NOT EXISTS idx_claims_date ON claims(claim_date);

-- Claim Receipts (uploaded bills)
CREATE TABLE IF NOT EXISTS claim_receipts (
    id SERIAL PRIMARY KEY,
    claim_id INT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255),
    file_type VARCHAR(50),
    file_size INT,
    ocr_amount DECIMAL(10,2),
    ocr_raw_text TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Claim Comments (manager feedback, etc.)
CREATE TABLE IF NOT EXISTS claim_comments (
    id SERIAL PRIMARY KEY,
    claim_id INT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    employee_id INT NOT NULL REFERENCES employees(id),
    comment TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Claim Status History (tracks approvals, rejections, appeals)
CREATE TABLE IF NOT EXISTS claim_status_history (
    id SERIAL PRIMARY KEY,
    claim_id INT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    from_status_id INT REFERENCES claim_statuses(id),
    to_status_id INT NOT NULL REFERENCES claim_statuses(id),
    changed_by INT REFERENCES employees(id),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for history lookups
CREATE INDEX IF NOT EXISTS idx_claim_status_history_claim ON claim_status_history(claim_id);

-- =============================================
-- CONVERSATION STATE (WhatsApp flow)
-- =============================================

-- Conversation States (persistent WhatsApp session)
CREATE TABLE IF NOT EXISTS conversation_states (
    id SERIAL PRIMARY KEY,
    chat_id VARCHAR(50) UNIQUE NOT NULL,
    employee_id INT REFERENCES employees(id),
    current_step VARCHAR(50) DEFAULT 'initial',
    category VARCHAR(20),
    context JSONB DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversation_chat_id ON conversation_states(chat_id);

-- =============================================
-- AUDIT LOGS
-- =============================================

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT,
    action VARCHAR(20) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    performed_by INT REFERENCES employees(id),
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_logs(created_at);

-- =============================================
-- HELPER FUNCTIONS
-- =============================================

-- Function to generate claim numbers
CREATE OR REPLACE FUNCTION generate_claim_number()
RETURNS VARCHAR(20) AS $$
DECLARE
    new_number VARCHAR(20);
    year_part VARCHAR(4);
    seq_part INT;
BEGIN
    year_part := TO_CHAR(CURRENT_DATE, 'YYYY');
    
    SELECT COALESCE(MAX(CAST(SUBSTRING(claim_number FROM 9) AS INT)), 0) + 1
    INTO seq_part
    FROM claims
    WHERE claim_number LIKE 'PC-' || year_part || '-%';
    
    new_number := 'PC-' || year_part || '-' || LPAD(seq_part::TEXT, 5, '0');
    RETURN new_number;
END;
$$ LANGUAGE plpgsql;

-- Function to get batta rate
CREATE OR REPLACE FUNCTION get_batta_rate(p_grade_id INT, p_location_id INT)
RETURNS DECIMAL(10,2) AS $$
DECLARE
    rate DECIMAL(10,2);
BEGIN
    SELECT rate_per_day INTO rate
    FROM batta_rates
    WHERE grade_id = p_grade_id
      AND location_id = p_location_id
      AND is_active = TRUE
      AND effective_from <= CURRENT_DATE
      AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
    ORDER BY effective_from DESC
    LIMIT 1;
    
    RETURN COALESCE(rate, 0);
END;
$$ LANGUAGE plpgsql;

-- Function to check category cap
CREATE OR REPLACE FUNCTION check_category_cap(
    p_category_id INT,
    p_grade_id INT,
    p_amount DECIMAL(10,2)
)
RETURNS TABLE(within_limit BOOLEAN, max_amount DECIMAL(10,2), message TEXT) AS $$
DECLARE
    cap_amount DECIMAL(10,2);
BEGIN
    SELECT cc.max_amount INTO cap_amount
    FROM category_caps cc
    WHERE cc.category_id = p_category_id
      AND (cc.grade_id IS NULL OR cc.grade_id = p_grade_id)
      AND cc.is_active = TRUE
      AND cc.effective_from <= CURRENT_DATE
      AND (cc.effective_to IS NULL OR cc.effective_to >= CURRENT_DATE)
    ORDER BY cc.grade_id NULLS LAST
    LIMIT 1;
    
    IF cap_amount IS NULL THEN
        RETURN QUERY SELECT TRUE, NULL::DECIMAL(10,2), 'No cap defined'::TEXT;
    ELSIF p_amount <= cap_amount THEN
        RETURN QUERY SELECT TRUE, cap_amount, 'Within limit'::TEXT;
    ELSE
        RETURN QUERY SELECT FALSE, cap_amount, ('Exceeds cap of ' || cap_amount)::TEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- TRIGGER FOR UPDATED_AT
-- =============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to relevant tables
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY['grades', 'units', 'locations', 'claim_categories', 
                                  'employees', 'batta_rates', 'category_caps', 
                                  'claims', 'conversation_states'])
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%I_updated_at ON %I;
            CREATE TRIGGER update_%I_updated_at
                BEFORE UPDATE ON %I
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', t, t, t, t);
    END LOOP;
END;
$$;
