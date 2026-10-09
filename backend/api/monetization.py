"""
BTube Partner Program (BPP) Monetization API
Tracks Eligibility, 2FA, Strikes, and UPI Payouts
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database.connection import get_db
from backend.database.models import Channel, User
from backend.auth.security import decode_token
from backend.bpp_engine import evaluate_bpp_eligibility

router = APIRouter(prefix="/api/bpp", tags=["Monetization"])

class PayoutUpiPayload(BaseModel):
    upi_id: str

@router.get("/dashboard")
def get_bpp_creator_dashboard(token_data: dict = Depends(decode_token), db: Session = Depends(get_db)):
    channel_id = token_data.get("channel_id")
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    user = db.query(User).filter(User.id == channel.user_id).first()

    evaluation = evaluate_bpp_eligibility(
        subscribers=channel.subscribers_count,
        watch_hours=channel.public_watch_hours_365d,
        shorts_views=channel.shorts_views_90d,
        strikes=channel.active_strikes,
        has_2fa=user.is_2fa_enabled if user else False
    )

    return {
        "channel_name": channel.channel_name,
        "current_tier": channel.bpp_tier,
        "metrics": {
            "subscribers": channel.subscribers_count,
            "watch_hours": round(channel.public_watch_hours_365d, 2),
            "shorts_views": channel.shorts_views_90d
        },
        "compliance": {
            "2fa_enabled": user.is_2fa_enabled if user else False,
            "active_strikes": channel.active_strikes
        },
        "evaluation": evaluation,
        "wallet": {
            "total_earnings_inr": channel.total_earnings_inr,
            "payout_upi_id": channel.payout_upi_id
        }
    }

@router.post("/set-payout-upi")
def set_payout_upi(payload: PayoutUpiPayload, token_data: dict = Depends(decode_token), db: Session = Depends(get_db)):
    channel_id = token_data.get("channel_id")
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if "@" not in payload.upi_id:
        raise HTTPException(status_code=400, detail="Invalid UPI ID format (e.g. name@okhdfcbank)")

    channel.payout_upi_id = payload.upi_id
    db.commit()
    return {"status": "success", "message": f"Payout UPI set to {payload.upi_id}"}
