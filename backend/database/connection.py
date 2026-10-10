"""
Database Connection & Session Pool Manager
Supports both local SQLite (with WAL concurrency) and Production PostgreSQL (Neon / Supabase / Render)
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Base Declaration (Prevents Circular Import with models.py)
Base = declarative_base()

# 2. Database URL Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./btube.db")

# SQLAlchemy 1.4+ compatibility fix for Render / Supabase URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Connection Engine & Pooling Setup
IS_SQLITE = "sqlite" in DATABASE_URL

if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

    # Enable SQLite WAL (Write-Ahead Logging) to prevent 'database is locked' on concurrent video streams
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()

else:
    # Production PostgreSQL Pooling Configuration
    engine = create_engine(
        DATABASE_URL,
        pool_size=15,             # Persistent active connections
        max_overflow=25,          # Burst capacity for high traffic
        pool_pre_ping=True,       # Auto-reconnect dead/idle connections (Neon/Supabase)
        pool_recycle=300          # Recycle connections every 5 minutes
    )

# 4. Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all database schema tables on startup if they don't exist"""
    # Import models here to ensure all ORM tables are registered before creation
    import backend.database.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

def get_db():
    """FastAPI Dependency for request-scoped database sessions with guaranteed cleanup"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
