-- Add message_id column to claim_receipts table
-- This enables receipt forwarding during appeals

ALTER TABLE claim_receipts 
ADD COLUMN IF NOT EXISTS message_id TEXT;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_claim_receipts_message_id 
ON claim_receipts(message_id);
