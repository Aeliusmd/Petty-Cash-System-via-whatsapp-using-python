"""
Rebuild structured ocr_raw_text for existing claim_receipts.

For receipts that have vendor/ocr_amount stored but ocr_raw_text is either
empty or raw unstructured text, this script rebuilds a structured
"Key: Value" format so the frontend can display it properly.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env.local'))

from app.db.database import db

async def rebuild_ocr_text():
    await db.connect()
    try:
        # Get all receipts that have vendor or ocr_amount but need structured text
        receipts = await db.query("""
            SELECT id, vendor, ocr_amount, ocr_raw_text
            FROM claim_receipts
            ORDER BY id
        """)
        
        print(f"Found {len(receipts)} total receipts")
        updated = 0

        for r in receipts:
            vendor = r.get('vendor') or ''
            ocr_amount = r.get('ocr_amount')
            existing_text = (r.get('ocr_raw_text') or '').strip()

            # Check if existing text is already structured (has "Key: Value" lines)
            has_structured = any(
                ':' in line and line.index(':') > 0 and line.index(':') < len(line) - 1
                for line in existing_text.split('\n')
                if line.strip() and line.strip() != '---'
            )

            if has_structured:
                # Already structured, skip
                continue

            # Build structured text from available columns
            structured_lines = []
            if vendor:
                structured_lines.append(f"Vendor: {vendor}")
            if ocr_amount:
                structured_lines.append(f"Total: {ocr_amount}")

            # Append existing raw text after separator if it has content
            if existing_text and existing_text != '---':
                structured_lines.append("---")
                structured_lines.append(existing_text)

            if not structured_lines:
                continue  # Nothing to update

            new_text = '\n'.join(structured_lines)

            await db.query(
                "UPDATE claim_receipts SET ocr_raw_text = $1 WHERE id = $2",
                new_text, r['id']
            )
            updated += 1
            print(f"  Receipt #{r['id']}: rebuilt -> {new_text[:80]}")

        print(f"\nDone. Updated {updated} receipts.")
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(rebuild_ocr_text())
