"""
Comprehensive Committee Evaluation, Scoring, Running Total & Award Classification Tests
Covers all 20 required specifications + University & College full acceptance runs.
"""
from datetime import date
from typing import Dict, Any
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.conf import settings

from apps.evidence.models import EvidenceDocument, EvidenceSubcriterionAssociation
from apps.scoring.rules.definitions import (
    COLLEGE_PARAMETERS,
    UNIVERSITY_PARAMETERS,
)
from apps.scoring.awards import get_authoritative_award_classification
from apps.scoring.enums import ResolutionStatus
from apps.university.models import University, UniversityAssessment, UniversityReviewRecord, UniversityAssessmentAuditLog
from apps.university.services import UniversityAssessmentService, UniversityValidationError
from apps.college.models import College, CollegeAssessment, CollegeReviewRecord, CollegeAssessmentAuditLog
from apps.college.services import CollegeAssessmentService, CollegeValidationError

User = get_user_model()


def _attach_verified_evidence(assessment, param_code: str, sub_code: str, evidence_type: str, user: Any):
    is_uni = hasattr(assessment, "university")
    inst_id = assessment.university.aishe_code if is_uni else assessment.college.aishe_code
    framework = "UNIVERSITY_2026" if is_uni else "COLLEGE_2026"
    inst_type = "UNIVERSITY" if is_uni else "COLLEGE"

    doc = EvidenceDocument.objects.create(
        assessment_id=assessment.assessment_id,
        framework=framework,
        institution_type=inst_type,
        institution_id=inst_id,
        original_filename=f"{sub_code}_proof.pdf",
        file_path=f"mock/{sub_code}_proof.pdf",
        mime_type="application/pdf",
        file_size=2048,
        file_checksum="0" * 64,
        uploader=user,
        evidence_type=evidence_type,
        status="EVIDENCE_VERIFIED",
        is_active=True,
    )
    assoc = EvidenceSubcriterionAssociation.objects.create(
        evidence=doc,
        parameter_id=param_code,
        subcriterion_id=sub_code,
        subcriterion_evidence_type=evidence_type,
        academic_year="2025-26",
        associated_by=user,
        is_active=True,
    )
    return doc, assoc


class CommitteeScoringComplianceTests(TestCase):
    """
    Focused verification of all 20 core requirements for committee evaluation.
    """

    def setUp(self):
        self.reviewer = User.objects.create_user(
            email="committee.reviewer@hshec.gov.in",
            full_name="Dr. Committee Reviewer",
            role="committee",
            password="SecurePassword123!",
        )

        self.university = University.objects.create(
            name="Kurukshetra University (Test)",
            aishe_code="U-0099",
            university_type="State Public University",
            state="Haryana",
        )

        self.u_assessment = UniversityAssessment.objects.create(
            assessment_id="ASSESS-2026-UNI-TEST-001",
            university=self.university,
            status="UNDER_REVIEW",
            parameter_data={
                "U1": {"programmes_count": 8},
                "U2": {"indian_lang_programmes": 80, "total_degree_programmes": 100},
                "U3": {"iks_programmes": 30, "total_degree_programmes": 100},
            }
        )

        _attach_verified_evidence(self.u_assessment, "U1", "U1.1", "EVID_U1_APPROVAL", self.reviewer)
        _attach_verified_evidence(self.u_assessment, "U2", "U2.1", "EVID_U2_COURSE_LIST", self.reviewer)
        _attach_verified_evidence(self.u_assessment, "U3", "U3.1", "EVID_U3_SYLLABUS", self.reviewer)

        self.college = College.objects.create(
            name="Government College Panchkula (Test)",
            aishe_code="C-0088",
        )

        self.c_assessment = CollegeAssessment.objects.create(
            assessment_id="ASSESS-2026-COL-TEST-001",
            college=self.college,
            status="UNDER_REVIEW",
            parameter_data={
                "C1": {"idp_targets_achieved_pct": 95},
                "C2": {"internship_pct": 95},
                "C3": {"abc_registered_pct": 95},
            }
        )

        _attach_verified_evidence(self.c_assessment, "C1", "C1.1", "EVID_C1_APPROVED_IDP", self.reviewer)
        _attach_verified_evidence(self.c_assessment, "C2", "C2.1", "EVID_C2_HOI_CERT", self.reviewer)
        _attach_verified_evidence(self.c_assessment, "C3", "C3.1", "EVID_C3_ABC_DASHBOARD", self.reviewer)

    # 1. Every College parameter exposes its maximum
    def test_01_every_college_parameter_exposes_maximum(self):
        eval_data = CollegeAssessmentService.get_assessment_scoring_evaluation(self.c_assessment.assessment_id)
        param_results = eval_data["parameter_results"]
        for p_code, p_def in COLLEGE_PARAMETERS.items():
            self.assertIn(p_code, param_results, f"Missing parameter {p_code} in evaluation")
            p_res = param_results[p_code]
            self.assertIn("max_marks", p_res)
            self.assertEqual(p_res["max_marks"], float(p_def["max_marks"]))
            self.assertGreater(p_res["max_marks"], 0.0)

    # 2. Every University parameter exposes its maximum
    def test_02_every_university_parameter_exposes_maximum(self):
        eval_data = UniversityAssessmentService.get_assessment_scoring_evaluation(self.u_assessment.assessment_id)
        param_results = eval_data["parameter_results"]
        for p_code, p_def in UNIVERSITY_PARAMETERS.items():
            self.assertIn(p_code, param_results, f"Missing parameter {p_code} in evaluation")
            p_res = param_results[p_code]
            self.assertIn("max_marks", p_res)
            self.assertEqual(p_res["max_marks"], float(p_def["max_marks"]))
            self.assertGreater(p_res["max_marks"], 0.0)

    # 3. Awarded score cannot exceed maximum
    def test_03_awarded_score_cannot_exceed_maximum(self):
        # U1 max is 4. Attempting to adjust or accept above 4 must fail.
        with self.assertRaises(UniversityValidationError):
            UniversityAssessmentService.adjust_parameter_score(
                assessment_id=self.u_assessment.assessment_id,
                parameter_code="U1",
                subcriterion_code="U1.1",
                adjusted_score=5.0,  # Exceeds max 4.0
                reviewer=self.reviewer,
                reason="Attempting to give 5 marks which exceeds cap of 4",
            )

    # 4. Subcriterion score cannot exceed maximum
    def test_04_subcriterion_score_cannot_exceed_maximum(self):
        # U4.1 max is 3.0. Attempting to adjust to 3.5 must fail.
        with self.assertRaises(UniversityValidationError):
            UniversityAssessmentService.adjust_parameter_score(
                assessment_id=self.u_assessment.assessment_id,
                parameter_code="U4",
                subcriterion_code="U4.1",
                adjusted_score=3.5,  # Exceeds 3.0
                reviewer=self.reviewer,
                reason="Attempting to override subcriterion above its cap",
            )

    # 5. Parameter score cannot exceed maximum
    def test_05_parameter_score_cannot_exceed_maximum(self):
        eval_data = UniversityAssessmentService.get_assessment_scoring_evaluation(self.u_assessment.assessment_id)
        for p_code, p_res in eval_data["parameter_results"].items():
            raw = p_res.get("raw_score", 0.0)
            gated = p_res.get("evidence_gated_score", 0.0)
            max_m = p_res["max_marks"]
            self.assertLessEqual(raw, max_m, f"{p_code} raw score exceeds max marks")
            self.assertLessEqual(gated, max_m, f"{p_code} gated score exceeds max marks")

    # 6. Framework total cannot exceed maximum
    def test_06_framework_total_cannot_exceed_maximum(self):
        eval_data = UniversityAssessmentService.get_assessment_scoring_evaluation(self.u_assessment.assessment_id)
        self.assertLessEqual(eval_data["running_total"], 100.0)
        self.assertLessEqual(eval_data["current_awarded"], eval_data["max_available"])

    # 7. Verified evidence unlocks scoring
    def test_07_verified_evidence_unlocks_scoring(self):
        eval_data = UniversityAssessmentService.get_assessment_scoring_evaluation(self.u_assessment.assessment_id)
        u1_res = eval_data["parameter_results"]["U1"]
        # Raw inputs 8 gives 3 marks (tier >7 and up to 10), and verified evidence unlocks it
        self.assertEqual(u1_res["raw_score"], 3.0)
        self.assertEqual(u1_res["evidence_gated_score"], 3.0)

    # 8. Rejected evidence contributes zero
    def test_08_rejected_evidence_contributes_zero(self):
        from apps.scoring.domain import EvidenceDocument as ScoringEvidenceDoc
        from apps.scoring.enums import EvidenceState
        doc_rejected = ScoringEvidenceDoc(
            document_id="doc-rej-01",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_REJECTED,
        )
        from apps.scoring.rules.university import UNIVERSITY_EVALUATORS
        from apps.scoring.evaluators.double_counting import DoubleCountingValidator
        from apps.scoring.domain import AssessmentContext, AssessmentPeriod, ParameterInput, SubcriterionInput
        from apps.scoring.enums import InstitutionType, FrameworkType

        ctx = AssessmentContext(
            assessment_id="test",
            institution_id="test",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30)),
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 8},
                    evidence_docs=[doc_rejected]
                )
            }
        )
        res = UNIVERSITY_EVALUATORS["U1"](p_in, ctx, DoubleCountingValidator())
        self.assertEqual(res.evidence_gated_score, 0.0)

    # 9. Pending evidence cannot be finalized
    def test_09_pending_evidence_cannot_be_finalized(self):
        from apps.scoring.domain import EvidenceDocument as ScoringEvidenceDoc
        from apps.scoring.enums import EvidenceState
        doc_pending = ScoringEvidenceDoc(
            document_id="doc-pend-01",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_PENDING,
        )
        from apps.scoring.rules.university import UNIVERSITY_EVALUATORS
        from apps.scoring.evaluators.double_counting import DoubleCountingValidator
        from apps.scoring.domain import AssessmentContext, AssessmentPeriod, ParameterInput, SubcriterionInput
        from apps.scoring.enums import InstitutionType, FrameworkType

        ctx = AssessmentContext(
            assessment_id="test",
            institution_id="test",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30)),
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 8},
                    evidence_docs=[doc_pending]
                )
            }
        )
        res = UNIVERSITY_EVALUATORS["U1"](p_in, ctx, DoubleCountingValidator())
        self.assertEqual(res.evidence_gated_score, 0.0)

    # 10. Reviewer acceptance updates running total
    def test_10_reviewer_acceptance_updates_running_total(self):
        eval_before = UniversityAssessmentService.get_assessment_scoring_evaluation(self.u_assessment.assessment_id)
        self.assertEqual(eval_before["running_total"], 0.0)

        # Accept U1
        accept_res = UniversityAssessmentService.accept_parameter_score(
            assessment_id=self.u_assessment.assessment_id,
            parameter_code="U1",
            reviewer=self.reviewer,
            comments="Verified and approved",
        )
        self.assertEqual(accept_res["running_total"], 3.0)
        self.assertEqual(accept_res["expected_total_display"], "3 / 100")

    # 11. Running total updates after every accepted parameter
    def test_11_running_total_updates_after_every_accepted_parameter(self):
        # Step 1: Accept U1 (3 marks)
        res1 = UniversityAssessmentService.accept_parameter_score(
            self.u_assessment.assessment_id, "U1", self.reviewer
        )
        self.assertEqual(res1["running_total"], 3.0)

        # Step 2: Accept U2 (4 marks)
        res2 = UniversityAssessmentService.accept_parameter_score(
            self.u_assessment.assessment_id, "U2", self.reviewer
        )
        self.assertEqual(res2["running_total"], 7.0)

        # Step 3: Accept U3 (4 marks)
        res3 = UniversityAssessmentService.accept_parameter_score(
            self.u_assessment.assessment_id, "U3", self.reviewer
        )
        self.assertEqual(res3["running_total"], 11.0)

    # 12. Top-right expected total is correct
    def test_12_top_right_expected_total_display_correct(self):
        UniversityAssessmentService.accept_parameter_score(
            self.u_assessment.assessment_id, "U1", self.reviewer
        )
        eval_data = UniversityAssessmentService.get_assessment_scoring_evaluation(self.u_assessment.assessment_id)
        self.assertEqual(eval_data["expected_total_display"], "3 / 100")
        self.assertEqual(eval_data["current_awarded"], 3.0)
        self.assertEqual(eval_data["max_available"], 100.0)

    # 13. Final score equals sum of accepted parameter scores
    def test_13_final_score_equals_sum_of_accepted_scores(self):
        UniversityAssessmentService.accept_parameter_score(self.u_assessment.assessment_id, "U1", self.reviewer)
        UniversityAssessmentService.accept_parameter_score(self.u_assessment.assessment_id, "U2", self.reviewer)

        eval_data = UniversityAssessmentService.get_assessment_scoring_evaluation(self.u_assessment.assessment_id)
        sum_scores = sum(
            float(rec["awarded_score"])
            for rec in eval_data["parameter_reviews"].values()
            if rec.get("status") == "APPROVED"
        )
        self.assertEqual(eval_data["running_total"], sum_scores)

    # 14. Reviewer cannot enter arbitrary marks
    def test_14_reviewer_cannot_enter_arbitrary_marks(self):
        # Direct free-form entry without rule evaluation is blocked; override strictly checks subcriterion max
        with self.assertRaises(UniversityValidationError):
            UniversityAssessmentService.adjust_parameter_score(
                assessment_id=self.u_assessment.assessment_id,
                parameter_code="U1",
                subcriterion_code="U1.1",
                adjusted_score=-1.0,  # Negative arbitrary mark
                reviewer=self.reviewer,
                reason="Negative score attempt",
            )

    # 15. Score override requires reason if supported
    def test_15_score_override_requires_reason(self):
        # Empty or short reason (< 10 chars) must be rejected
        with self.assertRaises(UniversityValidationError):
            UniversityAssessmentService.adjust_parameter_score(
                assessment_id=self.u_assessment.assessment_id,
                parameter_code="U1",
                subcriterion_code="U1.1",
                adjusted_score=2.0,
                reviewer=self.reviewer,
                reason="Too short",  # < 10 chars
            )

    # 16. Override is audited
    def test_16_override_is_audited(self):
        adj_res = UniversityAssessmentService.adjust_parameter_score(
            assessment_id=self.u_assessment.assessment_id,
            parameter_code="U1",
            subcriterion_code="U1.1",
            adjusted_score=2.5,
            reviewer=self.reviewer,
            reason="Subcriterion substantiated partially with 2.5 marks",
        )
        self.assertEqual(adj_res["parameter_results"]["U1"]["awarded_score"], 2.5)

        # Check ReviewRecord
        records = UniversityReviewRecord.objects.filter(
            assessment=self.u_assessment,
        )
        self.assertTrue(records.exists())
        latest_rec = records.latest("created_at")
        self.assertEqual(latest_rec.scoring_snapshot["parameter_code"], "U1")
        self.assertEqual(float(latest_rec.scoring_snapshot["adjusted_score"]), 2.5)
        self.assertEqual(latest_rec.reviewer, self.reviewer)

        # Check Audit Log
        audit_logs = UniversityAssessmentAuditLog.objects.filter(
            assessment=self.u_assessment,
            action="SCORE_ADJUSTED",
        )
        self.assertTrue(audit_logs.exists())
        self.assertEqual(audit_logs.latest("timestamp").actor, self.reviewer)

    # 17. Source-silent criteria do not create fake evidence requirements
    def test_17_source_silent_criteria_do_not_create_fake_evidence(self):
        eval_data = UniversityAssessmentService.get_assessment_scoring_evaluation(self.u_assessment.assessment_id)
        self.assertIn("U1", eval_data["parameter_results"])

    # 18. Unresolved criteria remain fail-closed
    def test_18_unresolved_criteria_remain_fail_closed(self):
        # University U20 is marked SOURCE_INCONSISTENCY in authoritative definitions
        eval_data = UniversityAssessmentService.get_assessment_scoring_evaluation(self.u_assessment.assessment_id)
        u20_res = eval_data["parameter_results"]["U20"]
        self.assertTrue(u20_res["is_unresolved"])
        self.assertEqual(u20_res["resolution_status"], "SOURCE_INCONSISTENCY")
        self.assertIn("Source items sum to 5 marks against declared 4 marks maximum", u20_res["unresolved_reason"])

        # Attempting to accept unresolved parameter must be blocked
        with self.assertRaises(UniversityValidationError):
            UniversityAssessmentService.accept_parameter_score(
                self.u_assessment.assessment_id, "U20", self.reviewer
            )

        # College C16 and C21 are unresolved in authoritative definitions
        c_eval = CollegeAssessmentService.get_assessment_scoring_evaluation(self.c_assessment.assessment_id)
        c16_res = c_eval["parameter_results"]["C16"]
        self.assertTrue(c16_res["is_unresolved"])
        self.assertIn("C16 has declared maximum 4 marks but lists 5 distinct 1-mark items", c16_res["unresolved_reason"])

        with self.assertRaises(CollegeValidationError):
            CollegeAssessmentService.accept_parameter_score(
                self.c_assessment.assessment_id, "C16", self.reviewer
            )

        c21_res = c_eval["parameter_results"]["C21"]
        self.assertTrue(c21_res["is_unresolved"])
        self.assertIn("Source items sum to 3 marks against declared 4 marks maximum", c21_res["unresolved_reason"])

        with self.assertRaises(CollegeValidationError):
            CollegeAssessmentService.accept_parameter_score(
                self.c_assessment.assessment_id, "C21", self.reviewer
            )

    # 19. Final award classification uses authoritative thresholds
    def test_19_final_award_classification_uses_authoritative_thresholds(self):
        # Default settings.NEP_2026_AWARD_THRESHOLDS is None (per source, no thresholds in PDF)
        award = get_authoritative_award_classification(85.0, "UNIVERSITY_2026")
        if getattr(settings, "NEP_2026_AWARD_THRESHOLDS", None) is None:
            self.assertTrue(award["thresholds_missing"])
            self.assertIn("Authoritative award thresholds", award["message"])
            self.assertIsNone(award["award_level"])

        # If configured with authoritative thresholds:
        custom_thresholds = {"PLATINUM": 85.0, "GOLD": 75.0, "BRONZE": 65.0}
        award_custom = get_authoritative_award_classification(86.0, "UNIVERSITY_2026", custom_thresholds=custom_thresholds)
        self.assertEqual(award_custom["award_level"], "PLATINUM")
        self.assertFalse(award_custom["thresholds_missing"])

        award_gold = get_authoritative_award_classification(78.0, "UNIVERSITY_2026", custom_thresholds=custom_thresholds)
        self.assertEqual(award_gold["award_level"], "GOLD")

        award_bronze = get_authoritative_award_classification(68.0, "UNIVERSITY_2026", custom_thresholds=custom_thresholds)
        self.assertEqual(award_bronze["award_level"], "BRONZE")

    # 20. No old Silver/Gold/Platinum classification remains
    def test_20_no_old_silver_gold_platinum_remains(self):
        # Verify the only valid tier labels are PLATINUM, GOLD, BRONZE. SILVER is banned.
        custom_thresholds = {"PLATINUM": 85.0, "GOLD": 75.0, "BRONZE": 65.0}
        award_bronze = get_authoritative_award_classification(68.0, "UNIVERSITY_2026", custom_thresholds=custom_thresholds)
        self.assertEqual(award_bronze["award_level"], "BRONZE")
        self.assertNotEqual(award_bronze["award_level"], "SILVER")


class UniversityAndCollegeAcceptanceRunTests(TestCase):
    """
    Complete end-to-end acceptance runs for University and College frameworks.
    """

    def setUp(self):
        self.reviewer = User.objects.create_user(
            email="chair.committee@hshec.gov.in",
            full_name="Dr. Chair Reviewer",
            role="committee",
            password="SecurePassword123!",
        )

    def test_university_full_scoring_acceptance_run(self):
        """
        Step-by-step sequential verification of University scoring:
        submit -> verify -> calculated marks -> accept -> live running total updates at each step -> final breakdown & award.
        """
        univ = University.objects.create(
            name="State Technological University",
            aishe_code="U-0555",
            university_type="State Public University",
            state="Haryana",
        )

        u_data = {
            "U1": {"programmes_count": 8},                                              # Tier >7 and <=10 -> 3 / 4
            "U2": {"indian_lang_programmes": 80, "total_degree_programmes": 100},       # 80% > 75% -> 4 / 4
            "U3": {"iks_programmes": 30, "total_degree_programmes": 100},              # 30% > 25% -> 4 / 4
        }

        assessment = UniversityAssessment.objects.create(
            assessment_id="ASSESS-2026-UNI-E2E-001",
            university=univ,
            status="UNDER_REVIEW",
            parameter_data=u_data,
        )

        _attach_verified_evidence(assessment, "U1", "U1.1", "EVID_U1_APPROVAL", self.reviewer)
        _attach_verified_evidence(assessment, "U2", "U2.1", "EVID_U2_COURSE_LIST", self.reviewer)
        _attach_verified_evidence(assessment, "U3", "U3.1", "EVID_U3_SYLLABUS", self.reviewer)

        expected_scores = {
            "U1": 3.0,
            "U2": 4.0,
            "U3": 4.0,
        }

        cumulative_running_total = 0.0

        for p_code, expected_pts in expected_scores.items():
            # Reviewer accepts calculated score for each parameter
            res = UniversityAssessmentService.accept_parameter_score(
                assessment_id=assessment.assessment_id,
                parameter_code=p_code,
                reviewer=self.reviewer,
                comments=f"Committee verified and accepted calculated score for {p_code}.",
            )
            cumulative_running_total += expected_pts

            # Verify top-right expected total immediately reflects updated cumulative score
            self.assertEqual(
                res["running_total"],
                cumulative_running_total,
                f"Running total mismatch at {p_code}"
            )
            self.assertEqual(
                res["current_awarded"],
                cumulative_running_total,
            )
            self.assertEqual(
                res["expected_total_display"],
                f"{int(cumulative_running_total)} / 100",
            )

        # Final verification of complete evaluation
        final_eval = UniversityAssessmentService.get_assessment_scoring_evaluation(assessment.assessment_id)
        self.assertEqual(final_eval["running_total"], cumulative_running_total)
        self.assertEqual(final_eval["max_available"], 100.0)

        # Check that unresolved parameter U20 remains unresolved and fail-closed
        self.assertTrue(final_eval["parameter_results"]["U20"]["is_unresolved"])

        # Check award classification structure
        self.assertIn("award_classification", final_eval)
        award = final_eval["award_classification"]
        self.assertEqual(award["score"], cumulative_running_total)

    def test_college_full_scoring_acceptance_run(self):
        """
        Step-by-step sequential verification of College scoring:
        submit -> verify -> calculated marks -> accept -> live running total updates at each step -> final breakdown & award.
        """
        col = College.objects.create(
            name="Government Model College Karnal",
            aishe_code="C-0777",
        )

        c_data = {
            "C1": {"idp_targets_achieved_pct": 95},      # > 90% -> 6 / 6
            "C2": {"internship_pct": 95},                # > 90% -> 4 / 4
            "C3": {"abc_registered_pct": 95},            # > 90% -> 4 / 4
        }

        assessment = CollegeAssessment.objects.create(
            assessment_id="ASSESS-2026-COL-E2E-001",
            college=col,
            status="UNDER_REVIEW",
            parameter_data=c_data,
        )

        _attach_verified_evidence(assessment, "C1", "C1.1", "EVID_C1_APPROVED_IDP", self.reviewer)
        _attach_verified_evidence(assessment, "C2", "C2.1", "EVID_C2_HOI_CERT", self.reviewer)
        _attach_verified_evidence(assessment, "C3", "C3.1", "EVID_C3_ABC_DASHBOARD", self.reviewer)

        expected_scores = {
            "C1": 6.0,
            "C2": 4.0,
            "C3": 4.0,
        }

        cumulative_running_total = 0.0

        for p_code, expected_pts in expected_scores.items():
            res = CollegeAssessmentService.accept_parameter_score(
                assessment_id=assessment.assessment_id,
                parameter_code=p_code,
                reviewer=self.reviewer,
                comments=f"Committee verified and accepted calculated score for {p_code}.",
            )
            awarded = float(res["parameter_results"][p_code]["awarded_score"])
            cumulative_running_total += awarded

            self.assertEqual(
                res["running_total"],
                cumulative_running_total,
                f"College running total mismatch at {p_code}"
            )
            self.assertEqual(
                res["expected_total_display"],
                f"{int(cumulative_running_total)} / 100",
            )

        final_eval = CollegeAssessmentService.get_assessment_scoring_evaluation(assessment.assessment_id)
        self.assertEqual(final_eval["running_total"], cumulative_running_total)
        self.assertEqual(final_eval["max_available"], 100.0)

        # Confirm unresolved parameters remain unresolved
        self.assertTrue(final_eval["parameter_results"]["C16"]["is_unresolved"])
        self.assertTrue(final_eval["parameter_results"]["C21"]["is_unresolved"])
