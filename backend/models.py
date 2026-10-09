"""
BTube Database Models & Schemas
Handles Users, Channels, BPP Monetization, Security & Copyright Claims
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# 1. BPP (BTube Partner Program) Status Schema
class BPPStatus(BaseModel):
    tier: str = "Not Eligible"  # "Not Eligible", "Tier 1 (Fan Funding)", "Tier 2 (Full)", "Suspended"
    subscribers_count: int = 0
    public_watch_hours_365d: float = 0.0
    shorts_views_90d: int = 0
    active_guideline_strikes: int = 0
    is_2fa_enabled: bool = False
    is_reused_content_flagged: bool = False
    total_earnings_inr: float = 0.0
    payout_upi_id: Optional[str] = None

# 2. Channel & User Schema
class UserProfile(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    channel_name: str
    channel_handle: str
    channel_avatar: str
    bpp: BPPStatus = Field(default_factory=BPPStatus)

# 3. Video Metadata with Copyright & Safety Flags
class VideoRecord(BaseModel):
    video_id: str
    channel_id: str
    title: str
    description: str
    category: str
    duration_seconds: int
    is_shorts: bool = False
    visibility: str = "Public"  # Public, Unlisted, Private, Scheduled
    schedule_time: Optional[datetime] = None

    # Algorithm & Performance Metrics
    views_count: int = 0
    impressions: int = 0
    likes_count: int = 0
    shares_count: int = 0
    watch_time_total_seconds: float = 0.0
    viral_score: float = 0.0

    # Safety & Copyright Filters
    safeshield_status: str = "Clean"  # "Clean", "Flagged_NSFW", "Blocked"
    copyscan_status: str = "Original"  # "Original", "Claim_Audio", "Reused_Content", "Strike"
    claim_details: Optional[str] = None
    is_monetized: bool = True
