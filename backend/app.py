"""
BTube Master FastAPI Application
Mounts Auth, Video Pipeline, SafeShield, CopyScan and BPP Monetization Engines.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database.connection import init_db
from backend.auth.routes import router as auth_router
from backend.api.videos import router as video_router
from backend.api.monetization import router as monetization_router

app = FastAPI(
    title="BTube API Engine",
    version="2.0.0",
    description="Full-stack modular engine for BTube: SafeShield, CopyScan, Viral Feed & BPP"
)

# CORS Setup for PWA frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-initialize database tables on server start
@app.on_event("startup")
def on_startup():
    init_db()

# Mount all feature routers
app.include_router(auth_router)
app.include_router(video_router)
app.include_router(monetization_router)

@app.get("/")
def root():
    return {
        "platform": "BTube Engine",
        "status": "Online",
        "version": "2.0.0",
        "safeshield": "Active",
        "copyscan": "Active"
    }
