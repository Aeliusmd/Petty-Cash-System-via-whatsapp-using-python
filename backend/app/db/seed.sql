-- Petty Cash Management System - Seed Data
-- Run this after schema.sql to populate initial master data

-- =============================================
-- CLAIM STATUSES
-- =============================================
INSERT INTO claim_statuses (code, name, description, display_order) VALUES
('DRAFT', 'Draft', 'Claim is being prepared', 1),
('PENDING', 'Pending Approval', 'Awaiting manager approval', 2),
('APPROVED', 'Approved', 'Claim has been approved', 3),
('REJECTED', 'Rejected', 'Claim has been rejected', 4),
('PAID', 'Paid', 'Claim has been reimbursed', 5)
ON CONFLICT (code) DO NOTHING;

-- =============================================
-- GRADES
-- =============================================
INSERT INTO grades (code, name, description) VALUES
('A', 'Grade A', 'Senior Management'),
('B', 'Grade B', 'Middle Management'),
('C', 'Grade C', 'Executives'),
('D', 'Grade D', 'Staff'),
('E', 'Grade E', 'Junior Staff')
ON CONFLICT (code) DO NOTHING;

-- =============================================
-- UNITS / DEPARTMENTS
-- =============================================
INSERT INTO units (code, name) VALUES
('FIN', 'Finance'),
('HR', 'Human Resources'),
('IT', 'Information Technology'),
('OPS', 'Operations'),
('SALES', 'Sales'),
('ADMIN', 'Administration'),
('MKT', 'Marketing')
ON CONFLICT (code) DO NOTHING;

-- =============================================
-- LOCATIONS
-- =============================================
INSERT INTO locations (code, name) VALUES
('CMB', 'Colombo'),
('KDY', 'Kandy'),
('GAL', 'Galle'),
('JAF', 'Jaffna'),
('ANU', 'Anuradhapura'),
('KUR', 'Kurunegala'),
('RAT', 'Ratnapura'),
('BAD', 'Badulla'),
('TRI', 'Trincomalee'),
('BAT', 'Batticaloa')
ON CONFLICT (code) DO NOTHING;

-- =============================================
-- CLAIM CATEGORIES
-- =============================================
INSERT INTO claim_categories (code, name, description, requires_receipt, display_order) VALUES
('BATTA', 'Batta (Daily Allowance)', 'Daily allowance for official travel', FALSE, 1),
('FUEL', 'Fuel Expenses', 'Vehicle fuel reimbursement', TRUE, 2),
('ACCOM', 'Accommodation', 'Hotel and lodging expenses', TRUE, 3),
('SUNDRY', 'Sundry Expenses', 'Miscellaneous expenses', FALSE, 4)
ON CONFLICT (code) DO NOTHING;

-- =============================================
-- BATTA RATES (Grade × Location)
-- =============================================
-- Grade A rates
INSERT INTO batta_rates (grade_id, location_id, rate_per_day) VALUES
((SELECT id FROM grades WHERE code = 'A'), (SELECT id FROM locations WHERE code = 'CMB'), 2500.00),
((SELECT id FROM grades WHERE code = 'A'), (SELECT id FROM locations WHERE code = 'KDY'), 2200.00),
((SELECT id FROM grades WHERE code = 'A'), (SELECT id FROM locations WHERE code = 'GAL'), 2200.00),
((SELECT id FROM grades WHERE code = 'A'), (SELECT id FROM locations WHERE code = 'JAF'), 2500.00),
((SELECT id FROM grades WHERE code = 'A'), (SELECT id FROM locations WHERE code = 'ANU'), 2000.00),
((SELECT id FROM grades WHERE code = 'A'), (SELECT id FROM locations WHERE code = 'KUR'), 2000.00),
((SELECT id FROM grades WHERE code = 'A'), (SELECT id FROM locations WHERE code = 'RAT'), 2000.00),
((SELECT id FROM grades WHERE code = 'A'), (SELECT id FROM locations WHERE code = 'BAD'), 2200.00),
((SELECT id FROM grades WHERE code = 'A'), (SELECT id FROM locations WHERE code = 'TRI'), 2500.00),
((SELECT id FROM grades WHERE code = 'A'), (SELECT id FROM locations WHERE code = 'BAT'), 2500.00)
ON CONFLICT DO NOTHING;

-- Grade B rates
INSERT INTO batta_rates (grade_id, location_id, rate_per_day) VALUES
((SELECT id FROM grades WHERE code = 'B'), (SELECT id FROM locations WHERE code = 'CMB'), 2000.00),
((SELECT id FROM grades WHERE code = 'B'), (SELECT id FROM locations WHERE code = 'KDY'), 1800.00),
((SELECT id FROM grades WHERE code = 'B'), (SELECT id FROM locations WHERE code = 'GAL'), 1800.00),
((SELECT id FROM grades WHERE code = 'B'), (SELECT id FROM locations WHERE code = 'JAF'), 2000.00),
((SELECT id FROM grades WHERE code = 'B'), (SELECT id FROM locations WHERE code = 'ANU'), 1600.00),
((SELECT id FROM grades WHERE code = 'B'), (SELECT id FROM locations WHERE code = 'KUR'), 1600.00),
((SELECT id FROM grades WHERE code = 'B'), (SELECT id FROM locations WHERE code = 'RAT'), 1600.00),
((SELECT id FROM grades WHERE code = 'B'), (SELECT id FROM locations WHERE code = 'BAD'), 1800.00),
((SELECT id FROM grades WHERE code = 'B'), (SELECT id FROM locations WHERE code = 'TRI'), 2000.00),
((SELECT id FROM grades WHERE code = 'B'), (SELECT id FROM locations WHERE code = 'BAT'), 2000.00)
ON CONFLICT DO NOTHING;

-- Grade C rates
INSERT INTO batta_rates (grade_id, location_id, rate_per_day) VALUES
((SELECT id FROM grades WHERE code = 'C'), (SELECT id FROM locations WHERE code = 'CMB'), 1800.00),
((SELECT id FROM grades WHERE code = 'C'), (SELECT id FROM locations WHERE code = 'KDY'), 1500.00),
((SELECT id FROM grades WHERE code = 'C'), (SELECT id FROM locations WHERE code = 'GAL'), 1500.00),
((SELECT id FROM grades WHERE code = 'C'), (SELECT id FROM locations WHERE code = 'JAF'), 1800.00),
((SELECT id FROM grades WHERE code = 'C'), (SELECT id FROM locations WHERE code = 'ANU'), 1400.00),
((SELECT id FROM grades WHERE code = 'C'), (SELECT id FROM locations WHERE code = 'KUR'), 1400.00),
((SELECT id FROM grades WHERE code = 'C'), (SELECT id FROM locations WHERE code = 'RAT'), 1400.00),
((SELECT id FROM grades WHERE code = 'C'), (SELECT id FROM locations WHERE code = 'BAD'), 1500.00),
((SELECT id FROM grades WHERE code = 'C'), (SELECT id FROM locations WHERE code = 'TRI'), 1800.00),
((SELECT id FROM grades WHERE code = 'C'), (SELECT id FROM locations WHERE code = 'BAT'), 1800.00)
ON CONFLICT DO NOTHING;

-- Grade D rates
INSERT INTO batta_rates (grade_id, location_id, rate_per_day) VALUES
((SELECT id FROM grades WHERE code = 'D'), (SELECT id FROM locations WHERE code = 'CMB'), 1500.00),
((SELECT id FROM grades WHERE code = 'D'), (SELECT id FROM locations WHERE code = 'KDY'), 1200.00),
((SELECT id FROM grades WHERE code = 'D'), (SELECT id FROM locations WHERE code = 'GAL'), 1200.00),
((SELECT id FROM grades WHERE code = 'D'), (SELECT id FROM locations WHERE code = 'JAF'), 1500.00),
((SELECT id FROM grades WHERE code = 'D'), (SELECT id FROM locations WHERE code = 'ANU'), 1100.00),
((SELECT id FROM grades WHERE code = 'D'), (SELECT id FROM locations WHERE code = 'KUR'), 1100.00),
((SELECT id FROM grades WHERE code = 'D'), (SELECT id FROM locations WHERE code = 'RAT'), 1100.00),
((SELECT id FROM grades WHERE code = 'D'), (SELECT id FROM locations WHERE code = 'BAD'), 1200.00),
((SELECT id FROM grades WHERE code = 'D'), (SELECT id FROM locations WHERE code = 'TRI'), 1500.00),
((SELECT id FROM grades WHERE code = 'D'), (SELECT id FROM locations WHERE code = 'BAT'), 1500.00)
ON CONFLICT DO NOTHING;

-- Grade E rates
INSERT INTO batta_rates (grade_id, location_id, rate_per_day) VALUES
((SELECT id FROM grades WHERE code = 'E'), (SELECT id FROM locations WHERE code = 'CMB'), 1200.00),
((SELECT id FROM grades WHERE code = 'E'), (SELECT id FROM locations WHERE code = 'KDY'), 1000.00),
((SELECT id FROM grades WHERE code = 'E'), (SELECT id FROM locations WHERE code = 'GAL'), 1000.00),
((SELECT id FROM grades WHERE code = 'E'), (SELECT id FROM locations WHERE code = 'JAF'), 1200.00),
((SELECT id FROM grades WHERE code = 'E'), (SELECT id FROM locations WHERE code = 'ANU'), 900.00),
((SELECT id FROM grades WHERE code = 'E'), (SELECT id FROM locations WHERE code = 'KUR'), 900.00),
((SELECT id FROM grades WHERE code = 'E'), (SELECT id FROM locations WHERE code = 'RAT'), 900.00),
((SELECT id FROM grades WHERE code = 'E'), (SELECT id FROM locations WHERE code = 'BAD'), 1000.00),
((SELECT id FROM grades WHERE code = 'E'), (SELECT id FROM locations WHERE code = 'TRI'), 1200.00),
((SELECT id FROM grades WHERE code = 'E'), (SELECT id FROM locations WHERE code = 'BAT'), 1200.00)
ON CONFLICT DO NOTHING;

-- =============================================
-- CATEGORY CAPS (Monthly limits)
-- =============================================
INSERT INTO category_caps (category_id, grade_id, max_amount, period) VALUES
-- Fuel caps by grade
((SELECT id FROM claim_categories WHERE code = 'FUEL'), (SELECT id FROM grades WHERE code = 'A'), 25000.00, 'monthly'),
((SELECT id FROM claim_categories WHERE code = 'FUEL'), (SELECT id FROM grades WHERE code = 'B'), 20000.00, 'monthly'),
((SELECT id FROM claim_categories WHERE code = 'FUEL'), (SELECT id FROM grades WHERE code = 'C'), 15000.00, 'monthly'),
((SELECT id FROM claim_categories WHERE code = 'FUEL'), (SELECT id FROM grades WHERE code = 'D'), 10000.00, 'monthly'),
((SELECT id FROM claim_categories WHERE code = 'FUEL'), (SELECT id FROM grades WHERE code = 'E'), 7500.00, 'monthly'),

-- Accommodation caps (per claim)
((SELECT id FROM claim_categories WHERE code = 'ACCOM'), (SELECT id FROM grades WHERE code = 'A'), 8000.00, 'daily'),
((SELECT id FROM claim_categories WHERE code = 'ACCOM'), (SELECT id FROM grades WHERE code = 'B'), 6000.00, 'daily'),
((SELECT id FROM claim_categories WHERE code = 'ACCOM'), (SELECT id FROM grades WHERE code = 'C'), 5000.00, 'daily'),
((SELECT id FROM claim_categories WHERE code = 'ACCOM'), (SELECT id FROM grades WHERE code = 'D'), 4000.00, 'daily'),
((SELECT id FROM claim_categories WHERE code = 'ACCOM'), (SELECT id FROM grades WHERE code = 'E'), 3000.00, 'daily'),

-- Sundry caps (monthly)
((SELECT id FROM claim_categories WHERE code = 'SUNDRY'), NULL, 5000.00, 'monthly')
ON CONFLICT DO NOTHING;

-- =============================================
-- SAMPLE EMPLOYEES (for testing)
-- =============================================
INSERT INTO employees (employee_code, name, phone_number, grade_id, unit_id, location_id, role) VALUES
('EMP001', 'John Manager', '94771234567', 
    (SELECT id FROM grades WHERE code = 'A'),
    (SELECT id FROM units WHERE code = 'FIN'),
    (SELECT id FROM locations WHERE code = 'CMB'),
    'manager'),
('EMP002', 'Jane Staff', '94777654321',
    (SELECT id FROM grades WHERE code = 'C'),
    (SELECT id FROM units WHERE code = 'FIN'),
    (SELECT id FROM locations WHERE code = 'CMB'),
    'staff'),
('EMP003', 'Bob Admin', '94779876543',
    (SELECT id FROM grades WHERE code = 'B'),
    (SELECT id FROM units WHERE code = 'ADMIN'),
    (SELECT id FROM locations WHERE code = 'CMB'),
    'admin')
ON CONFLICT (employee_code) DO NOTHING;

-- Set manager relationships
UPDATE employees SET manager_id = (SELECT id FROM employees WHERE employee_code = 'EMP001')
WHERE employee_code IN ('EMP002', 'EMP003');

-- =============================================
-- VERIFICATION QUERIES
-- =============================================
-- Run these to verify data:
-- SELECT * FROM grades;
-- SELECT * FROM locations;
-- SELECT * FROM claim_categories;
-- SELECT g.code as grade, l.code as location, br.rate_per_day FROM batta_rates br JOIN grades g ON br.grade_id = g.id JOIN locations l ON br.location_id = l.id ORDER BY g.code, l.code;
-- SELECT * FROM employees;
