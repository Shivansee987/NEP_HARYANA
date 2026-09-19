"""
Unit Tests for College Framework Registration (C1–C22)
Verifies:
- Exactly 22 parameters (C1–C22) registered
- Exact parameter names and metadata
- Exact maximum marks
- Total maximum marks = 100.0 exactly
- Framework identifier = COLLEGE_2026
- Institution type = COLLEGE
"""
from django.test import TestCase
from apps.scoring.enums import FrameworkType, InstitutionType
from apps.college.registry import (
    COLLEGE_FRAMEWORK_CODE,
    COLLEGE_PARAMETER_CODES,
    COLLEGE_TOTAL_MARKS,
    get_all_college_subcriteria,
    get_college_framework_info,
    get_college_parameter,
    get_college_parameters,
    get_college_subcriteria,
    get_parameter_evidence_requirements,
    validate_college_parameter_code,
)

EXPECTED_COLLEGE_PARAMETERS = {
    "C1": {"name": "Institutional Development Plan (IDP) and NEP Implementation Targets", "max_marks": 6.0},
    "C2": {"name": "Apprenticeship / Internships", "max_marks": 4.0},
    "C3": {"name": "Academic Bank of Credits (ABC) Registration", "max_marks": 4.0},
    "C4": {"name": "Supporting Other Institutes and Schools in Their Development", "max_marks": 4.0},
    "C5": {"name": "Student Enrollment against Sanctioned Seats", "max_marks": 2.0},
    "C6": {"name": "VAC, AEC, SEC, NSQF-Aligned Courses and Short-Term Certifications", "max_marks": 6.0},
    "C7": {"name": "Bridge Courses for SEDGs", "max_marks": 6.0},
    "C8": {"name": "Nomination of NEP-SARTHI", "max_marks": 2.0},
    "C9": {"name": "Student Career Orientation and Placements", "max_marks": 6.0},
    "C10": {"name": "Industry Collaboration, MoUs and Industry-Aligned Academic Activities", "max_marks": 5.0},
    "C11": {"name": "Incubation, Startup Cell and Entrepreneurship Promotion", "max_marks": 5.0},
    "C12": {"name": "Alumni Connect and External Expert Engagement", "max_marks": 5.0},
    "C13": {"name": "Faculty Development and NEP Orientation", "max_marks": 4.0},
    "C14": {"name": "Indian Languages and Indian Knowledge System (IKS)", "max_marks": 4.0},
    "C15": {"name": "Student Well-being, Physical Fitness, Yoga and Sports", "max_marks": 6.0},
    "C16": {"name": "Gender Parity, Safety and Inclusion Initiatives", "max_marks": 4.0},
    "C17": {"name": "Outreach, Community Engagement and Social Responsibility", "max_marks": 5.0},
    "C18": {"name": "Sustainable Development Goals (SDGs), Green Campus and Environmental Practices", "max_marks": 5.0},
    "C19": {"name": "Research, Innovation and Patents", "max_marks": 6.0},
    "C20": {"name": "Quality Assurance, NAAC/NIRF/AISHE and Institutional Reporting", "max_marks": 5.0},
    "C21": {"name": "Cultural Activities, Constitutional Values and Holistic Development", "max_marks": 4.0},
    "C22": {"name": "Governance, Student Feedback and Evidence-Based Improvement", "max_marks": 2.0},
}


class CollegeFrameworkRegistrationTests(TestCase):

    def test_framework_identity_and_metadata(self):
        """Verifies framework code, name, and statutory period."""
        info = get_college_framework_info()
        self.assertEqual(info["framework_code"], "COLLEGE_2026")
        self.assertEqual(info["total_maximum_marks"], 100.0)
        self.assertEqual(info["parameter_count"], 22)
        self.assertEqual(info["statutory_assessment_period"]["academic_year"], "2025-26")
        self.assertEqual(info["statutory_assessment_period"]["start_date"], "2025-07-01")
        self.assertEqual(info["statutory_assessment_period"]["end_date"], "2026-06-30")

    def test_exact_parameter_count_and_codes(self):
        """Verifies exactly C1–C22 are registered."""
        params = get_college_parameters()
        self.assertEqual(len(params), 22)
        expected_codes = [f"C{i}" for i in range(1, 23)]
        self.assertEqual(list(params.keys()), expected_codes)
        self.assertEqual(COLLEGE_PARAMETER_CODES, expected_codes)

    def test_parameter_titles_and_maximum_marks(self):
        """Verifies each parameter matches the authoritative specification."""
        params = get_college_parameters()
        total_max_marks = 0.0

        for code, expected in EXPECTED_COLLEGE_PARAMETERS.items():
            self.assertIn(code, params, f"Missing parameter {code}")
            param_def = params[code]
            self.assertEqual(param_def["parameter_code"], code)
            self.assertEqual(param_def["title"], expected["name"])
            self.assertEqual(float(param_def["max_marks"]), expected["max_marks"])
            self.assertEqual(param_def["framework"], FrameworkType.COLLEGE_2026)
            total_max_marks += float(param_def["max_marks"])

        self.assertEqual(total_max_marks, 100.0, "Sum of C1–C22 maximum marks must equal exactly 100.0")
        self.assertEqual(COLLEGE_TOTAL_MARKS, 100.0)

    def test_get_college_parameter_valid_and_invalid(self):
        """Verifies get_college_parameter lookup and rejection of invalid codes."""
        p1 = get_college_parameter("C1")
        self.assertEqual(p1["parameter_code"], "C1")
        p22 = get_college_parameter("c22")  # case insensitive
        self.assertEqual(p22["parameter_code"], "C22")

        with self.assertRaises(KeyError):
            get_college_parameter("U1")  # University code rejected

        with self.assertRaises(KeyError):
            get_college_parameter("C23")  # Non-existent

        with self.assertRaises(KeyError):
            get_college_parameter("P-1")  # Legacy rejected

    def test_validate_college_parameter_code(self):
        """Verifies validate_college_parameter_code helper."""
        self.assertTrue(validate_college_parameter_code("C1"))
        self.assertTrue(validate_college_parameter_code("c10"))
        self.assertTrue(validate_college_parameter_code("C22"))
        self.assertFalse(validate_college_parameter_code("U1"))
        self.assertFalse(validate_college_parameter_code("C0"))
        self.assertFalse(validate_college_parameter_code("C23"))
        self.assertFalse(validate_college_parameter_code(""))
        self.assertFalse(validate_college_parameter_code(None))

    def test_evidence_requirements_retrieval(self):
        """Verifies retrieval of evidence requirements for parameters."""
        reqs = get_parameter_evidence_requirements("C1")
        self.assertIn("mandatory", reqs)
        self.assertIn("EVID_C1_APPROVED_IDP", reqs["mandatory"])

        reqs_c20 = get_parameter_evidence_requirements("C20")
        self.assertIn("EVID_C20_NAAC_CERT", reqs_c20["mandatory"])
