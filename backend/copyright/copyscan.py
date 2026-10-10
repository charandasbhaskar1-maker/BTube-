"""
BTube CopyScan Engine & Content ID System
Implements:
- Audio Waveform Fingerprint Analysis & Registry Matching
- Automated Content ID Claim Resolution (Full Block vs 50/50 Revenue Sharing)
- Official 3-Strikes Penalties with 90-Day Expiration Windows
- Counter-Notification & Dispute Resolution Pipeline
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

# Official Master Registry for Regional Music, Folk Labels & Instrumentals
PROTECTED_AUDIO_REGISTRY = {
    "hash_cg_mor_maya": {
        "isrc": "IN-B01-26-00124",
        "song_name": "Mor Maya Ke Chhaiya",
        "artist_or_label": "CG Folk Music Records",
        "allow_monetization_share": True,  # 50/50 Split for Cover / Remix
        "claim_policy": "MONETIZE_SPLIT"
    },
    "hash_banjo_classical_tune": {
        "isrc": "IN-B01-26-00892",
        "song_name": "Typewriter Banjo Classical Raga",
        "artist_or_label": "Dhun AI Studio",
        "allow_monetization_share": False,
        "claim_policy": "ROUTE_TO_OWNER"
    },
    "hash_cg_hareli_geet": {
        "isrc": "IN-B01-26-00341",
        "song_name": "Hareli Tihaar Lok Dhun",
        "artist_or_label": "Chhattisgarh Lok Kala Parishad",
        "allow_monetization_share": True,
        "claim_policy": "MONETIZE_SPLIT"
    }
}

STRIKE_EXPIRATION_DAYS = 90


# ================= 1. AUDIO FINGERPRINT & CONTENT ID =================

def analyze_audio_fingerprint(audio_hash: Optional[str]) -> Dict[str, Any]:
    """
    Scans media audio signature against protected Content ID database.
    Determines monetization routing, revenue splits, and copyright claims.
    """
    if not audio_hash:
        return {
            "has_claim": False,
            "status": "Clean",
            "claim_type": "None",
            "song": None,
            "owner": None,
            "is_monetizable": True,
            "creator_share_percentage": 100,
            "impact": "100% original content. Eligible for standard YPP monetization."
        }

    clean_hash = audio_hash.strip().lower()

    # Direct or partial waveform signature match
    matched = None
    for reg_hash, data in PROTECTED_AUDIO_REGISTRY.items():
        if clean_hash == reg_hash or clean_hash.startswith(reg_hash):
            matched = data
            break

    if matched:
        is_split = matched.get("allow_monetization_share", False)
        return {
            "has_claim": True,
            "status": "Content_ID_Claim",
            "claim_type": "Music Recognition Claim",
            "isrc": matched.get("isrc"),
            "song": matched["song_name"],
            "owner": matched["artist_or_label"],
            "allow_share": is_split,
            "is_monetizable": is_split,
            "creator_share_percentage": 50 if is_split else 0,
            "claim_policy": matched.get("claim_policy"),
            "impact": (
                "Cover/Remix detected: 50% ad revenue shared with copyright owner."
                if is_split else
                f"Audio claimed by {matched['artist_or_label']}. All earnings routed to rights holder."
            )
        }

    return {
        "has_claim": False,
        "status": "Clean",
        "claim_type": "None",
        "song": None,
        "owner": None,
        "is_monetizable": True,
        "creator_share_percentage": 100,
        "impact": "No copyright match detected. Creator retains 100% rights."
    }


# ================= 2. 3-STRIKES POLICY & PENALTY ENGINE =================

def calculate_active_strikes(strikes_ledger: List[Dict[str, Any]]) -> int:
    """
    Calculates active strikes excluding those that have passed their 90-day expiration date.
    """
    now = datetime.now(timezone.utc)
    active_count = 0
    for strike in strikes_ledger:
        exp_date = strike.get("expires_at")
        if exp_date and isinstance(exp_date, str):
            exp_date = datetime.fromisoformat(exp_date.replace("Z", "+00:00"))
        
        if exp_date and exp_date > now and strike.get("status") != "RESOLVED":
            active_count += 1
            
    return active_count


def issue_strike_action(current_active_strikes: int, reason: str = "Copyright Takedown") -> Dict[str, Any]:
    """
    Official BTube 3-Strikes Enforcement:
    - Strike 1: 7-day upload and live stream freeze.
    - Strike 2: 14-day upload and playlist creation freeze.
    - Strike 3: Permanent channel termination & wallet lock.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=STRIKE_EXPIRATION_DAYS)
    new_strike_level = current_active_strikes + 1

    strike_record = {
        "strike_number": new_strike_level,
        "issued_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "reason": reason,
        "status": "ACTIVE"
    }

    if new_strike_level == 1:
        return {
            "strike_level": 1,
            "penalty": "Upload and live-streaming freeze for 7 days",
            "freeze_days": 7,
            "can_upload": False,
            "channel_status": "RESTRICTED",
            "strike_record": strike_record,
            "message": "Strike 1 issued. 1-week upload freeze. Expires in 90 days."
        }
    elif new_strike_level == 2:
        return {
            "strike_level": 2,
            "penalty": "Upload, live-streaming, and playlist freeze for 14 days",
            "freeze_days": 14,
            "can_upload": False,
            "channel_status": "RESTRICTED",
            "strike_record": strike_record,
            "message": "Strike 2 issued. 2-week freeze. One more strike leads to permanent termination."
        }
    else:
        return {
            "strike_level": 3,
            "penalty": "Permanent channel termination, content removal, and wallet lock",
            "freeze_days": None,
            "can_upload": False,
            "channel_status": "TERMINATED",
            "strike_record": strike_record,
            "message": "Strike 3 reached. Channel terminated under BTube Copyright Terms."
        }


# ================= 3. DISPUTES & COUNTER-NOTIFICATIONS =================

def submit_copyright_counter_claim(claim_id: str, reason: str, channel_id: str) -> Dict[str, Any]:
    """
    Submits a DMCA / Indian IT Act compliant counter-notification.
    Grants rights holder 30 days to respond before claim is automatically released.
    """
    now = datetime.now(timezone.utc)
    resolution_deadline = now + timedelta(days=30)

    return {
        "status": "DISPUTE_SUBMITTED",
        "claim_id": claim_id,
        "channel_id": channel_id,
        "dispute_reason": reason,
        "submitted_at": now.isoformat(),
        "deadline_for_claimant": resolution_deadline.isoformat(),
        "interim_status": "Video remains active; ad revenue held in escrow."
    }
