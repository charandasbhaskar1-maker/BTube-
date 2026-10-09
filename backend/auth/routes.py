"""
Authentication & Channel Routing API
Handles User Signup, Password Login, Google OAuth Bridge, and Token Issuance
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from backend.database.connection import get_db
from backend.database.models import User, Channel
from backend.auth.security import hash_password, verify_password, create_access_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class RegisterPayload(BaseModel):
    email: EmailStr
    password: str
    channel_name: str
    channel_handle: str

class LoginPayload(BaseModel):
    email: EmailStr
    password: str

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterPayload, db: Session = Depends(get_db)):
    # 1. Check if email already exists
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # 2. Check handle availability
    clean_handle = payload.channel_handle if payload.channel_handle.startswith("@") else f"@{payload.channel_handle}"
    existing_handle = db.query(Channel).filter(Channel.handle == clean_handle).first()
    if existing_handle:
        raise HTTPException(status_code=400, detail="This channel handle is already taken.")

    # 3. Create User & Channel
    new_user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_google_account=False,
        is_2fa_enabled=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_channel = Channel(
        user_id=new_user.id,
        channel_name=payload.channel_name,
        handle=clean_handle,
        subscribers_count=0
    )
    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)

    # 4. Generate JWT Token
    token = create_access_token(data={"sub": new_user.id, "email": new_user.email, "channel_id": new_channel.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": new_user.id,
        "channel_name": new_channel.channel_name,
        "handle": new_channel.handle
    }

@router.post("/login")
def login_user(payload: LoginPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    channel = db.query(Channel).filter(Channel.user_id == user.id).first()
    token = create_access_token(data={"sub": user.id, "email": user.email, "channel_id": channel.id if channel else None})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "channel_name": channel.channel_name if channel else "BTube Creator",
        "handle": channel.handle if channel else "@creator"
    }

@router.get("/me")
def get_current_user_profile(token_data: dict = Depends(decode_token), db: Session = Depends(get_db)):
    user_id = token_data.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    channel = db.query(Channel).filter(Channel.user_id == user.id).first()
    return {
        "email": user.email,
        "channel_name": channel.channel_name,
        "handle": channel.handle,
        "subscribers": channel.subscribers_count,
        "bpp_tier": channel.bpp_tier,
        "watch_hours": channel.public_watch_hours_365d,
        "strikes": channel.active_strikes
    }
