"""
BTube Partner Program (BPP) & Viral Algorithm Engine
"""

def evaluate_bpp_eligibility(subscribers: int, watch_hours: float, shorts_views: int, strikes: int, has_2fa: bool) -> dict:
    """
    Checks channel against official BPP Tier 1 and Tier 2 criteria.
    """
    if strikes > 0 or not has_2fa:
        return {
            "eligible": False,
            "tier": "Not Eligible",
            "reason": "Active strikes present or 2-Step Verification disabled"
        }

    # Tier 2: Full Monetization (1,000 Subs + 4,000 hrs OR 10M Shorts views)
    if subscribers >= 1000 and (watch_hours >= 4000.0 or shorts_views >= 10000000):
        return {
            "eligible": True,
            "tier": "Tier 2 (Full Revenue)",
            "features": ["Watch Page Ads", "Shorts Feed Ads", "BTube Premium Revenue", "Fan Funding"]
        }

    # Tier 1: Early Access / Fan Funding (500 Subs + 3,000 hrs OR 3M Shorts views)
    if subscribers >= 500 and (watch_hours >= 3000.0 or shorts_views >= 3000000):
        return {
            "eligible": True,
            "tier": "Tier 1 (Fan Funding)",
            "features": ["Super Thanks", "Channel Memberships", "Creator Badges"]
        }

    return {
        "eligible": False,
        "tier": "Not Eligible",
        "progress": {
            "subs": f"{subscribers}/500",
            "hours": f"{watch_hours}/3000",
            "shorts_views": f"{shorts_views}/3000000"
        }
    }


def calculate_viral_score(impressions: int, clicks: int, watch_time_sec: float, total_duration_sec: float, likes: int, shares: int) -> float:
    """
    Calculates Recommendation / Viral Score:
    Viral Score = (CTR * 0.25) + (Retention% * 0.40) + (Shares * 0.20) + (Likes * 0.15)
    """
    # 1. Click-Through Rate (CTR)
    ctr = (clicks / impressions * 100) if impressions > 0 else 0.0

    # 2. Average Retention Percentage
    expected_watch = total_duration_sec * clicks if clicks > 0 else 1.0
    retention_pct = min(100.0, (watch_time_sec / expected_watch) * 100) if expected_watch > 0 else 0.0

    # 3. Share velocity factor
    share_factor = min(100.0, shares * 5.0)

    # 4. Likes engagement factor
    likes_factor = min(100.0, (likes / clicks * 100)) if clicks > 0 else 0.0

    score = (ctr * 0.25) + (retention_pct * 0.40) + (share_factor * 0.20) + (likes_factor * 0.15)
    return round(score, 2)
