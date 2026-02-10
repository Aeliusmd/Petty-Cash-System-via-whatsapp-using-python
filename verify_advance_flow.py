
import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).parent / 'backend'
sys.path.append(str(backend_path))

from app.db.database import db
from app import reply_engine
from app.models.employee import Employee
from app.models.claim import Claim

async def verify_flow():
    print("🚀 Starting Verification for Advance Flow...")
    await db.connect()
    
    try:
        # 1. Get a test employee
        # Use a known test number or just the first active one
        rows = await db.query("SELECT * FROM employees WHERE is_active = TRUE LIMIT 1")
        if not rows:
            print("❌ No active employees found for testing")
            return
            
        employee = Employee(rows[0])
        chat_id = employee.whatsapp_chat_id or f"{employee.phone_number}@c.us"
        print(f"👤 Testing with Employee: {employee.name} (ID: {employee.id})")
        
        # 2. Test Step 1: Main Menu
        print("\n--- Test 1: Main Menu ---")
        response = await reply_engine.process_message(chat_id, "hi", employee_id=employee.id)
        print(f"🤖 Bot: {response[:100]}...")
        if "1️⃣ Reimbursement" in response and "2️⃣ Advance Request" in response:
            print("✅ Main menu updated correctly")
        else:
            print("❌ Main menu NOT updated")
            print(response)
            return

        # 3. Test Step 2: Select Advance
        print("\n--- Test 2: Select Advance ---")
        response = await reply_engine.process_message(chat_id, "2", employee_id=employee.id)
        print(f"🤖 Bot: {response}")
        if "Advance Request" in response and "category" in response.lower():
            print("✅ Advance selection works (Asking for category)")
        else:
            print("❌ Advance selection failed (Not asking for category)")
            return

        # 3.5 Test Step 2.5: Select Category
        print("\n--- Test 2.5: Select Category ---")
        # Assuming category 1 exists and is valid
        response = await reply_engine.process_message(chat_id, "1", employee_id=employee.id) 
        print(f"🤖 Bot: {response}")
        if "amount" in response.lower():
             print("✅ Category selected, asking for amount")
        else:
             print("❌ Category selection failed")
             return

        # 4. Test Step 3: Enter Amount
        print("\n--- Test 3: Enter Amount ---")
        response = await reply_engine.process_message(chat_id, "5000", employee_id=employee.id)
        print(f"🤖 Bot: {response}")
        if "What is this advance for" in response:
             print("✅ Amount accepted")
        else:
             print("❌ Amount rejected")
             return

        # 5. Test Step 4: Enter Description
        print("\n--- Test 4: Enter Description ---")
        response = await reply_engine.process_message(chat_id, "Test Advance Verification", employee_id=employee.id)
        print(f"🤖 Bot: {response}")
        if "Upload Quotation" in response and "skip" in response:
             print("✅ Description accepted, asking for quotation")
        else:
             print("❌ Description flow failed")
             return

        # 6. Test Step 5: Skip Quotation
        print("\n--- Test 5: Skip Quotation ---")
        response = await reply_engine.process_message(chat_id, "skip", employee_id=employee.id)
        print(f"🤖 Bot: {response}")
        if "Advance Request Summary" in response and "5,000" in response:
             print("✅ Skip works, summary shown")
        else:
             print("❌ Skip failed")
             return

        # 7. Test Step 6: Confirm
        print("\n--- Test 6: Confirm ---")
        response = await reply_engine.process_message(chat_id, "confirm", employee_id=employee.id)
        print(f"🤖 Bot: {response}")
        if "Advance Request Submitted" in response:
             print("✅ Confirmation worked")
             
             # Verify DB
             latest_claim = await db.query_one("SELECT * FROM claims WHERE employee_id = $1 ORDER BY id DESC LIMIT 1", employee.id)
             if latest_claim and latest_claim['claim_type'] == 'advance':
                 print(f"✅ DB Verification Pending: Claim ID {latest_claim['id']} has claim_type='{latest_claim['claim_type']}'")
             else:
                 print(f"❌ DB Verification Failed: {latest_claim}")
                 
        else:
             print("❌ Confirmation failed")
             return
             
    except Exception as e:
        print(f"❌ Verification Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(verify_flow())
