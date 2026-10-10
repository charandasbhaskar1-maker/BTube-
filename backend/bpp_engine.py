"""
BTube Partner Program (BPP) & Viral Algorithm Engine
Implements:
- Terms & Policies Synced Regional Creator Thresholds (200 Subs / 200 Hours / 5 Lakh Views)
- Strict 2FA & 0-Strike Compliance Evaluation
- Normalized Multi-Factor Recommendation Score (CTR, Audience Retention, Shares, Likes)
"""

from typing import Dict, Any

# Regional Creator Thresholds (Synced with terms.html Policy)
BPP_TIER1_SUBS = 200
BPP_TIER1_HOURS = 200.0
BPP_TIER1_SHORTS_VIEWS = 500000  # 5 Lakh Views

# Scaled National Tier (Full Ad-Sense Scaling)
BPP_TIER2_SUBS = 1000
BPP_TIER2_HOURS = 4000.0
BPP_TIER2_SHORTS_VIEWS = 10000000  # 10 Million Views


def evaluate_bpp_eligibility(
    subscribers: int,
    watch_hours: float,
    shorts_views: int,
    strikes: int,
    has_2fa: bool
) -> Dict[str, Any]:
    """
    Evaluates channel monetization qualification against official BTube policies.
    Enforces zero-strike standing and active two-step verification.
    """
    # 1. Compliance Gatekeeper
    if strikes > 0:
        return {
            "eligible": False,
            "tier": "Not Eligible",
            "reason": f"Active copyright/community strikes present ({strikes} active). Strikes must expire first.",
            "can_apply": False
        }

    if not has_2fa:
        return {
            "eligible": False,
            "tier": "Not Eligible",
            "reason": "2-Step Verification is disabled. Enable 2FA in Google / BTube security to qualify.",
            "can_apply": False
        }

    # 2. Tier 2: Scaled Platform Partner (Full Ad Revenue Split)
    if subscribers >= BPP_TIER2_SUBS and (watch_hours >= BPP_TIER2_HOURS or shorts_views >= BPP_TIER2_SHORTS_VIEWS):
        return {
            "eligible": True,
            "tier": "Tier 2 (Full Revenue Partner)",
            "can_apply": True,
            "features": [
                "Watch Page Video Advertisements (70/30 Split)",
                "Shorts Feed Revenue Share",
                "Super Thanks Fan Funding",
                "Channel Memberships & VIP Badges"
            ],
            "progress_pct": 100.0
        }

    # 3. Tier 1: Regional Creator Growth Partner (Super Thanks & Fan Funding)
    # Synced with terms.html: 200 Subs + 200 Hours OR 5 Lakh Views
    tier1_qualifies = subscribers >= BPP_TIER1_SUBS and (watch_hours >= BPP_TIER1_HOURS or shorts_views >= BPP_TIER1_SHORTS_VIEWS)

    sub_pct = min(100.0, (subscribers / BPP_TIER1_SUBS) * 100)
    hour_pct = min(100.0, (watch_hours / BPP_TIER1_HOURS) * 100)
    views_pct = min(100.0, (shorts_views / BPP_TIER1_SHORTS_VIEWS) * 100)

    overall_progress = round((sub_pct + max(hour_pct, views_pct)) / 2.0, 1)

    if tier1_qualifies:
        return {
            "eligible": True,
            "tier": "Tier 1 (Fan Funding & Super Thanks)",
            "can_apply": True,
            "features": [
                "Super Thanks 70/30 Fan Funding",
                "Creator Verified Badge",
                "Direct Creator Support Link"
            ],
            "progress_pct": 100.0
        }

    return {
        "eligible": False,
        "tier": "Not Eligible",
        "can_apply": False,
        "progress_pct": overall_progress,
        "metrics_progress": {
            "subscribers": {
                "current": subscribers,
                "target": BPP_TIER1_SUBS,
                "percentage": round(sub_pct, 1)
            },
            "watch_hours": {
                "current": round(watch_hours, 1),
                "target": BPP_TIER1_HOURS,
                "percentage": round(hour_pct, 1)
            },
            "shorts_views": {
                "current": shorts_views,
                "target": BPP_TIER1_SHORTS_VIEWS,
                "percentage": round(views_pct, 1)
            }
        }
    }


def calculate_viral_score(
    impressions: int,
    clicks: int,
    watch_time_sec: float,
    total_duration_sec: float,
    likes: int,
    shares: int,
    is_shorts: bool = False
) -> float:
    """
    Computes real-time Viral / Recommendation Ranking Score:
    Score = (CTR * 0.25) + (RetentionFactor * 0.45) + (ShareVelocity * 0.20) + (LikeRatio * 0.10)
    """
    # 1. Click-Through Rate (CTR) with smoothing
    effective_impressions = max(10, impressions)
    ctr = (clicks / effective_impressions) * 100.0

    # 2. Audience Retention
    if clicks > 0 and total_duration_sec > 0:
        avg_watch_per_view = watch_time_sec / clicks
        retention_ratio = avg_watch_per_view / total_duration_sec
        # Shorts often get > 100% due to loop playback
        max_retention_cap = 200.0 if is_shorts else 100.0
        retention_pct = min(max_retention_cap, retention_ratio * 100.0)
    else:
        retention_pct = 0.0

    # 3. Share Velocity (Strongest signal for viral discovery)
    share_factor = min(100.0, shares * 8.0)

    # 4. Like Engagement Ratio
    like_ratio = (likes / clicks * 100.0) if clicks > 0 else 0.0
    like_factor = min(100.0, like_ratio * 5.0)

    # Weighted Composite Score
    score = (ctr * 0.25) + (retention_pct * 0.45) + (share_factor * 0.20) + (like_factor * 0.10)
    return round(score, 2)
