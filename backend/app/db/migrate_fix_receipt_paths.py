"""
Database Migration: Fix Receipt File Paths
Converts full absolute paths to just filenames in claim_receipts table
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import Database


async def migrate_receipt_paths():
    """Update claim_receipts to store only filenames instead of full paths"""
    
    # Create database instance
    db = Database()
    
    try:
        print("🔄 Starting migration: fix receipt file paths...")
        
        # Connect to database
        await db.connect()
        
        # Get all receipts with their current file_path
        receipts = await db.query("""
            SELECT id, file_path 
            FROM claim_receipts
            WHERE file_path IS NOT NULL
        """)
        
        print(f"📊 Found {len(receipts)} receipt records to check")
        
        updated_count = 0
        
        for receipt in receipts:
            receipt_id = receipt['id']
            current_path = receipt['file_path']
            
            # Check if path contains directory separators (full path)
            if '/' in current_path or '\\' in current_path:
                # Extract just the filename
                # Handle both Windows and Unix paths
                normalized_path = current_path.replace('\\', '/')
                filename = normalized_path.split('/')[-1]
                
                # Update the record
                await db.execute("""
                    UPDATE claim_receipts 
                    SET file_path = $1 
                    WHERE id = $2
                """, filename, receipt_id)
                
                print(f"✅ Updated receipt {receipt_id}: {current_path} → {filename}")
                updated_count += 1
            else:
                # Already just a filename, skip
                pass
        
        print(f"✅ Migration complete! Updated {updated_count} records")
        
        # Close connection
        await db.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        await db.close()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(migrate_receipt_paths())
