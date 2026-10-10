"""
BTube Master FastAPI Application
Mounts Auth, Video Pipeline, SafeShield, CopyScan, Static Storage & BPP Monetization.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database.connection import init_db, engine
from backend.routes.auth import router as auth_router
from backend.routes.videos import router as video_router
from backend.routes.monetization import router as monetization_router

# Base Directory & Static Uploads Setup
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Modern Lifespan Handler (Replaces deprecated @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure Database Schema & Tables are created
    init_db()
    yield
    # Shutdown: Cleanly dispose connection pool
    engine.dispose()


app = FastAPI(
    title="BTube Engine API",
    version="2.4.0",
    description="Scalable Video Streaming, SafeShield, CopyScan & YPP/BPP Monetization Engine",
    lifespan=lifespan
)

# CORS Middleware (Supports local development & PWA domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Uploads directory for static video & thumbnail streaming
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Mount Feature Routers
app.include_router(auth_router)
app.include_router(video_router)
app.include_router(monetization_router)


@app.get("/")
def root():
    return {
        "platform": "BTube Engine",
        "status": "Online",
        "version": "2.4.0",
        "safeshield": "Active",
        "copyscan": "Active",
        "bpp_ledger": "70/30 Standard"
    }


@app.get("/health")
def health_check():
    """Service health probe for cloud hosting platforms."""
    db_status = "Connected"
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as e:
        db_status = f"Unreachable: {str(e)}"

    return {
        "api": "Healthy",
        "database": db_status,
        "storage": "Mounted" if UPLOAD_DIR.exists() else "Missing"
    }
