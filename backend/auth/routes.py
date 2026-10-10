"""
BTube Production Authentication & Multi-Channel Routing API
Implements:
- Standard Email/Password Registration & Login
- Google OAuth 2.0 / Firebase ID Token Verification & Auto-Provisioning
- YouTube-Style Multi-Channel Management (Create, List, Switch Channel)
- Secure Handle Reservation & Sanitization
"""

import re
import uuid
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User, Channel
from backend.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    verify_google_token
)

router = APIRouter(prefix="/api/auth", tags=["Authentication & Multi-Channel"])

RESERVED_HANDLES = {"@admin", "@btube", "@official", "@support", "@moderator", "@root"}
HANDLE_REGEX = re.compile(r"^@[a-z0-9_]{3,30}$")


# ================= SCHEMAS =================

class RegisterPayload(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=64)
    channel_name: str = Field(..., min_length=2, max_length=60)
    channel_handle: str = Field(..., min_length=3, max_length=32)

    @field_validator("channel_handle")
    @classmethod
    def clean_handle(cls, v: str) -> str:
        v = v.strip().lower()
        handle = v if v.startswith("@") else f"@{v}"
        if handle in RESERVED_HANDLES:
            raise ValueError("This handle is reserved by BTube platform.")
        if not HANDLE_REGEX.match(handle):
            raise ValueError("Handle must be 3-30 chars, lowercase alphanumeric or underscore (e.g. @bhaskar_vlogs).")
        return handle


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthPayload(BaseModel):
    id_token: str
    preferred_channel_name: Optional[str] = None


class CreateChannelPayload(BaseModel):
    channel_name: str = Field(..., min_length=2, max_length=60)
    channel_handle: str = Field(..., min_length=3, max_length=32)
    avatar_url: Optional[str] = None

    @field_validator("channel_handle")
    @classmethod
    def clean_handle(cls, v: str) -> str:
        v = v.strip().lower()
        handle = v if v.startswith("@") else f"@{v}"
        if handle in RESERVED_HANDLES or not HANDLE_REGEX.match(handle):
            raise ValueError("Invalid or reserved handle.")
        return handle


class SwitchChannelPayload(BaseModel):
    channel_id: str


# ================= ROUTES =================

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterPayload, db: Session = Depends(get_db)):
    # 1. Check existing account
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # 2. Check handle collision
    existing_handle = db.query(Channel).filter(Channel.handle == payload.channel_handle).first()
    if existing_handle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This channel handle is already taken."
        )

    # 3. Create User record
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    new_user = User(
        id=user_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_google_account=False,
        is_2fa_enabled=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_user)
    db.commit()

    # 4. Create Initial Primary Creator Channel
    channel_id = f"ch_{uuid.uuid4().hex[:12]}"
    new_channel = Channel(
        id=channel_id,
        user_id=new_user.id,
        channel_name=payload.channel_name,
        handle=payload.channel_handle,
        subscribers_count=0,
        is_monetized=False,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_channel)
    db.commit()

    token = create_access_token(data={
        "sub": new_user.id,
        "user_id": new_user.id,
        "email": new_user.email,
        "channel_id": new_channel.id,
        "name": new_channel.channel_name
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": new_user.id,
        "active_channel": {
            "id": new_channel.id,
            "name": new_channel.channel_name,
            "handle": new_channel.handle
        }
    }


@router.post("/login")
def login_user(payload: LoginPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    primary_channel = db.query(Channel).filter(Channel.user_id == user.id).first()
    channel_id = primary_channel.id if primary_channel else None
    channel_name = primary_channel.channel_name if primary_channel else "BTube Creator"

    token = create_access_token(data={
        "sub": user.id,
        "user_id": user.id,
        "email": user.email,
        "channel_id": channel_id,
        "name": channel_name
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "active_channel": {
            "id": channel_id,
            "name": channel_name,
            "handle": primary_channel.handle if primary_channel else "@creator"
        }
    }


@router.post("/google")
def google_auth_bridge(payload: GoogleAuthPayload, db: Session = Depends(get_db)):
    """
    Verifies Google OAuth/Firebase Token.
    Auto-creates User & Channel if logging in for the first time.
    """
    google_data = verify_google_token(payload.id_token)
    email = google_data.get("email")
    display_name = google_data.get("name") or payload.preferred_channel_name or "BTube Creator"
    avatar_url = google_data.get("picture")

    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Google OAuth payload.")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        # First time login: Create User & Primary Channel
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        user = User(
            id=user_id,
            email=email,
            hashed_password=None,
            is_google_account=True,
            is_2fa_enabled=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(user)
        db.commit()

        # Generate base handle from email prefix
        base_handle = "@" + re.sub(r"[^a-z0-9]", "", email.split("@")[0].lower())[:24]
        if db.query(Channel).filter(Channel.handle == base_handle).first():
            base_handle = f"{base_handle}_{uuid.uuid4().hex[:4]}"

        channel_id = f"ch_{uuid.uuid4().hex[:12]}"
        channel = Channel(
            id=channel_id,
            user_id=user.id,
            channel_name=display_name,
            handle=base_handle,
            avatar_url=avatar_url,
            subscribers_count=0,
            created_at=datetime.now(timezone.utc)
        )
        db.add(channel)
        db.commit()
    else:
        channel = db.query(Channel).filter(Channel.user_id == user.id).first()

    token = create_access_token(data={
        "sub": user.id,
        "user_id": user.id,
        "email": user.email,
        "channel_id": channel.id if channel else None,
        "name": channel.channel_name if channel else display_name,
        "photo": avatar_url
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": channel.channel_name if channel else display_name,
            "photo": avatar_url
        },
        "active_channel": {
            "id": channel.id if channel else None,
            "name": channel.channel_name if channel else display_name,
            "handle": channel.handle if channel else "@creator"
        }
    }


# ================= MULTI-CHANNEL SWITCHER ENGINE =================

@router.get("/channels/me")
def list_user_channels(token_data: dict = Depends(decode_token), db: Session = Depends(get_db)):
    """Returns all channels owned by the authenticated account for accounts.html"""
    user_id = token_data.get("sub") or token_data.get("user_id")
    channels = db.query(Channel).filter(Channel.user_id == user_id).all()
    active_id = token_data.get("channel_id")

    return [
        {
            "id": c.id,
            "name": c.channel_name,
            "handle": c.handle,
            "avatar": c.avatar_url,
            "subscribers": c.subscribers_count,
            "is_active": (c.id == active_id)
        }
        for c in channels
    ]


@router.post("/channels/create")
def create_additional_channel(
    payload: CreateChannelPayload,
    token_data: dict = Depends(decode_token),
    db: Session = Depends(get_db)
):
    """Allows creating secondary channels under the same Google login"""
    user_id = token_data.get("sub") or token_data.get("user_id")
    
    existing = db.query(Channel).filter(Channel.handle == payload.channel_handle).first()
    if existing:
        raise HTTPException(status_code=400, detail="This channel handle is already taken.")

    new_channel = Channel(
        id=f"ch_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        channel_name=payload.channel_name,
        handle=payload.channel_handle,
        avatar_url=payload.avatar_url,
        subscribers_count=0,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_channel)
    db.commit()

    return {
        "status": "success",
        "channel_id": new_channel.id,
        "name": new_channel.channel_name,
        "handle": new_channel.handle
    }


@router.post("/channels/switch")
def switch_active_channel(
    payload: SwitchChannelPayload,
    token_data: dict = Depends(decode_token),
    db: Session = Depends(get_db)
):
    """Issues an updated JWT token containing the new active channel context"""
    user_id = token_data.get("sub") or token_data.get("user_id")
    target_channel = db.query(Channel).filter(
        Channel.id == payload.channel_id,
        Channel.user_id == user_id
    ).first()

    if not target_channel:
        raise HTTPException(status_code=403, detail="You do not own this channel.")

    user = db.query(User).filter(User.id == user_id).first()

    # Issue refreshed token with the selected channel context
    new_token = create_access_token(data={
        "sub": user.id,
        "user_id": user.id,
        "email": user.email,
        "channel_id": target_channel.id,
        "name": target_channel.channel_name
    })

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "active_channel": {
            "id": target_channel.id,
            "name": target_channel.channel_name,
            "handle": target_channel.handle
        }
    }


@router.get("/me")
def get_current_user_profile(token_data: dict = Depends(decode_token), db: Session = Depends(get_db)):
    user_id = token_data.get("sub") or token_data.get("user_id")
    channel_id = token_data.get("channel_id")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        channel = db.query(Channel).filter(Channel.user_id == user.id).first()

    return {
        "user_id": user.id,
        "email": user.email,
        "channel_id": channel.id if channel else None,
        "channel_name": channel.channel_name if channel else "BTube Creator",
        "handle": channel.handle if channel else "@creator",
        "subscribers": channel.subscribers_count if channel else 0,
        "bpp_tier": channel.bpp_tier if channel else "STANDARD",
        "watch_hours": channel.public_watch_hours_365d if channel else 0.0,
        "strikes": channel.active_strikes if channel else 0
    }
