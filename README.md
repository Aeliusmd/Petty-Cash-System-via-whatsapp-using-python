# Petty Cash System via WhatsApp (Python)

WhatsApp-based petty cash claim system using WAHA and **Python/FastAPI** with PostgreSQL.
Includes a **Next.js Admin Panel** for manager approval workflow.

**Flexible Deployment:** Run everything in Docker **OR** run WAHA in Docker with Backend/Frontend locally for faster development.

## 📁 Project Structure

```
├── .env                    # Environment variables (create from .env.example)
├── .env.local              # Local dev environment (auto-created)
├── .env.example            # Example environment file
├── .gitignore              # Git ignore rules
├── Dockerfile              # Docker build file
├── docker-compose.yaml     # Docker Compose - Full mode (WAHA + Backend)
├── docker-compose.waha-only.yaml  # Docker Compose - Dev mode (WAHA only)
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
- Python 3.11+ with Conda (for Development Mode)

---

## 🎯 Two Deployment Modes

You can run this project in **two different modes** depending on your needs:

### Mode 1: Full Docker Mode (Production/Simple Setup)

**Best for:** Production, testing, or when you want everything containerized

- ✅ WAHA runs in Docker
- ✅ Backend runs in Docker
- ❌ Frontend runs separately with npm

### Mode 2: Development Mode (Faster Backend Iteration)

**Best for:** Active development, debugging, faster code changes

- ✅ WAHA runs in Docker
- ✅ Backend runs locally (Python)
- ✅ Frontend runs locally (npm)

---

## 📦 Mode 1: Full Docker Mode

### Step 1: Create .env file

```powershell
Copy-Item .env.example .env
# Edit .env with your actual credentials
```

### Step 2: Set Up Database

```powershell
# Create and activate conda environment
conda create --name petty_cash python=3.12 -y
conda activate petty_cash

# Install dependencies
pip install -r requirements.txt

# Setup database
python setup_db.py
```

### Step 3: Start All Services (Docker)

```powershell
docker compose down
docker compose up --build
```

This starts both WAHA and Backend in Docker containers.

### Step 4: Start Frontend Separately

```powershell
cd frontend
npm install
npm run dev
```

### Step 5: Start WAHA Session

1. Open: http://localhost:3000/dashboard/
2. Login: `admin` / `a9def4fc68164797a979facddf0b65b9`
3. Click **Start** on `default` session
4. Scan QR code with WhatsApp

### Step 6: Add Employee

```powershell
python add_employee.py 94779485361 "Visal" C CMB staff
```

**Access Points:**

- Admin Panel: http://localhost:3001
- Backend API: http://localhost:4101
- WAHA Dashboard: http://localhost:3000/dashboard/

---

## 🔧 Mode 2: Development Mode (Recommended for Development)

### Step 1: Create Environment Files

```powershell
# Copy .env.example to create both files
Copy-Item .env.example .env
Copy-Item .env.example .env.local

# Edit .env.local - this will be used when backend runs locally
# Make sure it has:
#   WAHA_BASE_URL=http://localhost:3000
#   DB_HOST=localhost
```

> **Note:** `.env.local` is already created for you with the correct settings!

### Step 2: Set Up Database

```powershell
# Create and activate conda environment
conda create --name petty_cash python=3.12 -y
conda activate petty_cash

# Install dependencies
pip install -r requirements.txt

# Setup database
python setup_db.py
```

### Step 3: Start Services in 3 Terminals

**Terminal 1 - WAHA (Docker):**

```powershell
docker compose -f docker-compose.waha-only.yaml up
```

**Terminal 2 - Backend (Local Python):**

```powershell
conda activate petty_cash
python run.py
```

**Terminal 3 - Frontend (Local npm):**

```powershell
cd frontend
npm install
npm run dev
```

### Step 4: Start WAHA Session

1. Open: http://localhost:3000/dashboard/
2. Login: `admin` / `a9def4fc68164797a979facddf0b65b9`
3. Click **Start** on `default` session
4. Scan QR code with WhatsApp

### Step 5: Add Employee

```powershell
# In Terminal 2 or a new terminal with conda activated
python add_employee.py 94779485361 "Visal" C CMB staff
```

**Access Points:**

- Admin Panel: http://localhost:3001
- Backend API: http://localhost:4101/docs
- WAHA Dashboard: http://localhost:3000/dashboard/

**Benefits of Development Mode:**

- 🚀 **Faster Backend Changes:** Code changes reload instantly (hot reload)
- 🐛 **Better Debugging:** Direct access to logs, better error traces
- 💻 **IDE Integration:** Full IDE debugging support for backend
- 📝 **Easy Code Edits:** No need to rebuild Docker containers

---

## 🔄 Switching Between Modes

**To switch from Full Docker → Development Mode:**

```powershell
# Stop Docker services
docker compose down

# Start WAHA only
docker compose -f docker-compose.waha-only.yaml up
# Then start backend and frontend locally (see Mode 2 Step 3)
```

**To switch from Development → Full Docker Mode:**

```powershell
# Stop WAHA-only container
docker compose -f docker-compose.waha-only.yaml down

# Stop backend (Ctrl+C in Terminal 2)
# Stop frontend (Ctrl+C in Terminal 3)

# Start full Docker
docker compose up --build
# Then start frontend separately (see Mode 1 Step 4)
```

---

## 🔄 Restarting Services

### Full Docker Mode

```powershell
docker compose down
docker compose up --build
```

### Development Mode

```powershell
# Restart WAHA (Terminal 1)
docker compose -f docker-compose.waha-only.yaml down
docker compose -f docker-compose.waha-only.yaml up

# Restart Backend (Terminal 2): Just Ctrl+C and run again
python run.py

# Restart Frontend (Terminal 3): Usually auto-reloads
# If needed: Ctrl+C and "npm run dev" again

---

## 📊 System Architecture

```

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Staff │ │ WAHA │ │ Python FastAPI │
│ (WhatsApp) │◄────►│ (port 3000) │◄────►│ (port 4101) │
└─────────────────┘ └─────────────────┘ └────────┬────────┘
│
┌─────────────────┐ ┌────────▼────────┐
│ Manager │ │ PostgreSQL │
│ (Admin Panel) │◄──────────────────────────────│ Database │
└─────────────────┘ Next.js (port 3000) └─────────────────┘

````

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
````

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

See **Mode 2: Development Mode** above for running the backend locally outside Docker.

This is the **recommended approach for active development** as it provides:

- Instant code reload with uvicorn's `--reload` flag
- Direct access to Python debugger
- Better error traces and logging
- No need to rebuild Docker containers

**Quick Reference:**

```powershell
# Terminal 1: WAHA (Docker)
docker compose -f docker-compose.waha-only.yaml up

# Terminal 2: Backend (Local)
conda activate petty_cash
python run.py

# Terminal 3: Frontend (Local)
cd frontend
npm run dev
```

---

## 📦 Environment Variables

The project uses two environment files:

### `.env` - Full Docker Mode

Used when running backend in Docker. Contains Docker network settings.

### `.env.local` - Development Mode

Used when running backend locally. Already configured with localhost settings.

**Key differences:**

| Variable      | .env (Docker)          | .env.local (Local)      |
| ------------- | ---------------------- | ----------------------- |
| WAHA_BASE_URL | `http://waha:3000`     | `http://localhost:3000` |
| DB_HOST       | `host.docker.internal` | `localhost`             |

**Required variables in both files:**

```env
# WAHA Configuration
WAHA_API_KEY=your_waha_api_key
WAHA_SESSION=default

# Database
DB_HOST=localhost  # or host.docker.internal for Docker
DB_PORT=5432
DB_NAME=petty_cash_db
DB_USER=postgres
DB_PASSWORD=postgres

# AWS Textract (for receipt OCR)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1

# OpenAI (for intelligent parsing)
OPENAI_API_KEY=your_openai_key
```

---

## 📝 License

MIT License
