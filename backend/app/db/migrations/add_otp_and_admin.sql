-- Migration: Add OTP codes table and is_admin column to employees

-- Create OTP codes table for authentication
CREATE TABLE IF NOT EXISTS otp_codes (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL,
    code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_phone_number (phone_number),
    INDEX idx_expires_at (expires_at)
);

-- Add is_admin column to employees table
ALTER TABLE employees 
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- Set first employee as admin (optional - update as needed)
-- UPDATE employees SET is_admin = TRUE WHERE id = 1;
