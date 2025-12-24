# Petty Cash System via WhatsApp (Python)

WhatsApp-based petty cash claim system using WAHA and **Python/FastAPI** with PostgreSQL.

## 📁 Project Structure

```
├── .env                    # Environment variables (create from .env.example)
├── .env.example            # Example environment file
├── .gitignore              # Git ignore rules
├── Dockerfile              # Docker build file
├── docker-compose.yaml     # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── run.py                  # Main entry point - run from root!
├── README.md               # This file
└── backend/
    └── app/
        ├── main.py         # FastAPI application
        ├── reply_engine.py # Conversation logic
        ├── waha_client.py  # WhatsApp API client
        ├── db/
        │   ├── database.py # PostgreSQL connection
        │   ├── setup.py    # Database initialization
        │   ├── add_employee.py # CLI tool
        │   ├── schema.sql  # Database schema
        │   └── seed.sql    # Seed data
        ├── models/
        │   ├── employee.py, claim.py, conversation.py, rates.py
        └── services/
            └── textract_service.py  # AWS Textract OCR
```

## 🚀 Quick Start

### Option 1: Run with Docker (Recommended)

```powershell
# From project root
cd "d:\MedCube\Projects\4th Month\Petty Cash System via whatsapp - python"
docker compose up --build
```

### Option 2: Run Locally

```powershell
# From project root
cd "d:\MedCube\Projects\4th Month\Petty Cash System via whatsapp - python"

# Install dependencies
pip install -r requirements.txt

# Setup database (first time only)
python -m backend.app.db.setup

# Run the server
python run.py
```

### Option 3: Run with Conda (Virtual Environment) This section explains how to use Anaconda/Miniconda

1. **Open Anaconda Prompt** (or terminal with conda in path)

2. **Create and Activate Environment**

   ```powershell
   # Create environment for Python 3.12
   conda create --name petty_cash python=3.12 -y

   # Activate the environment
   conda activate petty_cash
   ```

3. **Install Dependencies**

   ```powershell
   # Navigate to project root
   cd "d:\MedCube\Projects\4th Month\Petty Cash System via whatsapp - python"

   # Install requirements using pip
   pip install -r requirements.txt
   ```

4. **Setup Database (First time only)**

   ```powershell
   python setup_db.py
   ```

5. **Run the Server**
   ```powershell
   python run.py
   ```

### Step 1: Create .env file

```powershell
Copy-Item .env.example .env
# Edit .env with your actual credentials
```

### Step 2: Set Up Database

```powershell
python setup_db.py
```

### Step 3: Start Services

```powershell
docker compose up --build
```

### Step 4: Start WAHA Session

1. Open: http://localhost:3000/dashboard/
2. Login: `admin` / `a9def4fc68164797a979facddf0b65b9`
3. Click **Start** on `default` session
4. Scan QR code

### Step 5: Add Employee

```powershell
python add_employee.py 94779485361 "Visal" C CMB staff
```

## 📱 Managing Employees

```powershell
# List employees
python add_employee.py list

# Add employee
python add_employee.py <phone> "<name>" <grade> <location> [role]
```

| Parameter | Options                                          |
| --------- | ------------------------------------------------ |
| Grade     | A, B, C, D, E                                    |
| Location  | CMB, KDY, GAL, JAF, ANU, KUR, RAT, BAD, TRI, BAT |
| Role      | staff, manager, admin, finance                   |

## 📊 Architecture

```
WhatsApp User ←→ WAHA (port 3000) ←→ Python FastAPI (port 4101) ←→ PostgreSQL
```

## 🔐 Credentials

| Service    | URL                              | Username | Password                         |
| ---------- | -------------------------------- | -------- | -------------------------------- |
| WAHA       | http://localhost:3000/dashboard/ | admin    | a9def4fc68164797a979facddf0b65b9 |
| PostgreSQL | localhost:5432                   | postgres | postgres                         |
