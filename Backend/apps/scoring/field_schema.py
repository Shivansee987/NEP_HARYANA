"""
NEP Excellence Awards 2026 - Canonical Parameter Input Schema (C1–C22, U1–U20)

This is the ONE canonical contract for institution-submitted data:
  - backend serializer validation (apps.*.api.serializers)
  - engine input normalisation (apps.scoring.inputs)
  - the generated frontend module (Frontend/.../src/utils/nepFrameworkSchema.generated.js,
    produced by `manage.py export_nep_schema`)

Subcriterion titles and evidence text are transcribed from the source PDFs:
  University Parameters - NEP Excellence Awards 2026.pdf
  College Parameters - NEP Excellence Awards 2026.pdf

Field types:
  integer   non-negative whole number
  currency  non-negative amount in INR
  boolean   criterion met (checkbox)
  enum      one value from `options`
  multi_enum  list of distinct values from `options`
  text_list list of distinct non-empty strings
  date      ISO date (YYYY-MM-DD)

`period_bound` subcriteria are the ones whose source text explicitly bounds the activity/output to the
assessment period (e.g. "between July 2025 and June 2026", "during the evaluation period"). For those,
any positive claim must carry activity_period_start / activity_period_end inside 2025-07-01..2026-06-30.
"""
from copy import deepcopy
from typing import Any, Dict, List, Optional

ASSESSMENT_PERIOD_START = "2025-07-01"
ASSESSMENT_PERIOD_END = "2026-06-30"

PERIOD_START_KEY = "activity_period_start"
PERIOD_END_KEY = "activity_period_end"

C4_SUPPORT_AREAS = [
    {"value": "ACADEMIC_DEVELOPMENT", "label": "Academic development"},
    {"value": "COMMUNITY_ENGAGEMENT_AND_SERVICE", "label": "Community engagement and service"},
    {"value": "CONTRIBUTION_TO_FIELDS_OF_PRACTICE", "label": "Contribution to various fields of practice"},
    {"value": "FACULTY_DEVELOPMENT", "label": "Faculty development"},
]

NAAC_GRADES = [
    {"value": "A++", "label": "A++"},
    {"value": "A+", "label": "A+"},
    {"value": "A", "label": "A"},
    {"value": "B++", "label": "B++"},
    {"value": "B+", "label": "B+"},
    {"value": "B", "label": "B"},
    {"value": "C", "label": "C"},
    {"value": "NOT_ACCREDITED", "label": "Not accredited"},
]


def _int(key, label, placeholder="", max_field=None):
    f = {"key": key, "label": label, "type": "integer", "min": 0, "integer": True, "placeholder": placeholder}
    if max_field:
        f["max_field"] = max_field
    return f


def _bool(label, key="verified"):
    return {"key": key, "label": label, "type": "boolean"}


def _currency(key, label, placeholder=""):
    return {"key": key, "label": label, "type": "currency", "min": 0, "placeholder": placeholder}


def _sub(code, title, max_score, fields, period_bound=False, note=""):
    return {"code": code, "title": title, "max_score": float(max_score), "fields": fields,
            "period_bound": period_bound, "note": note}


# ---------------------------------------------------------------------------
# COLLEGE (C1–C22)
# ---------------------------------------------------------------------------
_COLLEGE: Dict[str, Dict[str, Any]] = {
    "C1": {
        "evidence_text": "Approved IDP, target-achievement report, minutes/records of review meetings.",
        "subcriteria": [
            _sub("C1.1", "Percentage achievement of IDP/NEP implementation targets fixed for 2024-25", 6, [
                _int("fixed_targets_2024_25", "Number of IDP/NEP implementation targets fixed for 2024-25", "e.g. 40"),
                _int("achieved_targets_2024_25", "Number of those targets achieved", "e.g. 37", max_field="fixed_targets_2024_25"),
            ]),
        ],
    },
    "C2": {
        "evidence_text": "Certificate from Head of Institution, sample of completion certificate/industry certificate.",
        "subcriteria": [
            _sub("C2.1", "Percentage of students who completed Apprenticeship / Internships including with local industry, "
                         "businesses, artists, crafts persons, etc., as well as research internships with faculty and researchers "
                         "at their own or other HEIs/research institutions, during the assessment period", 4, [
                _int("eligible_students", "Total number of students (base for the percentage)", "e.g. 600"),
                _int("students_completed", "Number of students who completed apprenticeship / internship", "e.g. 540",
                     max_field="eligible_students"),
            ]),
        ],
    },
    "C3": {
        "evidence_text": "ABC registration report/downloaded dashboard.",
        "subcriteria": [
            _sub("C3.1", "Percentage of enrolled students registered on Academic Bank of Credits", 4, [
                _int("total_enrolled_students", "Total number of enrolled students", "e.g. 1200"),
                _int("abc_registered_students", "Number of enrolled students registered on ABC", "e.g. 1100",
                     max_field="total_enrolled_students"),
            ]),
        ],
    },
    "C4": {
        "evidence_text": "Certificate from the support receiving Head of Institution/ Schools.",
        "subcriteria": [
            _sub("C4.A", "Supporting other Institutes in their academic development, community engagement and service, "
                         "contribution to various fields of practice, faculty development, etc. — 0.5 mark per area (max 2 marks)", 2, [
                {"key": "support_areas", "label": "Areas in which other institutes were supported", "type": "multi_enum",
                 "options": C4_SUPPORT_AREAS},
                {"key": "other_support_areas", "label": "Other areas of support to institutes (one per line)", "type": "text_list"},
            ]),
            _sub("C4.B", "Supporting Schools — 0.5 mark per area, only if a minimum of 5 schools are covered (max 2 marks)", 2, [
                _int("schools_covered", "Number of schools covered", "e.g. 6"),
                {"key": "school_support_areas", "label": "Areas in which schools were supported", "type": "multi_enum",
                 "options": C4_SUPPORT_AREAS},
                {"key": "other_school_support_areas", "label": "Other areas of support to schools (one per line)", "type": "text_list"},
            ]),
        ],
    },
    "C5": {
        "evidence_text": "",
        "subcriteria": [
            _sub("C5.1", "% of Sanctioned Seats filled in UG & PG", 2, [
                _int("sanctioned_intake", "Total sanctioned seats in UG & PG", "e.g. 800"),
                _int("admitted_students", "Seats filled in UG & PG", "e.g. 760"),
            ]),
        ],
    },
    "C6": {
        "evidence_text": "Course approval, student enrolment, certificates, partner/awarding body details.",
        "subcriteria": [
            _sub("C6.1", "Percentage of students certified in NSQF level 4.5 and above/add-on VAC, AEC, SEC, NSQF-Aligned "
                         "Courses and Short-Term Certifications in offline or online mode", 6, [
                _int("total_enrolled_students", "Total number of students", "e.g. 1200"),
                _int("certified_students", "Number of students certified", "e.g. 1000", max_field="total_enrolled_students"),
            ]),
        ],
    },
    "C7": {
        "evidence_text": "Relevant office orders.",
        "subcriteria": [
            _sub("C7.1", "Bridge Courses offered for students from SEDGs (100% → 3; 75% and above → 2; 50% and above → 1; below 50% → 0)", 3, [
                _int("total_sedg_students", "Total number of SEDG students", "e.g. 120"),
                _int("sedg_bridge_students", "SEDG students for whom bridge courses were offered", "e.g. 120",
                     max_field="total_sedg_students"),
            ]),
        ],
    },
    "C8": {
        "evidence_text": "Relevant office orders.",
        "subcriteria": [
            _sub("C8.1", "Nomination of NEP-SARTHI as per UGC Guidelines", 2, [
                _bool("NEP-SARTHI nominated as per UGC Guidelines"),
            ]),
        ],
    },
    "C9": {
        "evidence_text": "",
        "subcriteria": [
            _sub("C9.I", "Percentage of Eligible Students participated in placement fairs", 3, [
                _int("eligible_students", "Number of eligible students", "e.g. 300"),
                _int("participating_students", "Number of eligible students who participated in placement fairs", "e.g. 240",
                     max_field="eligible_students"),
            ]),
            _sub("C9.II", "Percentage of participating students placed", 3, [
                _int("placed_students", "Number of participating students placed", "e.g. 180"),
            ]),
        ],
    },
    "C10": {
        "evidence_text": "MoUs and proof of activities such as internships, expert lectures, joint curriculum, projects, visits or placements.",
        "subcriteria": [
            _sub("C10.1", "Number of active industry collaborations/MoUs with demonstrable academic activities during July 2025 "
                          "to June 2026 (active = at least one activity under the MoU during the evaluation period)", 5, [
                _int("active_mous_count", "Number of active industry collaborations/MoUs", "e.g. 5"),
            ], period_bound=True),
        ],
    },
    "C11": {
        "evidence_text": "Cell notification, activity report, registration/incubation records, funding/commercialisation proof.",
        "subcriteria": [
            _sub("C11.I", "Startup/companies/student ventures registered or incubated between July 2025 and June 2026", 3, [
                _int("ventures_count", "Number of startups/companies/student ventures registered or incubated", "e.g. 7"),
            ], period_bound=True),
            _sub("C11.II.a", "Functional incubation/startup/entrepreneurship cell with annual activity report", 1, [
                _bool("Functional incubation/startup/entrepreneurship cell with annual activity report", key="cell_functional"),
            ]),
            _sub("C11.II.b", "50% or more registered/incubated ventures monetised/commercialised/receiving seed support", 1, [
                _int("monetized_count", "Number of those ventures monetised/commercialised/receiving seed support", "e.g. 4"),
            ]),
        ],
    },
    "C12": {
        "evidence_text": "Alumni database, event reports, invitation letters, photographs, attendance and feedback records.",
        "subcriteria": [
            _sub("C12.1", "Alumni cell with updated alumni database", 1, [_bool("Alumni cell with updated alumni database")]),
            _sub("C12.2", "Alumni annual report/reunion organised between July 2025 and June 2026", 1,
                 [_bool("Alumni annual report/reunion organised")], period_bound=True),
            _sub("C12.3", "At least five alumni invited as experts/mentors/guest speakers or felicitated", 1,
                 [_bool("At least five alumni invited as experts/mentors/guest speakers or felicitated")]),
            _sub("C12.4", "Five or more extension lectures by external experts", 1,
                 [_bool("Five or more extension lectures by external experts")]),
            _sub("C12.5", "Alumni/experts engaged for placement, internship, mentoring or curriculum inputs", 1,
                 [_bool("Alumni/experts engaged for placement, internship, mentoring or curriculum inputs")]),
        ],
    },
    "C13": {
        "evidence_text": "Certificates, HRDC/MMTTC/FDP reports, faculty list.",
        "subcriteria": [
            _sub("C13.1", "Percentage of teachers trained/certified in NEP orientation, MMTTC/ FDP/ refresher/ technology-pedagogy programmes", 4, [
                _int("total_fulltime_faculty", "Total number of teachers", "e.g. 80"),
                _int("trained_faculty", "Number of teachers trained/certified", "e.g. 70", max_field="total_fulltime_faculty"),
            ]),
        ],
    },
    "C14": {
        "evidence_text": "Learning material certified by Head of Institution, activity reports (Ayurveda Garden Projects, IKS quizzes, "
                         "traditional sports, artisanal internships with local artisans, etc.).",
        "subcriteria": [
            _sub("C14.A", "Learning material developed by the teachers of College in Indian languages, including Hindi/Sanskrit/other "
                          "Indian languages in applicable courses — 0.5 marks for each content (max 2 marks)", 2, [
                _int("content_items", "Number of learning-material contents developed in Indian languages", "e.g. 4"),
            ]),
            _sub("C14.B", "Five or more IKS-related academic/co-curricular activities", 2, [
                _int("iks_activities", "Number of IKS-related academic/co-curricular activities", "e.g. 5"),
            ]),
        ],
    },
    "C15": {
        "evidence_text": "Centre notification, calendar, activity reports, participation certificates, photographs and attendance records.",
        "subcriteria": [
            _sub("C15.1", "Mental Health and Well-being Centre/Student Service Centre established", 1,
                 [_bool("Mental Health and Well-being Centre/Student Service Centre established")]),
            _sub("C15.2", "Minimum two workshops on mental health and well-being for students", 1,
                 [_bool("Minimum two workshops on mental health and well-being for students")]),
            _sub("C15.3", "Workshop on mental health/well-being for teaching and non-teaching staff", 1,
                 [_bool("Workshop on mental health/well-being for teaching and non-teaching staff")]),
            _sub("C15.4", "Annual activity calendar prepared as per UGC guidelines for physical fitness, sports, student health and well-being", 1,
                 [_bool("Annual activity calendar prepared as per UGC guidelines")]),
            _sub("C15.5", "Five or more sports/yoga/fitness activities conducted for students", 1,
                 [_bool("Five or more sports/yoga/fitness activities conducted for students")]),
            _sub("C15.6", "Student participation in inter-college/university/state/national sports/yoga events", 1,
                 [_bool("Student participation in inter-college/university/state/national sports/yoga events")]),
        ],
    },
    "C16": {
        "evidence_text": "Orders/notifications, photographs, SAKSHAM proof, workshop report and attendance.",
        "subcriteria": [
            _sub("C16.1", "Internal Complaints Committee and Women Cell constituted and displayed at prominent places", 1,
                 [_bool("Internal Complaints Committee and Women Cell constituted and displayed at prominent places")]),
            _sub("C16.2", "Gender parity/safety billboards or awareness material displayed in public places, hostels, canteens and academic buildings", 1,
                 [_bool("Gender parity/safety billboards or awareness material displayed")]),
            _sub("C16.3", "Gender Champion nominated and uploaded on SAKSHAM", 1,
                 [_bool("Gender Champion nominated and uploaded on SAKSHAM")]),
            _sub("C16.4", "Participation in SAKSHAM Gender Audit", 1, [_bool("Participation in SAKSHAM Gender Audit")]),
            _sub("C16.5", "Workshop for students on gender sensitisation/ SAKSHAM/Government initiatives on gender parity", 1,
                 [_bool("Workshop for students on gender sensitisation/SAKSHAM/Government initiatives on gender parity")]),
        ],
    },
    "C17": {
        "evidence_text": "Student participation list, activity reports, photographs, certificates and community feedback.",
        "subcriteria": [
            _sub("C17.1", "Percentage of students participating in outreach/ NSS/ NCC/ community engagement/ Unnat Bharat Abhiyan/ "
                          "social responsibility activities", 5, [
                _int("total_enrolled_students", "Total number of students", "e.g. 1200"),
                _int("participating_students", "Number of students participating", "e.g. 900", max_field="total_enrolled_students"),
            ]),
        ],
    },
    "C18": {
        "evidence_text": "Activity reports with SDG mapping, photographs, audit reports, club notification and outcome records.",
        "subcriteria": [
            _sub("C18.1", "Five or more activities mapped with SDGs", 2, [
                _int("sdg_activities", "Number of activities mapped with SDGs", "e.g. 6"),
            ]),
            _sub("C18.2", "Green campus/environmental practices such as waste segregation, energy conservation, water conservation, "
                          "plantation, plastic-free campus or recycling", 1,
                 [_bool("Green campus/environmental practices in place")]),
            _sub("C18.3", "Student-led environment/sustainability club or eco-club functional", 1,
                 [_bool("Student-led environment/sustainability club or eco-club functional")]),
            _sub("C18.4", "Annual report/evidence of SDG mapping and outcomes", 1,
                 [_bool("Annual report/evidence of SDG mapping and outcomes prepared")]),
        ],
    },
    "C19": {
        "evidence_text": "Patent filing/grant certificates, IPR cell records, innovation reports.",
        "subcriteria": [
            _sub("C19.I", "Patents filed between July 2025 and June 2026 — 1 mark for every two patents filed (max 2 marks)", 2, [
                _int("patents_filed", "Number of patents filed", "e.g. 4"),
            ], period_bound=True),
            _sub("C19.II", "Patents granted between July 2025 and June 2026 — 1 mark for each patent granted (max 2 marks)", 2, [
                _int("patents_granted", "Number of patents granted", "e.g. 2"),
            ], period_bound=True),
            _sub("C19.III", "Scopus index during evaluation period (100 and above → 2; 50 and above → 1)", 2, [
                _int("scopus_index", "Scopus index value during evaluation period", "e.g. 60"),
            ], period_bound=True,
                note="The source does not define the Scopus metric. A claimed value is not scored until the policy owner defines it (policy SCOPUS_METRIC)."),
        ],
    },
    "C20": {
        "evidence_text": "NAAC certificate, NIRF submission proof, AISHE certificate, IQAC/AQAR records.",
        "subcriteria": [
            _sub("C20.1", "NAAC accredited with A++/A+/A grade → 2 marks; B++/B+/B grade → 1 mark", 2, [
                {"key": "naac_grade", "label": "NAAC accreditation grade", "type": "enum", "options": NAAC_GRADES},
            ]),
            _sub("C20.2", "Registered for NIRF 2026 or participated in NIRF/India Rankings", 1,
                 [_bool("Registered for NIRF 2026 or participated in NIRF/India Rankings")]),
            _sub("C20.3", "AISHE data submitted for the latest cycle", 1, [_bool("AISHE data submitted for the latest cycle")]),
            _sub("C20.4", "IQAC annual quality assurance mechanism/AQAR or equivalent institutional quality report prepared", 1,
                 [_bool("IQAC annual quality assurance mechanism/AQAR or equivalent report prepared")]),
        ],
    },
    "C21": {
        "evidence_text": "Activity reports, photographs, attendance, certificates and curriculum/activity calendar.",
        "subcriteria": [
            _sub("C21.1", "Cultural/heritage/constitutional values activities organised between July 2025 and June 2026 "
                          "(five or more → 2; two to four → 1; no activity → 0)", 2, [
                _int("activities_count", "Number of cultural/heritage/constitutional values activities organised", "e.g. 5"),
            ], period_bound=True),
            _sub("C21.2", "Integration of ethics, constitutional values, civic duties or local culture in student activities/curriculum", 1,
                 [_bool("Ethics, constitutional values, civic duties or local culture integrated in student activities/curriculum")]),
        ],
    },
    "C22": {
        "evidence_text": "Office order for nomination of Student Feedback Nodal Officer, SOPs, Feedback forms/dashboard, analysis report, "
                         "ATR and minutes of meeting.",
        "subcriteria": [
            _sub("C22.1", "Structured student feedback collected and analysed for curriculum/ teaching/ student services", 1,
                 [_bool("Structured student feedback collected and analysed")]),
            _sub("C22.2", "Action Taken Report prepared and approved by competent authority/IQAC", 1,
                 [_bool("Action Taken Report prepared and approved by competent authority/IQAC")]),
        ],
    },
}

# ---------------------------------------------------------------------------
# UNIVERSITY (U1–U20)
# ---------------------------------------------------------------------------
_UNIVERSITY: Dict[str, Dict[str, Any]] = {
    "U1": {
        "evidence_text": "Approved curriculum / scheme of examination / BoS or Academic Council approval.",
        "subcriteria": [
            _sub("U1.1", "Number of degree programmes in which apprenticeship / field project / OJT is credit-bearing and embedded "
                         "in the approved curriculum", 4, [
                _int("programmes_count", "Number of degree programmes", "e.g. 11"),
            ]),
        ],
    },
    "U2": {
        "evidence_text": "List of courses, language-wise material, timetable/exam support notification.",
        "subcriteria": [
            _sub("U2.1", "% of degree programmes in which courses, learning material, bilingual delivery, or examination support is "
                         "provided in Indian languages, excluding Indian language/literature programmes counted as core subjects", 4, [
                _int("total_degree_programmes", "Total number of degree programmes", "e.g. 60"),
                _int("indian_lang_programmes", "Number of degree programmes with Indian-language provision", "e.g. 48",
                     max_field="total_degree_programmes"),
            ]),
        ],
    },
    "U3": {
        "evidence_text": "Syllabus, course outlines, approvals, activity/project records.",
        "subcriteria": [
            _sub("U3.1", "% of degree programmes in which IKS components are meaningfully integrated as courses/modules/projects/"
                         "VAC/SEC/AEC, excluding routine language courses unless they include explicit IKS content", 4, [
                _int("total_degree_programmes", "Total number of degree programmes", "e.g. 60"),
                _int("iks_programmes", "Number of degree programmes with IKS integration", "e.g. 18",
                     max_field="total_degree_programmes"),
            ]),
        ],
    },
    "U4": {
        "evidence_text": "Approved IDP, target sheet, progress report, supporting records.",
        "subcriteria": [
            _sub("U4.A", "Achievement of IDP targets fixed for 2024-25", 3, [
                _int("total_targets_2024_25", "Number of IDP targets fixed for 2024-25", "e.g. 40"),
                _int("achieved_targets_2024_25", "Number of 2024-25 targets achieved", "e.g. 37", max_field="total_targets_2024_25"),
            ]),
            _sub("U4.B", "Achievement of IDP targets fixed for 2025-26", 3, [
                _int("total_targets_2025_26", "Number of IDP targets fixed for 2025-26", "e.g. 45"),
                _int("achieved_targets_2025_26", "Number of 2025-26 targets achieved", "e.g. 41", max_field="total_targets_2025_26"),
            ]),
        ],
    },
    "U5": {
        "evidence_text": "Certificate from Head of Institution.",
        "subcriteria": [
            _sub("U5.A", "% of total students eligible for placement drives", 2, [
                _int("total_final_year_students", "Total number of students (base for the percentage)", "e.g. 2000"),
                _int("eligible_students", "Number of students eligible for placement drives", "e.g. 1600",
                     max_field="total_final_year_students"),
            ]),
            _sub("U5.B", "% of eligible students who received placement or pre-placement offers during internship / apprenticeship / "
                         "field exposure / placement drives", 2, [
                _int("placed_students", "Number of eligible students who received placement / pre-placement offers", "e.g. 1300"),
            ]),
        ],
    },
    "U6": {
        "evidence_text": "The source lists no parameter-specific evidence; the general instruction requires documentary evidence for all marks.",
        "subcriteria": [
            _sub("U6.A", "6A Assessment / Examination Reforms: Amendment in Examination Ordinance for Assessing Learning Outcomes", 4, [
                _bool("Examination Ordinance amended for assessing learning outcomes", key="ordinance_notified"),
            ]),
            _sub("U6.B", "6B Pedagogical Reforms: major interventions/tools to ensure experiential learning/problem solving skill "
                         "implemented by the University (1 mark per intervention/tool, max 4)", 4, [
                _int("tools_count", "Number of interventions/tools implemented", "e.g. 4"),
            ]),
        ],
    },
    "U7": {
        "evidence_text": "Appointment order, workload/course record, attendance, activity report.",
        "subcriteria": [
            _sub("U7.1", "PoP appointed as per applicable norms", 1, [_bool("PoP appointed as per applicable norms")]),
            _sub("U7.2", "Complete course / module delivered by PoP", 1, [_bool("Complete course / module delivered by PoP")]),
            _sub("U7.3", "Lab, studio, industry project, live project or mentoring activity conducted", 1,
                 [_bool("Lab, studio, industry project, live project or mentoring activity conducted")]),
            _sub("U7.4", "Documented outcomes such as student projects, prototypes, industry problem-solving, lectures or workshops", 1,
                 [_bool("Documented outcomes (student projects, prototypes, industry problem-solving, lectures or workshops)")]),
        ],
    },
    "U8": {
        "evidence_text": "Startup registration/incubation records, funding/revenue/commercialization proof.",
        "subcriteria": [
            _sub("U8.A", "Startups/companies registered/incubated between July 2025 and June 2026 (1-5 → 2; 6-10 → 3; more than 10 → 4)", 4, [
                _int("startups_count", "Number of startups/companies registered/incubated", "e.g. 8"),
            ], period_bound=True),
            _sub("U8.B", "50% or more of the reported startups are monetised/commercialised or have received funding/revenue/orders", 2, [
                _int("monetized_count", "Number of reported startups monetised/commercialised or with funding/revenue/orders", "e.g. 4"),
            ]),
        ],
    },
    "U9": {
        "evidence_text": "Signed MoU/LoI, activity reports, participant list, credit/research outputs.",
        "subcriteria": [
            _sub("U9.A", "Collaborations with foreign HEIs between July 2025 and June 2026: % of active collaborations "
                         "(at least 1 activity during the evaluation period) > 75% → 1 mark", 1, [
                _int("total_mous", "Number of collaborations with foreign HEIs", "e.g. 8"),
                _int("active_mous", "Number of active collaborations (at least 1 activity)", "e.g. 7", max_field="total_mous"),
            ], period_bound=True),
            _sub("U9.B", "Average activity per active collaboration (5 or more → 5; 4 → 4; 3 → 3; 2 → 2; 1 → 1)", 5, [
                _int("activities_count", "Total number of activities across all active collaborations", "e.g. 28"),
            ], period_bound=True,
                note="Average = total activities ÷ active collaborations (U9.A). Tiering of fractional averages below 5 is policy U9B_FRACTIONAL_AVERAGE."),
        ],
    },
    "U10": {
        "evidence_text": "Alumni report, database summary, event reports, invitations, photographs, proceedings.",
        "subcriteria": [
            _sub("U10.1", "Alumni Society registered", 1, [_bool("Alumni Society registered")]),
            _sub("U10.2", "Updated alumni database maintained", 1, [_bool("Updated alumni database maintained")]),
            _sub("U10.3", "Funding received from Alumni during evaluation period (>Rs.1 Crore → 2; <Rs.1 Crore → 1; none → 0)", 2, [
                _currency("funding_amount", "Alumni funding received during the evaluation period (INR)", "e.g. 2500000"),
            ], period_bound=True),
            _sub("U10.4", "At least 5 alumni invited as speakers/mentors/industry experts or recognised by the university during the "
                          "assessment period", 1,
                 [_bool("At least 5 alumni invited as speakers/mentors/industry experts or recognised")], period_bound=True),
        ],
    },
    "U11": {
        "evidence_text": "Orders, screenshots, photographs, workshop reports, attendance records.",
        "subcriteria": [
            _sub("U11.1", "Gender parity display boards/awareness material placed in public places, hostels, canteens and academic buildings", 1,
                 [_bool("Gender parity display boards/awareness material placed")]),
            _sub("U11.2", "Gender Champion nominated and uploaded on SAKSHAM/concerned platform, wherever applicable", 1,
                 [_bool("Gender Champion nominated and uploaded on SAKSHAM/concerned platform")]),
            _sub("U11.3", "Participation in SAKSHAM Gender Audit or equivalent gender audit exercise", 1,
                 [_bool("Participation in SAKSHAM Gender Audit or equivalent gender audit exercise")]),
            _sub("U11.4", "Workshop/session for students on gender sensitisation, SAKSHAM or Government initiatives on gender parity", 1,
                 [_bool("Workshop/session for students on gender sensitisation, SAKSHAM or Government initiatives")]),
        ],
    },
    "U12": {
        "evidence_text": "Notification, calendar, activity reports, attendance, counselling/support records.",
        "subcriteria": [
            _sub("U12.1", "Mental Health and Well-being Centre (MHWBC) and/or Student Service Centre established", 1,
                 [_bool("MHWBC and/or Student Service Centre established")]),
            _sub("U12.2", "Annual activity calendar for sports, yoga, fitness, health and well-being prepared and implemented", 1,
                 [_bool("Annual activity calendar prepared and implemented")]),
            _sub("U12.3", "Minimum two student workshops/activities on mental health, well-being, yoga/fitness or stress management "
                          "between July 2025 and June 2026", 1,
                 [_bool("Minimum two student workshops/activities conducted")], period_bound=True),
            _sub("U12.4", "Workshop/orientation organised for teaching and non-teaching staff on mental health/well-being/student support", 1,
                 [_bool("Workshop/orientation organised for teaching and non-teaching staff")]),
            _sub("U12.5", "Counselling/referral mechanism, student support records or annual well-being report maintained", 1,
                 [_bool("Counselling/referral mechanism, student support records or annual well-being report maintained")]),
        ],
    },
    "U13": {
        "evidence_text": "MOOCs policy, Academic Council approval, list of courses, student enrolment/completion data.",
        "subcriteria": [
            _sub("U13.1", "% of learners out of total regular learners who adopted online courses, MOOCs, SWAYAM/NPTEL or "
                          "HEI-designed online courses offered", 6, [
                _int("total_regular_learners", "Total number of regular learners", "e.g. 9000"),
                _int("regular_mooc_learners", "Number of regular learners who adopted online courses/MOOCs", "e.g. 5000",
                     max_field="total_regular_learners"),
            ]),
        ],
    },
    "U14": {
        "evidence_text": "Curriculum, course structure, elective basket, approvals, student enrolment.",
        "subcriteria": [
            _sub("U14.A", "% of degree programmes offering multidisciplinary learning through major-minor combinations, open electives, "
                          "multidisciplinary courses or flexible subject choices", 4, [
                _int("total_degree_programmes", "Total number of degree programmes", "e.g. 60"),
                _int("multidisciplinary_programmes", "Number of degree programmes offering multidisciplinary learning", "e.g. 55",
                     max_field="total_degree_programmes"),
            ]),
            _sub("U14.B", "Physical education/sports/yogasan embedded as AEC/VAC/NCC/NSS in all relevant programmes", 1,
                 [_bool("Physical education/sports/yogasan embedded as AEC/VAC/NCC/NSS in all relevant programmes")]),
            _sub("U14.C", "Industry-aligned VAC/SEC courses embedded in programmes", 1,
                 [_bool("Industry-aligned VAC/SEC courses embedded in programmes")]),
        ],
    },
    "U15": {
        "evidence_text": "Notification/ordinance, MEME student format.",
        "subcriteria": [
            _sub("U15.1", "Multiple entry-exit framework/rules notified and incorporated in ordinances/regulations/curriculum", 1,
                 [_bool("Multiple entry-exit framework/rules notified and incorporated")]),
            _sub("U15.2", "Multiple entry-exit format for application and certificate for students designed", 1,
                 [_bool("Multiple entry-exit format for application and certificate designed")]),
        ],
    },
    "U16": {
        "evidence_text": "Patent filing acknowledgement, grant certificate, commercialisation/licensing proof.",
        "subcriteria": [
            _sub("U16.I", "Patents filed between July 2025 and June 2026 — 1 mark for every five patents filed (max 2 marks)", 2, [
                _int("patents_filed", "Number of patents filed", "e.g. 10"),
            ], period_bound=True),
            _sub("U16.II", "Patents granted/commercialised/licensed during the assessment period — 1 mark each (max 2 marks)", 2, [
                _int("patents_granted", "Number of patents granted/commercialised/licensed", "e.g. 2"),
            ], period_bound=True),
            _sub("U16.III", "Scopus Index during evaluation period (400+ → 4; 300+ → 3; 200+ → 2; 100+ → 1)", 4, [
                _int("scopus_index", "Scopus index value during evaluation period", "e.g. 320"),
            ], period_bound=True,
                note="The source does not define the Scopus metric. A claimed value is not scored until the policy owner defines it (policy SCOPUS_METRIC)."),
        ],
    },
    "U17": {
        "evidence_text": "NIRF submission proof and ranking/band proof.",
        "subcriteria": [
            _sub("U17.1", "Registered/submitted data for NIRF 2026 rankings", 1, [_bool("Registered/submitted data for NIRF 2026")]),
            _sub("U17.2", "Ranked in top 100 in overall/university/category ranking or placed in an officially notified rank band in NIRF 2025", 1,
                 [_bool("Ranked in top 100 or placed in an officially notified rank band in NIRF 2025")]),
        ],
    },
    "U18": {
        "evidence_text": "Adopted policy, programme list, applications assessed, credits awarded, approval records.",
        "subcriteria": [
            _sub("U18.1", "RPL guidelines/policy adopted by the university in line with UGC/State guidelines", 1,
                 [_bool("RPL guidelines/policy adopted in line with UGC/State guidelines")]),
            _sub("U18.2", "Awareness workshop for faculty/ staff/ students for RPL organised by the HEI during the evaluation year", 1,
                 [_bool("RPL awareness workshop organised")], period_bound=True),
            _sub("U18.3", "RPL format for students circulated with guidelines", 2,
                 [_bool("RPL format for students circulated with guidelines")]),
        ],
    },
    "U19": {
        "evidence_text": "OBE framework, CO-PO mapping, attainment reports, examination/assessment records.",
        "subcriteria": [
            _sub("U19.A", "% of programmes in which Course Outcomes, Programme Outcomes, CO-PO mapping and attainment analysis "
                          "have been completed", 6, [
                _int("total_degree_programmes", "Total number of programmes", "e.g. 60"),
                _int("obe_programmes", "Number of programmes with CO, PO, CO-PO mapping and attainment analysis completed", "e.g. 55",
                     max_field="total_degree_programmes"),
            ]),
            _sub("U19.B", "Examinations are conducted according to CO-PO of the Programmes", 2,
                 [_bool("Examinations conducted according to CO-PO of the programmes")]),
        ],
    },
    "U20": {
        "evidence_text": "Activity reports, SDG mapping sheet, photographs, beneficiary records, annual report.",
        "subcriteria": [
            _sub("U20.1", "Number of activities conducted and mapped with SDGs during the assessment period (10 or more → 2; 5 and above → 1)", 2, [
                _int("activities_count", "Number of activities conducted and mapped with SDGs", "e.g. 12"),
            ], period_bound=True),
            _sub("U20.2", "Curriculum mapping with SDG", 2, [_bool("Curriculum mapped with SDGs")]),
            _sub("U20.3", "Annual SDG activity report with evidence of outcomes/beneficiaries and SDG mapping", 1,
                 [_bool("Annual SDG activity report with evidence of outcomes/beneficiaries and SDG mapping")]),
        ],
    },
}

_PERIOD_FIELDS = [
    {"key": PERIOD_START_KEY, "label": "Earliest date of the activities/outputs claimed", "type": "date",
     "min_date": ASSESSMENT_PERIOD_START, "max_date": ASSESSMENT_PERIOD_END, "requires_positive_claim": True},
    {"key": PERIOD_END_KEY, "label": "Latest date of the activities/outputs claimed", "type": "date",
     "min_date": ASSESSMENT_PERIOD_START, "max_date": ASSESSMENT_PERIOD_END, "requires_positive_claim": True},
]


def _finalise(raw: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out = {}
    for p_code, p in raw.items():
        subs = {}
        for s in p["subcriteria"]:
            s = deepcopy(s)
            if s["period_bound"]:
                s["fields"] = s["fields"] + deepcopy(_PERIOD_FIELDS)
            subs[s["code"]] = s
        out[p_code] = {"code": p_code, "evidence_text": p["evidence_text"], "subcriteria": subs}
    return out


COLLEGE_FIELD_SCHEMA: Dict[str, Dict[str, Any]] = _finalise(_COLLEGE)
UNIVERSITY_FIELD_SCHEMA: Dict[str, Dict[str, Any]] = _finalise(_UNIVERSITY)


def get_schema(parameter_code: str) -> Dict[str, Any]:
    code = parameter_code.strip().upper()
    if code in COLLEGE_FIELD_SCHEMA:
        return COLLEGE_FIELD_SCHEMA[code]
    return UNIVERSITY_FIELD_SCHEMA[code]


def get_subcriterion_schema(parameter_code: str, subcriterion_code: str) -> Optional[Dict[str, Any]]:
    return get_schema(parameter_code)["subcriteria"].get(subcriterion_code)


def all_field_keys(parameter_code: str, subcriterion_code: str) -> List[str]:
    sub = get_subcriterion_schema(parameter_code, subcriterion_code) or {"fields": []}
    return [f["key"] for f in sub["fields"]]
