-- Migration: Add prompt_message to claim_categories
-- This allows each category to have a custom prompt message shown to users

-- Add prompt_message column
ALTER TABLE claim_categories 
ADD COLUMN IF NOT EXISTS prompt_message TEXT;

-- Set default prompt messages for existing categories
UPDATE claim_categories 
SET prompt_message = 
    CASE 
        WHEN LOWER(name) LIKE '%batta%' OR LOWER(code) = 'batta' THEN 
            E'📦 Daily Allowance Claim\n\nPlease provide:\n• Date of travel\n• Location/Route\n• Purpose\n\nExample: "2024-01-15, Colombo to Galle, Client meeting"'
        
        WHEN LOWER(name) LIKE '%fuel%' OR LOWER(code) = 'fuel' THEN 
            E'⛽ Fuel Expense Claim\n\nPlease provide:\n• Date\n• Amount (Rs.)\n• Vehicle number\n• Purpose/Destination\n\nExample: "2024-01-15, Rs.5000, CAR-1234, Site visit to Kandy"'
        
        WHEN LOWER(name) LIKE '%accom%' OR LOWER(code) = 'accom' THEN 
            E'🏨 Accommodation Claim\n\nPlease provide:\n• Hotel name\n• Check-in and Check-out dates\n• Amount (Rs.)\n• Purpose\n\nExample: "Hotel Cinnamon, 15-16 Jan, Rs.8000, Conference attendance"'
        
        WHEN LOWER(name) LIKE '%sundry%' OR LOWER(code) = 'sundry' THEN 
            E'📝 Sundry Expense Claim\n\nPlease describe:\n• What was purchased\n• Amount (Rs.)\n• Purpose\n\nExample: "Stationery supplies, Rs.1500, Office use"'
        
        ELSE 
            E'📝 Expense Claim\n\nPlease provide:\n• Description of expense\n• Amount (Rs.)\n• Purpose\n\nExample: "Office supplies, Rs.2000, Team meeting"'
    END
WHERE prompt_message IS NULL;

-- Add comment
COMMENT ON COLUMN claim_categories.prompt_message IS 'Custom prompt message shown to users when they select this category';
