"""
BTube Security Guard Engine
Unified Gatekeeper combining SafeShield AI (NSFW/Vulgarity Filter) 
and CopyScan AI (Audio Fingerprint & Content ID Registry).
"""

import re
import os
from typing import Dict, Any, Optional

# Master Copyright Registry (Fallback if DB query is not passed)
DEFAULT_PROTECTED_AUDIO_DB = {
    "hash_cg_mor_maya": {
        "title": "Mor Maya Ke Chhaiya",
        "owner": "CG Folk Music Records",
        "allow_monetization_share": True  # 50/50 Split for Cover / Remix
    },
    "hash_banjo_classical_tune": {
        "title": "Typewriter Banjo Classical Raga",
        "owner": "Dhun AI Studio",
        "allow_monetization_share": False
    },
    "hash_cg_hareli_geet": {
        "title": "Hareli Tihaar Lok Dhun",
        "owner": "Chhattisgarh Lok Kala Parishad",
        "allow_monetization_share": True
    }
}

# Strict NSFW & Hate Speech Lexicon
STRICT_FORBIDDEN_TERMS = [
    "18+", "nsfw", "adult", "xxx", "porn", "nude", "sex", "erotic",
    "gandi", "ashleel", "chudai", "harami", "madarchod", "bhenchod"
]


def _clean_text(raw_text: str) -> str:
    """Removes obfuscation symbols, spaces, and punctuation to prevent bypass."""
    text = raw_text.lower()
    text = text.replace("@", "a").replace("0", "o").replace("1", "i").replace("$", "s")
    cleaned = re.sub(r'[^a-z0-9]', '', text)
    return cleaned


def scan_safeshield(video_filename: str, video_title: str) -> Dict[str, Any]:
    """
    Evaluates video title and filename against community safety standards.
    Prevents leetspeak and obfuscated vulgarity bypass.
    """
    if not video_title and not video_filename:
        return {"passed": True, "status": "Clean", "reason": "No text provided"}

    combined_text = f"{video_title} {video_filename}"
    cleaned = _clean_text(combined_text)

    for word in STRICT_FORBIDDEN_TERMS:
        # Match whole word in raw text OR continuous pattern in cleaned text
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, combined_text.lower()) or word in cleaned:
            return {
                "passed": False,
                "status": "Blocked",
                "matched_term": word,
                "reason": f"Violates BTube Community Guidelines: Prohibited content or inappropriate term detected ('{word}')."
            }

    return {
        "passed": True,
        "status": "Clean",
        "reason": "Passed all SafeShield community safety standards."
    }


def scan_copyscan(
    audio_signature_hash: Optional[str], 
    known_audio_db: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Scans audio fingerprint against the Content ID registry.
    Determines claims, takedowns, and 50/50 cover song monetization splits.
    """
    if not audio_signature_hash:
        return {
            "has_limitation": False,
            "status": "Original",
            "claim_type": "None",
            "matched_song": None,
            "owner": None,
            "is_monetizable": True,
            "creator_share_percentage": 100,
            "impact": "100% original audio. Eligible for creator monetization."
        }

    registry = known_audio_db if known_audio_db is not None else DEFAULT_PROTECTED_AUDIO_DB
    clean_hash = audio_signature_hash.strip().lower()

    # Search for exact or prefix waveform match
    matched = None
    for key, data in registry.items():
        if clean_hash == key or clean_hash.startswith(key):
            matched = data
            break

    if matched:
        allow_share = matched.get("allow_monetization_share", False)
        return {
            "has_limitation": True,
            "status": "Claim_Audio",
            "claim_type": "Content ID Match",
            "matched_song": matched["title"],
            "owner": matched["owner"],
            "is_monetizable": allow_share,
            "creator_share_percentage": 50 if allow_share else 0,
            "impact": (
                "Eligible Cover/Remix: 50% ad revenue shared with copyright owner."
                if allow_share else
                f"Audio claimed by {matched['owner']}. Video remains public, but all revenue is routed to owner."
            )
        }

    return {
        "has_limitation": False,
        "status": "Original",
        "claim_type": "None",
        "matched_song": None,
        "owner": None,
        "is_monetizable": True,
        "creator_share_percentage": 100,
        "impact": "100% Monetizable to creator."
    }


def run_full_security_audit(
    video_title: str, 
    video_filename: str, 
    audio_hash: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience orchestrator that executes both SafeShield and CopyScan audits in one call.
    """
    safety = scan_safeshield(video_filename, video_title)
    if not safety["passed"]:
        return {
            "approved": False,
            "safeshield": safety,
            "copyscan": {"status": "Skipped"},
            "decision": "REJECTED_BY_SAFESHIELD"
        }

    copyright_check = scan_copyscan(audio_hash)
    return {
        "approved": True,
        "safeshield": safety,
        "copyscan": copyright_check,
        "decision": "APPROVED"
    }
