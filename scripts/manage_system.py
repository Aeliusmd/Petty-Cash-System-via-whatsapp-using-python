
import asyncio
import httpx
import os
import sys
from getpass import getpass

# Configuration
API_URL = "http://localhost:4101"

# Colors for pretty output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

async def login():
    print(f"{Colors.HEADER}--- Login Required ---{Colors.ENDC}")
    phone = input("Enter Admin Phone Number: ").strip()
    
    # Request OTP
    async with httpx.AsyncClient() as client:
        try:
            print("Requesting OTP...")
            # Using a simplified flow assuming we can get the OTP code from the logs or if it's test environment
            # For this script to be user-friendly in dev, we might need a way to bypass or see the OTP.
            # But normally we'd ask user to check WhatsApp.
            
            resp = await client.post(f"{API_URL}/api/auth/request-otp", json={"phone_number": phone})
            if resp.status_code != 200:
                print(f"{Colors.FAIL}Error requesting OTP: {resp.text}{Colors.ENDC}")
                return None
            
            # Check if OTP was returned (dev mode)
            otp_code = resp.json().get('otp_code')
            if otp_code:
                print(f"{Colors.GREEN}DEV MODE: OTP is {otp_code}{Colors.ENDC}")
            else:
                print(f"{Colors.BLUE}OTP sent to WhatsApp. Please check.{Colors.ENDC}")
            
            otp_code = input("Enter OTP Code: ").strip()
            
            # Verify
            resp = await client.post(f"{API_URL}/api/auth/verify-otp", json={
                "phone_number": phone, 
                "otp_code": otp_code
            })
            
            if resp.status_code != 200:
                print(f"{Colors.FAIL}Login failed: {resp.text}{Colors.ENDC}")
                return None
                
            token = resp.json()['access_token']
            print(f"{Colors.GREEN}Login successful!{Colors.ENDC}")
            return token
            
        except Exception as e:
            print(f"{Colors.FAIL}Connection error: {e}{Colors.ENDC}")
            return None

async def manage_departments(client, headers):
    while True:
        print(f"\n{Colors.HEADER}--- Manage Departments (Units) ---{Colors.ENDC}")
        print("1. List Departments")
        print("2. Create Department")
        print("3. Delete Department")
        print("0. Back")
        
        choice = input("Select option: ").strip()
        
        if choice == '1':
            resp = await client.get(f"{API_URL}/api/units", headers=headers)
            if resp.status_code == 200:
                units = resp.json().get('units', [])
                print(f"\n{Colors.BOLD}Departments ({len(units)}):{Colors.ENDC}")
                print(f"{'ID':<5} {'Code':<10} {'Name':<30} {'Active'}")
                print("-" * 60)
                for u in units:
                    status = "✅" if u['is_active'] else "❌"
                    print(f"{u['id']:<5} {u['code']:<10} {u['name']:<30} {status}")
            else:
                print(f"{Colors.FAIL}Error: {resp.text}{Colors.ENDC}")
                
        elif choice == '2':
            code = input("Enter Department Code (e.g. HR, IT): ").strip()
            name = input("Enter Department Name: ").strip()
            data = {"code": code, "name": name, "is_active": True}
            
            resp = await client.post(f"{API_URL}/api/units", json=data, headers=headers)
            if resp.status_code == 200:
                print(f"{Colors.GREEN}Department created successfully!{Colors.ENDC}")
            else:
                 print(f"{Colors.FAIL}Error: {resp.text}{Colors.ENDC}")
                 
        elif choice == '3':
            uid = input("Enter Department ID to delete: ").strip()
            if not uid.isdigit():
                continue
            
            # Since my unit endpoint is super admin only, this might fail if logged in as regular admin
            # But let's try
            resp = await client.delete(f"{API_URL}/api/units/{uid}", headers=headers)
            if resp.status_code == 200:
                 print(f"{Colors.GREEN}Department deleted.{Colors.ENDC}")
            else:
                 print(f"{Colors.FAIL}Error: {resp.text}{Colors.ENDC}")
                 
        elif choice == '0':
            break

async def manage_categories(client, headers):
    # 1. Select Organization
    print(f"\n{Colors.BLUE}Fetching organizations...{Colors.ENDC}")
    resp = await client.get(f"{API_URL}/api/organizations", headers=headers)
    if resp.status_code != 200:
         print(f"{Colors.FAIL}Failed to fetch organizations.{Colors.ENDC}")
         return
    
    orgs = resp.json().get('organizations', [])
    if not orgs:
        print("No organizations found.")
        return
        
    print(f"\n{Colors.HEADER}--- Select Organization ---{Colors.ENDC}")
    for o in orgs:
        print(f"{o['id']}. {o['name']} ({o['code']})")
        
    org_id_input = input("\nEnter Organization ID: ").strip()
    if not org_id_input.isdigit():
        print("Invalid ID")
        return
    org_id = int(org_id_input)
    selected_org = next((o for o in orgs if o['id'] == org_id), None)
    if not selected_org:
        print("Organization not found.")
        return

    # 2. Select Department (Unit)
    print(f"\n{Colors.BLUE}Fetching departments for {selected_org['name']}...{Colors.ENDC}")
    resp = await client.get(f"{API_URL}/api/organizations/{org_id}/units", headers=headers)
    if resp.status_code != 200:
         print(f"{Colors.FAIL}Failed to fetch departments.{Colors.ENDC}")
         return
    
    units = resp.json().get('units', [])
    if not units:
        print("No departments found for this organization.")
        return
        
    print(f"\n{Colors.HEADER}--- Select Department ---{Colors.ENDC}")
    for u in units:
        print(f"{u['id']}. {u['name']} ({u['code']})")
    
    unit_id_input = input("\nEnter Department ID: ").strip()
    if not unit_id_input.isdigit():
         print("Invalid ID")
         return
    selected_unit_id = int(unit_id_input)
    selected_unit = next((u for u in units if u['id'] == selected_unit_id), None)
    if not selected_unit:
        print("Department not found.")
        return
        
    while True:
        print(f"\n{Colors.HEADER}--- Manage Categories [{selected_org['name']} > {selected_unit['name']}] ---{Colors.ENDC}")
        print("1. List Categories")
        print("2. Create Category")
        print("3. Delete Category")
        print("0. Back")
        
        choice = input("Select option: ").strip()
        
        if choice == '1':
            params = {'unit_id': selected_unit_id}
            resp = await client.get(f"{API_URL}/api/categories", params=params, headers=headers)
            if resp.status_code == 200:
                cats = resp.json().get('categories', [])
                print(f"\n{Colors.BOLD}Categories ({len(cats)}):{Colors.ENDC}")
                print(f"{'ID':<5} {'Code':<10} {'Name':<30} {'Order'}")
                print("-" * 60)
                for c in cats:
                    order = c.get('display_order', 0)
                    print(f"{c.get('id'):<5} {c.get('code'):<10} {c.get('name'):<30} {order}")
            else:
                 print(f"{Colors.FAIL}Error: {resp.text}{Colors.ENDC}")
                 
        elif choice == '2':
            code = input("Enter Category Code (e.g. FOOD): ").strip().upper()
            name = input("Enter Category Name: ").strip()
            desc = input("Description (optional): ").strip()
            order = input("Display Order (0-100): ").strip() or "0"
            
            data = {
                "code": code,
                "name": name,
                "description": desc,
                "display_order": int(order),
                "unit_id": selected_unit_id,
                "is_active": True
            }
            
            print(f"DEBUG: sending POST to {API_URL}/api/categories with data: {data}")
            resp = await client.post(f"{API_URL}/api/categories", json=data, headers=headers, follow_redirects=True)
            if resp.status_code == 200:
                print(f"{Colors.GREEN}Category created successfully!{Colors.ENDC}")
            else:
                 print(f"{Colors.FAIL}Error {resp.status_code}: {resp.text}{Colors.ENDC}")
                 
        elif choice == '3':
            cid = input("Enter Category ID to delete: ").strip()
            if not cid.isdigit(): continue
            
            resp = await client.delete(f"{API_URL}/api/categories/{cid}", headers=headers)
            if resp.status_code == 200:
                 print(f"{Colors.GREEN}Category deleted.{Colors.ENDC}")
            else:
                 print(f"{Colors.FAIL}Error: {resp.text}{Colors.ENDC}")
                 
        elif choice == '0':
            break

async def main():
    print(f"{Colors.BOLD}=== Petty Cash Management System ==={Colors.ENDC}")
    token = await login()
    if not token:
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        while True:
            print(f"\n{Colors.HEADER}--- Main Menu ---{Colors.ENDC}")
            print("1. Manage Departments (Units)")
            print("2. Manage Categories")
            print("0. Exit")
            
            choice = input("Select option: ").strip()
            
            if choice == '1':
                await manage_departments(client, headers)
            elif choice == '2':
                await manage_categories(client, headers)
            elif choice == '0':
                print("Goodbye!")
                break
            else:
                print("Invalid option")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
