"""
Concurrency Test for Bulk Receipt Upload
Tests that multiple concurrent receipt uploads don't lose data due to race conditions
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import db
from app.models import conversation as conversation_model


async def test_concurrent_receipts():
    """Test that concurrent receipt additions don't lose data"""
    print("🧪 Testing concurrent receipt uploads...")
    
    # Connect to database
    await db.connect()
    
    # Test chat ID
    test_chat_id = "test_concurrent_12345@c.us"
    
    # Clean up any existing test data
    await db.execute("DELETE FROM conversation_states WHERE chat_id = $1", test_chat_id)
    
    # Create initial conversation
    await conversation_model.get_or_create(test_chat_id)
    await conversation_model.update(test_chat_id, {
        'current_step': 'receipt_upload',
        'category': 'FUEL',
        'context': {'user_amount': 5000}
    })
    
    print(f"✅ Created test conversation: {test_chat_id}")
    
    # Create 10 test receipts
    receipts = [
        {'file_path': f'receipt_{i}.jpg', 'ocr_amount': 500 + i*10, 'vendor': f'Vendor {i}'}
        for i in range(1, 11)
    ]
    
    print(f"📤 Uploading {len(receipts)} receipts concurrently...")
    
    # Upload all receipts concurrently (simulates bulk upload)
    tasks = [
        conversation_model.add_receipt(test_chat_id, receipt)
        for receipt in receipts
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify all receipts were saved
    final_state = await conversation_model.get_or_create(test_chat_id)
    
    import json
    context = final_state.get('context')
    if isinstance(context, str):
        context = json.loads(context)
    
    saved_receipts = context.get('receipts', [])
    
    print(f"\n📊 Results:")
    print(f"   Expected receipts: {len(receipts)}")
    print(f"   Saved receipts: {len(saved_receipts)}")
    
    if len(saved_receipts) == len(receipts):
        print(f"   ✅ SUCCESS: All receipts saved correctly!")
        
        # Verify amounts
        total = sum(r.get('ocr_amount', 0) for r in saved_receipts)
        expected_total = sum(r['ocr_amount'] for r in receipts)
        print(f"   Total amount: Rs.{total} (expected: Rs.{expected_total})")
        
        if total == expected_total:
            print(f"   ✅ Amounts match!")
        else:
            print(f"   ❌ Amount mismatch!")
    else:
        print(f"   ❌ FAILURE: Lost {len(receipts) - len(saved_receipts)} receipts due to race condition!")
        print(f"\n   Saved receipts:")
        for i, r in enumerate(saved_receipts, 1):
            print(f"      {i}. {r.get('vendor')} - Rs.{r.get('ocr_amount')}")
    
    # Clean up
    await db.execute("DELETE FROM conversation_states WHERE chat_id = $1", test_chat_id)
    await db.close()
    
    return len(saved_receipts) == len(receipts)


if __name__ == "__main__":
    success = asyncio.run(test_concurrent_receipts())
    sys.exit(0 if success else 1)
