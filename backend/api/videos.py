"""
Video Operations API
Chunked Upload Pipeline, Range-Header Video Streaming, SafeShield/CopyScan integration,
Viral Feed Algorithm, and User Interactions (Likes & Comments).
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database.connection import get_db
from backend.database.models import Video, Channel
from backend.auth.security import decode_token
from backend.security.safeshield import scan_text_safeshield, scan_media_frames_safeshield
from backend.copyright.copyscan import analyze_audio_fingerprint
from backend.bpp_engine import calculate_viral_score

router = APIRouter(prefix="/api/videos", tags=["Videos"])

# Storage Directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
TEMP_CHUNKS_DIR = BASE_DIR / "uploads" / "temp_chunks"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMP_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)


# ================= SCHEMAS =================
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


class CommentPayload(BaseModel):
    comment_text: str


# ================= 1. FAST CHUNK UPLOAD ENGINE =================
@router.post("/upload-chunk")
async def upload_video_chunk(
    request: Request,
    x_chunk_index: int = Header(...),
    x_total_chunks: int = Header(...),
    x_video_title: str = Header(...)
):
    """
    Receives 2MB binary chunks from frontend uploaders and reassembles
    the complete media file when the final chunk arrives.
    """
    # Clean unique upload folder per video title
    safe_title = "".join(c for c in x_video_title if c.isalnum() or c in (' ', '_', '-')).strip()
    session_chunk_dir = TEMP_CHUNKS_DIR / safe_title
    session_chunk_dir.mkdir(parents=True, exist_ok=True)

    chunk_file_path = session_chunk_dir / f"chunk_{x_chunk_index}.part"

    # Read binary stream and write chunk
    body = await request.body()
    with open(chunk_file_path, "wb") as f:
        f.write(body)

    # Check if all chunks received
    existing_chunks = list(session_chunk_dir.glob("chunk_*.part"))
    if len(existing_chunks) == x_total_chunks:
        final_video_name = f"{safe_title}_{int(datetime.utcnow().timestamp())}.mp4"
        final_video_path = UPLOAD_DIR / final_video_name

        # Merge chunks in sequential order
        with open(final_video_path, "wb") as outfile:
            for idx in range(x_total_chunks):
                part_path = session_chunk_dir / f"chunk_{idx}.part"
                if part_path.exists():
                    with open(part_path, "rb") as infile:
                        shutil.copyfileobj(infile, outfile)

        # Cleanup temporary chunk directory
        shutil.rmtree(session_chunk_dir, ignore_errors=True)

        return {
            "status": "completed",
            "message": "All chunks assembled successfully.",
            "file_path": f"/uploads/{final_video_name}",
            "file_name": final_video_name
        }

    return {
        "status": "chunk_received",
        "chunk_index": x_chunk_index,
        "total_chunks": x_total_chunks
    }


# ================= 2. PUBLISH & AI AUDIT PIPELINE =================
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


# ================= 3. VIRAL HOMEPAGE FEED =================
@router.get("/feed")
def get_home_feed(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Video).filter(Video.visibility == "Public")
    if category and category.lower() != "all":
        query = query.filter(Video.category.ilike(f"%{category}%"))

    videos = query.all()

    # Dynamic Viral Scoring (CTR + Retention + Shares)
    for v in videos:
        v.viral_score = calculate_viral_score(
            impressions=v.impressions,
            clicks=v.views_count,
            watch_time_sec=v.watch_time_total_seconds,
            total_duration_sec=v.duration_seconds or 180,
            likes=v.likes_count,
            shares=v.shares_count
        )

    sorted_videos = sorted(videos, key=lambda x: x.viral_score, reverse=True)
    return sorted_videos


# ================= 4. BUFFER-FREE HTTP 206 RANGE STREAMING =================
@router.get("/{video_id}/stream")
def stream_video(video_id: str, request: Request, db: Session = Depends(get_db)):
    """
    HTTP 206 Partial Content video streamer.
    Supports instant playback scrubbing/seeking without buffering the whole file.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Local fallback sample if not stored locally
    file_path = Path(video.video_url.replace("/uploads/", str(UPLOAD_DIR) + "/"))
    if not file_path.exists():
        fallback_sample = BASE_DIR / "assets" / "sample.mp4"
        if fallback_sample.exists():
            file_path = fallback_sample
        else:
            raise HTTPException(status_code=404, detail="Video media file not found on disk")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    start, end = 0, file_size - 1
    if range_header:
        range_value = range_header.strip().replace("bytes=", "")
        parts = range_value.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1

    content_length = (end - start) + 1

    def iter_file():
        with open(file_path, "rb") as video_file:
            video_file.seek(start)
            bytes_left = content_length
            while bytes_left > 0:
                chunk_read = min(bytes_left, 1024 * 512)  # 512KB streaming chunks
                data = video_file.read(chunk_read)
                if not data:
                    break
                bytes_left -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": "video/mp4",
    }

    return StreamingResponse(iter_file(), status_code=206, headers=headers)


# ================= 5. VIEWS, LIKES & INTERACTION METRICS =================
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


@router.post("/{video_id}/like")
def toggle_like(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    video.likes_count += 1
    db.commit()
    return {"likes_count": video.likes_count}


@router.post("/{video_id}/comment")
def post_comment(video_id: str, payload: CommentPayload, db: Session = Depends(get_db)):
    # SafeShield comment profanity scanner
    check = scan_text_safeshield(payload.comment_text)
    if not check["passed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Comment rejected by SafeShield: Inappropriate or abusive language."
        )

    return {
        "status": "posted",
        "comment_text": payload.comment_text,
        "created_at": datetime.utcnow().isoformat()
    }
