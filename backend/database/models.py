"""
BTube Production Database Models (SQLAlchemy ORM)
Tables: users, channels, videos, comments, video_likes, monetization_transactions, payout_records
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, ForeignKey, Text, Numeric
)
from sqlalchemy.orm import relationship

# Import Base directly from connection to avoid duplicate metadata & circular imports
from backend.database.connection import Base


def generate_uuid():
    return str(uuid.uuid4())


# ================= 1. USER AUTHENTICATION =================
class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    is_google_account = Column(Boolean, default=False)
    is_2fa_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # One User can own Multiple Channels (YouTube Standard)
    channels = relationship("Channel", back_populates="owner", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    likes = relationship("VideoLike", back_populates="user", cascade="all, delete-orphan")


# ================= 2. CREATOR CHANNELS =================
class Channel(Base):
    __tablename__ = "channels"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    channel_name = Column(String(100), nullable=False)
    handle = Column(String(50), unique=True, index=True, nullable=False)
    avatar_url = Column(String(500), default="https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=150")
    subscribers_count = Column(Integer, default=0)
    
    # BPP Monetization Metrics
    bpp_tier = Column(String(32), default="STANDARD")  # STANDARD, TIER_1, TIER_2, SUSPENDED
    is_monetized = Column(Boolean, default=False)
    public_watch_hours_365d = Column(Float, default=0.0)
    shorts_views_90d = Column(Integer, default=0)
    
    # Financial Ledgers (High-Precision Numeric)
    total_lifetime_gross_inr = Column(Numeric(12, 2), default=0.00)
    creator_net_earned_inr = Column(Numeric(12, 2), default=0.00)
    withdrawable_balance_inr = Column(Numeric(12, 2), default=0.00)
    payout_upi_id = Column(String(120), nullable=True)
    
    # Policy & Strikes (90-Day Rolling Windows)
    active_strikes = Column(Integer, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    owner = relationship("User", back_populates="channels")
    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")
    monetization_ledger = relationship("MonetizationTransaction", back_populates="channel", cascade="all, delete-orphan")
    payouts = relationship("PayoutRecord", back_populates="channel", cascade="all, delete-orphan")


# ================= 3. VIDEOS & SHORTS =================
class Video(Base):
    __tablename__ = "videos"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    channel_id = Column(String(64), ForeignKey("channels.id"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    description = Column(Text, default="")
    category = Column(String(50), default="All")
    is_shorts = Column(Boolean, default=False)
    visibility = Column(String(20), default="Public")  # Public, Unlisted, Private
    schedule_time = Column(DateTime, nullable=True)

    # Media Stream & Assets
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, default=0)
    audio_hash = Column(String(128), nullable=True)

    # Performance & Recommendation Engine
    views_count = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    watch_time_total_seconds = Column(Float, default=0.0)
    viral_score = Column(Float, default=0.0)

    # Safety & Copyright Audits
    safeshield_status = Column(String(30), default="Clean")  # Clean, Processing, Flagged, Blocked
    copyscan_status = Column(String(30), default="Original")  # Original, Processing, Content_ID_Claim, Strike
    claim_details = Column(String(255), nullable=True)
    is_monetized = Column(Boolean, default=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    channel = relationship("Channel", back_populates="videos")
    comments = relationship("Comment", back_populates="video", cascade="all, delete-orphan")
    likes = relationship("VideoLike", back_populates="video", cascade="all, delete-orphan")
    transactions = relationship("MonetizationTransaction", back_populates="video", cascade="all, delete-orphan")


# ================= 4. COMMENTS & GOLDEN SUPER THANKS =================
class Comment(Base):
    __tablename__ = "comments"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    video_id = Column(String(64), ForeignKey("videos.id"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    author_name = Column(String(100), nullable=False)
    comment_text = Column(String(500), nullable=False)
    
    # Super Thanks Highlights
    is_super_thanks = Column(Boolean, default=False)
    super_thanks_amount = Column(Numeric(10, 2), nullable=True)
    badge_color = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    video = relationship("Video", back_populates="comments")
    author = relationship("User", back_populates="comments")


# ================= 5. VIDEO LIKES =================
class VideoLike(Base):
    __tablename__ = "video_likes"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    video_id = Column(String(64), ForeignKey("videos.id"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    video = relationship("Video", back_populates="likes")
    user = relationship("User", back_populates="likes")


# ================= 6. 70/30 MONETIZATION LEDGER =================
class MonetizationTransaction(Base):
    __tablename__ = "monetization_transactions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    video_id = Column(String(64), ForeignKey("videos.id"), nullable=False, index=True)
    channel_id = Column(String(64), ForeignKey("channels.id"), nullable=False, index=True)
    sender_user_id = Column(String(64), nullable=True)
    sender_name = Column(String(100), nullable=False)
    type = Column(String(32), default="SUPER_THANKS")  # SUPER_THANKS, AD_REVENUE, MEMBERSHIP
    
    # Double-entry ledger split
    gross_amount = Column(Numeric(10, 2), nullable=False)
    creator_net_share = Column(Numeric(10, 2), nullable=False)  # Exactly 70%
    platform_fee = Column(Numeric(10, 2), nullable=False)       # Exactly 30%
    currency = Column(String(8), default="INR")
    comment_text = Column(String(300), nullable=True)
    status = Column(String(32), default="COMPLETED")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    video = relationship("Video", back_populates="transactions")
    channel = relationship("Channel", back_populates="monetization_ledger")


# ================= 7. CREATOR PAYOUT RECORDS =================
class PayoutRecord(Base):
    __tablename__ = "payout_records"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    channel_id = Column(String(64), ForeignKey("channels.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    destination_upi = Column(String(120), nullable=False)
    status = Column(String(32), default="PROCESSING")  # PROCESSING, SETTLED, FAILED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    channel = relationship("Channel", back_populates="payouts")
