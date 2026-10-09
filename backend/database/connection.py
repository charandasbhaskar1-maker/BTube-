"""
Database Connection & Session Manager
Supports both local SQLite and Cloud PostgreSQL (Render / Supabase / Neon)
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models import Base

# Default to SQLite if no DATABASE_URL environment variable is provided
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./btube.db")

# PostgreSQL fix for SQLAlchemy (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all database tables on startup"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency to provide database session per request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
