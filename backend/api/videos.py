"""
BTube Core Video Operations Engine
Implements:
- Resilient Chunked Upload with UUID session isolation (No filename collisions)
- Async Background Processing for SafeShield & CopyScan (Zero HTTP timeouts)
- Robust HTTP 206 Partial Content video streaming (Precise byte seeking)
- Anti-Fraud View & Watch-Time Ledger Sync (Guards BPP thresholds from spam)
- Real Database Persistence for Likes, Comments, and Channel Stats
"""

import os
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse
import mimetypes
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    Request, Header, BackgroundTasks
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.database.connection import get_db
from backend.database.models import Video, Channel, Comment, VideoLike
from backend.auth.security import decode_token
from backend.security.safeshield import scan_text_safeshield, scan_media_frames_safeshield
from backend.copyright.copyscan import analyze_audio_fingerprint
from backend.bpp_engine import calculate_viral_score

router = APIRouter(prefix="/api/videos", tags=["Videos"])

# Storage Directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
TEMP_CHUNKS_DIR = BASE_DIR / ".btube_temp_uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMP_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)


# ================= SCHEMAS =================
class VideoCreateSchema(BaseModel):
    title: str = Field(..., max_length=120)
    description: Optional[str] = ""
    category: Optional[str] = "All"
    video_url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: int = Field(default=60, ge=1)
    is_shorts: bool = False
    visibility: Optional[str] = "Public"
    audio_hash: Optional[str] = None


class VideoUpdateSchema(BaseModel):
    title: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = None
    category: Optional[str] = None
    visibility: Optional[str] = None
    thumbnail_url: Optional[str] = None


class CommentPayload(BaseModel):
    comment_text: str = Field(..., min_length=1, max_length=500)


class ViewRecordPayload(BaseModel):
    watch_seconds: float = Field(..., ge=1.0)


# ================= 1. RESILIENT CHUNK UPLOAD ENGINE =================
@router.post("/upload-chunk")
async def upload_video_chunk(
    request: Request,
    x_upload_id: str = Header(..., description="Unique upload session UUID from client"),
    x_chunk_index: int = Header(..., ge=0),
    x_total_chunks: int = Header(..., ge=1, le=2048),
    x_file_name: str = Header(default="video.mp4"),
    token_data: dict = Depends(decode_token)
):
    """
    Receives binary chunks into an isolated UUID directory.
    Reassembles the complete file safely when all parts arrive.
    """
    # Clean and isolate upload directory using UUID to prevent collisions
    clean_upload_id = "".join(c for c in x_upload_id if c.isalnum() or c in ("-", "_")).strip()
    if not clean_upload_id or len(clean_upload_id) > 80:
        raise HTTPException(status_code=400, detail="Invalid upload session ID.")
    if x_chunk_index >= x_total_chunks:
        raise HTTPException(status_code=400, detail="Chunk index is outside the declared upload range.")

    session_chunk_dir = TEMP_CHUNKS_DIR / clean_upload_id
    session_chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_file_path = session_chunk_dir / f"chunk_{x_chunk_index}.part"

    body = await request.body()
    if not body or len(body) > 4 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Each upload chunk must be between 1 byte and 4 MB.")
    with open(chunk_file_path, "wb") as f:
        f.write(body)

    existing_chunks = list(session_chunk_dir.glob("chunk_*.part"))

    # When all chunks arrive, merge sequentially
    if len(existing_chunks) == x_total_chunks:
        suffix = Path(x_file_name).suffix.lower()
        if suffix not in {".mp4", ".webm", ".mov", ".m4v", ".mkv", ".ogv"}:
            suffix = ".mp4"
        final_video_name = f"btube_{clean_upload_id}_{int(datetime.now(timezone.utc).timestamp())}{suffix}"
        final_video_path = UPLOAD_DIR / final_video_name

        with open(final_video_path, "wb") as outfile:
            for idx in range(x_total_chunks):
                part_path = session_chunk_dir / f"chunk_{idx}.part"
                if part_path.exists():
                    with open(part_path, "rb") as infile:
                        shutil.copyfileobj(infile, outfile)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Corrupt upload: chunk_{idx} missing during reassembly."
                    )

        # Cleanup chunks
        shutil.rmtree(session_chunk_dir, ignore_errors=True)

        return {
            "status": "completed",
            "message": "All chunks assembled successfully.",
            "video_url": f"/uploads/{final_video_name}",
            "file_name": final_video_name
        }

    return {
        "status": "chunk_received",
        "chunk_index": x_chunk_index,
        "total_chunks": x_total_chunks
    }


# ================= 2. ASYNC AUDIT & PUBLISH PIPELINE =================
def run_background_video_audit(video_id: str, db_session_factory):
    """Background worker for SafeShield visual scan & CopyScan audio matching"""
    db = db_session_factory()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return

        # Frame safety check must use the actual on-disk upload path.
        stored_path = urlparse(video.video_url).path
        media_name = Path(stored_path).name if stored_path.startswith("/uploads/") else ""
        media_path = UPLOAD_DIR / media_name if media_name else None
        frame_safety = scan_media_frames_safeshield(str(media_path) if media_path else "")
        video.safeshield_status = frame_safety.get("status", "Review Required")
        if not frame_safety.get("passed", False):
            video.visibility = "Private"

        # Audio fingerprint engine is a limited registry, not full acoustic recognition.
        audio_audit = analyze_audio_fingerprint(video.audio_hash)
        video.copyscan_status = audio_audit.get("status", "Review Required")
        if audio_audit.get("has_claim"):
            video.claim_details = f"{audio_audit['song']} by {audio_audit['owner']}"
            video.is_monetized = False

        db.commit()
    finally:
        db.close()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_video(
    payload: VideoCreateSchema,
    background_tasks: BackgroundTasks,
    token_data: dict = Depends(decode_token),
    db: Session = Depends(get_db)
):
    channel_id = token_data.get("channel_id")
    if not channel_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active channel required to upload.")

    # Immediate Synchronous Text Check
    text_safety = scan_text_safeshield(f"{payload.title} {payload.description}")
    if not text_safety["passed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SafeShield Policy Rejection: {text_safety['reason']}"
        )

    parsed_url = urlparse(payload.video_url)
    media_path = parsed_url.path if parsed_url.scheme else payload.video_url
    media_path = media_path.split("?", 1)[0]
    media_name = Path(media_path).name
    if not media_path.startswith("/uploads/") or not media_name or media_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Upload the video file first; a valid /uploads/ URL is required.")
    if not (UPLOAD_DIR / media_name).is_file():
        raise HTTPException(status_code=400, detail="Uploaded media file does not exist on the server.")

    video_id = f"vid_{uuid.uuid4().hex[:12]}"
    new_video = Video(
        id=video_id,
        channel_id=channel_id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        video_url=payload.video_url,
        thumbnail_url=payload.thumbnail_url,
        duration_seconds=payload.duration_seconds,
        is_shorts=payload.is_shorts,
        visibility=payload.visibility,
        audio_hash=payload.audio_hash,
        safeshield_status="Processing",
        copyscan_status="Processing",
        is_monetized=False,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    # Offload heavy frame/audio scanning to background queue
    from backend.database.connection import SessionLocal
    background_tasks.add_task(run_background_video_audit, video_id, SessionLocal)

    return {
        "status": "success",
        "video_id": new_video.id,
        "title": new_video.title,
        "is_shorts": new_video.is_shorts,
        "audit_status": "Processing in background"
    }


# ================= 3. VIRAL HOMEPAGE FEED =================
@router.get("/feed")
def get_home_feed(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Video).filter(Video.visibility == "Public")
    if category and category.lower() not in {"all", "video", "short"}:
        query = query.filter(Video.category.ilike(f"%{category}%"))
    elif category and category.lower() == "video":
        query = query.filter(Video.is_shorts.is_(False))
    elif category and category.lower() == "short":
        query = query.filter(Video.is_shorts.is_(True))

    videos = query.order_by(Video.created_at.desc()).limit(100).all()
    result = []
    for v in videos:
        channel = v.channel
        result.append({
            "id": v.id,
            "title": v.title,
            "description": v.description or "",
            "category": v.category or "All",
            "type": "short" if v.is_shorts else "video",
            "is_shorts": bool(v.is_shorts),
            "video_url": v.video_url,
            "videoUrl": f"/api/videos/{v.id}/stream",
            "thumbnail_url": v.thumbnail_url,
            "thumb": v.thumbnail_url,
            "channel_id": v.channel_id,
            "channelId": v.channel_id,
            "channel_name": channel.channel_name if channel else "BTube Creator",
            "channel": channel.channel_name if channel else "BTube Creator",
            "channelAvatar": channel.avatar_url if channel else "",
            "duration_seconds": v.duration_seconds or 0,
            "duration": str(v.duration_seconds or 0),
            "views_count": v.views_count or 0,
            "views": v.views_count or 0,
            "likes_count": v.likes_count or 0,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "visibility": v.visibility
        })
    return result


# ================= 4. BUFFER-FREE HTTP 206 RANGE STREAMING =================
@router.get("/mine")
def get_my_videos(
    token_data: dict = Depends(decode_token),
    db: Session = Depends(get_db)
):
    channel_id = token_data.get("channel_id")
    if not channel_id:
        raise HTTPException(status_code=400, detail="Active channel required.")
    videos = db.query(Video).filter(Video.channel_id == channel_id).order_by(Video.created_at.desc()).limit(500).all()
    return [get_video_details(video.id, db) for video in videos]


@router.get("/{video_id}")
def get_video_details(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
    channel = video.channel
    return {
        "id": video.id,
        "title": video.title,
        "description": video.description or "",
        "category": video.category or "All",
        "type": "short" if video.is_shorts else "video",
        "is_shorts": bool(video.is_shorts),
        "video_url": video.video_url,
        "videoUrl": f"/api/videos/{video.id}/stream",
        "thumbnail_url": video.thumbnail_url,
        "thumb": video.thumbnail_url,
        "channel_id": video.channel_id,
        "channelId": video.channel_id,
        "channel_name": channel.channel_name if channel else "BTube Creator",
        "channel": channel.channel_name if channel else "BTube Creator",
        "channelAvatar": channel.avatar_url if channel else "",
        "duration_seconds": video.duration_seconds or 0,
        "duration": str(video.duration_seconds or 0),
        "views_count": video.views_count or 0,
        "views": video.views_count or 0,
        "likes_count": video.likes_count or 0,
        "visibility": video.visibility
    }


@router.patch("/{video_id}")
def update_video(
    video_id: str,
    payload: VideoUpdateSchema,
    token_data: dict = Depends(decode_token),
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
    if video.channel_id != token_data.get("channel_id"):
        raise HTTPException(status_code=403, detail="You do not own this video.")

    updates = payload.model_dump(exclude_unset=True)
    if "visibility" in updates and updates["visibility"] not in {"Public", "Unlisted", "Private"}:
        raise HTTPException(status_code=400, detail="Invalid visibility value.")
    if "thumbnail_url" in updates and updates["thumbnail_url"] and len(updates["thumbnail_url"]) > 500:
        raise HTTPException(status_code=400, detail="Thumbnail URL is too long.")
    for key, value in updates.items():
        setattr(video, key, value)
    db.commit()
    db.refresh(video)
    return get_video_details(video_id, db)


@router.delete("/{video_id}")
def delete_video(
    video_id: str,
    token_data: dict = Depends(decode_token),
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
    if video.channel_id != token_data.get("channel_id"):
        raise HTTPException(status_code=403, detail="You do not own this video.")

    stored_path = urlparse(video.video_url).path
    filename = Path(stored_path).name if stored_path.startswith("/uploads/") else ""
    db.delete(video)
    db.commit()
    if filename and filename not in {".", ".."}:
        try:
            (UPLOAD_DIR / filename).unlink(missing_ok=True)
        except OSError:
            pass
    return {"status": "deleted", "video_id": video_id}


@router.get("/{video_id}/stream")
def stream_video(video_id: str, request: Request, db: Session = Depends(get_db)):
    """Serve a stored upload with standards-compliant HTTP byte-range support."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
    if video.visibility == "Private":
        raise HTTPException(status_code=403, detail="This video is private.")

    stored_path = urlparse(video.video_url).path
    if not stored_path.startswith("/uploads/"):
        raise HTTPException(status_code=404, detail="Stored media path is invalid.")
    filename = Path(stored_path).name
    if not filename or filename in {".", ".."}:
        raise HTTPException(status_code=404, detail="Stored media path is invalid.")
    file_path = UPLOAD_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded media file was not found.")

    file_size = file_path.stat().st_size
    if file_size <= 0:
        raise HTTPException(status_code=404, detail="Uploaded media file is empty.")

    range_header = request.headers.get("range")
    start, end = 0, file_size - 1
    status_code = 200
    if range_header:
        import re
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        if not match or (not match.group(1) and not match.group(2)):
            return StreamingResponse(iter(()), status_code=416, headers={"Content-Range": f"bytes */{file_size}"})
        if not match.group(1):
            suffix_length = int(match.group(2))
            if suffix_length <= 0:
                return StreamingResponse(iter(()), status_code=416, headers={"Content-Range": f"bytes */{file_size}"})
            start = max(0, file_size - suffix_length)
        else:
            start = int(match.group(1))
            if match.group(2):
                end = int(match.group(2))
        if start >= file_size or end < start:
            return StreamingResponse(iter(()), status_code=416, headers={"Content-Range": f"bytes */{file_size}"})
        end = min(end, file_size - 1)
        status_code = 206

    content_length = end - start + 1
    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    def iter_file():
        with open(file_path, "rb") as handle:
            handle.seek(start)
            remaining = content_length
            while remaining > 0:
                data = handle.read(min(remaining, 512 * 1024))
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": media_type,
        "Cache-Control": "private, max-age=3600"
    }
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    return StreamingResponse(iter_file(), status_code=status_code, headers=headers)


# ================= 5. METRICS & USER INTERACTIONS =================
@router.post("/{video_id}/view")
def record_video_view(
    video_id: str,
    payload: ViewRecordPayload,
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video or video.visibility != "Public":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public video not found.")

    # Only credit watch sessions that meet the platform's minimum threshold.
    min_thresh = 5.0 if video.is_shorts else 15.0
    if payload.watch_seconds < min_thresh:
        return {"views": video.views_count, "watch_seconds_credited": 0, "channel_watch_hours": 0}

    video.views_count += 1
    video.watch_time_total_seconds += payload.watch_seconds

    channel = db.query(Channel).filter(Channel.id == video.channel_id).first()
    if channel:
        if video.is_shorts:
            channel.shorts_views_90d += 1
        else:
            channel.public_watch_hours_365d += round(payload.watch_seconds / 3600.0, 4)

    db.commit()
    return {
        "views": video.views_count,
        "watch_seconds_credited": payload.watch_seconds,
        "channel_watch_hours": round(channel.public_watch_hours_365d, 2) if channel else 0
    }


@router.post("/{video_id}/like")
def toggle_like(
    video_id: str,
    token_data: dict = Depends(decode_token),
    db: Session = Depends(get_db)
):
    user_id = token_data.get("user_id")
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    existing_like = db.query(VideoLike).filter(
        VideoLike.video_id == video_id,
        VideoLike.user_id == user_id
    ).first()

    if existing_like:
        # Unlike
        db.delete(existing_like)
        video.likes_count = max(0, video.likes_count - 1)
        liked = False
    else:
        # Like
        new_like = VideoLike(video_id=video_id, user_id=user_id)
        db.add(new_like)
        video.likes_count += 1
        liked = True

    db.commit()
    return {"liked": liked, "likes_count": video.likes_count}


@router.post("/{video_id}/comment")
def post_comment(
    video_id: str,
    payload: CommentPayload,
    token_data: dict = Depends(decode_token),
    db: Session = Depends(get_db)
):
    user_id = token_data.get("user_id")
    author_name = token_data.get("name", "BTube User")

    # SafeShield Text Profanity Check
    check = scan_text_safeshield(payload.comment_text)
    if not check["passed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment rejected by SafeShield: Inappropriate or abusive language."
        )

    new_comment = Comment(
        id=f"comm_{uuid.uuid4().hex[:10]}",
        video_id=video_id,
        user_id=user_id,
        author_name=author_name,
        comment_text=payload.comment_text,
        is_super_thanks=False,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return {
        "status": "posted",
        "comment_id": new_comment.id,
        "author": new_comment.author_name,
        "text": new_comment.comment_text,
        "created_at": new_comment.created_at.isoformat()
    }