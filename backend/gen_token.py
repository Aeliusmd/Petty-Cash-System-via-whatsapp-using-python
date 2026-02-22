import asyncio
from app.db.database import db
from app.models.employee import Employee
from app.services.auth_service import AuthService

async def main():
    await db.connect()
    
    # 1. Get super admin
    employees = await Employee.find_all()
    super_admin = next((e for e in employees if e.role == 'super_admin'), employees[0])
    
    # 2. Generate token
    auth_service = AuthService()
    token = await auth_service.create_access_token(super_admin)
    print("TOKEN_START", token, "TOKEN_END")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
