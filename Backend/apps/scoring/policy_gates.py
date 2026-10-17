"""
Pending council decisions that block OFFICIAL certification (FIN-03 / SCO-01).

Some subcriteria carry marks that no institution can currently earn, because the authoritative source gives
them no documentary-evidence rule and the framework fails closed without evidence. Certifying while they are
unresolved would issue an official result that is capped below 100 for reasons the institution cannot affect.

No scoring rule is invented here. Each entry names the decision the council must take. The block lifts by
itself once the evidence taxonomy gives every listed subcriterion an ACTIVE contract with an accepted evidence
type (that change is made only after the council's decision is recorded); there is no switch to override it.
"""
from typing import Dict, List

from apps.evidence.taxonomy import ContractStatus, get_subcriterion_contract

PENDING_COUNCIL_DECISIONS: Dict[str, tuple] = {
    "UNIVERSITY_2026": (
        {
            "id": "POL-U6",
            "parameter": "U6",
            "subcriteria": ("U6.A", "U6.B"),
            "marks": 8.0,
            "decision_required": (
                "Which documentary evidence proves U6.A and U6.B? The University PDF gives U6 no evidence line, "
                "while its general instructions award marks only on uploaded documentary evidence."
            ),
        },
        {
            "id": "POL-U18.3",
            "parameter": "U18",
            "subcriteria": ("U18.3",),
            "marks": 2.0,
            "decision_required": (
                "Does U18's parameter-level evidence (adopted policy, programme list, applications assessed, "
                "approval records) also prove U18.3, or which evidence does?"
            ),
        },
    ),
    "COLLEGE_2026": (),
}


def _subcriterion_resolved(framework: str, parameter: str, subcriterion: str) -> bool:
    contract = get_subcriterion_contract(framework, parameter, subcriterion)
    return bool(contract and contract.status == ContractStatus.ACTIVE and contract.canonical_evidence_type)


def open_certification_policy_blockers(framework: str) -> List[dict]:
    """The pending decisions for `framework` that still block official certification."""
    open_items = []
    for item in PENDING_COUNCIL_DECISIONS.get(framework, ()):
        unresolved = [s for s in item["subcriteria"] if not _subcriterion_resolved(framework, item["parameter"], s)]
        if unresolved:
            open_items.append({**item, "subcriteria": list(item["subcriteria"]), "unresolved_subcriteria": unresolved})
    return open_items


def certification_policy_message(blockers: List[dict]) -> str:
    marks = sum(b["marks"] for b in blockers)
    subs = ", ".join(s for b in blockers for s in b["unresolved_subcriteria"])
    return (
        f"Official certification is on hold pending a council decision: {subs} ({marks:g} marks) cannot be scored "
        f"because no documentary-evidence rule has been approved for them. Scores remain provisional until the "
        f"decision is recorded and the evidence taxonomy is updated."
    )
