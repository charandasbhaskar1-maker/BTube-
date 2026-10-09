"""
Video Operations API
Upload pipeline, SafeShield/CopyScan integration, and Viral Ranked Feed.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.database.connection import get_db
from backend.database.models import Video, Channel
from backend.auth.security import decode_token
from backend.security.safeshield import scan_text_safeshield, scan_media_frames_safeshield
from backend.copyright.copyscan import analyze_audio_fingerprint
from backend.bpp_engine import calculate_viral_score

router = APIRouter(prefix="/api/videos", tags=["Videos"])

class VideoCreateSchema(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = "All"
    video_url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: int = 60
    is_shorts: bool = False
    visibility: Optional[str] = "Public"
    audio_hash: Optional[str] = None

@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_video(
    payload: VideoCreateSchema,
    token_data: dict = Depends(decode_token),
    db: Session = Depends(get_db)
):
    channel_id = token_data.get("channel_id")
    if not channel_id:
        raise HTTPException(status_code=400, detail="Channel not found for this account.")

    # 1. SafeShield AI Text Scan
    text_safety = scan_text_safeshield(f"{payload.title} {payload.description}")
    if not text_safety["passed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SafeShield Block: {text_safety['reason']}"
        )

    # 2. SafeShield AI Visual Frame Scan
    frame_safety = scan_media_frames_safeshield(payload.video_url)
    if not frame_safety["passed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SafeShield Block: Inappropriate or NSFW visuals detected in video frames."
        )

    # 3. CopyScan Audio Fingerprint Scan
    audio_audit = analyze_audio_fingerprint(payload.audio_hash)

    new_video = Video(
        channel_id=channel_id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        video_url=payload.video_url,
        thumbnail_url=payload.thumbnail_url,
        duration_seconds=payload.duration_seconds,
        is_shorts=payload.is_shorts,
        visibility=payload.visibility,
        safeshield_status="Clean",
        copyscan_status=audio_audit["status"],
        claim_details=f"{audio_audit['song']} by {audio_audit['owner']}" if audio_audit.get("has_claim") else None,
        is_monetized=not audio_audit.get("has_claim", False)
    )

    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    return {
        "status": "success",
        "video_id": new_video.id,
        "title": new_video.title,
        "safeshield": new_video.safeshield_status,
        "copyscan": new_video.copyscan_status,
        "is_monetized": new_video.is_monetized,
        "claim_notice": new_video.claim_details
    }

@router.get("/feed")
def get_home_feed(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Video).filter(Video.visibility == "Public")
    if category and category.lower() != "all":
        query = query.filter(Video.category.ilike(category))

    videos = query.all()

    # Recalculate and sort dynamically by Viral Score
    for v in videos:
        v.viral_score = calculate_viral_score(
            impressions=v.impressions,
            clicks=v.views_count,
            watch_time_sec=v.watch_time_total_seconds,
            total_duration_sec=v.duration_seconds,
            likes=v.likes_count,
            shares=v.shares_count
        )

    sorted_videos = sorted(videos, key=lambda x: x.viral_score, reverse=True)
    return sorted_videos

@router.post("/{video_id}/view")
def record_video_view(video_id: str, watch_seconds: float, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    video.views_count += 1
    video.watch_time_total_seconds += watch_seconds

    # Credit watch hours to channel
    channel = db.query(Channel).filter(Channel.id == video.channel_id).first()
    if channel:
        if video.is_shorts:
            channel.shorts_views_90d += 1
        else:
            channel.public_watch_hours_365d += round(watch_seconds / 3600.0, 4)

    db.commit()
    return {"views": video.views_count, "watch_hours_credited": round(watch_seconds / 3600.0, 4)}
