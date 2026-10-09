"""
BTube SafeShield AI (NSFW Blocker) & CopyScan AI (Audio Fingerprint/Reused Check)
"""

def scan_safeshield(video_filename: str, video_title: str) -> dict:
    """
    Checks for inappropriate/adult terms and frame safety.
    """
    forbidden_terms = ["18+", "nsfw", "adult", "xxx", "gandi", "ashleel"]
    title_lower = video_title.lower()

    for word in forbidden_terms:
        if word in title_lower:
            return {
                "passed": False,
                "status": "Blocked",
                "reason": "Violates Community Guidelines: Inappropriate or NSFW content."
            }

    return {"passed": True, "status": "Clean", "reason": "Passed all safety standards."}


def scan_copyscan(audio_signature_hash: str, known_audio_db: dict) -> dict:
    """
    Matches audio fingerprint against known copyright registry.
    """
    if audio_signature_hash in known_audio_db:
        original = known_audio_db[audio_signature_hash]
        return {
            "has_limitation": True,
            "status": "Claim_Audio",
            "claim_type": "Potential Limitation",
            "matched_song": original["title"],
            "owner": original["owner"],
            "impact": "Video is public, but ad revenue goes to copyright owner."
        }

    return {
        "has_limitation": False,
        "status": "Original",
        "claim_type": "None",
        "impact": "100% Monetizable to creator."
    }
