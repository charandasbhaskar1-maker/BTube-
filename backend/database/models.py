"""
BTube Database Models (SQLAlchemy ORM)
Tables: users, channels, videos, comments, strikes, earnings
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    is_google_account = Column(Boolean, default=False)
    is_2fa_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to Channel
    channel = relationship("Channel", back_populates="owner", uselist=False)

class Channel(Base):
    __tablename__ = "channels"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    channel_name = Column(String(100), nullable=False)
    handle = Column(String(50), unique=True, nullable=False)
    avatar_url = Column(String, default="https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=150")
    subscribers_count = Column(Integer, default=0)
    
    # BPP Monetization Stats
    bpp_tier = Column(String, default="Not Eligible")  # Not Eligible, Tier 1, Tier 2, Suspended
    public_watch_hours_365d = Column(Float, default=0.0)
    shorts_views_90d = Column(Integer, default=0)
    total_earnings_inr = Column(Float, default=0.0)
    payout_upi_id = Column(String, nullable=True)
    
    # Policy Violations
    active_strikes = Column(Integer, default=0)

    # Relationships
    owner = relationship("User", back_populates="channel")
    videos = relationship("Video", back_populates="channel")

class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=generate_uuid)
    channel_id = Column(String, ForeignKey("channels.id"), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, default="")
    category = Column(String(50), default="All")
    is_shorts = Column(Boolean, default=False)
    visibility = Column(String(20), default="Public")  # Public, Unlisted, Private, Scheduled
    schedule_time = Column(DateTime, nullable=True)

    # Media paths
    video_url = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=True)
    duration_seconds = Column(Integer, default=0)

    # Recommendation / Performance Metrics
    views_count = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    watch_time_total_seconds = Column(Float, default=0.0)
    viral_score = Column(Float, default=0.0)

    # Safety & Copyright Status
    safeshield_status = Column(String(30), default="Clean")  # Clean, Blocked
    copyscan_status = Column(String(30), default="Original")  # Original, Claim_Audio, Reused_Content, Strike
    claim_details = Column(String, nullable=True)
    is_monetized = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    channel = relationship("Channel", back_populates="videos")
