"""
NEP Excellence Awards 2026 - Evidence Gating Evaluator
Enforces mandatory documentary proof before allowing raw scores to become earned scores.
"""
from typing import Any, Dict, List, Optional, Tuple

from apps.scoring.domain import EvidenceDocument
from apps.scoring.enums import EvidenceState, GatingStatus


def evaluate_evidence(
    mandatory_evidence_types: List[str],
    uploaded_docs: List[EvidenceDocument]
) -> Tuple[GatingStatus, float, Dict[str, Any]]:
    """
    Evaluates documentary proof for a subcriterion against mandatory evidence requirements.
    
    Returns:
        (gating_status, score_multiplier, trace)
        
    Gating Rules:
        - If mandatory evidence is absent -> FAILED_EVIDENCE_ABSENT, multiplier = 0.0
        - If any mandatory document is EVIDENCE_REJECTED -> FAILED_EVIDENCE_REJECTED, multiplier = 0.0
        - If any mandatory document is EVIDENCE_PENDING (or PRESENT but unverified) ->
          PROVISIONAL_PENDING_VERIFICATION, multiplier = 0.0 (earned score = 0, certification blocked)
        - If all mandatory evidence types have at least one EVIDENCE_VERIFIED document ->
          PASSED_EVIDENCE_VERIFIED, multiplier = 1.0
        - If mandatory_evidence_types is empty -> NO_EVIDENCE_REQUIRED, multiplier = 1.0
    """
    trace = {
        "mandatory_types_required": mandatory_evidence_types,
        "uploaded_docs_count": len(uploaded_docs),
        "document_statuses": {},
    }

    if not mandatory_evidence_types:
        return GatingStatus.NO_EVIDENCE_REQUIRED, 1.0, trace

    # Map uploaded docs by document_type
    docs_by_type: Dict[str, List[EvidenceDocument]] = {}
    for doc in uploaded_docs:
        docs_by_type.setdefault(doc.document_type, []).append(doc)
        trace["document_statuses"].setdefault(doc.document_type, []).append({
            "document_id": doc.document_id,
            "status": doc.status.value if isinstance(doc.status, EvidenceState) else doc.status,
            "verified_by": doc.verified_by,
            "rejection_reason": doc.rejection_reason,
        })

    # Check each mandatory evidence type
    missing_types = []
    rejected_types = []
    pending_types = []
    verified_types = []

    for req_type in mandatory_evidence_types:
        matching_docs = docs_by_type.get(req_type, [])
        if not matching_docs:
            missing_types.append(req_type)
            continue

        # Check statuses among matching documents
        has_verified = any(d.status == EvidenceState.EVIDENCE_VERIFIED for d in matching_docs)
        has_rejected = any(d.status == EvidenceState.EVIDENCE_REJECTED for d in matching_docs)
        has_pending = any(d.status in (EvidenceState.EVIDENCE_PENDING, EvidenceState.EVIDENCE_PRESENT) for d in matching_docs)

        if has_rejected and not has_verified:
            rejected_types.append(req_type)
        elif has_verified:
            verified_types.append(req_type)
        elif has_pending:
            pending_types.append(req_type)
        else:
            missing_types.append(req_type)

    trace["missing_types"] = missing_types
    trace["rejected_types"] = rejected_types
    trace["pending_types"] = pending_types
    trace["verified_types"] = verified_types

    # Priority 1: If any mandatory type is completely absent
    if missing_types:
        trace["gating_decision"] = f"Missing mandatory documentary proof: {', '.join(missing_types)}"
        return GatingStatus.FAILED_EVIDENCE_ABSENT, 0.0, trace

    # Priority 2: If any mandatory type has rejected evidence
    if rejected_types:
        trace["gating_decision"] = f"Mandatory evidence rejected: {', '.join(rejected_types)}"
        return GatingStatus.FAILED_EVIDENCE_REJECTED, 0.0, trace

    # Priority 3: If any mandatory type is still pending verification
    if pending_types:
        trace["gating_decision"] = f"Evidence pending verification: {', '.join(pending_types)}. Earned score blocked."
        return GatingStatus.PROVISIONAL_PENDING_VERIFICATION, 0.0, trace

    # Priority 4: All required types verified
    if len(verified_types) == len(mandatory_evidence_types):
        trace["gating_decision"] = "All mandatory documentary requirements verified."
        return GatingStatus.PASSED_EVIDENCE_VERIFIED, 1.0, trace

    # Fallback
    trace["gating_decision"] = "Evidence requirements unfulfilled."
    return GatingStatus.FAILED_EVIDENCE_ABSENT, 0.0, trace
