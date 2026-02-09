"""
WhatsApp Petty Cash Backend Server
Refactored with OOP and MVC Architecture

FastAPI-based async server with:
- Controllers: API route handlers
- Services: Business logic
- Models: Database operations
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Load environment
from app.config import config
from app.db import db

# Import routers from controllers
from app.controllers.auth_controller import router as auth_router
from app.controllers.employee_controller import router as employee_router
from app.controllers.claim_controller import router as claim_router
from app.controllers.category_controller import router as category_router
from app.controllers.organization_controller import router as organization_router
from app.controllers.audit_controller import router as audit_router
from app.controllers.dashboard_controller import router as dashboard_router
from app.controllers.configuration_controller import router as config_router
from app.controllers.role_controller import router as role_router
from app.controllers.provisioning_controller import router as provisioning_router
from app.controllers.mobile_controller import router as mobile_router

# Import webhook handler (will be moved to controller in next phase)
from app.webhooks import webhook_router


# Message deduplication cache
processed_messages: set = set()
MAX_CACHE_SIZE = 1000


def is_message_processed(message_id: str) -> bool:
    """Check if message was already processed"""
    if not message_id:
        return False
    if message_id in processed_messages:
        return True
    processed_messages.add(message_id)
    if len(processed_messages) > MAX_CACHE_SIZE:
        processed_messages.pop()
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    print('🚀 Starting WhatsApp Petty Cash Backend (MVC Edition)...')
    
    try:
        await db.connect()
        if await db.check_connection():
            print('📦 Database connected successfully')
        else:
            print('⚠️ Database not connected')
    except Exception as e:
        print(f'⚠️ Database connection failed: {e}')
    
    yield
    
    await db.close()
    print('👋 Backend shutdown complete')


# Create FastAPI application
app = FastAPI(
    title="WhatsApp Petty Cash Backend",
    description="Petty Cash Management System with WhatsApp Integration - Refactored with OOP/MVC",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# INCLUDE ROUTERS FROM CONTROLLERS (MVC Pattern)
# ============================================================

# Authentication
app.include_router(auth_router)

# Employee Management
app.include_router(employee_router)

# Claims Management
app.include_router(claim_router)

# Categories
app.include_router(category_router)

# Organizations (Multi-tenant)
app.include_router(organization_router)

# Audit Logs
app.include_router(audit_router)

# Dashboard Stats
app.include_router(dashboard_router)

# Configuration (Units, Grades, Locations)
app.include_router(config_router)

# Role Management (RBAC)
app.include_router(role_router)

# Organization Signup (Provisioning)
app.include_router(provisioning_router)

# Webhooks (WhatsApp events)
app.include_router(webhook_router)

# Mobile BFF Router
app.include_router(mobile_router)


# ============================================================
# STATIC FILES (Receipts)
# ============================================================

# Import shared receipts directory configuration
from app.config_paths import RECEIPTS_DIR as receipts_dir

app.mount("/api/receipts", StaticFiles(directory=str(receipts_dir)), name="receipts")


# ============================================================
# ROOT ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "whatsapp-petty-cash-backend",
        "version": "2.0.0",
        "architecture": "OOP + MVC"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    db_connected = await db.check_connection() if db else False
    return {
        "status": "healthy" if db_connected else "degraded",
        "database": "connected" if db_connected else "disconnected",
        "version": "2.0.0"
    }


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    print(f"❌ Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error", "detail": str(exc)}
    )


# For backward compatibility, expose is_message_processed
__all__ = ['app', 'is_message_processed']
