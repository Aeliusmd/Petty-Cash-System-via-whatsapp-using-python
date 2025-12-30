# Petty Cash System via WhatsApp (Python)

WhatsApp-based petty cash claim system using WAHA and **Python/FastAPI** with PostgreSQL.
Includes a **Next.js Admin Panel** for manager approval workflow.

## 📁 Project Structure

```
├── .env                    # Environment variables (create from .env.example)
├── .env.example            # Example environment file
├── .gitignore              # Git ignore rules
├── Dockerfile              # Docker build file
├── docker-compose.yaml     # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── run.py                  # Main entry point - run from root!
├── setup_db.py             # Database setup script
├── add_employee.py         # CLI tool to add employees
├── README.md               # This file
├── docs/                   # Documentation
│   ├── REQUIREMENTS.md     # Business requirements
│   └── USER_STORIES.md     # User stories
├── backend/
│   └── app/
│       ├── main.py         # FastAPI application + API endpoints
│       ├── reply_engine.py # WhatsApp conversation logic
│       ├── waha_client.py  # WhatsApp API client
│       ├── db/
│       │   ├── database.py # PostgreSQL connection
│       │   ├── schema.sql  # Database schema
│       │   └── seed.sql    # Seed data
│       ├── models/
│       │   ├── employee.py, claim.py, conversation.py, rates.py
│       └── services/
│           ├── textract_service.py   # AWS Textract OCR
│           ├── location_service.py   # GPS location service
│           └── notification_service.py # WhatsApp notifications
└── frontend/               # Next.js Admin Panel
    ├── src/app/
    │   ├── page.tsx        # Dashboard
    │   ├── claims/page.tsx # Claims list
    │   └── claims/[id]/page.tsx # Claim details
    └── package.json
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for Admin Panel)
- PostgreSQL (local or remote)

### Step 1: Create .env file

```powershell
Copy-Item .env.example .env
# Edit .env with your actual credentials
```

### Step 2: Set Up Database

```powershell
python setup_db.py
```

### Step 3: Start Backend Services (Docker)

```powershell
docker compose up --build
```

### Step 4: Start Admin Panel (Frontend)

```powershell
cd frontend
npm install
npm run dev
```

- **Admin Panel**: http://localhost:3000
- **Backend API**: http://localhost:4101
- **WAHA Dashboard**: http://localhost:3000/dashboard/

### Step 5: Start WAHA Session

1. Open: http://localhost:3000/dashboard/
2. Login: `admin` / `a9def4fc68164797a979facddf0b65b9`
3. Click **Start** on `default` session
4. Scan QR code with WhatsApp

### Step 6: Add Employee

```powershell
python add_employee.py 94779485361 "Visal" C CMB staff
```

---

## 📊 System Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Staff          │      │  WAHA           │      │  Python FastAPI │
│  (WhatsApp)     │◄────►│  (port 3000)    │◄────►│  (port 4101)    │
└─────────────────┘      └─────────────────┘      └────────┬────────┘
                                                           │
┌─────────────────┐                               ┌────────▼────────┐
│  Manager        │                               │  PostgreSQL     │
│  (Admin Panel)  │◄──────────────────────────────│  Database       │
└─────────────────┘      Next.js (port 3000)      └─────────────────┘
```

---

## 🔌 API Endpoints

| Endpoint                   | Method | Description                                           |
| -------------------------- | ------ | ----------------------------------------------------- |
| `/api/claims`              | GET    | List claims (filter: status, employee_id, manager_id) |
| `/api/claims/{id}`         | GET    | Get claim details                                     |
| `/api/claims/{id}/approve` | POST   | Approve claim                                         |
| `/api/claims/{id}/reject`  | POST   | Reject claim with reason                              |
| `/api/stats`               | GET    | Dashboard statistics                                  |
| `/api/employees`           | GET    | List employees                                        |
| `/health`                  | GET    | Health check                                          |
| `/webhooks/waha`           | POST   | WAHA webhook endpoint                                 |

---

## 📱 Managing Employees

```powershell
# List employees
python add_employee.py list

# Add employee
python add_employee.py <phone> "<name>" <grade> <location> [role]

# Examples
python add_employee.py 94771234567 "John Doe" B KDY staff
python add_employee.py 94779876543 "Jane Manager" A CMB manager
```

| Parameter | Options                                          |
| --------- | ------------------------------------------------ |
| Grade     | A, B, C, D, E                                    |
| Location  | CMB, KDY, GAL, JAF, ANU, KUR, RAT, BAD, TRI, BAT |
| Role      | staff, manager, admin, finance                   |

---

## 🔐 Credentials

| Service    | URL                              | Username | Password                         |
| ---------- | -------------------------------- | -------- | -------------------------------- |
| WAHA       | http://localhost:3000/dashboard/ | admin    | a9def4fc68164797a979facddf0b65b9 |
| PostgreSQL | localhost:5432                   | postgres | postgres                         |

---

## 📋 Features

### Staff (WhatsApp)

- ✅ Submit claims via WhatsApp (Batta, Fuel, Accommodation, Sundry)
- ✅ Upload receipts (OCR extraction)
- ✅ Location sharing (GPS-based batta calculation)
- ✅ Receive approval/rejection notifications

### Manager (Admin Panel)

- ✅ View dashboard with statistics
- ✅ View all claims with status filters
- ✅ Approve claims
- ✅ Reject claims with reason
- ✅ Staff receives WhatsApp notification with rejection reason

### Admin

- ✅ Configure batta rates (Grade × Location)
- ✅ Configure category caps
- ✅ Manage employees

---

## 🛠️ Development

### Run Backend Locally (without Docker)

```powershell
# Install dependencies
pip install -r requirements.txt

# Setup database
python setup_db.py

# Run server
python run.py
```

### Run Frontend

```powershell
cd frontend
npm install
npm run dev
```

### Build Frontend for Production

```powershell
cd frontend
npm run build
npm run start
```

---

## 📦 Environment Variables

Create `.env` file with:

```env
# WAHA Configuration
WAHA_API_KEY=your_waha_api_key
WHATSAPP_DEFAULT_SESSION=default

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=petty_cash_db
DB_USER=postgres
DB_PASSWORD=postgres

# AWS Textract (for receipt OCR)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=ap-south-1
```

---

## 📝 License

MIT License
