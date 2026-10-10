"""
BTube Database Schemas & DTO Models (Pydantic V2)
Handles Users, Multi-Channel Profiles, Videos, 70/30 Monetization Ledger & Safety Audits
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ================= 1. BPP MONETIZATION & METRICS =================
class BPPStatusSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tier: str = "STANDARD"  # STANDARD, TIER_1, TIER_2, SUSPENDED
    is_monetized: bool = False
    subscribers_count: int = 0
    public_watch_hours_365d: float = 0.0
    shorts_views_90d: int = 0
    active_strikes: int = 0
    
    # Financial Balance (High Precision Decimal)
    total_lifetime_gross_inr: Decimal = Field(default=Decimal("0.00"))
    creator_net_earned_inr: Decimal = Field(default=Decimal("0.00"))
    withdrawable_balance_inr: Decimal = Field(default=Decimal("0.00"))
    payout_upi_id: Optional[str] = None


# ================= 2. CHANNELS & USER PROFILES =================
class ChannelMinimalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_name: str
    handle: str
    avatar_url: Optional[str] = None
    subscribers_count: int = 0
    is_monetized: bool = False


class ChannelDetailedSchema(ChannelMinimalSchema):
    bpp_tier: str
    public_watch_hours_365d: float
    shorts_views_90d: int
    active_strikes: int
    total_lifetime_gross_inr: Decimal
    creator_net_earned_inr: Decimal
    withdrawable_balance_inr: Decimal
    payout_upi_id: Optional[str] = None
    created_at: datetime


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: EmailStr
    is_google_account: bool
    is_2fa_enabled: bool
    created_at: datetime
    active_channel: Optional[ChannelMinimalSchema] = None
    all_channels: List[ChannelMinimalSchema] = Field(default_factory=list)


# ================= 3. VIDEO & SHORTS SCHEMAS =================
class VideoRecordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    title: str
    description: Optional[str] = ""
    category: str = "All"
    duration_seconds: int = 0
    is_shorts: bool = False
    visibility: str = "Public"  # Public, Unlisted, Private
    schedule_time: Optional[datetime] = None

    # Stream & Visuals
    video_url: str
    thumbnail_url: Optional[str] = None

    # Performance & Viral Metrics
    views_count: int = 0
    impressions: int = 0
    likes_count: int = 0
    shares_count: int = 0
    watch_time_total_seconds: float = 0.0
    viral_score: float = 0.0

    # Safety & Copyright Verification
    safeshield_status: str = "Clean"  # Clean, Processing, Flagged, Blocked
    copyscan_status: str = "Original"  # Original, Processing, Content_ID_Claim, Strike
    claim_details: Optional[str] = None
    is_monetized: bool = True
    created_at: datetime


# ================= 4. COMMENTS & SUPER THANKS =================
class CommentResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    author_name: str
    comment_text: str
    is_super_thanks: bool = False
    super_thanks_amount: Optional[Decimal] = None
    badge_color: Optional[str] = None
    created_at: datetime


# ================= 5. FINANCIAL 70/30 TRANSACTION LEDGER =================
class MonetizationTransactionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    channel_id: str
    sender_name: str
    type: str = "SUPER_THANKS"
    gross_amount: Decimal
    creator_net_share: Decimal  # Exactly 70%
    platform_fee: Decimal       # Exactly 30%
    currency: str = "INR"
    comment_text: Optional[str] = None
    status: str = "COMPLETED"
    created_at: datetime


class PayoutRecordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    amount: Decimal
    destination_upi: str
    status: str  # PROCESSING, SETTLED, FAILED
    created_at: datetime
