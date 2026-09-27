"""
NEP Excellence Awards 2026 - Evidence Taxonomy Contract & Enforcement Layer
Authoritative evidence taxonomy mapping derived strictly from NEP Excellence Awards 2026 specifications.

Implements Step 4C Evidence Contract Layer:
1. Distinguishes:
   - SOURCE_DOCUMENTARY_REQUIREMENT: What the authoritative NEP source explicitly requires.
   - BACKEND_EVIDENCE_TYPE: The canonical identifier used by the application.
   - SCORE_UNLOCK_REQUIREMENT: The condition required before the subcriterion may contribute to scoring.
2. Removes unsafe parameter-level evidence fallback for MULTI-SUBCRITERION parameters (fails closed).
3. Preserves SOURCE_SILENT cases (U6, C5, C9) as explicitly unresolved with no invented evidence requirements.
4. Preserves source-required-but-currently-missing evidence (U16 Scopus, C19 Scopus, U18 workshop) as UNRESOLVED_MISSING.
5. Quarantines legacy coarse evidence identifiers from unlocking unrelated multi-subcriterion requirements.
6. Preserves legitimate document reuse across subcriteria while preventing sibling unlocking.
7. Enforces strict framework isolation and institution isolation.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from apps.evidence.exceptions import EvidenceDomainError
from apps.scoring.enums import FrameworkType
from apps.scoring.rules.definitions import COLLEGE_PARAMETERS, UNIVERSITY_PARAMETERS


class EvidenceTaxonomyError(EvidenceDomainError):
    """Base exception for evidence taxonomy contract violations."""
    pass


class UnknownEvidenceTypeError(EvidenceTaxonomyError):
    """Raised when an unrecognized evidence_type identifier is provided."""
    pass


class EvidenceTypeFrameworkMismatchError(EvidenceTaxonomyError):
    """Raised when an evidence_type from one framework is submitted for another framework."""
    pass


class EvidenceTypeParameterMismatchError(EvidenceTaxonomyError):
    """Raised when an evidence_type is incompatible with the specified parameter or subcriterion."""
    pass


class AmbiguousEvidenceTypeError(EvidenceTaxonomyError):
    """Raised when a parameter accepts multiple evidence types but none was explicitly specified."""
    pass


class MissingEvidenceTypeError(EvidenceTaxonomyError):
    """Raised when neither evidence_type nor parameter_id is provided for assessment evidence."""
    pass


class SubcriterionEvidenceContractViolationError(EvidenceTypeParameterMismatchError):
    """Raised when an evidence submission violates a subcriterion-level evidence contract."""
    pass


class SourceSilentSubcriterionError(SubcriterionEvidenceContractViolationError):
    """Raised when evidence is submitted or derived for a subcriterion where the source is silent."""
    pass


class UnresolvedEvidenceRequirementError(SubcriterionEvidenceContractViolationError):
    """Raised when evidence is submitted or derived for an unresolved source requirement."""
    pass


class QuarantinedLegacyEvidenceError(SubcriterionEvidenceContractViolationError):
    """Raised when a legacy coarse evidence identifier is used to satisfy an unrelated subcriterion."""
    pass


class InvalidSubcriterionEvidenceTypeError(SubcriterionEvidenceContractViolationError):
    """Raised when an invalid or uncanonical evidence type is used for a subcriterion."""
    pass


class ContractStatus(str, Enum):
    ACTIVE = "ACTIVE"                              # Has authoritative source requirement and active backend evidence type
    SOURCE_SILENT = "SOURCE_SILENT"                # Source PDF is silent on evidence requirements (e.g. U6, C5, C9)
    UNRESOLVED_MISSING = "UNRESOLVED_MISSING"      # Source requires evidence but metric/evidence is unresolved (e.g. U16.III Scopus, C19.III Scopus, U18.3 RPL workshop)
    LEGACY_QUARANTINED = "LEGACY_QUARANTINED"      # Legacy coarse evidence quarantined from multi-subcriterion unlocking


@dataclass(frozen=True)
class SubcriterionEvidenceContract:
    framework: str
    parameter_id: str
    subcriterion_id: str
    source_documentary_requirement: Optional[str]
    canonical_evidence_type: Optional[str]
    score_unlock_requirement: Optional[str]
    status: ContractStatus = ContractStatus.ACTIVE
    allowed_evidence_types: Tuple[str, ...] = ()
    is_source_silent: bool = False
    is_unresolved: bool = False
    is_quarantined: bool = False
    quarantined_types: Tuple[str, ...] = ()
    notes: str = ""


# Single-subcriterion parameters (genuine 1:1 parameter-to-subcriterion mapping)
SINGLE_SUBCRITERION_PARAMETERS: Dict[str, Tuple[str, ...]] = {
    # University
    "U1": ("U1.1",),
    "U2": ("U2.1",),
    "U3": ("U3.1",),
    "U13": ("U13.1",),
    # College
    "C1": ("C1.1", "C1.I", "C1.II"),
    "C2": ("C2.1",),
    "C3": ("C3.1",),
    "C6": ("C6.1",),
    "C7": ("C7.1", "C7.I", "C7.II"),
    "C8": ("C8.1",),
    "C12": ("C12.1", "C12.2", "C12.3", "C12.4", "C12.5"),
    "C13": ("C13.1",),
    "C17": ("C17.1", "C17.I", "C17.II"),
}

# Multi-subcriterion parameters (MUST NOT fall back to parameter-level evidence)
MULTI_SUBCRITERION_PARAMETERS: Set[str] = {
    # University
    "U4", "U5", "U6", "U7", "U8", "U9", "U10", "U11", "U12", "U14", "U15", "U16", "U17", "U18", "U19", "U20",
    # College
    "C4", "C5", "C9", "C10", "C11", "C14", "C15", "C16", "C18", "C19", "C20", "C21", "C22",
}

# Source-silent parameters where authoritative source specifies no documentary evidence
SOURCE_SILENT_PARAMETERS: Set[str] = {"U6", "C5", "C9"}

# Legacy coarse evidence types that must be quarantined from unlocking multi-subcriterion requirements
LEGACY_COARSE_EVIDENCE_TYPES: Set[str] = {
    "EVID_GENERAL",
    "EVID_U7_APPOINTMENT",
    "EVID_U10_REG_CERT",
    "EVID_U17_NIRF_2026_PROOF",
    "EVID_C20_NAAC_CERT",
    "EVID_U6_ORDINANCE_GAZETTE",
    "EVID_C5_SANCTION_LETTER",
    "EVID_C9_FAIR_REGISTER",
}


def _extract_taxonomy_for_parameters(
    params: Dict[str, Any]
) -> Tuple[Set[str], Dict[str, List[str]], Dict[Tuple[str, str], List[str]]]:
    """
    Extracts all valid evidence types, parameter-to-types mapping, and subcriterion-to-types mapping.
    """
    all_types: Set[str] = set()
    param_map: Dict[str, List[str]] = {}
    sub_map: Dict[Tuple[str, str], List[str]] = {}

    for param_code, param_def in params.items():
        p_types: List[str] = list(dict.fromkeys(
            param_def.get("mandatory_evidence", []) + param_def.get("allowed_evidence", [])
        ))
        for sub_code, sub_def in param_def.get("subcriteria", {}).items():
            s_types: List[str] = list(dict.fromkeys(
                sub_def.get("mandatory_evidence", []) + sub_def.get("allowed_evidence", [])
            ))
            if s_types:
                sub_map[(param_code, sub_code)] = s_types
                for t in s_types:
                    if t not in p_types:
                        p_types.append(t)
        param_map[param_code] = p_types
        all_types.update(p_types)

    return all_types, param_map, sub_map


# Initial taxonomy from definitions.py
UNIVERSITY_EVIDENCE_TYPES, UNIVERSITY_PARAM_MAP, UNIVERSITY_SUB_MAP = _extract_taxonomy_for_parameters(UNIVERSITY_PARAMETERS)
COLLEGE_EVIDENCE_TYPES, COLLEGE_PARAM_MAP, COLLEGE_SUB_MAP = _extract_taxonomy_for_parameters(COLLEGE_PARAMETERS)

# Canonical subcriterion-level evidence types derived from authoritative specification
ADDITIONAL_UNIVERSITY_EVIDENCE_TYPES: Set[str] = {
    "EVID_U7_TEACHING_LOGS",
    "EVID_U7_WORKSHOP_REPORTS",
    "EVID_U7_PROJECT_REPORTS",
    "EVID_U10_PORTAL_PROOF",
    "EVID_U10_FINANCIAL_RECORDS",
    "EVID_U10_EVENT_REPORTS",
    "EVID_U16_GRANT",
    "EVID_U17_NIRF_2025_RANK",
    "EVID_U18_LEARNER_CERTS",
    "EVID_U20_CURRICULUM_MAP",
    "EVID_U20_SUSTAINABILITY_REPORT",
}

ADDITIONAL_COLLEGE_EVIDENCE_TYPES: Set[str] = {
    "EVID_C19_GRANT_CERTS",
    "EVID_C20_NIRF_PROOF",
    "EVID_C20_AISHE_CERT",
    "EVID_C20_IQAC_MINUTES",
}

UNIVERSITY_EVIDENCE_TYPES = UNIVERSITY_EVIDENCE_TYPES | ADDITIONAL_UNIVERSITY_EVIDENCE_TYPES
COLLEGE_EVIDENCE_TYPES = COLLEGE_EVIDENCE_TYPES | ADDITIONAL_COLLEGE_EVIDENCE_TYPES
ALL_EVIDENCE_TYPES: Set[str] = UNIVERSITY_EVIDENCE_TYPES | COLLEGE_EVIDENCE_TYPES


# =============================================================================
# EXHAUSTIVE SUBCRITERION EVIDENCE CONTRACT REGISTRY (101 SUBCRITERIA)
# =============================================================================
SUBCRITERION_EVIDENCE_CONTRACTS: Dict[Tuple[str, str, str], SubcriterionEvidenceContract] = {}


def _register_contract(
    framework: str,
    parameter_id: str,
    subcriterion_id: str,
    source_documentary_requirement: Optional[str],
    canonical_evidence_type: Optional[str],
    score_unlock_requirement: Optional[str],
    status: ContractStatus = ContractStatus.ACTIVE,
    allowed_evidence_types: Tuple[str, ...] = (),
    is_source_silent: bool = False,
    is_unresolved: bool = False,
    is_quarantined: bool = False,
    quarantined_types: Tuple[str, ...] = (),
    notes: str = "",
    aliases: Tuple[str, ...] = (),
):
    """Registers a subcriterion contract and its aliases."""
    contract = SubcriterionEvidenceContract(
        framework=framework,
        parameter_id=parameter_id,
        subcriterion_id=subcriterion_id,
        source_documentary_requirement=source_documentary_requirement,
        canonical_evidence_type=canonical_evidence_type,
        score_unlock_requirement=score_unlock_requirement,
        status=status,
        allowed_evidence_types=allowed_evidence_types,
        is_source_silent=is_source_silent,
        is_unresolved=is_unresolved,
        is_quarantined=is_quarantined,
        quarantined_types=quarantined_types,
        notes=notes,
    )
    all_subs = (subcriterion_id,) + aliases
    for s_code in all_subs:
        SUBCRITERION_EVIDENCE_CONTRACTS[(framework, parameter_id, s_code)] = contract


# -----------------------------------------------------------------------------
# UNIVERSITY CONTRACTS (U1–U20: 51 SUBCRITERIA)
# -----------------------------------------------------------------------------

# U1 (1 subcriterion)
_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U1",
    subcriterion_id="U1.1",
    source_documentary_requirement="Approval by statutory bodies (BoS, AC, EC) and copy of curriculum with apprenticeship embedded",
    canonical_evidence_type="EVID_U1_APPROVAL",
    score_unlock_requirement="Verified evidence of approved apprenticeship-embedded degree programmes (EVID_U1_APPROVAL)",
    allowed_evidence_types=("EVID_U1_APPROVAL",),
)

# U2 (1 subcriterion)
_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U2",
    subcriterion_id="U2.1",
    source_documentary_requirement="Curriculum, scheme of examination, BoS/Academic council approval",
    canonical_evidence_type="EVID_U2_COURSE_LIST",
    score_unlock_requirement="Verified evidence of courses offered in Indian languages (EVID_U2_COURSE_LIST)",
    allowed_evidence_types=("EVID_U2_COURSE_LIST",),
)

# U3 (1 subcriterion)
_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U3",
    subcriterion_id="U3.1",
    source_documentary_requirement="Curriculum documents highlighting IKS integration, BoS/Academic Council approvals, course completion data",
    canonical_evidence_type="EVID_U3_SYLLABUS",
    score_unlock_requirement="Verified evidence of IKS integration in programmes (EVID_U3_SYLLABUS)",
    allowed_evidence_types=("EVID_U3_SYLLABUS",),
)

# U4 (4 subcriteria)
for sub_id, alias in [("U4.A", "U4.1"), ("U4.B", "U4.2"), ("U4.1", "U4.A"), ("U4.2", "U4.B")]:
    _register_contract(
        framework="UNIVERSITY_2026",
        parameter_id="U4",
        subcriterion_id=sub_id,
        source_documentary_requirement="Copy of IDP with target sheet, Progress report approved by competent authority",
        canonical_evidence_type="EVID_U4_PROGRESS_REPORT",
        score_unlock_requirement="Verified approved progress report or IDP target sheet",
        allowed_evidence_types=("EVID_U4_PROGRESS_REPORT", "EVID_U4_IDP", "EVID_U4_TARGET_SHEET"),
        aliases=(alias,),
    )

# U5 (2 subcriteria)
for sub_id, alias in [("U5.A", "U5.1"), ("U5.B", "U5.2")]:
    _register_contract(
        framework="UNIVERSITY_2026",
        parameter_id="U5",
        subcriterion_id=sub_id,
        source_documentary_requirement="Placement cell records, offer letters, summary certified by Head of Institution",
        canonical_evidence_type="EVID_U5_HOI_CERT",
        score_unlock_requirement="Verified Head of Institution placement certification",
        allowed_evidence_types=("EVID_U5_HOI_CERT",),
        aliases=(alias,),
    )

# U6 (2 subcriteria: SOURCE_SILENT)
for sub_id, alias in [("U6.A", "U6.1"), ("U6.B", "U6.2")]:
    _register_contract(
        framework="UNIVERSITY_2026",
        parameter_id="U6",
        subcriterion_id=sub_id,
        source_documentary_requirement=None,
        canonical_evidence_type=None,
        score_unlock_requirement="SOURCE_SILENT_UNRESOLVED_NO_UNLOCK",
        status=ContractStatus.SOURCE_SILENT,
        allowed_evidence_types=(),
        is_source_silent=True,
        notes="Authoritative NEP 2026 specification has no documentary evidence clause for U6. Fails closed.",
        aliases=(alias,),
    )

# U7 (4 subcriteria: Independent, no sibling leakage)
_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U7",
    subcriterion_id="U7.1",
    source_documentary_requirement="Notification/Guidelines, Selection committee minutes, Appointment orders, Service agreements",
    canonical_evidence_type="EVID_U7_APPOINTMENT",
    score_unlock_requirement="Verified appointment letter and formal terms of engagement of Professor of Practice",
    allowed_evidence_types=("EVID_U7_APPOINTMENT",),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U7",
    subcriterion_id="U7.2",
    source_documentary_requirement="Teaching logs, workload delivery records, minimum 40 hours interaction records",
    canonical_evidence_type="EVID_U7_TEACHING_LOGS",
    score_unlock_requirement="Verified teaching logs and workload records of Professor of Practice",
    allowed_evidence_types=("EVID_U7_TEACHING_LOGS",),
    quarantined_types=("EVID_U7_APPOINTMENT",),
    notes="Appointment letters do not satisfy teaching log requirement.",
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U7",
    subcriterion_id="U7.3",
    source_documentary_requirement="Workshop reports, training session attendance, feedback records conducted by PoP",
    canonical_evidence_type="EVID_U7_WORKSHOP_REPORTS",
    score_unlock_requirement="Verified workshop and training session reports by PoP",
    allowed_evidence_types=("EVID_U7_WORKSHOP_REPORTS",),
    quarantined_types=("EVID_U7_APPOINTMENT",),
    notes="Appointment letters do not satisfy workshop delivery requirement.",
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U7",
    subcriterion_id="U7.4",
    source_documentary_requirement="Real-world project reports, industry problem-solving outcomes driven by PoP",
    canonical_evidence_type="EVID_U7_PROJECT_REPORTS",
    score_unlock_requirement="Verified project outcome reports and industry deliverables",
    allowed_evidence_types=("EVID_U7_PROJECT_REPORTS",),
    quarantined_types=("EVID_U7_APPOINTMENT",),
    notes="Appointment letters do not satisfy project outcome requirement.",
)

# U8 (2 subcriteria: U8.A, U8.B)
for sub_id, alias in [("U8.A", "U8.1"), ("U8.B", "U8.2")]:
    _register_contract(
        framework="UNIVERSITY_2026",
        parameter_id="U8",
        subcriterion_id=sub_id,
        source_documentary_requirement="Incubation cell registration, list of incubated startups, proof of funds/revenue",
        canonical_evidence_type="EVID_U8_INCUBATION_REG",
        score_unlock_requirement="Verified incubation cell registration and startup performance proof",
        allowed_evidence_types=("EVID_U8_INCUBATION_REG",),
        aliases=(alias,),
    )

# U9 (2 subcriteria: U9.A, U9.B)
for sub_id, alias in [("U9.A", "U9.1"), ("U9.B", "U9.2")]:
    _register_contract(
        framework="UNIVERSITY_2026",
        parameter_id="U9",
        subcriterion_id=sub_id,
        source_documentary_requirement="MoUs with QS top 500, Activity reports, Student/faculty exchange records, joint research output",
        canonical_evidence_type="EVID_U9_MOU",
        score_unlock_requirement="Verified foreign HEI MoUs and exchange/activity records",
        allowed_evidence_types=("EVID_U9_MOU",),
        aliases=(alias,),
    )

# U10 (4 subcriteria: Alumni Cell, independent evidence)
_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U10",
    subcriterion_id="U10.1",
    source_documentary_requirement="Registration certificate under Societies Registration Act",
    canonical_evidence_type="EVID_U10_REG_CERT",
    score_unlock_requirement="Verified alumni association society registration certificate",
    allowed_evidence_types=("EVID_U10_REG_CERT",),
    aliases=("U10.I",),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U10",
    subcriterion_id="U10.2",
    source_documentary_requirement="Functional alumni portal screenshots, verified database records",
    canonical_evidence_type="EVID_U10_PORTAL_PROOF",
    score_unlock_requirement="Verified alumni portal and database coverage proof",
    allowed_evidence_types=("EVID_U10_PORTAL_PROOF",),
    quarantined_types=("EVID_U10_REG_CERT",),
    aliases=("U10.II",),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U10",
    subcriterion_id="U10.3",
    source_documentary_requirement="Audited accounts of alumni fund, bank statements, contribution receipts (>Rs. 1 Crore)",
    canonical_evidence_type="EVID_U10_FINANCIAL_RECORDS",
    score_unlock_requirement="Verified audited accounts of alumni financial contributions",
    allowed_evidence_types=("EVID_U10_FINANCIAL_RECORDS",),
    quarantined_types=("EVID_U10_REG_CERT",),
    notes="Society registration certificate does not satisfy alumni financial contributions.",
    aliases=("U10.III",),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U10",
    subcriterion_id="U10.4",
    source_documentary_requirement="Event reports, guest lecture records of distinguished alumni invited",
    canonical_evidence_type="EVID_U10_EVENT_REPORTS",
    score_unlock_requirement="Verified event reports of distinguished alumni interactions",
    allowed_evidence_types=("EVID_U10_EVENT_REPORTS",),
    quarantined_types=("EVID_U10_REG_CERT",),
    aliases=("U10.IV",),
)

# U11 (4 subcriteria)
for sub_id in ("U11.1", "U11.2", "U11.3", "U11.4"):
    _register_contract(
        framework="UNIVERSITY_2026",
        parameter_id="U11",
        subcriterion_id=sub_id,
        source_documentary_requirement="ICC annual report, training attendance, mentorship logs, facility photos",
        canonical_evidence_type="EVID_U11_BOARDS",
        score_unlock_requirement="Verified gender parity initiatives documentation",
        allowed_evidence_types=("EVID_U11_BOARDS",),
    )

# U12 (5 subcriteria)
for sub_id in ("U12.1", "U12.2", "U12.3", "U12.4", "U12.5"):
    _register_contract(
        framework="UNIVERSITY_2026",
        parameter_id="U12",
        subcriterion_id=sub_id,
        source_documentary_requirement="Counsellor appointment, health camp reports, event photos, sports inventory",
        canonical_evidence_type="EVID_U12_CENTRE_NOTIF",
        score_unlock_requirement="Verified physical fitness and student health center documentation",
        allowed_evidence_types=("EVID_U12_CENTRE_NOTIF",),
    )

# U13 (1 subcriterion)
_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U13",
    subcriterion_id="U13.1",
    source_documentary_requirement="Policy notification, credit transfer notifications, SWAYAM certificates",
    canonical_evidence_type="EVID_U13_POLICY",
    score_unlock_requirement="Verified online courses and MOOCs policy and adoption proof",
    allowed_evidence_types=("EVID_U13_POLICY",),
)

# U14 (3 subcriteria in definitions: U14.A, U14.B, U14.C)
for sub_id, alias in [("U14.A", "U14.1"), ("U14.B", "U14.2"), ("U14.C", "U14.3")]:
    _register_contract(
        framework="UNIVERSITY_2026",
        parameter_id="U14",
        subcriterion_id=sub_id,
        source_documentary_requirement="Ordinances, course syllabi, curriculum structure showing credit-bearing courses",
        canonical_evidence_type="EVID_U14_CURRICULUM",
        score_unlock_requirement="Verified multidisciplinary curriculum and ordinances",
        allowed_evidence_types=("EVID_U14_CURRICULUM",),
        aliases=(alias,),
    )

# U15 (2 subcriteria)
for sub_id in ("U15.1", "U15.2"):
    _register_contract(
        framework="UNIVERSITY_2026",
        parameter_id="U15",
        subcriterion_id=sub_id,
        source_documentary_requirement="Approved guidelines/ordinance, list of students awarded exit certificates",
        canonical_evidence_type="EVID_U15_ORDINANCE",
        score_unlock_requirement="Verified multiple entry-exit operationalization proof",
        allowed_evidence_types=("EVID_U15_ORDINANCE",),
    )

# U16 (3 subcriteria: Patents & Scopus)
_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U16",
    subcriterion_id="U16.I",
    source_documentary_requirement="Patent filing receipts from Indian Patent Office",
    canonical_evidence_type="EVID_U16_FILING",
    score_unlock_requirement="Verified official patent filing receipts",
    allowed_evidence_types=("EVID_U16_FILING",),
    aliases=("U16.1", "U16.A"),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U16",
    subcriterion_id="U16.II",
    source_documentary_requirement="Patent grant certificates / technology transfer agreements",
    canonical_evidence_type="EVID_U16_GRANT",
    score_unlock_requirement="Verified official patent grant certificates",
    allowed_evidence_types=("EVID_U16_GRANT",),
    aliases=("U16.2", "U16.B"),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U16",
    subcriterion_id="U16.III",
    source_documentary_requirement=None,
    canonical_evidence_type=None,
    score_unlock_requirement="UNRESOLVED_MISSING_NO_UNLOCK",
    status=ContractStatus.UNRESOLVED_MISSING,
    allowed_evidence_types=(),
    is_unresolved=True,
    notes="Authoritative PDF specifies metric (Scopus publications per faculty) but evidence table is silent on required documentation. Fails closed.",
    aliases=("U16.3", "U16.C"),
)

# U17 (2 subcriteria: NIRF submission vs NIRF rank)
_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U17",
    subcriterion_id="U17.1",
    source_documentary_requirement="Proof of submission / acknowledgement of NIRF 2026",
    canonical_evidence_type="EVID_U17_NIRF_2026_PROOF",
    score_unlock_requirement="Verified NIRF 2026 submission proof",
    allowed_evidence_types=("EVID_U17_NIRF_2026_PROOF",),
    aliases=("U17.I",),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U17",
    subcriterion_id="U17.2",
    source_documentary_requirement="Official NIRF 2025 ranking certificate / gazette / rank card",
    canonical_evidence_type="EVID_U17_NIRF_2025_RANK",
    score_unlock_requirement="Verified NIRF 2025 official ranking certificate",
    allowed_evidence_types=("EVID_U17_NIRF_2025_RANK",),
    quarantined_types=("EVID_U17_NIRF_2026_PROOF",),
    notes="NIRF 2026 submission proof does not satisfy NIRF 2025 ranking achievement.",
    aliases=("U17.II",),
)

# U18 (3 subcriteria: RPL)
_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U18",
    subcriterion_id="U18.1",
    source_documentary_requirement="Approved institutional RPL policy/guidelines",
    canonical_evidence_type="EVID_U18_POLICY",
    score_unlock_requirement="Verified approved institutional RPL policy",
    allowed_evidence_types=("EVID_U18_POLICY",),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U18",
    subcriterion_id="U18.2",
    source_documentary_requirement="Certificates issued to learners under RPL",
    canonical_evidence_type="EVID_U18_LEARNER_CERTS",
    score_unlock_requirement="Verified RPL learner certificates",
    allowed_evidence_types=("EVID_U18_LEARNER_CERTS",),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U18",
    subcriterion_id="U18.3",
    source_documentary_requirement=None,
    canonical_evidence_type=None,
    score_unlock_requirement="UNRESOLVED_MISSING_NO_UNLOCK",
    status=ContractStatus.UNRESOLVED_MISSING,
    allowed_evidence_types=(),
    is_unresolved=True,
    notes="Source specifies workshop organized under RPL, but documentary evidence section does not define required documentation. Fails closed.",
)

# U19 (2 subcriteria: U19.A, U19.B)
for sub_id, alias in [("U19.A", "U19.1"), ("U19.B", "U19.2")]:
    _register_contract(
        framework="UNIVERSITY_2026",
        parameter_id="U19",
        subcriterion_id=sub_id,
        source_documentary_requirement="Curriculum with OBE mappings, sample attainment sheets, sample question papers with Bloom levels certified by CoE",
        canonical_evidence_type="EVID_U19_OBE_FRAMEWORK",
        score_unlock_requirement="Verified Outcome-Based Education curriculum and attainment sheets",
        allowed_evidence_types=("EVID_U19_OBE_FRAMEWORK",),
        aliases=(alias,),
    )

# U20 (3 subcriteria: SDGs)
_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U20",
    subcriterion_id="U20.1",
    source_documentary_requirement="Activity reports with geo-tagged photos for community/environmental activities mapped to SDGs",
    canonical_evidence_type="EVID_U20_ACTIVITY_REPORTS",
    score_unlock_requirement="Verified SDG-aligned activity reports with geo-tagged photos",
    allowed_evidence_types=("EVID_U20_ACTIVITY_REPORTS",),
    aliases=("U20.I",),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U20",
    subcriterion_id="U20.2",
    source_documentary_requirement="Curriculum mapping document to SDGs",
    canonical_evidence_type="EVID_U20_CURRICULUM_MAP",
    score_unlock_requirement="Verified SDG curriculum mapping documentation",
    allowed_evidence_types=("EVID_U20_CURRICULUM_MAP", "EVID_U20_ACTIVITY_REPORTS"),
    aliases=("U20.II",),
)

_register_contract(
    framework="UNIVERSITY_2026",
    parameter_id="U20",
    subcriterion_id="U20.3",
    source_documentary_requirement="Published annual sustainability report",
    canonical_evidence_type="EVID_U20_SUSTAINABILITY_REPORT",
    score_unlock_requirement="Verified published annual sustainability report",
    allowed_evidence_types=("EVID_U20_SUSTAINABILITY_REPORT", "EVID_U20_ACTIVITY_REPORTS"),
    aliases=("U20.III",),
)


# -----------------------------------------------------------------------------
# COLLEGE CONTRACTS (C1–C22: 50 SUBCRITERIA)
# -----------------------------------------------------------------------------

# C1 (1 subcriterion in definitions: C1.1)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C1",
    subcriterion_id="C1.1",
    source_documentary_requirement="Copy of IDP, Governing Body approval, Progress report certified by Principal",
    canonical_evidence_type="EVID_C1_APPROVED_IDP",
    score_unlock_requirement="Verified copy of IDP and Principal-certified progress report",
    allowed_evidence_types=("EVID_C1_APPROVED_IDP",),
    aliases=("C1.I", "C1.II"),
)

# C2 (1 subcriterion)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C2",
    subcriterion_id="C2.1",
    source_documentary_requirement="Internship completion certificates / institutional data / MoUs",
    canonical_evidence_type="EVID_C2_HOI_CERT",
    score_unlock_requirement="Verified internship completion certificates and institutional data",
    allowed_evidence_types=("EVID_C2_HOI_CERT",),
)

# C3 (1 subcriterion)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C3",
    subcriterion_id="C3.1",
    source_documentary_requirement="ABC portal screenshot/report with total enrollment and registered students",
    canonical_evidence_type="EVID_C3_ABC_DASHBOARD",
    score_unlock_requirement="Verified Academic Bank of Credits portal registration report",
    allowed_evidence_types=("EVID_C3_ABC_DASHBOARD",),
)

# C4 (2 subcriteria: C4.A, C4.B)
for sub_id, alias in [("C4.A", "C4.1"), ("C4.B", "C4.2")]:
    _register_contract(
        framework="COLLEGE_2026",
        parameter_id="C4",
        subcriterion_id=sub_id,
        source_documentary_requirement="MoU/agreement with mentee institutes/schools, activity reports with geo-tagged photos",
        canonical_evidence_type="EVID_C4_INSTITUTE_CERTS",
        score_unlock_requirement="Verified mentoring MoU and activity reports with geo-tagged photos",
        allowed_evidence_types=("EVID_C4_INSTITUTE_CERTS",),
        aliases=(alias, sub_id.replace("A", "I").replace("B", "II")),
    )

# C5 (1 subcriterion: SOURCE_SILENT)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C5",
    subcriterion_id="C5.1",
    source_documentary_requirement=None,
    canonical_evidence_type=None,
    score_unlock_requirement="SOURCE_SILENT_UNRESOLVED_NO_UNLOCK",
    status=ContractStatus.SOURCE_SILENT,
    allowed_evidence_types=(),
    is_source_silent=True,
    notes="Authoritative NEP 2026 specification has no documentary evidence clause for C5. Fails closed.",
)

# C6 (1 subcriterion)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C6",
    subcriterion_id="C6.1",
    source_documentary_requirement="Course list, syllabi, student enrollment data certified by Principal",
    canonical_evidence_type="EVID_C6_COURSE_APPROVAL",
    score_unlock_requirement="Verified Principal-certified course list, syllabi, and enrollment data",
    allowed_evidence_types=("EVID_C6_COURSE_APPROVAL",),
)

# C7 (1 subcriterion in definitions: C7.1)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C7",
    subcriterion_id="C7.1",
    source_documentary_requirement="Relevant office orders",
    canonical_evidence_type="EVID_C7_OFFICE_ORDERS",
    score_unlock_requirement="Verified office orders for bridge courses",
    allowed_evidence_types=("EVID_C7_OFFICE_ORDERS",),
    aliases=("C7.I", "C7.II"),
)

# C8 (1 subcriterion)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C8",
    subcriterion_id="C8.1",
    source_documentary_requirement="Relevant office orders",
    canonical_evidence_type="EVID_C8_OFFICE_ORDERS",
    score_unlock_requirement="Verified NEP-SARTHI nomination office orders",
    allowed_evidence_types=("EVID_C8_OFFICE_ORDERS",),
)

# C9 (2 subcriteria in definitions: C9.I, C9.II: SOURCE_SILENT)
for sub_id, alias in [("C9.I", "C9.1"), ("C9.II", "C9.2")]:
    _register_contract(
        framework="COLLEGE_2026",
        parameter_id="C9",
        subcriterion_id=sub_id,
        source_documentary_requirement=None,
        canonical_evidence_type=None,
        score_unlock_requirement="SOURCE_SILENT_UNRESOLVED_NO_UNLOCK",
        status=ContractStatus.SOURCE_SILENT,
        allowed_evidence_types=(),
        is_source_silent=True,
        notes="Authoritative NEP 2026 specification has no documentary evidence clause for C9. Fails closed.",
        aliases=(alias,),
    )

# C10 (1 subcriterion in definitions: C10.1)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C10",
    subcriterion_id="C10.1",
    source_documentary_requirement="Copies of MoUs, activity reports with attendance/certificates",
    canonical_evidence_type="EVID_C10_MOU_DOCS",
    score_unlock_requirement="Verified industry MoUs and activity reports",
    allowed_evidence_types=("EVID_C10_MOU_DOCS",),
    aliases=("C10.I", "C10.II"),
)

# C11 (3 subcriteria in definitions: C11.I, C11.II.a, C11.II.b)
for sub_id, alias in [("C11.I", "C11.1"), ("C11.II.a", "C11.2"), ("C11.II.b", "C11.3")]:
    _register_contract(
        framework="COLLEGE_2026",
        parameter_id="C11",
        subcriterion_id=sub_id,
        source_documentary_requirement="Cell establishment notification, annual activity report, list of startups/ventures supported with details",
        canonical_evidence_type="EVID_C11_REGISTRATION",
        score_unlock_requirement="Verified entrepreneurship/incubation cell establishment and activity reports",
        allowed_evidence_types=("EVID_C11_REGISTRATION",),
        aliases=(alias,),
    )

# C12 (5 subcriteria in definitions: C12.1 - C12.5)
for sub_id in ("C12.1", "C12.2", "C12.3", "C12.4", "C12.5"):
    _register_contract(
        framework="COLLEGE_2026",
        parameter_id="C12",
        subcriterion_id=sub_id,
        source_documentary_requirement="Registration certificate, database summary, event reports with photos, contribution receipts/audited statements, engagement letters",
        canonical_evidence_type="EVID_C12_DATABASE",
        score_unlock_requirement="Verified alumni connect and expert engagement documentation",
        allowed_evidence_types=("EVID_C12_DATABASE",),
    )

# C13 (1 subcriterion)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C13",
    subcriterion_id="C13.1",
    source_documentary_requirement="Certificates of faculty, summary list certified by Principal",
    canonical_evidence_type="EVID_C13_FDP_CERTS",
    score_unlock_requirement="Verified faculty development certificates and Principal summary list",
    allowed_evidence_types=("EVID_C13_FDP_CERTS",),
)

# C14 (2 subcriteria: C14.A, C14.B)
for sub_id, alias in [("C14.A", "C14.1"), ("C14.B", "C14.2")]:
    _register_contract(
        framework="COLLEGE_2026",
        parameter_id="C14",
        subcriterion_id=sub_id,
        source_documentary_requirement="Timetable/course allotment showing bilingual mode, syllabus/activity reports for IKS",
        canonical_evidence_type="EVID_C14_MATERIAL_CERT",
        score_unlock_requirement="Verified timetable and course material for bilingual/IKS courses",
        allowed_evidence_types=("EVID_C14_MATERIAL_CERT",),
        aliases=(alias, sub_id.replace("A", "I").replace("B", "II")),
    )

# C15 (6 subcriteria: C15.1 - C15.6)
for sub_id in ("C15.1", "C15.2", "C15.3", "C15.4", "C15.5", "C15.6"):
    _register_contract(
        framework="COLLEGE_2026",
        parameter_id="C15",
        subcriterion_id=sub_id,
        source_documentary_requirement="Notifications, activity reports with photos, sports participation certificates, committee minutes",
        canonical_evidence_type="EVID_C15_CENTRE_ORDER",
        score_unlock_requirement="Verified student well-being notifications and activity reports",
        allowed_evidence_types=("EVID_C15_CENTRE_ORDER",),
    )

# C16 (5 subcriteria: C16.1 - C16.5)
for sub_id in ("C16.1", "C16.2", "C16.3", "C16.4", "C16.5"):
    _register_contract(
        framework="COLLEGE_2026",
        parameter_id="C16",
        subcriterion_id=sub_id,
        source_documentary_requirement="ICC annual report, workshop reports with photos, geo-tagged photos of facilities, event reports",
        canonical_evidence_type="EVID_C16_ICC_ORDERS",
        score_unlock_requirement="Verified ICC annual report, facility photos, and gender sensitization records",
        allowed_evidence_types=("EVID_C16_ICC_ORDERS",),
    )

# C17 (1 subcriterion)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C17",
    subcriterion_id="C17.1",
    source_documentary_requirement="Annual reports of NSS/NCC/YRC with attendance and geo-tagged photos",
    canonical_evidence_type="EVID_C17_STUDENT_LIST",
    score_unlock_requirement="Verified annual outreach reports with attendance and geo-tagged photos",
    allowed_evidence_types=("EVID_C17_STUDENT_LIST",),
    aliases=("C17.I", "C17.II"),
)

# C18 (4 subcriteria: C18.1 - C18.4)
for sub_id in ("C18.1", "C18.2", "C18.3", "C18.4"):
    _register_contract(
        framework="COLLEGE_2026",
        parameter_id="C18",
        subcriterion_id=sub_id,
        source_documentary_requirement="Audit reports, geo-tagged photos, bills/work orders, activity reports",
        canonical_evidence_type="EVID_C18_ACTIVITY_REPORTS",
        score_unlock_requirement="Verified green/energy audit reports and activity records",
        allowed_evidence_types=("EVID_C18_ACTIVITY_REPORTS",),
    )

# C19 (3 subcriteria: Patents & Scopus)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C19",
    subcriterion_id="C19.I",
    source_documentary_requirement="Patent application documents from Indian Patent Office or international patent offices",
    canonical_evidence_type="EVID_C19_FILING_CERTS",
    score_unlock_requirement="Verified patent application documents",
    allowed_evidence_types=("EVID_C19_FILING_CERTS",),
    aliases=("C19.1",),
)

_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C19",
    subcriterion_id="C19.II",
    source_documentary_requirement="Patent publication / grant documents from Indian Patent Office or international patent offices",
    canonical_evidence_type="EVID_C19_GRANT_CERTS",
    score_unlock_requirement="Verified patent grant/publication documents",
    allowed_evidence_types=("EVID_C19_GRANT_CERTS",),
    aliases=("C19.2",),
)

_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C19",
    subcriterion_id="C19.III",
    source_documentary_requirement=None,
    canonical_evidence_type=None,
    score_unlock_requirement="UNRESOLVED_MISSING_NO_UNLOCK",
    status=ContractStatus.UNRESOLVED_MISSING,
    allowed_evidence_types=(),
    is_unresolved=True,
    notes="Authoritative PDF specifies Scopus metric but documentary evidence table is silent on documentation. Fails closed.",
    aliases=("C19.3",),
)

# C20 (4 subcriteria: NAAC, NIRF, AISHE, IQAC - strictly quarantined)
_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C20",
    subcriterion_id="C20.1",
    source_documentary_requirement="NAAC accreditation certificate with grade",
    canonical_evidence_type="EVID_C20_NAAC_CERT",
    score_unlock_requirement="Verified NAAC accreditation certificate",
    allowed_evidence_types=("EVID_C20_NAAC_CERT",),
    aliases=("C20.a",),
)

_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C20",
    subcriterion_id="C20.2",
    source_documentary_requirement="NIRF submission / participation proof for latest cycle",
    canonical_evidence_type="EVID_C20_NIRF_PROOF",
    score_unlock_requirement="Verified NIRF participation proof",
    allowed_evidence_types=("EVID_C20_NIRF_PROOF",),
    quarantined_types=("EVID_C20_NAAC_CERT",),
    notes="NAAC certificate does not satisfy NIRF participation requirement.",
    aliases=("C20.b",),
)

_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C20",
    subcriterion_id="C20.3",
    source_documentary_requirement="AISHE data submitted for latest year (certificate / survey upload acknowledgement)",
    canonical_evidence_type="EVID_C20_AISHE_CERT",
    score_unlock_requirement="Verified AISHE survey submission certificate",
    allowed_evidence_types=("EVID_C20_AISHE_CERT",),
    quarantined_types=("EVID_C20_NAAC_CERT",),
    notes="NAAC certificate does not satisfy AISHE survey submission requirement.",
    aliases=("C20.c",),
)

_register_contract(
    framework="COLLEGE_2026",
    parameter_id="C20",
    subcriterion_id="C20.4",
    source_documentary_requirement="IQAC established, regular meetings and AQAR submitted (IQAC minutes and AQAR submission proof)",
    canonical_evidence_type="EVID_C20_IQAC_MINUTES",
    score_unlock_requirement="Verified IQAC minutes and AQAR submission proof",
    allowed_evidence_types=("EVID_C20_IQAC_MINUTES",),
    quarantined_types=("EVID_C20_NAAC_CERT",),
    notes="NAAC certificate does not satisfy IQAC minutes and AQAR submission requirement.",
    aliases=("C20.d",),
)

# C21 (2 subcriteria: C21.1, C21.2)
for sub_id, alias in [("C21.1", "C21.I"), ("C21.2", "C21.II")]:
    _register_contract(
        framework="COLLEGE_2026",
        parameter_id="C21",
        subcriterion_id=sub_id,
        source_documentary_requirement="Event reports with photos, prize/participation certificates, notifications",
        canonical_evidence_type="EVID_C21_ACTIVITY_REPORTS",
        score_unlock_requirement="Verified cultural and constitutional values activity reports",
        allowed_evidence_types=("EVID_C21_ACTIVITY_REPORTS",),
        aliases=(alias,),
    )

# C22 (2 subcriteria: C22.1, C22.2)
for sub_id, alias in [("C22.1", "C22.I"), ("C22.2", "C22.II")]:
    _register_contract(
        framework="COLLEGE_2026",
        parameter_id="C22",
        subcriterion_id=sub_id,
        source_documentary_requirement="Feedback analysis report, ATR copy, website link screenshot",
        canonical_evidence_type="EVID_C22_NODAL_ORDER",
        score_unlock_requirement="Verified student feedback analysis and Action Taken Report",
        allowed_evidence_types=("EVID_C22_NODAL_ORDER",),
        aliases=(alias,),
    )


def normalize_framework(framework: str) -> str:
    """Normalizes and validates framework identifier."""
    if not framework:
        raise EvidenceTaxonomyError("Framework identifier is required.")
    clean = framework.strip().upper()
    if clean not in (FrameworkType.UNIVERSITY_2026.value, FrameworkType.COLLEGE_2026.value):
        raise EvidenceTypeFrameworkMismatchError(f"Invalid framework identifier: '{framework}'.")
    return clean


def get_valid_evidence_types_for_framework(framework: str) -> Set[str]:
    """Returns the set of all valid evidence types for the given framework."""
    clean = normalize_framework(framework)
    if clean == FrameworkType.UNIVERSITY_2026.value:
        return UNIVERSITY_EVIDENCE_TYPES
    return COLLEGE_EVIDENCE_TYPES


def get_subcriterion_contract(
    framework: str,
    parameter_id: str,
    subcriterion_id: str
) -> Optional[SubcriterionEvidenceContract]:
    """
    Retrieves the explicit subcriterion evidence contract.
    Supports canonical codes and recognized aliases.
    """
    clean_fw = normalize_framework(framework)
    param_clean = parameter_id.strip().upper() if parameter_id else ""
    sub_clean = subcriterion_id.strip().upper() if subcriterion_id else ""

    # Direct lookup
    contract = SUBCRITERION_EVIDENCE_CONTRACTS.get((clean_fw, param_clean, sub_clean))
    if contract:
        return contract

    # Case-insensitive or stripped lookup
    for (fw_k, p_k, s_k), c in SUBCRITERION_EVIDENCE_CONTRACTS.items():
        if fw_k == clean_fw and p_k == param_clean and s_k.upper() == sub_clean:
            return c

    return None


def get_allowed_evidence_types(
    framework: str,
    parameter_id: str,
    subcriterion_id: Optional[str] = None
) -> List[str]:
    """
    Returns allowed evidence types for a given framework, parameter, and optional subcriterion.

    CRITICAL STEP 4C ENFORCEMENT BOUNDARY:
    - If subcriterion_id is provided:
        * Queries the explicit subcriterion evidence contract.
        * If parameter has multiple subcriteria and this subcriterion lacks an active contract
          (or is SOURCE_SILENT / UNRESOLVED), FAILS CLOSED and returns [] (never falls back to
          parameter-level mandatory_evidence).
        * If parameter is single-subcriterion, returns the contract's allowed types or genuine single types.
    - If subcriterion_id is NOT provided:
        * For single-subcriterion parameters: returns genuine allowed types.
        * For multi-subcriterion parameters: returns distinct active evidence types across all subcriteria,
          or [] if parameter is source-silent.
    """
    clean_fw = normalize_framework(framework)
    param_clean = parameter_id.strip().upper() if parameter_id else ""
    sub_clean = subcriterion_id.strip().upper() if subcriterion_id else ""

    # Framework isolation check on parameter prefix
    if param_clean:
        if clean_fw == FrameworkType.UNIVERSITY_2026.value:
            if param_clean.startswith("C") and not param_clean.startswith("CR"):
                raise EvidenceTypeFrameworkMismatchError(
                    f"Framework isolation violation: Parameter '{parameter_id}' belongs to College "
                    f"and cannot be queried under University framework."
                )
        elif clean_fw == FrameworkType.COLLEGE_2026.value:
            if param_clean.startswith("U"):
                raise EvidenceTypeFrameworkMismatchError(
                    f"Framework isolation violation: Parameter '{parameter_id}' belongs to University "
                    f"and cannot be queried under College framework."
                )

    if clean_fw == FrameworkType.UNIVERSITY_2026.value:
        param_map = UNIVERSITY_PARAM_MAP
    else:
        param_map = COLLEGE_PARAM_MAP

    if param_clean not in param_map:
        raise EvidenceTypeParameterMismatchError(
            f"Parameter '{parameter_id}' is not recognized in framework '{clean_fw}'."
        )

    # 1. When subcriterion_id is explicitly provided:
    if sub_clean:
        contract = get_subcriterion_contract(clean_fw, param_clean, sub_clean)
        if contract is not None:
            if contract.status == ContractStatus.ACTIVE:
                return list(contract.allowed_evidence_types)
            # Source-silent, unresolved-missing, or quarantined -> fail closed!
            return []

        # If subcriterion has NO explicit contract:
        if param_clean in MULTI_SUBCRITERION_PARAMETERS:
            # Multi-subcriterion parameter: MUST FAIL CLOSED!
            # Do NOT fall back to parameter-level mandatory evidence!
            return []

        # Single-subcriterion parameter: check if subcriterion matches
        allowed_single = SINGLE_SUBCRITERION_PARAMETERS.get(param_clean, ())
        if sub_clean in allowed_single or any(sub_clean.endswith(f".{x}") for x in ("1", "I", "A")):
            return param_map.get(param_clean, [])
        return []

    # 2. When subcriterion_id is NOT provided (parameter-level query):
    if param_clean in SINGLE_SUBCRITERION_PARAMETERS:
        single_sub = SINGLE_SUBCRITERION_PARAMETERS[param_clean][0]
        contract = get_subcriterion_contract(clean_fw, param_clean, single_sub)
        if contract and contract.status in (ContractStatus.SOURCE_SILENT, ContractStatus.UNRESOLVED_MISSING):
            return []
        return param_map.get(param_clean, [])

    # For multi-subcriterion parameters queried without subcriterion:
    if param_clean in SOURCE_SILENT_PARAMETERS:
        return []

    param_types: List[str] = []
    for (fw_k, p_k, s_k), contract in SUBCRITERION_EVIDENCE_CONTRACTS.items():
        if fw_k == clean_fw and p_k == param_clean and contract.status == ContractStatus.ACTIVE:
            for t in contract.allowed_evidence_types:
                if t not in param_types:
                    param_types.append(t)
    return param_types or param_map.get(param_clean, [])


def validate_subcriterion_evidence_contract(
    framework: str,
    parameter_id: str,
    subcriterion_id: str,
    evidence_type: str,
) -> SubcriterionEvidenceContract:
    """
    Validates an evidence type against a specific subcriterion evidence contract.

    Distinguishes:
    1. Valid canonical evidence type -> returns SubcriterionEvidenceContract
    2. Invalid evidence type -> UnknownEvidenceTypeError
    3. Source-silent subcriterion -> SourceSilentSubcriterionError
    4. Unresolved source requirement -> UnresolvedEvidenceRequirementError
    5. Quarantined legacy coarse evidence -> QuarantinedLegacyEvidenceError
    6. Subcriterion contract mismatch -> SubcriterionEvidenceContractViolationError
    7. Framework mismatch -> EvidenceTypeFrameworkMismatchError
    """
    clean_fw = normalize_framework(framework)
    param_clean = parameter_id.strip().upper() if parameter_id else ""
    sub_clean = subcriterion_id.strip().upper() if subcriterion_id else ""
    ev_clean = evidence_type.strip() if evidence_type else ""

    # 1. Framework isolation check on parameter identifier
    if clean_fw == FrameworkType.UNIVERSITY_2026.value and param_clean.startswith("C") and not param_clean.startswith("CR"):
        raise EvidenceTypeFrameworkMismatchError(
            f"Framework isolation violation: Cannot associate College parameter '{parameter_id}' to University assessment."
        )
    if clean_fw == FrameworkType.COLLEGE_2026.value and param_clean.startswith("U"):
        raise EvidenceTypeFrameworkMismatchError(
            f"Framework isolation violation: Cannot associate University parameter '{parameter_id}' to College assessment."
        )

    # 2. Lookup subcriterion contract
    contract = get_subcriterion_contract(clean_fw, param_clean, sub_clean)

    # 3. Check Contract Status: SOURCE_SILENT (no documentary evidence permitted or defined)
    if contract and contract.status == ContractStatus.SOURCE_SILENT:
        raise SourceSilentSubcriterionError(
            f"Subcriterion '{sub_clean}' in parameter '{param_clean}' is SOURCE_SILENT. "
            f"The authoritative NEP 2026 specification specifies no documentary evidence requirement. "
            f"No evidence may be submitted or associated; self-certification/declarations are prohibited."
        )

    # 4. Check Contract Status: UNRESOLVED_MISSING (no evidence permitted until authoritative resolution)
    if contract and contract.status == ContractStatus.UNRESOLVED_MISSING:
        raise UnresolvedEvidenceRequirementError(
            f"Subcriterion '{sub_clean}' in parameter '{param_clean}' has an UNRESOLVED documentary requirement. "
            f"{contract.notes}. Evidence cannot be accepted until authoritative resolution."
        )

    # 5. Basic validation of evidence type identifier
    if not ev_clean:
        raise MissingEvidenceTypeError("Evidence type is required for subcriterion contract validation.")

    if ev_clean == "EVID_GENERAL":
        raise UnknownEvidenceTypeError(
            "EVID_GENERAL is not a valid evidence type for NEP 2026 assessment evidence. "
            "Evidence must conform to the authoritative parameter taxonomy."
        )

    if ev_clean not in ALL_EVIDENCE_TYPES:
        raise UnknownEvidenceTypeError(
            f"Unknown evidence_type '{ev_clean}'. Must be a recognized NEP 2026 evidence identifier."
        )

    # 6. Framework isolation check on evidence type
    fw_types = get_valid_evidence_types_for_framework(clean_fw)
    if ev_clean not in fw_types:
        other_fw = "College" if clean_fw == FrameworkType.UNIVERSITY_2026.value else "University"
        raise EvidenceTypeFrameworkMismatchError(
            f"Framework isolation violation: Evidence type '{ev_clean}' belongs to {other_fw} framework "
            f"and cannot be used in a {clean_fw} assessment."
        )

    # 7. Check if contract is None
    if contract is None:
        if param_clean in MULTI_SUBCRITERION_PARAMETERS:
            raise SubcriterionEvidenceContractViolationError(
                f"Multi-subcriterion parameter '{param_clean}' has no defined evidence contract for "
                f"subcriterion '{sub_clean}'. Fails closed."
            )
        # Single-subcriterion fallback
        allowed_single = SINGLE_SUBCRITERION_PARAMETERS.get(param_clean, ())
        if sub_clean not in allowed_single and not any(sub_clean.endswith(f".{x}") for x in ("1", "I", "A")):
            raise SubcriterionEvidenceContractViolationError(
                f"Subcriterion '{sub_clean}' is not recognized for single-subcriterion parameter '{param_clean}'."
            )
        allowed = get_allowed_evidence_types(clean_fw, param_clean, sub_clean)
        if ev_clean not in allowed:
            raise InvalidSubcriterionEvidenceTypeError(
                f"Evidence type '{ev_clean}' is not valid for parameter '{param_clean}'. Allowed: {allowed}."
            )
        # Construct synthetic contract for single subcriterion
        return SubcriterionEvidenceContract(
            framework=clean_fw,
            parameter_id=param_clean,
            subcriterion_id=sub_clean,
            source_documentary_requirement=f"Authoritative documentary proof for {param_clean}",
            canonical_evidence_type=ev_clean,
            score_unlock_requirement=f"Verified {ev_clean}",
            status=ContractStatus.ACTIVE,
            allowed_evidence_types=tuple(allowed),
        )

    # 7. Check Quarantined Legacy Coarse Evidence
    if ev_clean in contract.quarantined_types or (ev_clean in LEGACY_COARSE_EVIDENCE_TYPES and ev_clean not in contract.allowed_evidence_types):
        raise QuarantinedLegacyEvidenceError(
            f"Evidence type '{ev_clean}' is a legacy coarse identifier and is quarantined from satisfying "
            f"subcriterion '{sub_clean}' in parameter '{param_clean}' ({contract.notes or 'independent proof required'})."
        )

    # 8. Check Allowed Evidence Types
    if ev_clean not in contract.allowed_evidence_types:
        raise InvalidSubcriterionEvidenceTypeError(
            f"Evidence type '{ev_clean}' is not permitted for subcriterion '{sub_clean}' in parameter '{param_clean}'. "
            f"Allowed types: {list(contract.allowed_evidence_types)}."
        )

    return contract


def derive_or_validate_evidence_type(
    framework: str,
    evidence_type: Optional[str] = None,
    parameter_id: Optional[str] = None,
    subcriterion_id: Optional[str] = None,
) -> str:
    """
    Validates or deterministically derives evidence_type against the authoritative taxonomy and contracts.

    Rules:
    1. If evidence_type is provided:
       - Must not be EVID_GENERAL.
       - Must exist in ALL_EVIDENCE_TYPES.
       - Must belong to the specified framework (no cross-framework evidence).
       - If subcriterion_id is provided, validates against the subcriterion evidence contract.
       - If only parameter_id is provided, must be in the parameter's allowed types.
       - Returns the validated evidence_type.
    2. If evidence_type is NOT provided (None or blank):
       - parameter_id must be provided.
       - If subcriterion_id is provided, attempts derivation from subcriterion contract:
         * If contract has exactly ONE allowed type, deterministically derives it.
         * If contract is SOURCE_SILENT or UNRESOLVED_MISSING, raises appropriate contract exception.
         * If contract has multiple types, raises AmbiguousEvidenceTypeError.
       - If subcriterion_id is NOT provided:
         * If parameter has exactly ONE allowed type (e.g. single-subcriterion), derives it.
         * If parameter has MULTIPLE allowed types (e.g. U4, U7), raises AmbiguousEvidenceTypeError.
         * If parameter has NO defined evidence types, raises EvidenceTypeParameterMismatchError.
    """
    clean_fw = normalize_framework(framework)
    param_clean = parameter_id.strip().upper() if parameter_id else None
    sub_clean = subcriterion_id.strip().upper() if subcriterion_id else None
    ev_clean = evidence_type.strip() if (evidence_type and evidence_type.strip()) else None

    # Check framework isolation for parameter_id if provided
    if param_clean:
        if clean_fw == FrameworkType.UNIVERSITY_2026.value:
            if param_clean.startswith("C") and not param_clean.startswith("CR"):
                raise EvidenceTypeFrameworkMismatchError(
                    f"Framework isolation violation: Cannot associate College parameter '{parameter_id}' "
                    f"to University assessment."
                )
        elif clean_fw == FrameworkType.COLLEGE_2026.value:
            if param_clean.startswith("U"):
                raise EvidenceTypeFrameworkMismatchError(
                    f"Framework isolation violation: Cannot associate University parameter '{parameter_id}' "
                    f"to College assessment."
                )

    # Case 1: evidence_type is explicitly provided
    if ev_clean:
        if ev_clean == "EVID_GENERAL":
            raise UnknownEvidenceTypeError(
                "EVID_GENERAL is not a valid evidence type for NEP 2026 assessment evidence. "
                "Evidence must conform to the authoritative parameter taxonomy."
            )

        if ev_clean not in ALL_EVIDENCE_TYPES:
            raise UnknownEvidenceTypeError(
                f"Unknown evidence_type '{ev_clean}'. Must be a recognized NEP 2026 evidence identifier."
            )

        fw_types = get_valid_evidence_types_for_framework(clean_fw)
        if ev_clean not in fw_types:
            other_fw = "College" if clean_fw == FrameworkType.UNIVERSITY_2026.value else "University"
            raise EvidenceTypeFrameworkMismatchError(
                f"Evidence type '{ev_clean}' belongs to the {other_fw} framework and cannot be used in a {clean_fw} assessment."
            )

        # If subcriterion_id is provided, validate against subcriterion contract
        if param_clean and sub_clean:
            contract = validate_subcriterion_evidence_contract(clean_fw, param_clean, sub_clean, ev_clean)
            return ev_clean

        # If only parameter_id is provided
        if param_clean:
            allowed = get_allowed_evidence_types(clean_fw, param_clean, sub_clean)
            if ev_clean not in allowed:
                raise EvidenceTypeParameterMismatchError(
                    f"Evidence type '{ev_clean}' is not valid for parameter '{param_clean}'. "
                    f"Allowed types: {allowed}."
                )

        return ev_clean

    # Case 2: evidence_type is NOT provided -> attempt deterministic derivation
    if not param_clean:
        raise MissingEvidenceTypeError(
            "Either a valid evidence_type or an unambiguous parameter_id must be provided for assessment evidence."
        )

    # Check source-silent or unresolved subcriterion first
    if sub_clean:
        contract = get_subcriterion_contract(clean_fw, param_clean, sub_clean)
        if contract is not None:
            if contract.status == ContractStatus.SOURCE_SILENT:
                raise SourceSilentSubcriterionError(
                    f"Subcriterion '{sub_clean}' in parameter '{param_clean}' is SOURCE_SILENT. "
                    f"Authoritative source specifies no documentary evidence."
                )
            if contract.status == ContractStatus.UNRESOLVED_MISSING:
                raise UnresolvedEvidenceRequirementError(
                    f"Subcriterion '{sub_clean}' in parameter '{param_clean}' has an unresolved evidence requirement: {contract.notes}."
                )
            if contract.canonical_evidence_type:
                return contract.canonical_evidence_type
            if len(contract.allowed_evidence_types) == 1:
                return contract.allowed_evidence_types[0]
            if len(contract.allowed_evidence_types) > 1:
                raise AmbiguousEvidenceTypeError(
                    f"Subcriterion '{sub_clean}' accepts multiple evidence types: {sorted(contract.allowed_evidence_types)}. "
                    f"Please explicitly specify 'evidence_type'."
                )
            raise EvidenceTypeParameterMismatchError(
                f"Subcriterion '{sub_clean}' has no valid evidence types defined."
            )

    allowed = get_allowed_evidence_types(clean_fw, param_clean, sub_clean)
    if not allowed:
        if param_clean in SOURCE_SILENT_PARAMETERS:
            raise SourceSilentSubcriterionError(
                f"Parameter '{param_clean}' is SOURCE_SILENT. Authoritative source specifies no documentary evidence."
            )
        raise EvidenceTypeParameterMismatchError(
            f"Parameter '{param_clean}' has no defined evidence requirements in framework '{clean_fw}'."
        )

    if len(allowed) == 1:
        return allowed[0]

    # Multiple allowed evidence types (e.g. U4, U7 overall)
    raise AmbiguousEvidenceTypeError(
        f"Parameter '{param_clean}' accepts multiple evidence types: {sorted(allowed)}. "
        f"Please explicitly specify 'evidence_type' or target subcriterion."
    )
