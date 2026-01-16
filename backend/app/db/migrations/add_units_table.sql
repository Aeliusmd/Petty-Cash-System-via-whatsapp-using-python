-- Migration: Add units (organizations) table
-- Run this to create the units table for organizational management

CREATE TABLE IF NOT EXISTS units (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert some default units
INSERT INTO units (code, name) VALUES
    ('HQ', 'Headquarters'),
    ('SALES', 'Sales Department'),
    ('OPS', 'Operations')
ON CONFLICT (code) DO NOTHING;
