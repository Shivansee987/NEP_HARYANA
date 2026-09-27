"""
NEP Excellence Awards 2026 - Policy Decision Registry

The source PDFs contain items the implementation must NOT resolve on its own
(arithmetic contradictions, undefined metrics, uncovered boundary values).
Each such item is registered here with an explicit status. A decision can only
be supplied by the rubric owner through configuration:

    settings.NEP_2026_POLICY_DECISIONS = {
        "SCOPUS_METRIC": {"status": "RESOLVED", "metric_label": "...", "decided_by": "...", "reference": "..."},
        "BOUNDARY_C5_75": {"status": "RESOLVED", "score": 1.0, "decided_by": "...", "reference": "..."},
        "U9B_FRACTIONAL_AVERAGE": {"status": "RESOLVED", "rule": "FLOOR", ...},
    }

Certification impact of each item:
    ADVISORY            - scored literally from the source (stated maximum is the ceiling); the open
                          question is surfaced on every result but does not block certification.
    BLOCKS_WHEN_TRIGGERED - only an input that actually hits the undefined case blocks certification
                          (e.g. exactly 75.0% for C5, a fractional U9.B average, a claimed Scopus value).
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings


ADVISORY = "ADVISORY"
BLOCKS_WHEN_TRIGGERED = "BLOCKS_WHEN_TRIGGERED"

UNRESOLVED = "UNRESOLVED"
RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class PolicyItem:
    policy_id: str
    parameters: Tuple[str, ...]
    question: str
    implementation_default: str
    certification_impact: str
    built_in_status: str = UNRESOLVED
    built_in_resolution: Optional[Dict[str, Any]] = None
    allowed_rules: Tuple[str, ...] = field(default_factory=tuple)


POLICY_ITEMS: Dict[str, PolicyItem] = {p.policy_id: p for p in [
    PolicyItem(
        policy_id="C7_MAXIMUM",
        parameters=("C7",),
        question="C7 states a maximum of 6 marks but its rubric tiers top out at 3 marks.",
        implementation_default="Scored literally from the source tiers (achievable 3 of stated 6). No marks are added.",
        certification_impact=ADVISORY,
    ),
    PolicyItem(
        policy_id="C16_ITEMS_EXCEED_MAXIMUM",
        parameters=("C16",),
        question="C16 lists five 1-mark items (5 marks) against a stated maximum of 4 marks.",
        implementation_default="Each item scores 1 mark; the parameter total is capped at the stated maximum of 4.",
        certification_impact=ADVISORY,
    ),
    PolicyItem(
        policy_id="U20_ITEMS_EXCEED_MAXIMUM",
        parameters=("U20",),
        question="U20 components total 5 marks (2 + 2 + 1) against a stated maximum of 4 marks.",
        implementation_default="Components are scored as written; the parameter total is capped at the stated maximum of 4.",
        certification_impact=ADVISORY,
    ),
    PolicyItem(
        policy_id="C21_MAXIMUM",
        parameters=("C21",),
        question="C21 states a maximum of 4 marks but its components can reach only 3 marks.",
        implementation_default="Scored literally from the source components (achievable 3 of stated 4). No marks are added.",
        certification_impact=ADVISORY,
    ),
    PolicyItem(
        policy_id="U8A_COMPONENT_HEADER",
        parameters=("U8",),
        question="U8.A header says '3 marks' while its tiers award up to 4 marks (4 + 2 = stated maximum 6).",
        implementation_default="Tiers are applied as written (up to 4), consistent with the stated parameter maximum of 6.",
        certification_impact=ADVISORY,
    ),
    PolicyItem(
        policy_id="C8_BINARY",
        parameters=("C8",),
        question="C8 (Nomination of NEP-SARTHI, 2 marks) has a single criterion line without tiers.",
        implementation_default="Binary: nomination made and supported by verified office orders -> 2 marks, otherwise 0.",
        certification_impact=ADVISORY,
        built_in_status=RESOLVED,
        built_in_resolution={
            "rule": "BINARY_2_MARKS",
            "decided_by": "Scoring repair brief (2026-09-28)",
            "reference": "NEP 2026 scoring repair instruction: 'C8: binary 2-mark criterion.'",
        },
    ),
    PolicyItem(
        policy_id="SCOPUS_METRIC",
        parameters=("C19", "U16"),
        question="C19.III / U16.III score a 'Scopus index during evaluation period' whose metric is not defined in the source.",
        implementation_default="No value is scored until the metric is defined. A claimed Scopus value blocks certification.",
        certification_impact=BLOCKS_WHEN_TRIGGERED,
    ),
    PolicyItem(
        policy_id="BOUNDARY_C5_75",
        parameters=("C5",),
        question="C5: exactly 75% of sanctioned seats filled is covered by neither '>75% and <90%' nor '<75%'.",
        implementation_default="An input of exactly 75.0% is not scored and blocks certification.",
        certification_impact=BLOCKS_WHEN_TRIGGERED,
    ),
    PolicyItem(
        policy_id="BOUNDARY_U5A_50",
        parameters=("U5",),
        question="U5.A: exactly 50% eligibility is covered by neither '>50% and up to 75%' nor '<50%'.",
        implementation_default="An input of exactly 50.0% is not scored and blocks certification.",
        certification_impact=BLOCKS_WHEN_TRIGGERED,
    ),
    PolicyItem(
        policy_id="BOUNDARY_U10_3_1CR",
        parameters=("U10",),
        question="U10.3: alumni funding of exactly Rs. 1 Crore is covered by neither '>Rs.1 Crore' nor '<Rs.1 Crore'.",
        implementation_default="An input of exactly Rs. 1,00,00,000 is not scored and blocks certification.",
        certification_impact=BLOCKS_WHEN_TRIGGERED,
    ),
    PolicyItem(
        policy_id="BOUNDARY_C21_1_ACTIVITY",
        parameters=("C21",),
        question="C21.I: exactly one activity is covered by neither 'Two to four' nor 'No activity'.",
        implementation_default="An input of exactly 1 activity is not scored and blocks certification.",
        certification_impact=BLOCKS_WHEN_TRIGGERED,
    ),
    PolicyItem(
        policy_id="U9B_FRACTIONAL_AVERAGE",
        parameters=("U9",),
        question="U9.B tiers are whole numbers (5+, 4, 3, 2, 1); the source does not say how a fractional average is tiered.",
        implementation_default="A fractional average below 5 is not scored and blocks certification.",
        certification_impact=BLOCKS_WHEN_TRIGGERED,
        allowed_rules=("FLOOR", "ROUND_HALF_UP", "CEIL"),
    ),
    PolicyItem(
        policy_id="AWARD_THRESHOLDS",
        parameters=(),
        question="The parameter PDFs do not define Platinum / Gold / Bronze award bands.",
        implementation_default="Award classification is reported as UNCONFIGURED.",
        certification_impact=ADVISORY,
    ),
]}

BOUNDARY_POLICY_BY_SUBCRITERION = {
    "C5.1": "BOUNDARY_C5_75",
    "U5.A": "BOUNDARY_U5A_50",
    "U10.3": "BOUNDARY_U10_3_1CR",
    "C21.1": "BOUNDARY_C21_1_ACTIVITY",
}

ADVISORY_POLICY_BY_PARAMETER = {
    "C7": "C7_MAXIMUM",
    "C16": "C16_ITEMS_EXCEED_MAXIMUM",
    "U20": "U20_ITEMS_EXCEED_MAXIMUM",
    "C21": "C21_MAXIMUM",
    "U8": "U8A_COMPONENT_HEADER",
    "C8": "C8_BINARY",
}


def _configured_decisions() -> Dict[str, Dict[str, Any]]:
    decisions = getattr(settings, "NEP_2026_POLICY_DECISIONS", None) or {}
    return decisions if isinstance(decisions, dict) else {}


def get_policy_state(policy_id: str) -> Dict[str, Any]:
    """Returns the effective status and resolution of a policy item."""
    item = POLICY_ITEMS[policy_id]
    configured = _configured_decisions().get(policy_id)
    if isinstance(configured, dict) and str(configured.get("status", "")).upper() == RESOLVED:
        return {"policy_id": policy_id, "status": RESOLVED, "resolution": dict(configured), "source": "CONFIGURATION"}
    if item.built_in_status == RESOLVED:
        return {"policy_id": policy_id, "status": RESOLVED, "resolution": dict(item.built_in_resolution or {}), "source": "BUILT_IN"}
    return {"policy_id": policy_id, "status": UNRESOLVED, "resolution": None, "source": None}


def is_resolved(policy_id: str) -> bool:
    return get_policy_state(policy_id)["status"] == RESOLVED


def policy_notice(policy_id: str, triggered: bool = False) -> Dict[str, Any]:
    item = POLICY_ITEMS[policy_id]
    state = get_policy_state(policy_id)
    return {
        "policy_id": policy_id,
        "parameters": list(item.parameters),
        "question": item.question,
        "implementation_default": item.implementation_default,
        "certification_impact": item.certification_impact,
        "status": state["status"],
        "resolution": state["resolution"],
        "triggered": triggered,
        "blocks_certification": bool(
            triggered and item.certification_impact == BLOCKS_WHEN_TRIGGERED and state["status"] != RESOLVED
        ),
    }


def boundary_resolution_score(policy_id: str) -> Optional[float]:
    """Returns the configured score for a boundary void, or None when unresolved/invalid."""
    state = get_policy_state(policy_id)
    if state["status"] != RESOLVED:
        return None
    try:
        return float(state["resolution"]["score"])
    except (KeyError, TypeError, ValueError):
        return None


def u9b_fractional_rule() -> Optional[str]:
    state = get_policy_state("U9B_FRACTIONAL_AVERAGE")
    if state["status"] != RESOLVED:
        return None
    rule = str((state["resolution"] or {}).get("rule", "")).upper()
    return rule if rule in POLICY_ITEMS["U9B_FRACTIONAL_AVERAGE"].allowed_rules else None


def scopus_metric_resolution() -> Optional[Dict[str, Any]]:
    state = get_policy_state("SCOPUS_METRIC")
    return state["resolution"] if state["status"] == RESOLVED else None


def get_policy_register() -> List[Dict[str, Any]]:
    """Full register for reports and admin display."""
    return [policy_notice(pid) for pid in POLICY_ITEMS]
