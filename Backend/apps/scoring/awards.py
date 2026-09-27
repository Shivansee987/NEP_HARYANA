"""
NEP Excellence Awards 2026 - Authoritative Award Classification Engine
Evaluates final award classification strictly against authoritative Platinum / Gold / Bronze thresholds.
Prohibits arbitrary threshold guessing and bans legacy Silver/Gold/Platinum categorization.
"""
from enum import Enum
from typing import Any, Dict, Optional
from django.conf import settings


class AwardTier(str, Enum):
    PLATINUM = "PLATINUM"
    GOLD = "GOLD"
    BRONZE = "BRONZE"
    NO_AWARD = "NO_AWARD"


def get_authoritative_award_classification(
    score: float,
    framework: str,
    custom_thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Evaluates final score against authoritative Platinum, Gold, and Bronze thresholds.
    
    Invariants:
    1. Only PLATINUM, GOLD, BRONZE labels are permitted. Old legacy Silver/Gold/Platinum is banned.
    2. If no authoritative thresholds are defined in configuration, percentages are NOT guessed.
       The function explicitly reports missing threshold configuration.
    3. Classification is strictly deterministic:
       score >= PLATINUM -> PLATINUM
       score >= GOLD -> GOLD
       score >= BRONZE -> BRONZE
       score < BRONZE -> NO_AWARD
    """
    # 1. Lookup configured thresholds
    thresholds = custom_thresholds
    if thresholds is None:
        thresholds = getattr(settings, "NEP_2026_AWARD_THRESHOLDS", None)

    # 2. Handle missing authoritative thresholds explicitly
    if not thresholds or not isinstance(thresholds, dict):
        return {
            "award_level": None,
            "status": "THRESHOLD_CONFIGURATION_MISSING",
            "is_configured": False,
            "thresholds_missing": True,
            "score": round(score, 2),
            "framework": framework,
            "configured_thresholds": None,
            "message": (
                "Authoritative award thresholds (Platinum / Gold / Bronze) missing from source specification "
                "— requires State Council determination."
            ),
        }

    # 3. Deterministic evaluation with authoritative configured thresholds
    try:
        plat_min = float(thresholds["PLATINUM"])
        gold_min = float(thresholds["GOLD"])
        bronze_min = float(thresholds["BRONZE"])
    except (KeyError, TypeError, ValueError) as err:
        return {
            "award_level": None,
            "status": "INVALID_THRESHOLD_CONFIGURATION",
            "is_configured": False,
            "thresholds_missing": True,
            "score": round(score, 2),
            "framework": framework,
            "configured_thresholds": thresholds,
            "message": f"Configured award thresholds are invalid or incomplete: {err}",
        }

    normalized_score = round(score, 2)

    if normalized_score >= plat_min:
        level = AwardTier.PLATINUM.value
    elif normalized_score >= gold_min:
        level = AwardTier.GOLD.value
    elif normalized_score >= bronze_min:
        level = AwardTier.BRONZE.value
    else:
        level = AwardTier.NO_AWARD.value

    return {
        "award_level": level,
        "status": "DETERMINED",
        "is_configured": True,
        "thresholds_missing": False,
        "score": normalized_score,
        "framework": framework,
        "configured_thresholds": {
            "PLATINUM": plat_min,
            "GOLD": gold_min,
            "BRONZE": bronze_min,
        },
        "message": f"Award level classified as {level} based on authoritative thresholds.",
    }
