import uuid
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

import hashlib
from apps.authentication.models import User, College
from apps.university.models import University, UniversityAssessment, UniversityAssessmentAuditLog
from apps.college.models import CollegeAssessment, CollegeAssessmentAuditLog
from apps.nominations.models import Nomination
from apps.evidence.models import EvidenceDocument, EvidenceSubcriterionAssociation, ReviewerAuthorization
from apps.evidence.storage import get_evidence_storage
from apps.evidence.enums import EvidenceLifecycleState
from apps.evidence.services import EvidenceService


class Command(BaseCommand):
    help = "Seeds rich demo assessments and submissions across College and University frameworks."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Seeding Demo Submissions for NEP Haryana ==="))

        with transaction.atomic():
            self._seed_universities()
            self._seed_reviewer_authorizations()
            self._seed_university_assessments()
            self._seed_college_assessments()
            self._seed_nominations()
            self._seed_evidence_records()

        self.stdout.write(self.style.SUCCESS("[SUCCESS] Successfully seeded demo submissions!"))

    def _seed_universities(self):
        self.stdout.write("* Ensuring Haryana State Universities exist...")
        unis = [
            {
                "name": "Dev Test University",
                "aishe_code": "U-DEV-001",
                "university_type": "State Public University",
                "state": "Haryana",
                "address": "State Capital Complex, Panchkula, Haryana",
                "contact_email": "nodal@dev.local",
                "contact_phone": "+91 172 2560001",
            },
            {
                "name": "Kurukshetra University, Kurukshetra",
                "aishe_code": "U-0123",
                "university_type": "State Public University",
                "state": "Haryana",
                "address": "Thanesar, Kurukshetra, Haryana 136119",
                "contact_email": "registrar@kuk.ac.in",
                "contact_phone": "+91 1744 238169",
            },
            {
                "name": "Maharshi Dayanand University, Rohtak",
                "aishe_code": "U-0124",
                "university_type": "State Public University",
                "state": "Haryana",
                "address": "Delhi Road, Rohtak, Haryana 124001",
                "contact_email": "registrar@mdurohtak.ac.in",
                "contact_phone": "+91 1262 274327",
            },
            {
                "name": "Chaudhary Charan Singh Haryana Agricultural University, Hisar",
                "aishe_code": "U-0125",
                "university_type": "State Agricultural University",
                "state": "Haryana",
                "address": "Hisar, Haryana 125004",
                "contact_email": "registrar@hau.ac.in",
                "contact_phone": "+91 1662 231640",
            },
            {
                "name": "J.C. Bose University of Science and Technology, YMCA, Faridabad",
                "aishe_code": "U-0126",
                "university_type": "State Technical University",
                "state": "Haryana",
                "address": "NH-2, Sector 6, Faridabad, Haryana 121006",
                "contact_email": "registrar@jcboseust.ac.in",
                "contact_phone": "+91 129 2310126",
            },
            {
                "name": "Deenbandhu Chhotu Ram University of Science and Technology, Murthal",
                "aishe_code": "U-0127",
                "university_type": "State Technical University",
                "state": "Haryana",
                "address": "50th K.M. Stone, N.H. 1, Murthal, Sonipat, Haryana 131039",
                "contact_email": "registrar@dcrustm.org",
                "contact_phone": "+91 130 2484005",
            },
        ]

        for u_data in unis:
            # First look for matching by name or aishe_code
            uni = University.objects.filter(name=u_data["name"]).first()
            if not uni and u_data["aishe_code"]:
                uni = University.objects.filter(aishe_code=u_data["aishe_code"]).first()

            if uni:
                uni.aishe_code = u_data["aishe_code"]
                uni.university_type = u_data["university_type"]
                uni.state = u_data["state"]
                uni.address = u_data["address"]
                uni.contact_email = u_data["contact_email"]
                uni.contact_phone = u_data["contact_phone"]
                uni.is_active = True
                uni.save()
            else:
                University.objects.create(**u_data)

    def _seed_reviewer_authorizations(self):
        self.stdout.write("* Setting up Reviewer Authorizations for committee & chair...")
        reviewer = User.objects.filter(email="committee@dev.local").first()
        chair = User.objects.filter(email="chair@dev.local").first()
        admin = User.objects.filter(email="admin@dev.local").first()

        for u in [reviewer, chair]:
            if u:
                ReviewerAuthorization.objects.update_or_create(
                    user=u,
                    framework="ALL",
                    defaults={
                        "is_active": True,
                        "granted_by": admin,
                        "institution_id": "",
                    }
                )

    def _seed_university_assessments(self):
        self.stdout.write("* Seeding University Assessments (UNIVERSITY_2026)...")
        now = timezone.now()
        reviewer = User.objects.filter(email="committee@dev.local").first()
        chair = User.objects.filter(email="chair@dev.local").first()
        admin = User.objects.filter(email="admin@dev.local").first()

        uni_configs = [
            {
                "name": "Dev Test University",
                "assessment_id": "ASSESS-2026-UNI-DEV-001",
                "status": "SUBMITTED",
                "assigned_reviewer": None,
                "submitted_at": now - timedelta(hours=4),
                "certified_score": None,
                "certification_status": "",
                "parameters": {
                    "U1": {"raw_inputs": {"U1.1": {"achieved_targets": 92, "fixed_targets": 100}}},
                    "U2": {"raw_inputs": {"U2.1": {"curriculum_revised": True, "departments": 16}}},
                    "U3": {"raw_inputs": {"U3.1": {"multidisciplinary_programs": 14}}},
                    "U4": {"raw_inputs": {"U4.1": {"abc_registered_students_pct": 98.4}}},
                }
            },
            {
                "name": "Kurukshetra University, Kurukshetra",
                "assessment_id": "ASSESS-2026-UNI-U0123-2026",
                "status": "UNDER_REVIEW",
                "assigned_reviewer": reviewer,
                "submitted_at": now - timedelta(days=3),
                "certified_score": None,
                "certification_status": "",
                "parameters": {
                    "U1": {"raw_inputs": {"U1.1": {"achieved_targets": 96, "fixed_targets": 100}}},
                    "U2": {"raw_inputs": {"U2.1": {"curriculum_revised": True, "departments": 24}}},
                    "U3": {"raw_inputs": {"U3.1": {"multidisciplinary_programs": 22}}},
                    "U4": {"raw_inputs": {"U4.1": {"abc_registered_students_pct": 99.1}}},
                    "U5": {"raw_inputs": {"U5.1": {"research_patents_filed": 18, "publications_scopus": 340}}},
                }
            },
            {
                "name": "Maharshi Dayanand University, Rohtak",
                "assessment_id": "ASSESS-2026-UNI-U0124-2026",
                "status": "SUBMITTED",
                "assigned_reviewer": None,
                "submitted_at": now - timedelta(days=1),
                "certified_score": None,
                "certification_status": "",
                "parameters": {
                    "U1": {"raw_inputs": {"U1.1": {"achieved_targets": 88, "fixed_targets": 100}}},
                    "U2": {"raw_inputs": {"U2.1": {"curriculum_revised": True, "departments": 20}}},
                    "U3": {"raw_inputs": {"U3.1": {"multidisciplinary_programs": 18}}},
                    "U4": {"raw_inputs": {"U4.1": {"abc_registered_students_pct": 95.8}}},
                }
            },
            {
                "name": "Chaudhary Charan Singh Haryana Agricultural University, Hisar",
                "assessment_id": "ASSESS-2026-UNI-U0125-2026",
                "status": "CERTIFIED",
                "assigned_reviewer": chair,
                "submitted_at": now - timedelta(days=12),
                "certified_score": 94.8,
                "certification_status": "CERTIFIED",
                "parameters": {
                    "U1": {"raw_inputs": {"U1.1": {"achieved_targets": 98, "fixed_targets": 100}}},
                    "U2": {"raw_inputs": {"U2.1": {"curriculum_revised": True, "departments": 15}}},
                    "U3": {"raw_inputs": {"U3.1": {"multidisciplinary_programs": 16}}},
                    "U4": {"raw_inputs": {"U4.1": {"abc_registered_students_pct": 99.5}}},
                    "U5": {"raw_inputs": {"U5.1": {"research_patents_filed": 26, "agri_tech_transfer": 14}}},
                }
            },
            {
                "name": "J.C. Bose University of Science and Technology, YMCA, Faridabad",
                "assessment_id": "ASSESS-2026-UNI-U0126-2026",
                "status": "SUBMITTED",
                "assigned_reviewer": None,
                "submitted_at": now - timedelta(days=2),
                "certified_score": None,
                "certification_status": "",
                "parameters": {
                    "U1": {"raw_inputs": {"U1.1": {"achieved_targets": 91, "fixed_targets": 100}}},
                    "U2": {"raw_inputs": {"U2.1": {"curriculum_revised": True, "departments": 14}}},
                    "U3": {"raw_inputs": {"U3.1": {"multidisciplinary_programs": 12}}},
                    "U4": {"raw_inputs": {"U4.1": {"abc_registered_students_pct": 97.2}}},
                }
            },
        ]

        for cfg in uni_configs:
            uni = University.objects.filter(name=cfg["name"]).first()
            if not uni:
                continue

            # Update existing or create new
            assess = UniversityAssessment.objects.filter(university=uni).first()
            if not assess:
                assess = UniversityAssessment(
                    assessment_id=cfg["assessment_id"],
                    university=uni,
                    framework="UNIVERSITY_2026",
                    academic_year="2025-26",
                    period_start=date(2025, 7, 1),
                    period_end=date(2026, 6, 30),
                )
            
            assess.status = cfg["status"]
            assess.assigned_reviewer = cfg["assigned_reviewer"]
            assess.submitted_at = cfg["submitted_at"]
            assess.certified_score = cfg["certified_score"]
            assess.certification_status = cfg["certification_status"]
            assess.parameter_data = cfg["parameters"]
            assess.save()

            # Record audit log if none exists
            if not assess.audit_logs.exists():
                try:
                    UniversityAssessmentAuditLog.objects.create(
                        assessment=assess,
                        actor=admin,
                        action="SUBMITTED",
                        previous_state="DRAFT",
                        new_state=cfg["status"],
                        reason="Official institutional submission for NEP Excellence Awards 2026."
                    )
                except Exception:
                    pass

    def _seed_college_assessments(self):
        self.stdout.write("* Seeding College Assessments (COLLEGE_2026)...")
        now = timezone.now()
        reviewer = User.objects.filter(email="committee@dev.local").first()
        chair = User.objects.filter(email="chair@dev.local").first()
        admin = User.objects.filter(email="admin@dev.local").first()

        col_configs = [
            {
                "name": "Dev Test College",
                "assessment_id": "ASSESS-2026-COL-DEV-001",
                "status": "SUBMITTED",
                "assigned_reviewer": None,
                "submitted_at": now - timedelta(hours=3),
                "certified_score": None,
                "certification_status": "",
                "parameters": {
                    "C1": {"raw_inputs": {"C1.1": {"achieved_targets": 88, "fixed_targets": 100}}},
                    "C2": {"raw_inputs": {"C2.1": {"multidisciplinary_offered": True, "students_enrolled": 340}}},
                    "C3": {"raw_inputs": {"C3.1": {"abc_id_generated_pct": 98.2}}},
                }
            },
            {
                "name": "Government College, Sector 14, Gurugram",
                "assessment_id": "ASSESS-2026-COL-C23456-2026",
                "status": "SUBMITTED",
                "assigned_reviewer": None,
                "submitted_at": now - timedelta(days=1),
                "certified_score": None,
                "certification_status": "",
                "parameters": {
                    "C1": {"raw_inputs": {"C1.1": {"achieved_targets": 94, "fixed_targets": 100}}},
                    "C2": {"raw_inputs": {"C2.1": {"multidisciplinary_offered": True, "students_enrolled": 680}}},
                    "C3": {"raw_inputs": {"C3.1": {"abc_id_generated_pct": 99.4}}},
                }
            },
            {
                "name": "Government College, Sector 9, Ambala",
                "assessment_id": "ASSESS-2026-COL-C12345-2026",
                "status": "UNDER_REVIEW",
                "assigned_reviewer": reviewer,
                "submitted_at": now - timedelta(days=4),
                "certified_score": None,
                "certification_status": "",
                "parameters": {
                    "C1": {"raw_inputs": {"C1.1": {"achieved_targets": 82, "fixed_targets": 100}}},
                    "C2": {"raw_inputs": {"C2.1": {"multidisciplinary_offered": True, "students_enrolled": 290}}},
                    "C3": {"raw_inputs": {"C3.1": {"abc_id_generated_pct": 94.0}}},
                }
            },
            {
                "name": "Government College for Girls, Sector 14, Panchkula",
                "assessment_id": "ASSESS-2026-COL-C34567-2026",
                "status": "CERTIFIED",
                "assigned_reviewer": reviewer,
                "submitted_at": now - timedelta(days=9),
                "certified_score": 91.4,
                "certification_status": "CERTIFIED",
                "parameters": {
                    "C1": {"raw_inputs": {"C1.1": {"achieved_targets": 95, "fixed_targets": 100}}},
                    "C2": {"raw_inputs": {"C2.1": {"multidisciplinary_offered": True, "students_enrolled": 520}}},
                    "C3": {"raw_inputs": {"C3.1": {"abc_id_generated_pct": 99.8}}},
                    "C4": {"raw_inputs": {"C4.1": {"internships_completed": 310}}},
                }
            },
            {
                "name": "Dyal Singh College, Karnal",
                "assessment_id": "ASSESS-2026-COL-C45678-2026",
                "status": "SUBMITTED",
                "assigned_reviewer": None,
                "submitted_at": now - timedelta(days=2),
                "certified_score": None,
                "certification_status": "",
                "parameters": {
                    "C1": {"raw_inputs": {"C1.1": {"achieved_targets": 86, "fixed_targets": 100}}},
                    "C2": {"raw_inputs": {"C2.1": {"multidisciplinary_offered": True, "students_enrolled": 410}}},
                    "C3": {"raw_inputs": {"C3.1": {"abc_id_generated_pct": 96.5}}},
                }
            },
            {
                "name": "Pandit Neki Ram Sharma Government College, Rohtak",
                "assessment_id": "ASSESS-2026-COL-C67890-2026",
                "status": "UNDER_REVIEW",
                "assigned_reviewer": chair,
                "submitted_at": now - timedelta(days=3),
                "certified_score": None,
                "certification_status": "",
                "parameters": {
                    "C1": {"raw_inputs": {"C1.1": {"achieved_targets": 89, "fixed_targets": 100}}},
                    "C2": {"raw_inputs": {"C2.1": {"multidisciplinary_offered": True, "students_enrolled": 490}}},
                    "C3": {"raw_inputs": {"C3.1": {"abc_id_generated_pct": 97.2}}},
                }
            },
            {
                "name": "Hindu College, Sonepat",
                "assessment_id": "ASSESS-2026-COL-C89012-2026",
                "status": "CERTIFIED",
                "assigned_reviewer": reviewer,
                "submitted_at": now - timedelta(days=14),
                "certified_score": 84.6,
                "certification_status": "CERTIFIED",
                "parameters": {
                    "C1": {"raw_inputs": {"C1.1": {"achieved_targets": 85, "fixed_targets": 100}}},
                    "C2": {"raw_inputs": {"C2.1": {"multidisciplinary_offered": True, "students_enrolled": 380}}},
                    "C3": {"raw_inputs": {"C3.1": {"abc_id_generated_pct": 95.0}}},
                }
            },
        ]

        for cfg in col_configs:
            college = College.objects.filter(name=cfg["name"]).first()
            if not college:
                continue

            assess = CollegeAssessment.objects.filter(college=college).first()
            if not assess:
                assess = CollegeAssessment(
                    assessment_id=cfg["assessment_id"],
                    college=college,
                    framework="COLLEGE_2026",
                    academic_year="2025-26",
                    period_start=date(2025, 7, 1),
                    period_end=date(2026, 6, 30),
                )
            
            assess.status = cfg["status"]
            assess.assigned_reviewer = cfg["assigned_reviewer"]
            assess.submitted_at = cfg["submitted_at"]
            assess.certified_score = cfg["certified_score"]
            assess.certification_status = cfg["certification_status"]
            assess.parameter_data = cfg["parameters"]
            assess.save()

            if not assess.audit_logs.exists():
                try:
                    CollegeAssessmentAuditLog.objects.create(
                        assessment=assess,
                        actor=admin,
                        action="SUBMITTED",
                        previous_state="DRAFT",
                        new_state=cfg["status"],
                        reason="Institutional self-appraisal submitted for committee screening."
                    )
                except Exception:
                    pass

    def _seed_nominations(self):
        self.stdout.write("* Seeding Institutional Nominations (College Management & Reports)...")
        now = timezone.now()

        nom_data = [
            {
                "college_name": "Dev Test College",
                "form_id": "nep-excellence-nomination-2025",
                "head_name": "Dr. Ramesh Sharma",
                "head_contact": "+91 98120 12345",
                "address": "State Education Zone, Panchkula, Haryana",
                "institution_type": "Govt",
                "score": 86,
                "award_category": "Gold",
                "is_submitted": True,
                "status": "Pending Review",
                "submitted_at": now - timedelta(hours=3),
                "remarks": "Strong multidisciplinary curriculum integration under NEP 2020.",
            },
            {
                "college_name": "Government College, Sector 14, Gurugram",
                "form_id": "nep-excellence-nomination-2025",
                "head_name": "Dr. Ashok Kumar",
                "head_contact": "+91 94160 54321",
                "address": "Sector 14, Gurugram, Haryana",
                "institution_type": "Govt",
                "score": 94,
                "award_category": "Platinum",
                "is_submitted": True,
                "status": "Pending Review",
                "submitted_at": now - timedelta(days=1),
                "remarks": "Excellent industry connect and 99.4% ABC registration achieved.",
            },
            {
                "college_name": "Government College, Sector 9, Ambala",
                "form_id": "nep-excellence-nomination-2025",
                "head_name": "Dr. Sunita Verma",
                "head_contact": "+91 94161 67890",
                "address": "Sector 9, Ambala City, Haryana",
                "institution_type": "Govt",
                "score": 78,
                "award_category": "Silver",
                "is_submitted": True,
                "status": "Under Review",
                "submitted_at": now - timedelta(days=4),
                "remarks": "Vocational skill lab expansion in progress.",
            },
            {
                "college_name": "Government College for Girls, Sector 14, Panchkula",
                "form_id": "nep-excellence-nomination-2025",
                "head_name": "Dr. Meenakshi Chaudhary",
                "head_contact": "+91 98960 11223",
                "address": "Sector 14, Panchkula, Haryana",
                "institution_type": "Govt",
                "score": 91,
                "award_category": "Platinum",
                "is_submitted": True,
                "status": "Approved",
                "submitted_at": now - timedelta(days=9),
                "remarks": "Outstanding women leadership in STEM and digital initiatives.",
            },
            {
                "college_name": "Dyal Singh College, Karnal",
                "form_id": "nep-excellence-nomination-2025",
                "head_name": "Dr. Ashima Gakhar",
                "head_contact": "+91 98961 33445",
                "address": "Kunjpura Road, Karnal, Haryana",
                "institution_type": "Aided",
                "score": 76,
                "award_category": "Silver",
                "is_submitted": True,
                "status": "Pending Review",
                "submitted_at": now - timedelta(days=2),
                "remarks": "Active NCC, NSS units and community outreach modules.",
            },
            {
                "college_name": "Pandit Neki Ram Sharma Government College, Rohtak",
                "form_id": "nep-excellence-nomination-2025",
                "head_name": "Dr. Satish Sharma",
                "head_contact": "+91 98130 55667",
                "address": "Delhi Road, Rohtak, Haryana",
                "institution_type": "Govt",
                "score": 88,
                "award_category": "Gold",
                "is_submitted": True,
                "status": "Under Review",
                "submitted_at": now - timedelta(days=3),
                "remarks": "High research output and faculty publications in peer-reviewed journals.",
            },
            {
                "college_name": "Hindu College, Sonepat",
                "form_id": "nep-excellence-nomination-2025",
                "head_name": "Dr. Rajiv Sharma",
                "head_contact": "+91 98122 77889",
                "address": "D.L.F. Colony, Sonepat, Haryana",
                "institution_type": "Aided",
                "score": 84,
                "award_category": "Gold",
                "is_submitted": True,
                "status": "Approved",
                "submitted_at": now - timedelta(days=14),
                "remarks": "Comprehensive implementation of 4-year undergraduate program.",
            },
            {
                "college_name": "Government Post Graduate College, Hisar",
                "form_id": "nep-excellence-nomination-2025",
                "head_name": "Dr. Pardeep Singh",
                "head_contact": "+91 94165 99001",
                "address": "Rajgarh Road, Hisar, Haryana",
                "institution_type": "Govt",
                "score": 45,
                "award_category": "No Award",
                "is_submitted": False,
                "status": "Draft",
                "submitted_at": None,
                "remarks": "Self-appraisal draft in progress.",
            },
            {
                "college_name": "Government College, Faridabad",
                "form_id": "nep-excellence-nomination-2025",
                "head_name": "Dr. Sunita Arora",
                "head_contact": "+91 98180 22334",
                "address": "Sector 16A, Faridabad, Haryana",
                "institution_type": "Govt",
                "score": 0,
                "award_category": "No Award",
                "is_submitted": False,
                "status": "Draft",
                "submitted_at": None,
                "remarks": "Awaiting department head approval.",
            },
        ]

        for item in nom_data:
            college = College.objects.filter(name=item["college_name"]).first()
            if not college:
                continue

            # Build mock answers with evidence links
            sample_answers = {
                f"indicator_{i}": {
                    "score": min(5, (item["score"] // 20) + (i % 3)),
                    "evidence_url": f"https://hshec.gov.in/evidence/{college.aishe_code}/indicator_{i}.pdf",
                    "comments": f"Verified documented evidence for indicator {i}."
                }
                for i in range(1, 21)
            }

            nom, _ = Nomination.objects.update_or_create(
                form_id=item["form_id"],
                college=college,
                defaults={
                    "head_name": item["head_name"],
                    "head_contact": item["head_contact"],
                    "address": item["address"],
                    "institution_type": item["institution_type"],
                    "answers": sample_answers,
                    "score": item["score"],
                    "award_category": item["award_category"],
                    "is_submitted": item["is_submitted"],
                    "status": item["status"],
                    "remarks": item["remarks"],
                    "submitted_at": item["submitted_at"],
                }
            )

    def _seed_evidence_records(self):
        self.stdout.write("* Seeding Evidence Documents and Subcriterion Associations...")
        storage = get_evidence_storage()
        admin = User.objects.filter(email="admin@dev.local").first()
        nodal = User.objects.filter(email="nodal@dev.local").first() or admin
        principal = User.objects.filter(email="principal@dev.local").first() or admin

        # Minimal valid PDF file
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>\nendobj\n"
            b"4 0 obj\n<< /Length 55 >>\nstream\n"
            b"BT /F1 12 Tf 72 712 Td (NEP 2026 Haryana Official Evidence Document) Tj ET\n"
            b"endstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
            b"0000000115 00000 n \n0000000216 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n321\n%%EOF\n"
        )
        pdf_checksum = hashlib.sha256(pdf_bytes).hexdigest()

        # Seed definitions
        targets = [
            {
                "assessment_id": "ASSESS-2026-UNI-DEV-001",
                "framework": "UNIVERSITY_2026",
                "inst_type": "UNIVERSITY",
                "inst_id": "U-DEV-001",
                "uploader": nodal,
                "associations": [
                    {
                        "filename": "curriculum_revision_u1_1.pdf",
                        "parameter_id": "U1",
                        "subcriterion_id": "U1.1",
                        "evidence_type": "EVID_U1_CURRICULUM_DOC",
                        "page_start": 1,
                        "page_end": 4,
                        "section_identifier": "Annexure A - Syllabus 2025",
                        "claim_description": "Approved curriculum restructuring and alignment under NEP 2020 guidelines.",
                    },
                    {
                        "filename": "multidisciplinary_programs_u1_2.pdf",
                        "parameter_id": "U1",
                        "subcriterion_id": "U1.2",
                        "evidence_type": "EVID_U1_PROGRAM_LIST",
                        "page_start": 2,
                        "page_end": 6,
                        "section_identifier": "Board of Studies Resolution 14/B",
                        "claim_description": "Approval of 14 multidisciplinary minor combinations for undergraduate students.",
                    },
                    {
                        "filename": "pop_appointment_orders_u2_1.pdf",
                        "parameter_id": "U2",
                        "subcriterion_id": "U2.1",
                        "evidence_type": "EVID_U2_POP_APPOINTMENT",
                        "page_start": 1,
                        "page_end": 3,
                        "section_identifier": "Executive Council Order #882",
                        "claim_description": "Appointment orders of 6 distinguished Professors of Practice from industry.",
                    },
                    {
                        "filename": "abc_digilocker_portal_u4_1.pdf",
                        "parameter_id": "U4",
                        "subcriterion_id": "U4.1",
                        "evidence_type": "EVID_U4_ABC_REGISTRATION",
                        "page_start": 1,
                        "page_end": 2,
                        "section_identifier": "DigiLocker Verification Summary",
                        "claim_description": "98.4% student ABC ID registration verified via DigiLocker NAD API.",
                    },
                ]
            },
            {
                "assessment_id": "ASSESS-2026-UNI-U0123-2026",
                "framework": "UNIVERSITY_2026",
                "inst_type": "UNIVERSITY",
                "inst_id": "U-0123",
                "uploader": admin,
                "associations": [
                    {
                        "filename": "kuk_curriculum_resolution.pdf",
                        "parameter_id": "U1",
                        "subcriterion_id": "U1.1",
                        "evidence_type": "EVID_U1_CURRICULUM_DOC",
                        "page_start": 1,
                        "page_end": 8,
                        "section_identifier": "Academic Council Minute item 4",
                        "claim_description": "Complete redesign of 24 PG departments according to NEP outcome framework.",
                    },
                    {
                        "filename": "kuk_research_patents.pdf",
                        "parameter_id": "U5",
                        "subcriterion_id": "U5.1",
                        "evidence_type": "EVID_U5_PATENTS_PUBLICATION",
                        "page_start": 1,
                        "page_end": 12,
                        "section_identifier": "IPR Cell Certificate 2025-26",
                        "claim_description": "Documentation of 18 patents filed and 340 indexed publications.",
                    }
                ]
            },
            {
                "assessment_id": "ASSESS-2026-COL-DEV-001",
                "framework": "COLLEGE_2026",
                "inst_type": "COLLEGE",
                "inst_id": "C-DEV-001",
                "uploader": principal,
                "associations": [
                    {
                        "filename": "college_multidisciplinary_c1_1.pdf",
                        "parameter_id": "C1",
                        "subcriterion_id": "C1.1",
                        "evidence_type": "EVID_C1_MULTIDISCIPLINARY",
                        "page_start": 1,
                        "page_end": 5,
                        "section_identifier": "Prospectus 2025-26 Page 12",
                        "claim_description": "Introduction of 4-year undergraduate degree with multiple entry/exit options.",
                    },
                    {
                        "filename": "internship_placement_c2_1.pdf",
                        "parameter_id": "C2",
                        "subcriterion_id": "C2.1",
                        "evidence_type": "EVID_C2_INTERNSHIP_MOU",
                        "page_start": 1,
                        "page_end": 7,
                        "section_identifier": "Industry MoUs Portfolio",
                        "claim_description": "MoUs with 12 local manufacturing enterprises for mandatory student internships.",
                    },
                    {
                        "filename": "college_abc_compliance_c3_1.pdf",
                        "parameter_id": "C3",
                        "subcriterion_id": "C3.1",
                        "evidence_type": "EVID_C3_ABC_COMPLIANCE",
                        "page_start": 1,
                        "page_end": 2,
                        "section_identifier": "University Portal Report",
                        "claim_description": "ABC IDs created for 96.5% of total enrolled first and second year students.",
                    },
                ]
            }
        ]

        for target in targets:
            for item in target["associations"]:
                storage_key = f"evidence/{target['framework']}/{target['assessment_id']}/{pdf_checksum[:2]}/{pdf_checksum}_{item['filename']}"
                storage.save(storage_key, pdf_bytes, mime_type="application/pdf")

                doc, _ = EvidenceDocument.objects.update_or_create(
                    assessment_id=target["assessment_id"],
                    original_filename=item["filename"],
                    defaults={
                        "uploader": target["uploader"],
                        "framework": target["framework"],
                        "institution_type": target["inst_type"],
                        "institution_id": target["inst_id"],
                        "file_path": storage_key,
                        "file_size": len(pdf_bytes),
                        "file_checksum": pdf_checksum,
                        "mime_type": "application/pdf",
                        "status": EvidenceLifecycleState.EVIDENCE_PENDING,
                        "document_date": timezone.now().date(),
                        "academic_year": "2025-26",
                        "is_active": True,
                    }
                )

                EvidenceSubcriterionAssociation.objects.update_or_create(
                    evidence=doc,
                    parameter_id=item["parameter_id"],
                    subcriterion_id=item["subcriterion_id"],
                    defaults={
                        "associated_by": target["uploader"],
                        "subcriterion_evidence_type": item["evidence_type"],
                        "page_start": item["page_start"],
                        "page_end": item["page_end"],
                        "section_identifier": item["section_identifier"],
                        "claim_description": item["claim_description"],
                        "academic_year": "2025-26",
                        "is_active": True,
                    }
                )
