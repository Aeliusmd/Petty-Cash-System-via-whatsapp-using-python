# Quick Start Guide: Development Mode

This guide will help you start the Petty Cash System in **Development Mode** with WAHA in Docker and Backend + Frontend running locally.

## 🎯 Why Development Mode?

- ✅ **Instant code reload** - Backend changes apply immediately
- ✅ **Better debugging** - Full access to Python debugger and logs
- ✅ **Faster iteration** - No Docker rebuilds needed
- ✅ **IDE integration** - Your IDE can debug the backend directly

## 📋 Prerequisites

Before starting, ensure you have:

- ✅ Docker Desktop installed and running
- ✅ PostgreSQL running locally (localhost:5432)
- ✅ Conda environment activated: `conda activate petty_cash`
- ✅ Dependencies installed: `pip install -r requirements.txt`
- ✅ Database setup complete: `python setup_db.py`

## 🚀 Starting the System

You'll need **3 terminal windows** open. Follow these steps:

### Terminal 1: WAHA (Docker)

```powershell
# Navigate to project root
cd "d:\MedCube\Projects\4th Month\Petty Cash System via whatsapp - python"

# Start WAHA container
docker compose -f docker-compose.waha-only.yaml up
```

**Expected output:**

- WAHA container starts
- Logs show WAHA listening on port 3000
- If session exists, it will auto-start

**Verify:** Open http://localhost:3000/dashboard/ in browser

---

### Terminal 2: Backend (Local Python)

```powershell
# Navigate to project root
cd "d:\MedCube\Projects\4th Month\Petty Cash System via whatsapp - python"

# Activate conda environment
conda activate petty_cash

# Start backend
python run.py
```

**Expected output:**

```
📄 Loaded environment from: .env.local (LOCAL DEVELOPMENT MODE)
🚀 Starting Petty Cash System...
📍 Running from: d:\MedCube\Projects\4th Month\Petty Cash System via whatsapp - python
🔌 Port: 4101
📦 Database connected successfully
INFO:     Uvicorn running on http://0.0.0.0:4101
INFO:     Application startup complete.
```

**Verify:** Open http://localhost:4101/docs in browser (should show API documentation)

---

### Terminal 3: Frontend (Local npm)

```powershell
# Navigate to frontend folder
cd "d:\MedCube\Projects\4th Month\Petty Cash System via whatsapp - python\frontend"

# Start frontend
npm run dev
```

**Expected output:**

```
> frontend@0.1.0 dev
> next dev -p 3001

  ▲ Next.js 14.x.x
  - Local:        http://localhost:3001
  - Network:      http://192.168.x.x:3001

 ✓ Ready in 2.3s
```

**Verify:** Open http://localhost:3001 in browser (should show login page)

---

## ✅ Verification Checklist

After all three services are running, verify:

1. **WAHA Dashboard:** http://localhost:3000/dashboard/
   - Login with `admin` / `a9def4fc68164797a979facddf0b65b9`
   - Session should be running (green status)

2. **Backend API:** http://localhost:4101/docs
   - Swagger docs should load
   - Try `/health` endpoint - should return healthy status

3. **Frontend:** http://localhost:3001
   - Login page should load
   - Try logging in with employee credentials

4. **WhatsApp Integration:**
   - Send "Hi" to your WhatsApp bot
   - Check Terminal 2 logs - should see incoming webhook
   - Bot should respond with menu

## 🔧 Troubleshooting

### WAHA can't reach backend (webhook fails)

**Symptom:** WAHA shows webhook errors in Terminal 1

**Solution:**

- Ensure backend is running (check Terminal 2)
- Verify backend is on port 4101: `curl http://localhost:4101/health`
- Check Windows Firewall isn't blocking port 4101

### Backend can't connect to WAHA

**Symptom:** Backend logs show "WAHA sendText error"

**Solution:**

- Ensure WAHA is running (check Terminal 1)
- Verify `.env.local` has `WAHA_BASE_URL=http://localhost:3000`
- Test WAHA: `curl http://localhost:3000/api/sessions`

### Frontend can't connect to backend

**Symptom:** Login fails with "Failed to fetch" error

**Solution:**

- Ensure backend is running (check Terminal 2)
- Check browser console for CORS errors
- Verify frontend is configured to use `http://localhost:4101`

### Database connection fails

**Symptom:** Backend shows "Database not connected"

**Solution:**

- Ensure PostgreSQL is running: `psql -U postgres -c "\l"`
- Check `.env.local` has correct DB credentials
- Verify database exists: `petty_cash_db`

## 🛑 Stopping the System

To stop all services:

1. **Terminal 3:** Press `Ctrl+C` to stop frontend
2. **Terminal 2:** Press `Ctrl+C` to stop backend
3. **Terminal 1:** Press `Ctrl+C`, then run:
   ```powershell
   docker compose -f docker-compose.waha-only.yaml down
   ```

## 🔄 Switching Back to Full Docker Mode

If you want to switch back to running everything in Docker:

```powershell
# Stop WAHA-only
docker compose -f docker-compose.waha-only.yaml down

# Start full Docker stack
docker compose up --build

# Start frontend separately (in another terminal)
cd frontend
npm run dev
```

## 📚 Next Steps

- Add employees: `python add_employee.py <phone> "<name>" <grade> <location> <role>`
- Test claim submission via WhatsApp
- Access admin panel to approve/reject claims
- Make code changes - backend will auto-reload!

---

**Need help?** Check the main README.md for complete documentation.
