-- Add vendor column to claim_receipts table
-- This stores the vendor/merchant name extracted from receipts via OCR

ALTER TABLE claim_receipts 
ADD COLUMN IF NOT EXISTS vendor VARCHAR(255);

-- Add index for vendor searches
CREATE INDEX IF NOT EXISTS idx_claim_receipts_vendor 
ON claim_receipts(vendor);
