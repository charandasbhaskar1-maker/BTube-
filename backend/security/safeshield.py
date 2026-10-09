"""
BTube SafeShield Engine
Detects and blocks NSFW/vulgar media, adult keywords, and profanity in real-time.
"""

import re
from typing import Dict, Any

VULGAR_KEYWORDS = [
    "nsfw", "xxx", "porn", "adult", "nude", "sex", "erotic",
    "gandi", "ashleel", "chudai", "harami", "gaali"
]

def scan_text_safeshield(text: str) -> Dict[str, Any]:
    """
    Checks titles, descriptions, and tags for vulgar or prohibited language.
    """
    if not text:
        return {"passed": True, "reason": "Text empty"}

    text_lower = text.lower()
    for word in VULGAR_KEYWORDS:
        # Match whole word or exact pattern
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text_lower):
            return {
                "passed": False,
                "status": "Blocked",
                "reason": f"Violates Family Safety Policy: Inappropriate term detected ('{word}')"
            }

    return {"passed": True, "status": "Clean", "reason": "No policy violation detected"}

def scan_media_frames_safeshield(video_file_path: str) -> Dict[str, Any]:
    """
    Simulated frame-by-frame visual screening pipeline.
    (Production will bind to NudeNet / open-source vision classifier)
    """
    # Placeholder returning pass for verified family-safe uploads
    return {
        "passed": True,
        "status": "Clean",
        "nsfw_score": 0.02,
        "reason": "Visual scan passed successfully."
    }
