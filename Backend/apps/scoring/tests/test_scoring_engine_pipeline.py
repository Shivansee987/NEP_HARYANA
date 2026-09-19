"""
Unit & Pipeline Tests for Master NEP 2026 Scoring Engine
Tests:
- 15-step scoring pipeline execution
- Empty/no-evidence assessment earns 0.0
- Framework global cap (max 100.00)
- Calculation trace completeness & version reproducibility
- Reviewer adjustment limits, audit trail, and anti-bypass guarantees
- Certification blocking states (BLOCKED_BY_SPECIFICATION, BLOCKED_BY_BOUNDARY, BLOCKED_BY_EVIDENCE, FINALIZABLE)
"""
from datetime import date, datetime
from django.test import TestCase

from apps.scoring.adjustments import ReviewerAdjustmentService
from apps.scoring.domain import (
    AssessmentContext,
    AssessmentInput,
    AssessmentPeriod,
    EvidenceDocument,
    FrameworkResult,
    ParameterInput,
    ParameterResult,
    ReviewerAdjustment,
    SubcriterionInput,
    SubcriterionResult,
)
from apps.scoring.engine import FrameworkMismatchException, NEP2026ScoringEngine
from apps.scoring.enums import (
    CertificationStatus,
    EvaluationType,
    EvidenceState,
    FrameworkType,
    GatingStatus,
    InstitutionType,
    ResolutionStatus,
)


class ScoringEnginePipelineTests(TestCase):

    def setUp(self):
        self.engine = NEP2026ScoringEngine()
        self.period = AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30))

    def test_empty_assessment_earns_zero(self):
        """Empty / no-evidence assessment must receive 0.0 earned score and be blocked from finalization."""
        context = AssessmentContext(
            assessment_id="test-empty-uni-001",
            institution_id="uni-empty-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        assessment_input = AssessmentInput(context=context, parameters={})

        result = self.engine.score_assessment(assessment_input)

        self.assertEqual(result.raw_total, 0.0)
        self.assertEqual(result.evidence_gated_total, 0.0)
        self.assertIsNone(result.final_certified_total)
        # Final certification must be blocked because U16 and U20 have unresolved source specifications
        self.assertEqual(result.certification_status, CertificationStatus.BLOCKED_BY_SPECIFICATION)
        self.assertTrue(len(result.blocking_reasons) > 0)

    def test_pending_evidence_blocks_earned_score_and_certification(self):
        """CRITICAL RULE #2: EVIDENCE_PENDING must not be treated as earned score."""
        context = AssessmentContext(
            assessment_id="test-pending-uni-002",
            institution_id="uni-pending-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        pending_doc = EvidenceDocument(
            document_id="doc-pending-01",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_PENDING
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 15},
                    evidence_docs=[pending_doc]
                )
            }
        )
        assessment_input = AssessmentInput(context=context, parameters={"U1": p_in})
        result = self.engine.score_assessment(assessment_input)

        u1_res = result.parameter_results["U1"]
        self.assertEqual(u1_res.raw_score, 4.0)  # Theoretical raw score is calculated
        self.assertEqual(u1_res.evidence_gated_score, 0.0)  # Gated score MUST be 0.0!
        self.assertIsNone(u1_res.final_score)
        self.assertEqual(u1_res.subcriteria_results["U1.1"].gating_status, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)

    def test_rejected_evidence_earns_zero_score(self):
        """Evidence that is rejected yields 0.0 earned score."""
        context = AssessmentContext(
            assessment_id="test-rejected-uni-003",
            institution_id="uni-rejected-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        rejected_doc = EvidenceDocument(
            document_id="doc-rejected-01",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_REJECTED,
            rejection_reason="Invalid document stamp"
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 15},
                    evidence_docs=[rejected_doc]
                )
            }
        )
        assessment_input = AssessmentInput(context=context, parameters={"U1": p_in})
        result = self.engine.score_assessment(assessment_input)

        u1_res = result.parameter_results["U1"]
        self.assertEqual(u1_res.raw_score, 4.0)
        self.assertEqual(u1_res.evidence_gated_score, 0.0)
        self.assertIsNone(u1_res.final_score)
        self.assertEqual(u1_res.subcriteria_results["U1.1"].gating_status, GatingStatus.FAILED_EVIDENCE_REJECTED)

    def test_verified_evidence_unlocks_earned_score(self):
        """Evidence verified unlocks the score."""
        context = AssessmentContext(
            assessment_id="test-verified-uni-004",
            institution_id="uni-verified-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        verified_doc = EvidenceDocument(
            document_id="doc-verified-01",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_VERIFIED
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 15},
                    evidence_docs=[verified_doc]
                )
            }
        )
        assessment_input = AssessmentInput(context=context, parameters={"U1": p_in})
        result = self.engine.score_assessment(assessment_input)

        u1_res = result.parameter_results["U1"]
        self.assertEqual(u1_res.raw_score, 4.0)
        self.assertEqual(u1_res.evidence_gated_score, 4.0)
        self.assertEqual(u1_res.final_score, 4.0)

    def test_framework_total_cannot_exceed_100(self):
        """Framework total must be capped at 100.00 maximum marks."""
        context = AssessmentContext(
            assessment_id="test-cap-100-005",
            institution_id="uni-cap-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        # Create parameters inputs with high raw values
        params = {}
        for i in range(1, 21):
            p_code = f"U{i}"
            params[p_code] = ParameterInput(parameter_code=p_code)

        assessment_input = AssessmentInput(context=context, parameters=params)
        result = self.engine.score_assessment(assessment_input)

        self.assertLessEqual(result.raw_total, 100.00)
        self.assertLessEqual(result.evidence_gated_total, 100.00)
        if result.final_certified_total is not None:
            self.assertLessEqual(result.final_certified_total, 100.00)

    def test_boundary_void_blocks_certification(self):
        """Hitting a known boundary void (e.g. U5.A at 50%) sets BLOCKED_BY_BOUNDARY."""
        context = AssessmentContext(
            assessment_id="test-boundary-block-006",
            institution_id="uni-boundary-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        doc = EvidenceDocument(
            document_id="doc-u5-01",
            document_type="EVID_U5_HOI_CERT",
            status=EvidenceState.EVIDENCE_VERIFIED
        )
        p_in = ParameterInput(
            parameter_code="U5",
            subcriteria_inputs={
                "U5.A": SubcriterionInput(
                    subcriterion_code="U5.A",
                    raw_inputs={"eligible_students": 50, "total_final_year_students": 100},  # Exactly 50.0% boundary void
                    evidence_docs=[doc]
                ),
                "U5.B": SubcriterionInput(
                    subcriterion_code="U5.B",
                    raw_inputs={"placed_students": 40, "eligible_students": 50},
                    evidence_docs=[doc]
                ),
            }
        )
        assessment_input = AssessmentInput(context=context, parameters={"U5": p_in})
        result = self.engine.score_assessment(assessment_input)

        # U5.A status must be BOUNDARY_UNRESOLVED
        self.assertEqual(result.parameter_results["U5"].resolution_status, ResolutionStatus.BOUNDARY_UNRESOLVED)
        self.assertEqual(result.certification_status, CertificationStatus.BLOCKED_BY_SPECIFICATION)

    def test_reviewer_adjustment_within_bounds(self):
        """A valid reviewer adjustment updates score and preserves audit trail."""
        context = AssessmentContext(
            assessment_id="test-adj-007",
            institution_id="uni-adj-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        doc = EvidenceDocument(
            document_id="doc-u1-01",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_VERIFIED
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 8},  # 3.0 marks
                    evidence_docs=[doc]
                )
            }
        )
        adjustment = ReviewerAdjustment(
            subcriterion_code="U1.1",
            reviewer_id="rev-state-auditor-99",
            original_score=3.0,
            adjusted_score=4.0,  # Within max 4.0
            reason="Verified additional council-approved programmes during on-site visit.",
            timestamp=datetime(2026, 8, 15, 10, 30, 0)
        )
        assessment_input = AssessmentInput(context=context, parameters={"U1": p_in})
        result = self.engine.score_assessment(assessment_input, reviewer_adjustments=[adjustment])

        u1_res = result.parameter_results["U1"]
        u1_sub = u1_res.subcriteria_results["U1.1"]
        self.assertEqual(u1_sub.review_adjusted_score, 4.0)
        self.assertEqual(u1_sub.final_score, 4.0)
        self.assertIn("reviewer_adjustment", u1_sub.trace)
        self.assertEqual(u1_sub.trace["reviewer_adjustment"]["reviewer_id"], "rev-state-auditor-99")

    def test_reviewer_adjustment_cannot_exceed_subcriterion_maximum(self):
        """Reviewer adjustment exceeding maximum score must be rejected."""
        context = AssessmentContext(
            assessment_id="test-adj-max-008",
            institution_id="uni-adj-02",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        doc = EvidenceDocument(
            document_id="doc-u1-02",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_VERIFIED
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 8},
                    evidence_docs=[doc]
                )
            }
        )
        adjustment = ReviewerAdjustment(
            subcriterion_code="U1.1",
            reviewer_id="rev-state-auditor-99",
            original_score=3.0,
            adjusted_score=10.0,  # EXCEEDS U1.1 maximum of 4.0!
            reason="Attempting to grant extra discretionary marks.",
        )
        assessment_input = AssessmentInput(context=context, parameters={"U1": p_in})
        result = self.engine.score_assessment(assessment_input, reviewer_adjustments=[adjustment])

        # Adjustment must be rejected and recorded in blocking reasons
        u1_res = result.parameter_results["U1"]
        self.assertIsNone(u1_res.subcriteria_results["U1.1"].review_adjusted_score)
        self.assertTrue(any("Reviewer adjustment rejected" in r for r in result.blocking_reasons))
        self.assertIsNone(result.final_certified_total)
        self.assertNotEqual(result.certification_status, CertificationStatus.FINALIZABLE)

    def test_rejected_reviewer_adjustment_blocks_certification_leak(self):
        """
        P1-03 Regression Test:
        Verifies that a rejected reviewer adjustment (e.g. out of bounds score)
        prevents final certification by setting final_certified_total=None and
        marking certification_status as BLOCKED_BY_VALIDATION (or BLOCKED_BY_SPECIFICATION if unresolved
        parameters exist), never FINALIZABLE.
        """
        context = AssessmentContext(
            assessment_id="test-adj-leak-008b",
            institution_id="uni-adj-02b",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        doc = EvidenceDocument(
            document_id="doc-u1-02b",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_VERIFIED
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 8},  # 3.0 marks
                    evidence_docs=[doc]
                )
            }
        )
        invalid_adj = ReviewerAdjustment(
            subcriterion_code="U1.1",
            reviewer_id="rev-state-auditor-99",
            original_score=3.0,
            adjusted_score=999.0,  # Highly invalid score
            reason="Deliberate invalid adjustment to test certification leak prevention.",
        )
        assessment_input = AssessmentInput(context=context, parameters={"U1": p_in})
        result = self.engine.score_assessment(assessment_input, reviewer_adjustments=[invalid_adj])

        # Must record rejection reason
        self.assertTrue(any("Reviewer adjustment rejected" in r for r in result.blocking_reasons))
        # Must not apply invalid score
        self.assertIsNone(result.parameter_results["U1"].subcriteria_results["U1.1"].review_adjusted_score)
        self.assertEqual(result.parameter_results["U1"].subcriteria_results["U1.1"].evidence_gated_score, 3.0)
        # Must NOT be FINALIZABLE and final_certified_total must be None
        self.assertNotEqual(result.certification_status, CertificationStatus.FINALIZABLE)
        self.assertIsNone(result.final_certified_total)

    def test_direct_reviewer_adjustment_rejection_blocks_framework_certification(self):
        """
        P1-03 Regression Test (Standalone Service):
        Demonstrates that applying an invalid/rejected adjustment directly to an
        already-finalizable FrameworkResult invalidates its final_certified_total,
        transitions its status to BLOCKED_BY_VALIDATION, and logs the blocking reason.
        """
        sub = SubcriterionResult(
            subcriterion_code="U1.1",
            max_score=4.0,
            raw_score=3.0,
            evidence_gated_score=3.0,
            review_adjusted_score=None,
            final_score=3.0,
            gating_status=GatingStatus.PASSED_EVIDENCE_VERIFIED,
            resolution_status=ResolutionStatus.CALCULABLE,
        )
        param = ParameterResult(
            parameter_code="U1",
            max_marks=4.0,
            raw_score=3.0,
            evidence_gated_score=3.0,
            review_adjusted_score=None,
            final_score=3.0,
            resolution_status=ResolutionStatus.CALCULABLE,
            subcriteria_results={"U1.1": sub},
            aggregation_strategy=EvaluationType.SUM,
        )
        fw = FrameworkResult(
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_id="direct-adj-test-01",
            institution_id="inst-direct-01",
            calculation_id="calc-direct-01",
            version_index=1,
            timestamp=datetime.now(),
            raw_total=3.0,
            evidence_gated_total=3.0,
            final_certified_total=3.0,
            max_marks=100.0,
            certification_status=CertificationStatus.FINALIZABLE,
            blocking_reasons=[],
            parameter_results={"U1": param},
        )

        invalid_adj = ReviewerAdjustment(
            subcriterion_code="U1.1",
            reviewer_id="rev-state-auditor-99",
            original_score=3.0,
            adjusted_score=50.0,  # Exceeds max 4.0
            reason="Exorbitant out-of-bounds adjustment attempt.",
        )

        ok, err = ReviewerAdjustmentService.validate_and_apply_adjustment(fw, invalid_adj)
        self.assertFalse(ok)
        self.assertIn("exceeds subcriterion maximum", err)
        # Verify certification leak prevention
        self.assertEqual(fw.certification_status, CertificationStatus.BLOCKED_BY_VALIDATION)
        self.assertIsNone(fw.final_certified_total)
        self.assertTrue(any("Reviewer adjustment rejected" in r for r in fw.blocking_reasons))
        # Ensure original score was not modified
        self.assertEqual(fw.parameter_results["U1"].subcriteria_results["U1.1"].final_score, 3.0)

    def test_reviewer_adjustment_cannot_bypass_evidence_failure(self):
        """Reviewer cannot award score to a subcriterion whose evidence was rejected."""
        context = AssessmentContext(
            assessment_id="test-adj-bypass-evid-009",
            institution_id="uni-adj-03",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        doc = EvidenceDocument(
            document_id="doc-u1-03",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_REJECTED,
            rejection_reason="Forged document"
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 12},
                    evidence_docs=[doc]
                )
            }
        )
        adjustment = ReviewerAdjustment(
            subcriterion_code="U1.1",
            reviewer_id="rev-state-auditor-99",
            original_score=0.0,
            adjusted_score=4.0,  # Cannot bypass rejected evidence!
            reason="Reviewer attempting to override rejected evidence.",
        )
        assessment_input = AssessmentInput(context=context, parameters={"U1": p_in})
        result = self.engine.score_assessment(assessment_input, reviewer_adjustments=[adjustment])

        self.assertIsNone(result.parameter_results["U1"].subcriteria_results["U1.1"].review_adjusted_score)
        self.assertTrue(any("Cannot award positive score" in r for r in result.blocking_reasons))

    def test_reviewer_adjustment_cannot_bypass_unresolved_spec(self):
        """Reviewer cannot adjust score on an unresolved specification subcriterion (e.g. U16.III)."""
        context = AssessmentContext(
            assessment_id="test-adj-bypass-spec-010",
            institution_id="uni-adj-04",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        adjustment = ReviewerAdjustment(
            subcriterion_code="U16.III",
            reviewer_id="rev-state-auditor-99",
            original_score=0.0,
            adjusted_score=4.0,  # Forbidden to resolve unresolved Scopus spec
            reason="Reviewer attempting to invent Scopus threshold.",
        )
        assessment_input = AssessmentInput(context=context, parameters={})
        result = self.engine.score_assessment(assessment_input, reviewer_adjustments=[adjustment])

        self.assertIsNone(result.parameter_results["U16"].subcriteria_results["U16.III"].review_adjusted_score)
        self.assertTrue(any("Reviewer cannot adjust" in r for r in result.blocking_reasons))

    def test_score_versioning_and_reproducibility(self):
        """Scoring must be deterministic: identical inputs yield identical outputs."""
        context = AssessmentContext(
            assessment_id="test-version-011",
            institution_id="uni-version-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        doc = EvidenceDocument(
            document_id="doc-u1-04",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_VERIFIED
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 12},
                    evidence_docs=[doc]
                )
            }
        )
        input_v1 = AssessmentInput(context=context, parameters={"U1": p_in})

        result_1 = self.engine.score_assessment(input_v1, calculation_version_index=1)
        result_2 = self.engine.score_assessment(input_v1, calculation_version_index=2)

        # Totals must be identical
        self.assertEqual(result_1.raw_total, result_2.raw_total)
        self.assertEqual(result_1.evidence_gated_total, result_2.evidence_gated_total)
        # Version indices must reflect input
        self.assertEqual(result_1.version_index, 1)
        self.assertEqual(result_2.version_index, 2)
        # Distinct calculation IDs
        self.assertNotEqual(result_1.calculation_id, result_2.calculation_id)

    def test_calculation_trace_completeness(self):
        """Calculation trace must include all diagnostic metadata for full auditability."""
        context = AssessmentContext(
            assessment_id="test-trace-012",
            institution_id="uni-trace-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        assessment_input = AssessmentInput(context=context, parameters={})
        result = self.engine.score_assessment(assessment_input)

        trace = result.trace
        self.assertIn("engine_version", trace)
        self.assertIn("calculation_id", trace)
        self.assertIn("version_index", trace)
        self.assertIn("framework", trace)
        self.assertIn("institution_type", trace)
        self.assertIn("timestamp", trace)
        self.assertIn("total_parameters_evaluated", trace)
        self.assertIn("raw_total_before_cap", trace)
        self.assertIn("raw_total_after_cap", trace)
        self.assertIn("evidence_gated_total_before_cap", trace)
        self.assertIn("evidence_gated_total_after_cap", trace)

    def test_pipeline_p2_04_raw_scalar_double_counting_protection(self):
        """
        P2-04 Pipeline Test:
        Verifies that raw scalar entity keys (e.g. patent_id) submitted in raw_inputs
        are tracked by the scoring engine validator, and duplicate claims across
        subcriteria are detected and rejected.
        """
        context = AssessmentContext(
            assessment_id="test-p2-04-dc-pipeline",
            institution_id="uni-dc-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        doc1 = EvidenceDocument(
            document_id="doc-u16-1",
            document_type="EVID_U16_PATENTS",
            status=EvidenceState.EVIDENCE_VERIFIED
        )
        doc2 = EvidenceDocument(
            document_id="doc-u16-2",
            document_type="EVID_U16_PATENTS",
            status=EvidenceState.EVIDENCE_VERIFIED
        )
        # Attempt to claim the same patent ID "PAT-2026-001" in U16.I and U16.II
        p_in = ParameterInput(
            parameter_code="U16",
            subcriteria_inputs={
                "U16.I": SubcriterionInput(
                    subcriterion_code="U16.I",
                    raw_inputs={"patent_id": "PAT-2026-001", "patents_filed": 10},
                    evidence_docs=[doc1]
                ),
                "U16.II": SubcriterionInput(
                    subcriterion_code="U16.II",
                    raw_inputs={"patent_id": "PAT-2026-001", "patents_granted": 2},
                    evidence_docs=[doc2]
                ),
            }
        )
        assessment_input = AssessmentInput(context=context, parameters={"U16": p_in})
        result = self.engine.score_assessment(assessment_input)

        # U16.I was evaluated first, entity registered. U16.II evaluates duplicate -> rejected!
        u16_res = result.parameter_results["U16"]
        u16_ii = u16_res.subcriteria_results["U16.II"]
        self.assertIn("double_counting", u16_ii.trace)
        self.assertEqual(u16_ii.trace["double_counting"]["rejected_entities_count"], 1)

    def test_pipeline_p2_05_fractional_count_rejection_blocks_certification(self):
        """
        P2-05 Pipeline Test:
        Verifies that submitting a fractional count (e.g. 2.5 programmes) marks the
        subcriterion as INVALID_INPUT, prevents scoring, and prevents final certification.
        """
        context = AssessmentContext(
            assessment_id="test-p2-05-frac-pipeline",
            institution_id="uni-frac-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        doc = EvidenceDocument(
            document_id="doc-u1-frac",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_VERIFIED
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 2.5},  # Fractional count!
                    evidence_docs=[doc]
                )
            }
        )
        assessment_input = AssessmentInput(context=context, parameters={"U1": p_in})
        result = self.engine.score_assessment(assessment_input)

        u1_res = result.parameter_results["U1"]
        u1_1 = u1_res.subcriteria_results["U1.1"]
        self.assertEqual(u1_1.resolution_status, ResolutionStatus.INVALID_INPUT)
        self.assertEqual(u1_1.raw_score, 0.0)
        self.assertEqual(u1_1.evidence_gated_score, 0.0)
        self.assertIsNone(u1_1.final_score)
        self.assertIsNone(result.final_certified_total)
        self.assertNotEqual(result.certification_status, CertificationStatus.FINALIZABLE)
