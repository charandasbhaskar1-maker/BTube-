"""
BTube Core FastAPI Backend
Handles Video Uploads, SafeShield Screening, CopyScan Audio Matching,
Viral Algorithm Feeds, and BPP Partner Program Evaluation.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import uuid

from backend.models import UserProfile, VideoRecord, BPPStatus
from backend.bpp_engine import evaluate_bpp_eligibility, calculate_viral_score
from backend.security_guard import scan_safeshield, scan_copyscan

app = FastAPI(
    title="BTube Backend API",
    version="1.0.0",
    description="Backend engine for BTube: SafeShield AI, CopyScan, BPP Monetization & Viral Feed"
)

# Enable CORS for frontend PWA integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory mock database
MOCK_USERS_DB = {}
MOCK_VIDEOS_DB = {}

# Sample known audio database for CopyScan fingerprinting
SAMPLE_KNOWN_AUDIO_REGISTRY = {
    "hash_cg_mor_maya": {
        "title": "Mor Maya Ke Chhaiya",
        "owner": "CG Folk Records Ltd",
        "allowed_remix": True
    },
    "hash_banjo_riff_101": {
        "title": "Typewriter Banjo Classical Dhun",
        "owner": "Dhun AI Studio",
        "allowed_remix": False
    }
}


@app.get("/")
def root():
    return {"message": "BTube Engine API is running smoothly", "status": "online"}


# ==============================================================
# 1. BPP (BTUBE PARTNER PROGRAM) MONETIZATION ENDPOINTS
# ==============================================================

@app.get("/api/bpp/status/{user_id}", response_model=dict)
def get_bpp_status(user_id: str):
    """
    Checks creator's progress towards BPP Tier 1 (Fan Funding) & Tier 2 (Full Revenue).
    """
    user = MOCK_USERS_DB.get(user_id)
    if not user:
        # Return fallback demo criteria if user is new
        return evaluate_bpp_eligibility(
            subscribers=245,
            watch_hours=140.0,
            shorts_views=45000,
            strikes=0,
            has_2fa=True
        )

    bpp_data = user.bpp
    assessment = evaluate_bpp_eligibility(
        subscribers=bpp_data.subscribers_count,
        watch_hours=bpp_data.public_watch_hours_365d,
        shorts_views=bpp_data.shorts_views_90d,
        strikes=bpp_data.active_guideline_strikes,
        has_2fa=bpp_data.is_2fa_enabled
    )
    return assessment


# ==============================================================
# 2. VIDEO UPLOAD, SAFESHIELD & COPYSCAN PRE-PUBLISH PIPELINE
# ==============================================================

class VideoUploadPayload(VideoRecord):
    audio_fingerprint_hash: Optional[str] = "clean_original_audio"


@app.post("/api/videos/upload", status_code=status.HTTP_201_CREATED)
def upload_video_pipeline(payload: VideoUploadPayload):
    """
    Automatic 3-Level Gatekeeper:
    1. SafeShield AI (blocks inappropriate & vulgar uploads)
    2. CopyScan AI (flags reused content & audio claims)
    3. Publish to Feed with initial Viral Score
    """
    # Step 1: SafeShield AI Verification
    safety_check = scan_safeshield(
        video_filename=f"{payload.video_id}.mp4",
        video_title=payload.title
    )
    if not safety_check["passed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SafeShield Block: {safety_check['reason']}"
        )

    # Step 2: CopyScan Fingerprint Verification
    audio_claim = scan_copyscan(
        audio_signature_hash=payload.audio_fingerprint_hash,
        known_audio_db=SAMPLE_KNOWN_AUDIO_REGISTRY
    )

    # Configure copyright & monetization flags based on claim
    if audio_claim["has_limitation"]:
        payload.copyscan_status = audio_claim["status"]
        payload.claim_details = f"Claimed by {audio_claim['owner']} ({audio_claim['matched_song']})"
        payload.is_monetized = False  # Revenue redirected to original creator
    else:
        payload.copyscan_status = "Original"
        payload.is_monetized = True

    payload.safeshield_status = "Clean"
    
    # Calculate baseline viral score
    payload.viral_score = calculate_viral_score(
        impressions=payload.impressions,
        clicks=payload.views_count,
        watch_time_sec=payload.watch_time_total_seconds,
        total_duration_sec=payload.duration_seconds,
        likes=payload.likes_count,
        shares=payload.shares_count
    )

    # Store in database
    MOCK_VIDEOS_DB[payload.video_id] = payload
    return {
        "status": "success",
        "video_id": payload.video_id,
        "safeshield": safety_check["status"],
        "copyscan": payload.copyscan_status,
        "monetized": payload.is_monetized,
        "claim_notice": payload.claim_details
    }


# ==============================================================
# 3. VIRAL RECOMMENDATION FEED
# ==============================================================

@app.get("/api/feed/home", response_model=List[VideoRecord])
def get_ranked_home_feed(category: Optional[str] = None):
    """
    Returns videos ordered by Viral Score (CTR + Retention + Shares + Likes).
    """
    videos = list(MOCK_VIDEOS_DB.values())
    if category and category != "All":
        videos = [v for v in videos if v.category.lower() == category.lower()]

    # Sort descending based on calculated viral score
    ranked_videos = sorted(videos, key=lambda v: v.viral_score, reverse=True)
    return ranked_videos
