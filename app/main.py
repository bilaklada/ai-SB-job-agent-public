"""
FastAPI application entrypoint.
This file contains the minimal API setup to verify that the backend runs correctly.
"""
from fastapi import FastAPI

# Import routers
from app.api.routes_jobs import router as jobs_router
from app.api.routes_admin import router as admin_router

# Import database Base & engine to create tables
from app.db.session import engine, Base
import app.db.models  # IMPORTANT — ensures models are registered before create_all()

# Create FastAPI application instance
app = FastAPI()

# Auto-create database tables on startup
Base.metadata.create_all(bind=engine)

# Health check endpoint — used by developers, Docker, and monitoring tools
@app.get("/health")
def health():
    return {"status": "ok"}

# Include job-related routes
app.include_router(jobs_router)

# Include admin/debug routes
app.include_router(admin_router)
