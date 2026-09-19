"""Category E Tests: Evidence-Gated Parameter Evaluation.

Verifies:
- NO_EVIDENCE yields score 0.0 with NO_EVIDENCE gating status.
- EVIDENCE_PENDING yields score 0.0 with PENDING gating status.
- EVIDENCE_REJECTED yields score 0.0 with REJECTED gating status.
- EVIDENCE_VERIFIED allows mathematical score calculation.
- Multi-subcriterion evidence gating isolates subcriteria appropriately.
"""

from datetime import date
from django.test import SimpleTestCase

from apps.scoring.domain import (
    AssessmentContext,
    AssessmentInput,
    AssessmentPeriod,
    EvidenceDocument,
    EvidenceState,
    ParameterInput,
    SubcriterionInput,
)
from apps.scoring.enums import FrameworkType, GatingStatus, InstitutionType
from apps.scoring.engine import NEP2026ScoringEngine


class EvidenceGatingTests(SimpleTestCase):
    """Test evidence gating behavior for University parameters."""

    def setUp(self):
        self.engine = NEP2026ScoringEngine()
        self.period = AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30))
        self.context = AssessmentContext(
            assessment_id="test-gating-uni-001",
            institution_id="uni-gating-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )

    def test_u1_no_evidence_yields_zero(self):
        """U1 with raw valid input but NO_EVIDENCE yields 0.0."""
        p_input = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 15},
                    evidence_docs=[],
                )
            },
        )
        assessment_input = AssessmentInput(context=self.context, parameters={"U1": p_input})
        result = self.engine.score_assessment(assessment_input)
        u1_res = result.parameter_results["U1"]
        self.assertEqual(u1_res.evidence_gated_score, 0.0)
        self.assertEqual(u1_res.subcriteria_results["U1.1"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

    def test_u1_pending_evidence_yields_zero(self):
        """U1 with raw valid input but EVIDENCE_PENDING yields 0.0."""
        pending_doc = EvidenceDocument(
            document_id="doc-pending-01",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_PENDING,
        )
        p_input = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 15},
                    evidence_docs=[pending_doc],
                )
            },
        )
        assessment_input = AssessmentInput(context=self.context, parameters={"U1": p_input})
        result = self.engine.score_assessment(assessment_input)
        u1_res = result.parameter_results["U1"]
        self.assertEqual(u1_res.evidence_gated_score, 0.0)
        self.assertEqual(u1_res.subcriteria_results["U1.1"].gating_status, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)

    def test_u1_rejected_evidence_yields_zero(self):
        """U1 with raw valid input but EVIDENCE_REJECTED yields 0.0."""
        rejected_doc = EvidenceDocument(
            document_id="doc-rejected-01",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_REJECTED,
        )
        p_input = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 15},
                    evidence_docs=[rejected_doc],
                )
            },
        )
        assessment_input = AssessmentInput(context=self.context, parameters={"U1": p_input})
        result = self.engine.score_assessment(assessment_input)
        u1_res = result.parameter_results["U1"]
        self.assertEqual(u1_res.evidence_gated_score, 0.0)
        self.assertEqual(u1_res.subcriteria_results["U1.1"].gating_status, GatingStatus.FAILED_EVIDENCE_REJECTED)

    def test_u1_verified_evidence_unlocks_scoring(self):
        """U1 with raw valid input and EVIDENCE_VERIFIED evaluates to max marks 4.0."""
        verified_doc = EvidenceDocument(
            document_id="doc-verified-01",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_VERIFIED,
        )
        p_input = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 15},
                    evidence_docs=[verified_doc],
                )
            },
        )
        assessment_input = AssessmentInput(context=self.context, parameters={"U1": p_input})
        result = self.engine.score_assessment(assessment_input)
        u1_res = result.parameter_results["U1"]
        self.assertEqual(u1_res.evidence_gated_score, 4.0)
        self.assertEqual(u1_res.subcriteria_results["U1.1"].gating_status, GatingStatus.PASSED_EVIDENCE_VERIFIED)

    def test_multi_subcriterion_evidence_partial_gating(self):
        """U4 with U4.A verified (>90% -> 3m) and U4.B rejected yields partial score 3.0."""
        doc_a = EvidenceDocument(
            document_id="doc-u4-a",
            document_type="EVID_U4_PROGRESS_REPORT",
            status=EvidenceState.EVIDENCE_VERIFIED,
        )
        doc_b = EvidenceDocument(
            document_id="doc-u4-b",
            document_type="EVID_U4_PROGRESS_REPORT",
            status=EvidenceState.EVIDENCE_REJECTED,
        )
        p_input = ParameterInput(
            parameter_code="U4",
            subcriteria_inputs={
                "U4.A": SubcriterionInput(
                    subcriterion_code="U4.A",
                    raw_inputs={"achieved_targets_2024_25": 95, "total_targets_2024_25": 100},
                    evidence_docs=[doc_a],
                ),
                "U4.B": SubcriterionInput(
                    subcriterion_code="U4.B",
                    raw_inputs={"achieved_targets_2025_26": 95, "total_targets_2025_26": 100},
                    evidence_docs=[doc_b],
                ),
            },
        )
        assessment_input = AssessmentInput(context=self.context, parameters={"U4": p_input})
        result = self.engine.score_assessment(assessment_input)
        u4_res = result.parameter_results["U4"]
        self.assertEqual(u4_res.evidence_gated_score, 3.0)
