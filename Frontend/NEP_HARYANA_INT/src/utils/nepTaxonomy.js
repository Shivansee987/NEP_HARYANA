/**
 * NEP Excellence Awards 2026 — Authoritative Taxonomy & Metadata Dictionary
 * 
 * PROVENANCE & SOURCE OF TRUTH:
 * Derived strictly from official Haryana Higher Education Council source documents:
 * 1. University Parameters - NEP Excellence Awards 2026.pdf (U1–U20, 100 Marks)
 * 2. College Parameters - NEP Excellence Awards 2026 (1).pdf (C1–C22, 100 Marks)
 * 3. Master Specification: NEP_2026_PARAMETER_SPECIFICATION.md
 * 4. Backend Authoritative Registry: apps.scoring.rules.definitions & apps.evidence.taxonomy
 * 
 * INVARIANTS:
 * - College: Exactly 22 parameters (C1–C22). Zero U parameters.
 * - University: Exactly 20 parameters (U1–U20). Zero C parameters.
 * - Preserves authoritative subcriterion codes (e.g. C4.A, C4.B, C9.I, C9.II, C11.I, C11.II.a/b, U14.A-C, U16.I-III).
 * - Preserves source ambiguities as neutral UNRESOLVED notices without inventing scoring rules.
 * - Subcriterion evidence mapped 1:1 to authoritative evidence contracts.
 */

export const REJECTION_REASON_CODES = [
  {
    code: "INCOMPLETE_DOCUMENTATION",
    label: "Incomplete Documentation",
    description: "Required sections, annexures, or institutional proofs are missing or omitted.",
  },
  {
    code: "MISMATCHED_CRITERIA",
    label: "Mismatched Criteria",
    description: "Document content does not substantiate the specific parameter or subcriterion claimed.",
  },
  {
    code: "ILLEGIBLE_DOCUMENT",
    label: "Illegible Document",
    description: "Uploaded document is unreadable, corrupted, distorted, or blank.",
  },
  {
    code: "OUT_OF_PERIOD",
    label: "Out of Assessment Window",
    description: "Document dates fall outside statutory window (2025-07-01 to 2026-06-30).",
  },
  {
    code: "UNAUTHORIZED_SIGNATORY",
    label: "Unauthorized Signatory",
    description: "Document lacks mandatory institutional signature, official seal, or registrar stamp.",
  },
  {
    code: "INTEGRITY_MISMATCH",
    label: "Integrity Mismatch",
    description: "File checksum, version, or contents do not match inspected statutory records.",
  },
  {
    code: "OTHER",
    label: "Other Justification",
    description: "Specific reviewer feedback detailed in the comments.",
  },
];

export const UNIVERSITY_PARAMETER_CODES = [
  "U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9", "U10",
  "U11", "U12", "U13", "U14", "U15", "U16", "U17", "U18", "U19", "U20"
];

export const COLLEGE_PARAMETER_CODES = [
  "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
  "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18", "C19", "C20",
  "C21", "C22"
];

export const UNIVERSITY_PARAMETER_TITLES = {
  "U1": "Apprenticeship Embedded Degree Programmes",
  "U2": "Courses Offered in Indian Languages",
  "U3": "Integration of Indian Knowledge Systems (IKS)",
  "U4": "Targets Achieved under Institutional Development Plan (IDP)",
  "U5": "Percentage of Students Who Received Placement / Pre-Placement Offers",
  "U6": "Academic Reforms",
  "U7": "Professor of Practice (PoP) Engagement",
  "U8": "Incubation / Startup Cell Performance as per NISP",
  "U9": "Academic / Research Collaboration with Foreign HEIs",
  "U10": "Functional Alumni Connect Cell",
  "U11": "Gender Parity Initiatives",
  "U12": "Physical Fitness, Sports, Yoga, Health, Welfare, Psychological Well-being",
  "U13": "Online Courses / MOOCs Policy and Adoption",
  "U14": "Multidisciplinary Education",
  "U15": "Multiple Entry-Exit Operationalized",
  "U16": "Research Outcome: Patents Filed and Granted",
  "U17": "Registration and Performance in NIRF",
  "U18": "Recognition of Prior Learning (RPL) Adoption and Implementation",
  "U19": "Adoption of Outcome-Based Education (OBE)",
  "U20": "Activities Aligned with Sustainable Development Goals (SDGs)"
};

export const COLLEGE_PARAMETER_TITLES = {
  "C1": "Institutional Development Plan (IDP) and NEP Implementation Targets",
  "C2": "Apprenticeship / Internships",
  "C3": "Academic Bank of Credits (ABC) Registration",
  "C4": "Supporting Other Institutes and Schools in Their Development",
  "C5": "Student Enrollment against Sanctioned Seats",
  "C6": "VAC, AEC, SEC, NSQF-Aligned Courses and Short-Term Certifications",
  "C7": "Bridge Courses for SEDGs",
  "C8": "Nomination of NEP-SARTHI",
  "C9": "Student Career Orientation and Placements",
  "C10": "Industry Collaboration, MoUs and Industry-Aligned Academic Activities",
  "C11": "Incubation, Startup Cell and Entrepreneurship Promotion",
  "C12": "Alumni Connect and External Expert Engagement",
  "C13": "Faculty Development and NEP Orientation",
  "C14": "Indian Languages and Indian Knowledge System (IKS)",
  "C15": "Student Well-being, Physical Fitness, Yoga and Sports",
  "C16": "Gender Parity, Safety and Inclusion Initiatives",
  "C17": "Outreach, Community Engagement and Social Responsibility",
  "C18": "Sustainable Development Goals (SDGs), Green Campus and Environmental Practices",
  "C19": "Research, Innovation and Patents",
  "C20": "Quality Assurance, NAAC/NIRF/AISHE and Institutional Reporting",
  "C21": "Cultural Activities, Constitutional Values and Holistic Development",
  "C22": "Governance, Student Feedback and Evidence-Based Improvement"
};

export const UNRESOLVED_SPEC_NOTICES = {
  // University Ambiguities preserved from source
  U8: "SOURCE_HEADER_AMBIGUITY: Section text references 3 marks while component arithmetic allocates 4 marks + 2 marks (6 marks total). Handled closed under strict non-exceedance.",
  U16: "UNRESOLVED_REQUIREMENT: Subcriterion U16.III references Scopus index requirement without published metric cutoff in source.",
  U18: "UNRESOLVED_REQUIREMENT: Subcriterion U18.3 references RPL workshop metric without explicit evaluation rule in source.",
  U20: "ARITHMETIC_GAP: Stated maximum is 4 marks while component sum (2+2+1) totals 5 marks. Capped at 4.0 marks invariant.",
  U6: "SOURCE_SILENT: Authoritative source specification specifies zero mandatory documentary evidence for this parameter.",
  
  // College Ambiguities preserved from source
  C5: "SOURCE_SILENT: Authoritative source specification specifies zero mandatory documentary evidence for this parameter.",
  C7: "THRESHOLD_INCONSISTENCY: Boundary operator gap in source Sedg threshold table. Preserved without arbitrary normalization.",
  C8: "UNRESOLVED_RULE: Applicable statutory evaluation rule is pending council resolution.",
  C9: "SOURCE_SILENT: Authoritative source specification specifies zero mandatory documentary evidence for this parameter.",
  C16: "ARITHMETIC_GAP: Stated parameter maximum is 4 marks while five 1-mark components total 5 marks. Capped at 4.0 marks invariant.",
  C19: "UNRESOLVED_REQUIREMENT: Subcriterion C19.III references Scopus index requirement without published metric cutoff in source.",
  C21: "COMPONENT_CAP: Stated parameter maximum is 4 marks with written component ceiling. Evaluated under strict non-exceedance.",
};

export const COLLEGE_FRAMEWORK_DATA = {
  "C1": {
    "code": "C1",
    "title": "Institutional Development Plan (IDP) and NEP Implementation Targets",
    "maxMarks": 6.0,
    "periodRule": "REFERENCE_YEAR_DEPENDENT",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C1_APPROVED_IDP"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C1.1",
        "title": "Annual NEP Target Achievement Rate under Approved IDP (2024\u201325)",
        "maxScore": 6.0,
        "documentaryRequirement": "Copy of IDP, Governing Body approval, Progress report certified by Principal",
        "canonicalEvidenceType": "EVID_C1_APPROVED_IDP",
        "allowedEvidenceTypes": [
          "EVID_C1_APPROVED_IDP"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "achieved_targets_2024_25",
            "label": "Targets Achieved (2024\u201325)",
            "type": "number",
            "placeholder": "e.g. 92"
          },
          {
            "key": "fixed_targets_2024_25",
            "label": "Targets Fixed in IDP (2024\u201325)",
            "type": "number",
            "placeholder": "e.g. 100"
          }
        ]
      }
    ]
  },
  "C2": {
    "code": "C2",
    "title": "Apprenticeship / Internships",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C2_HOI_CERT"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C2.1",
        "title": "Percentage of Eligible Students Completing Internships / Apprenticeships",
        "maxScore": 4.0,
        "documentaryRequirement": "Internship completion certificates / institutional data / MoUs",
        "canonicalEvidenceType": "EVID_C2_HOI_CERT",
        "allowedEvidenceTypes": [
          "EVID_C2_HOI_CERT"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "students_completed",
            "label": "Students Completed Internship/Apprenticeship",
            "type": "number",
            "placeholder": "e.g. 460"
          },
          {
            "key": "eligible_students",
            "label": "Total Eligible Final/Pre-Final Students",
            "type": "number",
            "placeholder": "e.g. 500"
          }
        ]
      }
    ]
  },
  "C3": {
    "code": "C3",
    "title": "Academic Bank of Credits (ABC) Registration",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_INSENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C3_ABC_DASHBOARD"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C3.1",
        "title": "Percentage of Enrolled Students with Active ABC / APAAR Accounts",
        "maxScore": 4.0,
        "documentaryRequirement": "ABC portal screenshot/report with total enrollment and registered students",
        "canonicalEvidenceType": "EVID_C3_ABC_DASHBOARD",
        "allowedEvidenceTypes": [
          "EVID_C3_ABC_DASHBOARD"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "abc_registered_students",
            "label": "Students Registered on ABC / APAAR",
            "type": "number",
            "placeholder": "e.g. 1850"
          },
          {
            "key": "total_enrolled_students",
            "label": "Total Enrolled Students in College",
            "type": "number",
            "placeholder": "e.g. 2000"
          }
        ]
      }
    ]
  },
  "C4": {
    "code": "C4",
    "title": "Supporting Other Institutes and Schools in Their Development",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C4_INSTITUTE_CERTS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C4.A",
        "title": "Support and Mentorship Provided to Other Higher Education Institutes (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "MoU/agreement with mentee institutes/schools, activity reports with geo-tagged photos",
        "canonicalEvidenceType": "EVID_C4_INSTITUTE_CERTS",
        "allowedEvidenceTypes": [
          "EVID_C4_INSTITUTE_CERTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "heis_mentored",
            "label": "Number of Mentored HEIs with Demonstrable Activities",
            "type": "number",
            "placeholder": "e.g. 2"
          }
        ]
      },
      {
        "code": "C4.B",
        "title": "Handholding and Developmental Support to Local Schools (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "MoU/agreement with mentee institutes/schools, activity reports with geo-tagged photos",
        "canonicalEvidenceType": "EVID_C4_INSTITUTE_CERTS",
        "allowedEvidenceTypes": [
          "EVID_C4_INSTITUTE_CERTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "schools_mentored",
            "label": "Number of Supported Schools with Tangible Interventions",
            "type": "number",
            "placeholder": "e.g. 2"
          }
        ]
      }
    ]
  },
  "C5": {
    "code": "C5",
    "title": "Student Enrollment against Sanctioned Seats",
    "maxMarks": 2.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "BOUNDARY_UNRESOLVED",
    "mandatoryEvidence": [
      "EVID_C5_SANCTION_LETTER"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C5.1",
        "title": "Percentage of Sanctioned Seats Filled in UG & PG Programmes",
        "maxScore": 2.0,
        "documentaryRequirement": "Source silent: No documentary evidence required by council specification.",
        "canonicalEvidenceType": null,
        "allowedEvidenceTypes": [],
        "contractStatus": "SOURCE_SILENT",
        "isSourceSilent": true,
        "isUnresolved": false,
        "fields": [
          {
            "key": "admitted_students",
            "label": "Total Students Enrolled / Admitted",
            "type": "number",
            "placeholder": "e.g. 920"
          },
          {
            "key": "sanctioned_intake",
            "label": "Total Sanctioned Seats Across Programmes",
            "type": "number",
            "placeholder": "e.g. 1000"
          }
        ]
      }
    ]
  },
  "C6": {
    "code": "C6",
    "title": "VAC, AEC, SEC, NSQF-Aligned Courses and Short-Term Certifications",
    "maxMarks": 6.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C6_COURSE_APPROVAL"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C6.1",
        "title": "Percentage of Students Certified in NSQF-Aligned / VAC / AEC / SEC Courses",
        "maxScore": 6.0,
        "documentaryRequirement": "Course list, syllabi, student enrollment data certified by Principal",
        "canonicalEvidenceType": "EVID_C6_COURSE_APPROVAL",
        "allowedEvidenceTypes": [
          "EVID_C6_COURSE_APPROVAL"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "certified_students",
            "label": "Students Certified in Skill / Value-Added Courses",
            "type": "number",
            "placeholder": "e.g. 350"
          },
          {
            "key": "total_enrolled_students",
            "label": "Total Enrolled Students in College",
            "type": "number",
            "placeholder": "e.g. 1000"
          }
        ]
      }
    ]
  },
  "C7": {
    "code": "C7",
    "title": "Bridge Courses for SEDGs",
    "maxMarks": 6.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "UNRESOLVED_RULE",
    "mandatoryEvidence": [
      "EVID_C7_OFFICE_ORDERS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C7.1",
        "title": "Bridge Courses Conducted for Socio-Economically Disadvantaged Groups (SEDGs)",
        "maxScore": 3.0,
        "documentaryRequirement": "Relevant office orders",
        "canonicalEvidenceType": "EVID_C7_OFFICE_ORDERS",
        "allowedEvidenceTypes": [
          "EVID_C7_OFFICE_ORDERS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "sedg_bridge_students",
            "label": "SEDG Students Benefited through Bridge Courses",
            "type": "number",
            "placeholder": "e.g. 120"
          },
          {
            "key": "total_sedg_students",
            "label": "Total SEDG Students Enrolled",
            "type": "number",
            "placeholder": "e.g. 200"
          }
        ]
      }
    ]
  },
  "C8": {
    "code": "C8",
    "title": "Nomination of NEP-SARTHI",
    "maxMarks": 2.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "UNRESOLVED_RULE",
    "mandatoryEvidence": [
      "EVID_C8_OFFICE_ORDERS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C8.1",
        "title": "Nomination and Active Deployment of NEP-SARTHI Student Ambassadors",
        "maxScore": 2.0,
        "documentaryRequirement": "Relevant office orders",
        "canonicalEvidenceType": "EVID_C8_OFFICE_ORDERS",
        "allowedEvidenceTypes": [
          "EVID_C8_OFFICE_ORDERS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "NEP-SARTHI Nominated and Active Activity Reports Submitted",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "C9": {
    "code": "C9",
    "title": "Student Career Orientation and Placements",
    "maxMarks": 6.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C9_FAIR_REGISTER"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C9.I",
        "title": "Placement Fair / Career Orientation Participation Percentage",
        "maxScore": 3.0,
        "documentaryRequirement": "Source silent: No documentary evidence required by council specification.",
        "canonicalEvidenceType": null,
        "allowedEvidenceTypes": [],
        "contractStatus": "SOURCE_SILENT",
        "isSourceSilent": true,
        "isUnresolved": false,
        "fields": [
          {
            "key": "participating_students",
            "label": "Students Attending Placement/Orientation Drives",
            "type": "number",
            "placeholder": "e.g. 300"
          },
          {
            "key": "eligible_students",
            "label": "Total Eligible Final Year Students",
            "type": "number",
            "placeholder": "e.g. 400"
          }
        ]
      },
      {
        "code": "C9.II",
        "title": "Placement / Progression Conversion Percentage",
        "maxScore": 3.0,
        "documentaryRequirement": "Source silent: No documentary evidence required by council specification.",
        "canonicalEvidenceType": null,
        "allowedEvidenceTypes": [],
        "contractStatus": "SOURCE_SILENT",
        "isSourceSilent": true,
        "isUnresolved": false,
        "fields": [
          {
            "key": "placed_students",
            "label": "Students Placed or Progressed to Higher Education",
            "type": "number",
            "placeholder": "e.g. 210"
          },
          {
            "key": "participating_students",
            "label": "Total Participating Candidates",
            "type": "number",
            "placeholder": "e.g. 300"
          }
        ]
      }
    ]
  },
  "C10": {
    "code": "C10",
    "title": "Industry Collaboration, MoUs and Industry-Aligned Academic Activities",
    "maxMarks": 5.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C10_MOU_DOCS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C10.1",
        "title": "Number of Active Industry Collaborations / MoUs with Tangible Academic Activities",
        "maxScore": 5.0,
        "documentaryRequirement": "Copies of MoUs, activity reports with attendance/certificates",
        "canonicalEvidenceType": "EVID_C10_MOU_DOCS",
        "allowedEvidenceTypes": [
          "EVID_C10_MOU_DOCS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "active_mous_count",
            "label": "Number of Active MoUs with Documented Activities",
            "type": "number",
            "placeholder": "e.g. 5"
          }
        ]
      }
    ]
  },
  "C11": {
    "code": "C11",
    "title": "Incubation, Startup Cell and Entrepreneurship Promotion",
    "maxMarks": 5.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C11_REGISTRATION"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C11.I",
        "title": "Incubation Centre / Entrepreneurship Development Cell Established",
        "maxScore": 3.0,
        "documentaryRequirement": "Cell establishment notification, annual activity report, list of startups/ventures supported with details",
        "canonicalEvidenceType": "EVID_C11_REGISTRATION",
        "allowedEvidenceTypes": [
          "EVID_C11_REGISTRATION"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "cell_functional",
            "label": "Dedicated Incubation / E-Cell Established and Functional",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C11.II.a",
        "title": "Student Startups / Ventures Incubated (Count)",
        "maxScore": 1.0,
        "documentaryRequirement": "Cell establishment notification, annual activity report, list of startups/ventures supported with details",
        "canonicalEvidenceType": "EVID_C11_REGISTRATION",
        "allowedEvidenceTypes": [
          "EVID_C11_REGISTRATION"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "ventures_count",
            "label": "Number of Startups/Ventures Incubated",
            "type": "number",
            "placeholder": "e.g. 3"
          }
        ]
      },
      {
        "code": "C11.II.b",
        "title": "Commercialized / Revenue-Generating Student Ventures",
        "maxScore": 1.0,
        "documentaryRequirement": "Cell establishment notification, annual activity report, list of startups/ventures supported with details",
        "canonicalEvidenceType": "EVID_C11_REGISTRATION",
        "allowedEvidenceTypes": [
          "EVID_C11_REGISTRATION"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "monetized_count",
            "label": "Number of Ventures Generating Revenue / Orders",
            "type": "number",
            "placeholder": "e.g. 1"
          }
        ]
      }
    ]
  },
  "C12": {
    "code": "C12",
    "title": "Alumni Connect and External Expert Engagement",
    "maxMarks": 5.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "FIXED_ITEM_SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C12_DATABASE"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C12.1",
        "title": "Registered Alumni Association with Maintained Database (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Registration certificate, database summary, event reports with photos, contribution receipts/audited statements, engagement letters",
        "canonicalEvidenceType": "EVID_C12_DATABASE",
        "allowedEvidenceTypes": [
          "EVID_C12_DATABASE"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Alumni Database Maintained with Active Membership",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C12.2",
        "title": "Society Registration Certificate of Alumni Association (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Registration certificate, database summary, event reports with photos, contribution receipts/audited statements, engagement letters",
        "canonicalEvidenceType": "EVID_C12_DATABASE",
        "allowedEvidenceTypes": [
          "EVID_C12_DATABASE"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Alumni Association Formally Registered under Societies Act",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C12.3",
        "title": "Alumni Financial Contribution / Endowment Mobilization (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Registration certificate, database summary, event reports with photos, contribution receipts/audited statements, engagement letters",
        "canonicalEvidenceType": "EVID_C12_DATABASE",
        "allowedEvidenceTypes": [
          "EVID_C12_DATABASE"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Financial Contribution Received and Audited",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C12.4",
        "title": "Alumni Guest Lectures & Interactive Sessions (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Registration certificate, database summary, event reports with photos, contribution receipts/audited statements, engagement letters",
        "canonicalEvidenceType": "EVID_C12_DATABASE",
        "allowedEvidenceTypes": [
          "EVID_C12_DATABASE"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Lectures Conducted by Distinguished Alumni",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C12.5",
        "title": "Formal Alumni Mentorship Programme Operational (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Registration certificate, database summary, event reports with photos, contribution receipts/audited statements, engagement letters",
        "canonicalEvidenceType": "EVID_C12_DATABASE",
        "allowedEvidenceTypes": [
          "EVID_C12_DATABASE"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Mentorship Logs and Student Guidance Maintained",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "C13": {
    "code": "C13",
    "title": "Faculty Development and NEP Orientation",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C13_FDP_CERTS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C13.1",
        "title": "Percentage of Full-Time Faculty Trained in NEP / FDP / MMTTC Programmes",
        "maxScore": 4.0,
        "documentaryRequirement": "Certificates of faculty, summary list certified by Principal",
        "canonicalEvidenceType": "EVID_C13_FDP_CERTS",
        "allowedEvidenceTypes": [
          "EVID_C13_FDP_CERTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "trained_faculty",
            "label": "Full-Time Faculty Completed NEP / FDP Programmes",
            "type": "number",
            "placeholder": "e.g. 45"
          },
          {
            "key": "total_fulltime_faculty",
            "label": "Total Sanctioned / Regular Faculty Members",
            "type": "number",
            "placeholder": "e.g. 50"
          }
        ]
      }
    ]
  },
  "C14": {
    "code": "C14",
    "title": "Indian Languages and Indian Knowledge System (IKS)",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C14_MATERIAL_CERT"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C14.A",
        "title": "Teaching-Learning Materials Developed / Offered in Indian Languages (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Timetable/course allotment showing bilingual mode, syllabus/activity reports for IKS",
        "canonicalEvidenceType": "EVID_C14_MATERIAL_CERT",
        "allowedEvidenceTypes": [
          "EVID_C14_MATERIAL_CERT"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "content_items",
            "label": "Number of Courses/Modules with Indian Language Content",
            "type": "number",
            "placeholder": "e.g. 4"
          }
        ]
      },
      {
        "code": "C14.B",
        "title": "Indian Knowledge Systems (IKS) Courses & Cultural Activities (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Timetable/course allotment showing bilingual mode, syllabus/activity reports for IKS",
        "canonicalEvidenceType": "EVID_C14_MATERIAL_CERT",
        "allowedEvidenceTypes": [
          "EVID_C14_MATERIAL_CERT"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "iks_activities",
            "label": "Number of Documented IKS Courses / Workshops Conducted",
            "type": "number",
            "placeholder": "e.g. 3"
          }
        ]
      }
    ]
  },
  "C15": {
    "code": "C15",
    "title": "Student Well-being, Physical Fitness, Yoga and Sports",
    "maxMarks": 6.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "FIXED_ITEM_SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C15_CENTRE_ORDER"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C15.1",
        "title": "Health & Psychological Well-being Centre Established (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Notifications, activity reports with photos, sports participation certificates, committee minutes",
        "canonicalEvidenceType": "EVID_C15_CENTRE_ORDER",
        "allowedEvidenceTypes": [
          "EVID_C15_CENTRE_ORDER"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Dedicated Well-being Centre & Trained Counsellor Available",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C15.2",
        "title": "Sports & Gymnasium Infrastructure Maintained (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Notifications, activity reports with photos, sports participation certificates, committee minutes",
        "canonicalEvidenceType": "EVID_C15_CENTRE_ORDER",
        "allowedEvidenceTypes": [
          "EVID_C15_CENTRE_ORDER"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Functional Indoor/Outdoor Sports Facilities Maintained",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C15.3",
        "title": "Yoga & Meditation Regular Sessions (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Notifications, activity reports with photos, sports participation certificates, committee minutes",
        "canonicalEvidenceType": "EVID_C15_CENTRE_ORDER",
        "allowedEvidenceTypes": [
          "EVID_C15_CENTRE_ORDER"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Periodic Yoga Workshops / International Yoga Day Held",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C15.4",
        "title": "Annual Health Checkup & Medical Camps Conducted (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Notifications, activity reports with photos, sports participation certificates, committee minutes",
        "canonicalEvidenceType": "EVID_C15_CENTRE_ORDER",
        "allowedEvidenceTypes": [
          "EVID_C15_CENTRE_ORDER"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "General / Eye / Dental Health Camps for Students",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C15.5",
        "title": "Participation in Fit India Movement Activities (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Notifications, activity reports with photos, sports participation certificates, committee minutes",
        "canonicalEvidenceType": "EVID_C15_CENTRE_ORDER",
        "allowedEvidenceTypes": [
          "EVID_C15_CENTRE_ORDER"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Fit India Freedom Run / Fitness Drives Conducted",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C15.6",
        "title": "Psychological Counselling Logbook Maintained (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Notifications, activity reports with photos, sports participation certificates, committee minutes",
        "canonicalEvidenceType": "EVID_C15_CENTRE_ORDER",
        "allowedEvidenceTypes": [
          "EVID_C15_CENTRE_ORDER"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Confidential Student Counselling Services Active",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "C16": {
    "code": "C16",
    "title": "Gender Parity, Safety and Inclusion Initiatives",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "FIXED_ITEM_SUM",
    "resolutionStatus": "UNRESOLVED_RULE",
    "mandatoryEvidence": [
      "EVID_C16_ICC_ORDERS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C16.1",
        "title": "Internal Complaints Committee (ICC) Constituted with Annual Filing (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "ICC annual report, workshop reports with photos, geo-tagged photos of facilities, event reports",
        "canonicalEvidenceType": "EVID_C16_ICC_ORDERS",
        "allowedEvidenceTypes": [
          "EVID_C16_ICC_ORDERS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "ICC Constituted and Annual Report Filed with Authority",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C16.2",
        "title": "Active Women Development Cell Conducts Awareness Programmes (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "ICC annual report, workshop reports with photos, geo-tagged photos of facilities, event reports",
        "canonicalEvidenceType": "EVID_C16_ICC_ORDERS",
        "allowedEvidenceTypes": [
          "EVID_C16_ICC_ORDERS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Women Cell Conducted Gender Sensitivity Drives",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C16.3",
        "title": "Campus Safety Measures & CCTV Surveillance Deployed (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "ICC annual report, workshop reports with photos, geo-tagged photos of facilities, event reports",
        "canonicalEvidenceType": "EVID_C16_ICC_ORDERS",
        "allowedEvidenceTypes": [
          "EVID_C16_ICC_ORDERS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "CCTV Coverage, Security Personnel & Helpdesks in Place",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C16.4",
        "title": "Gender Safety Audit Formally Executed (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "ICC annual report, workshop reports with photos, geo-tagged photos of facilities, event reports",
        "canonicalEvidenceType": "EVID_C16_ICC_ORDERS",
        "allowedEvidenceTypes": [
          "EVID_C16_ICC_ORDERS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Internal/External Gender Safety Audit Documented",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C16.5",
        "title": "Self-Defense Training Imparted to Female Students (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "ICC annual report, workshop reports with photos, geo-tagged photos of facilities, event reports",
        "canonicalEvidenceType": "EVID_C16_ICC_ORDERS",
        "allowedEvidenceTypes": [
          "EVID_C16_ICC_ORDERS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Organized Self-Defense Workshop Completed",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "C17": {
    "code": "C17",
    "title": "Outreach, Community Engagement and Social Responsibility",
    "maxMarks": 5.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C17_STUDENT_LIST"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C17.1",
        "title": "Percentage of Students Participating in Community Outreach / NSS / NCC / Unnat Bharat",
        "maxScore": 5.0,
        "documentaryRequirement": "Annual reports of NSS/NCC/YRC with attendance and geo-tagged photos",
        "canonicalEvidenceType": "EVID_C17_STUDENT_LIST",
        "allowedEvidenceTypes": [
          "EVID_C17_STUDENT_LIST"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "participating_students",
            "label": "Students Engaged in Community Extension Activities",
            "type": "number",
            "placeholder": "e.g. 500"
          },
          {
            "key": "total_enrolled_students",
            "label": "Total Enrolled Students in College",
            "type": "number",
            "placeholder": "e.g. 1000"
          }
        ]
      }
    ]
  },
  "C18": {
    "code": "C18",
    "title": "Sustainable Development Goals (SDGs), Green Campus and Environmental Practices",
    "maxMarks": 5.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C18_ACTIVITY_REPORTS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C18.1",
        "title": "Documented Activities Mapped to Sustainable Development Goals (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Audit reports, geo-tagged photos, bills/work orders, activity reports",
        "canonicalEvidenceType": "EVID_C18_ACTIVITY_REPORTS",
        "allowedEvidenceTypes": [
          "EVID_C18_ACTIVITY_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "sdg_activities",
            "label": "Number of Documented Activities Mapped to UN SDGs",
            "type": "number",
            "placeholder": "e.g. 5"
          }
        ]
      },
      {
        "code": "C18.2",
        "title": "Green / Energy / Environmental Audit Certified by Accredited Agency (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Audit reports, geo-tagged photos, bills/work orders, activity reports",
        "canonicalEvidenceType": "EVID_C18_ACTIVITY_REPORTS",
        "allowedEvidenceTypes": [
          "EVID_C18_ACTIVITY_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Valid Green / Energy Audit Report Available",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C18.3",
        "title": "Rooftop Solar Plant / Renewable Energy Generation Installed (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Audit reports, geo-tagged photos, bills/work orders, activity reports",
        "canonicalEvidenceType": "EVID_C18_ACTIVITY_REPORTS",
        "allowedEvidenceTypes": [
          "EVID_C18_ACTIVITY_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Solar Energy Generation Facility Operational on Campus",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C18.4",
        "title": "Waste Management & Rainwater Harvesting Infrastructure (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Audit reports, geo-tagged photos, bills/work orders, activity reports",
        "canonicalEvidenceType": "EVID_C18_ACTIVITY_REPORTS",
        "allowedEvidenceTypes": [
          "EVID_C18_ACTIVITY_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Solid/Liquid Waste Management & Rainwater Unit Active",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "C19": {
    "code": "C19",
    "title": "Research, Innovation and Patents",
    "maxMarks": 6.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "UNRESOLVED_RULE",
    "mandatoryEvidence": [
      "EVID_C19_FILING_CERTS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C19.I",
        "title": "Patents Filed during Assessment Period (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Patent application documents from Indian Patent Office or international patent offices",
        "canonicalEvidenceType": "EVID_C19_FILING_CERTS",
        "allowedEvidenceTypes": [
          "EVID_C19_FILING_CERTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "patents_filed",
            "label": "Number of Patents Filed with Official Acknowledgement",
            "type": "number",
            "placeholder": "e.g. 2"
          }
        ]
      },
      {
        "code": "C19.II",
        "title": "Patents Granted / Commercialized (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Patent publication / grant documents from Indian Patent Office or international patent offices",
        "canonicalEvidenceType": "EVID_C19_GRANT_CERTS",
        "allowedEvidenceTypes": [
          "EVID_C19_GRANT_CERTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "patents_granted",
            "label": "Number of Patents Granted / Commercialized",
            "type": "number",
            "placeholder": "e.g. 1"
          }
        ]
      },
      {
        "code": "C19.III",
        "title": "Research Publications / Scopus Indexed Output (2 Marks) [UNRESOLVED_MISSING]",
        "maxScore": 2.0,
        "documentaryRequirement": "Documentary proof required as per guidelines.",
        "canonicalEvidenceType": null,
        "allowedEvidenceTypes": [],
        "contractStatus": "UNRESOLVED_MISSING",
        "isSourceSilent": false,
        "isUnresolved": true,
        "fields": [
          {
            "key": "scopus_publications",
            "label": "Scopus Indexed Publications Count",
            "type": "number",
            "placeholder": "e.g. 5"
          }
        ]
      }
    ]
  },
  "C20": {
    "code": "C20",
    "title": "Quality Assurance, NAAC/NIRF/AISHE and Institutional Reporting",
    "maxMarks": 5.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C20_NAAC_CERT"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C20.1",
        "title": "Valid NAAC Accreditation Grade (2 Marks for A/A+/A++, 1 Mark for B/B+/B++)",
        "maxScore": 2.0,
        "documentaryRequirement": "NAAC accreditation certificate with grade",
        "canonicalEvidenceType": "EVID_C20_NAAC_CERT",
        "allowedEvidenceTypes": [
          "EVID_C20_NAAC_CERT"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Valid NAAC Grade Certificate Available",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C20.2",
        "title": "Registration / Participation in NIRF 2026 Rankings (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "NIRF submission / participation proof for latest cycle",
        "canonicalEvidenceType": "EVID_C20_NIRF_PROOF",
        "allowedEvidenceTypes": [
          "EVID_C20_NIRF_PROOF"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "NIRF 2026 Submission Acknowledgement Obtained",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C20.3",
        "title": "Timely AISHE Data Submission for Latest Cycle (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "AISHE data submitted for latest year (certificate / survey upload acknowledgement)",
        "canonicalEvidenceType": "EVID_C20_AISHE_CERT",
        "allowedEvidenceTypes": [
          "EVID_C20_AISHE_CERT"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "AISHE Certificate for 2024\u201325 Uploaded",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C20.4",
        "title": "Functional IQAC & AQAR Submission Timelines (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "IQAC established, regular meetings and AQAR submitted (IQAC minutes and AQAR submission proof)",
        "canonicalEvidenceType": "EVID_C20_IQAC_MINUTES",
        "allowedEvidenceTypes": [
          "EVID_C20_IQAC_MINUTES"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "IQAC Minutes & Latest AQAR Submission Acknowledgement",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "C21": {
    "code": "C21",
    "title": "Cultural Activities, Constitutional Values and Holistic Development",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "SOURCE_INCONSISTENCY",
    "mandatoryEvidence": [
      "EVID_C21_ACTIVITY_REPORTS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C21.1",
        "title": "National Days & Constitutional Values Observance (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Event reports with photos, prize/participation certificates, notifications",
        "canonicalEvidenceType": "EVID_C21_ACTIVITY_REPORTS",
        "allowedEvidenceTypes": [
          "EVID_C21_ACTIVITY_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "activities_count",
            "label": "Number of National Days / Constitutional Events Celebrated",
            "type": "number",
            "placeholder": "e.g. 4"
          }
        ]
      },
      {
        "code": "C21.2",
        "title": "Cultural & Heritage Activities / Youth Festival Participation (2 Marks)",
        "maxScore": 1.0,
        "documentaryRequirement": "Event reports with photos, prize/participation certificates, notifications",
        "canonicalEvidenceType": "EVID_C21_ACTIVITY_REPORTS",
        "allowedEvidenceTypes": [
          "EVID_C21_ACTIVITY_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "State/University Youth Festival Participation Documented",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "C22": {
    "code": "C22",
    "title": "Governance, Student Feedback and Evidence-Based Improvement",
    "maxMarks": 2.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_C22_NODAL_ORDER"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "C22.1",
        "title": "Dedicated NEP Implementation Cell & Nodal Officer Appointed (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Feedback analysis report, ATR copy, website link screenshot",
        "canonicalEvidenceType": "EVID_C22_NODAL_ORDER",
        "allowedEvidenceTypes": [
          "EVID_C22_NODAL_ORDER"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "NEP Implementation Cell Formally Notified",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "C22.2",
        "title": "Structured Student Feedback on NEP & Published Action Taken Report (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Feedback analysis report, ATR copy, website link screenshot",
        "canonicalEvidenceType": "EVID_C22_NODAL_ORDER",
        "allowedEvidenceTypes": [
          "EVID_C22_NODAL_ORDER"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Student Feedback Collected and ATR Uploaded on Website",
            "type": "checkbox"
          }
        ]
      }
    ]
  }
};

export const UNIVERSITY_FRAMEWORK_DATA = {
  "U1": {
    "code": "U1",
    "title": "Apprenticeship Embedded Degree Programmes",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_INSENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U1_APPROVAL"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U1.1",
        "title": "Number of Degree Programmes with Embedded Apprenticeship / Internship",
        "maxScore": 4.0,
        "documentaryRequirement": "Approval by statutory bodies (BoS, AC, EC) and copy of curriculum with apprenticeship embedded",
        "canonicalEvidenceType": "EVID_U1_APPROVAL",
        "allowedEvidenceTypes": [
          "EVID_U1_APPROVAL"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "programmes_count",
            "label": "Degree Programmes with Apprenticeship Embedded",
            "type": "number",
            "placeholder": "e.g. 12"
          }
        ]
      }
    ]
  },
  "U2": {
    "code": "U2",
    "title": "Courses Offered in Indian Languages",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_INSENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U2_COURSE_LIST"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U2.1",
        "title": "Percentage of Degree Programmes Offered / Supported in Indian Languages",
        "maxScore": 4.0,
        "documentaryRequirement": "Curriculum, scheme of examination, BoS/Academic council approval",
        "canonicalEvidenceType": "EVID_U2_COURSE_LIST",
        "allowedEvidenceTypes": [
          "EVID_U2_COURSE_LIST"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "indian_lang_programmes",
            "label": "Programmes with Bilingual / Indian Language Support",
            "type": "number",
            "placeholder": "e.g. 35"
          },
          {
            "key": "total_degree_programmes",
            "label": "Total Regular Degree Programmes Offered",
            "type": "number",
            "placeholder": "e.g. 45"
          }
        ]
      }
    ]
  },
  "U3": {
    "code": "U3",
    "title": "Integration of Indian Knowledge Systems (IKS)",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_INSENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U3_SYLLABUS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U3.1",
        "title": "Percentage of Degree Programmes with Meaningfully Integrated IKS Components",
        "maxScore": 4.0,
        "documentaryRequirement": "Curriculum documents highlighting IKS integration, BoS/Academic Council approvals, course completion data",
        "canonicalEvidenceType": "EVID_U3_SYLLABUS",
        "allowedEvidenceTypes": [
          "EVID_U3_SYLLABUS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "iks_programmes",
            "label": "Programmes Integrating Indian Knowledge Systems",
            "type": "number",
            "placeholder": "e.g. 15"
          },
          {
            "key": "total_degree_programmes",
            "label": "Total Regular Degree Programmes Offered",
            "type": "number",
            "placeholder": "e.g. 50"
          }
        ]
      }
    ]
  },
  "U4": {
    "code": "U4",
    "title": "Targets Achieved under Institutional Development Plan (IDP)",
    "maxMarks": 6.0,
    "periodRule": "MULTI_PERIOD",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [],
    "allowedEvidence": [
      "EVID_U4_IDP",
      "EVID_U4_TARGET_SHEET",
      "EVID_U4_PROGRESS_REPORT"
    ],
    "subcriteria": [
      {
        "code": "U4.A",
        "title": "IDP Target Achievement Rate for Academic Year 2024\u201325 (3 Marks)",
        "maxScore": 3.0,
        "documentaryRequirement": "Copy of IDP with target sheet, Progress report approved by competent authority",
        "canonicalEvidenceType": "EVID_U4_PROGRESS_REPORT",
        "allowedEvidenceTypes": [
          "EVID_U4_PROGRESS_REPORT",
          "EVID_U4_IDP",
          "EVID_U4_TARGET_SHEET"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "achieved_targets_2024_25",
            "label": "Targets Achieved (2024\u201325)",
            "type": "number",
            "placeholder": "e.g. 85"
          },
          {
            "key": "fixed_targets_2024_25",
            "label": "Targets Fixed in IDP (2024\u201325)",
            "type": "number",
            "placeholder": "e.g. 100"
          }
        ]
      },
      {
        "code": "U4.B",
        "title": "IDP Target Achievement Rate for Academic Year 2025\u201326 (3 Marks)",
        "maxScore": 3.0,
        "documentaryRequirement": "Copy of IDP with target sheet, Progress report approved by competent authority",
        "canonicalEvidenceType": "EVID_U4_PROGRESS_REPORT",
        "allowedEvidenceTypes": [
          "EVID_U4_PROGRESS_REPORT",
          "EVID_U4_IDP",
          "EVID_U4_TARGET_SHEET"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "achieved_targets_2025_26",
            "label": "Targets Achieved (2025\u201326)",
            "type": "number",
            "placeholder": "e.g. 90"
          },
          {
            "key": "fixed_targets_2025_26",
            "label": "Targets Fixed in IDP (2025\u201326)",
            "type": "number",
            "placeholder": "e.g. 100"
          }
        ]
      }
    ]
  },
  "U5": {
    "code": "U5",
    "title": "Percentage of Students Who Received Placement / Pre-Placement Offers",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "BOUNDARY_UNRESOLVED",
    "mandatoryEvidence": [
      "EVID_U5_HOI_CERT"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U5.A",
        "title": "Percentage of Total Graduating Students Eligible for Placement Drives (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Placement cell records, offer letters, summary certified by Head of Institution",
        "canonicalEvidenceType": "EVID_U5_HOI_CERT",
        "allowedEvidenceTypes": [
          "EVID_U5_HOI_CERT"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "eligible_students",
            "label": "Students Meeting Placement Eligibility Criteria",
            "type": "number",
            "placeholder": "e.g. 800"
          },
          {
            "key": "total_graduating_students",
            "label": "Total Graduating Class Strength",
            "type": "number",
            "placeholder": "e.g. 1000"
          }
        ]
      },
      {
        "code": "U5.B",
        "title": "Percentage of Eligible Students Securing Placement / PPO Offers (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Placement cell records, offer letters, summary certified by Head of Institution",
        "canonicalEvidenceType": "EVID_U5_HOI_CERT",
        "allowedEvidenceTypes": [
          "EVID_U5_HOI_CERT"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "placed_students",
            "label": "Students Receiving Placement or Pre-Placement Offers",
            "type": "number",
            "placeholder": "e.g. 650"
          },
          {
            "key": "eligible_students",
            "label": "Total Eligible Placement Candidates",
            "type": "number",
            "placeholder": "e.g. 800"
          }
        ]
      }
    ]
  },
  "U6": {
    "code": "U6",
    "title": "Academic Reforms",
    "maxMarks": 8.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U6_ORDINANCE_GAZETTE"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U6.A",
        "title": "Academic Council / EC Ordinance Notification for Exam Reforms (4 Marks)",
        "maxScore": 4.0,
        "documentaryRequirement": "Source silent: No documentary evidence required by council specification.",
        "canonicalEvidenceType": null,
        "allowedEvidenceTypes": [],
        "contractStatus": "SOURCE_SILENT",
        "isSourceSilent": true,
        "isUnresolved": false,
        "fields": [
          {
            "key": "ordinance_notified",
            "label": "Ordinance Gazette / Academic Council Approval in Place",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U6.B",
        "title": "Pedagogical Interventions & Digital Tools Implemented (4 Marks)",
        "maxScore": 4.0,
        "documentaryRequirement": "Source silent: No documentary evidence required by council specification.",
        "canonicalEvidenceType": null,
        "allowedEvidenceTypes": [],
        "contractStatus": "SOURCE_SILENT",
        "isSourceSilent": true,
        "isUnresolved": false,
        "fields": [
          {
            "key": "tools_count",
            "label": "Count of Documented Pedagogical / Evaluation Interventions",
            "type": "number",
            "placeholder": "e.g. 4"
          }
        ]
      }
    ]
  },
  "U7": {
    "code": "U7",
    "title": "Professor of Practice (PoP) Engagement",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "FIXED_ITEM_SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U7_APPOINTMENT"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U7.1",
        "title": "Formal Notification & Selection of Professor of Practice (PoP) (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Notification/Guidelines, Selection committee minutes, Appointment orders, Service agreements",
        "canonicalEvidenceType": "EVID_U7_APPOINTMENT",
        "allowedEvidenceTypes": [
          "EVID_U7_APPOINTMENT"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "PoPs Formally Appointed per UGC Guidelines",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U7.2",
        "title": "Active Teaching & Course Delivery by PoP (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Teaching logs, workload delivery records, minimum 40 hours interaction records",
        "canonicalEvidenceType": "EVID_U7_TEACHING_LOGS",
        "allowedEvidenceTypes": [
          "EVID_U7_TEACHING_LOGS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Course Allotment and Lecture Delivery Logs Verified",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U7.3",
        "title": "Workshops, Seminars & Curriculum Reviews Led by PoP (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Workshop reports, training session attendance, feedback records conducted by PoP",
        "canonicalEvidenceType": "EVID_U7_WORKSHOP_REPORTS",
        "allowedEvidenceTypes": [
          "EVID_U7_WORKSHOP_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Technical Workshops / BOS Sessions Conducted by PoP",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U7.4",
        "title": "Real-World Industrial Projects & Mentorship Guided by PoP (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Real-world project reports, industry problem-solving outcomes driven by PoP",
        "canonicalEvidenceType": "EVID_U7_PROJECT_REPORTS",
        "allowedEvidenceTypes": [
          "EVID_U7_PROJECT_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Student Projects or Industry Problem Solving Mentored",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "U8": {
    "code": "U8",
    "title": "Incubation / Startup Cell Performance as per NISP",
    "maxMarks": 6.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "COMPOSITE",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U8_INCUBATION_REG"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U8.A",
        "title": "Startups / Companies Registered & Incubated under NISP (4 Marks)",
        "maxScore": 4.0,
        "documentaryRequirement": "Incubation cell registration, list of incubated startups, proof of funds/revenue",
        "canonicalEvidenceType": "EVID_U8_INCUBATION_REG",
        "allowedEvidenceTypes": [
          "EVID_U8_INCUBATION_REG"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "startups_count",
            "label": "Count of Incubated Startups (July 2025 \u2013 June 2026)",
            "type": "number",
            "placeholder": "e.g. 12"
          }
        ]
      },
      {
        "code": "U8.B",
        "title": "Commercialized / Revenue Generating Incubated Startups (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Incubation cell registration, list of incubated startups, proof of funds/revenue",
        "canonicalEvidenceType": "EVID_U8_INCUBATION_REG",
        "allowedEvidenceTypes": [
          "EVID_U8_INCUBATION_REG"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "commercialized_count",
            "label": "Count of Startups Generating Revenue / Funding",
            "type": "number",
            "placeholder": "e.g. 6"
          }
        ]
      }
    ]
  },
  "U9": {
    "code": "U9",
    "title": "Academic / Research Collaboration with Foreign HEIs",
    "maxMarks": 6.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "COMPOSITE",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U9_MOU"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U9.A",
        "title": "Percentage of Foreign HEI Collaborations with QS Top 500 Institutions (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "MoUs with QS top 500, Activity reports, Student/faculty exchange records, joint research output",
        "canonicalEvidenceType": "EVID_U9_MOU",
        "allowedEvidenceTypes": [
          "EVID_U9_MOU"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "qs500_collaborations",
            "label": "MoUs with QS Top 500 Universities",
            "type": "number",
            "placeholder": "e.g. 3"
          },
          {
            "key": "total_foreign_mous",
            "label": "Total Active Foreign MoUs",
            "type": "number",
            "placeholder": "e.g. 5"
          }
        ]
      },
      {
        "code": "U9.B",
        "title": "Average Demonstrable Activities Conducted per Foreign MoU (5 Marks)",
        "maxScore": 5.0,
        "documentaryRequirement": "MoUs with QS top 500, Activity reports, Student/faculty exchange records, joint research output",
        "canonicalEvidenceType": "EVID_U9_MOU",
        "allowedEvidenceTypes": [
          "EVID_U9_MOU"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "activities_count",
            "label": "Total Documented Activities Across Active Foreign MoUs",
            "type": "number",
            "placeholder": "e.g. 15"
          }
        ]
      }
    ]
  },
  "U10": {
    "code": "U10",
    "title": "Functional Alumni Connect Cell",
    "maxMarks": 5.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "BOUNDARY_UNRESOLVED",
    "mandatoryEvidence": [
      "EVID_U10_REG_CERT"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U10.1",
        "title": "Alumni Association Registered under Societies Act (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Registration certificate under Societies Registration Act",
        "canonicalEvidenceType": "EVID_U10_REG_CERT",
        "allowedEvidenceTypes": [
          "EVID_U10_REG_CERT"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Alumni Association Legally Registered",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U10.2",
        "title": "Functional Online Alumni Portal & Updated Database Maintained (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Functional alumni portal screenshots, verified database records",
        "canonicalEvidenceType": "EVID_U10_PORTAL_PROOF",
        "allowedEvidenceTypes": [
          "EVID_U10_PORTAL_PROOF"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Digital Portal Active with Graduate Records",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U10.3",
        "title": "Funding Received from Alumni during Evaluation Period (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Audited accounts of alumni fund, bank statements, contribution receipts (>Rs. 1 Crore)",
        "canonicalEvidenceType": "EVID_U10_FINANCIAL_RECORDS",
        "allowedEvidenceTypes": [
          "EVID_U10_FINANCIAL_RECORDS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "funding_amount",
            "label": "Total Alumni Donations / Funding (in INR)",
            "type": "number",
            "placeholder": "e.g. 12000000"
          }
        ]
      },
      {
        "code": "U10.4",
        "title": "Distinguished Alumni Guest Lectures & Academic Engagement (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Event reports, guest lecture records of distinguished alumni invited",
        "canonicalEvidenceType": "EVID_U10_EVENT_REPORTS",
        "allowedEvidenceTypes": [
          "EVID_U10_EVENT_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Documented Sessions Conducted by Alumni",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "U11": {
    "code": "U11",
    "title": "Gender Parity Initiatives",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "FIXED_ITEM_SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U11_BOARDS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U11.1",
        "title": "ICC Constituted with Regular Meetings & Annual Report Filed (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "ICC annual report, training attendance, mentorship logs, facility photos",
        "canonicalEvidenceType": "EVID_U11_BOARDS",
        "allowedEvidenceTypes": [
          "EVID_U11_BOARDS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "ICC Statutory Compliance Verified",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U11.2",
        "title": "Women Cell / Centre for Women Studies Active with Awareness Programmes (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "ICC annual report, training attendance, mentorship logs, facility photos",
        "canonicalEvidenceType": "EVID_U11_BOARDS",
        "allowedEvidenceTypes": [
          "EVID_U11_BOARDS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Gender Sensitization & Leadership Workshops Conducted",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U11.3",
        "title": "Campus Security, Well-Lit Pathways & Surveillance Infrastructure (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "ICC annual report, training attendance, mentorship logs, facility photos",
        "canonicalEvidenceType": "EVID_U11_BOARDS",
        "allowedEvidenceTypes": [
          "EVID_U11_BOARDS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Campus Safety Measures & CCTV Deployed",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U11.4",
        "title": "Gender Safety Audit Formally Executed with Action Plan (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "ICC annual report, training attendance, mentorship logs, facility photos",
        "canonicalEvidenceType": "EVID_U11_BOARDS",
        "allowedEvidenceTypes": [
          "EVID_U11_BOARDS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Safety Audit Conducted and Recommendations Implemented",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "U12": {
    "code": "U12",
    "title": "Physical Fitness, Sports, Yoga, Health, Welfare, Psychological Well-being",
    "maxMarks": 5.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "FIXED_ITEM_SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U12_CENTRE_NOTIF"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U12.1",
        "title": "Mental Health & Well-being Centre (MHWBC) / Student Service Centre Established (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Counsellor appointment, health camp reports, event photos, sports inventory",
        "canonicalEvidenceType": "EVID_U12_CENTRE_NOTIF",
        "allowedEvidenceTypes": [
          "EVID_U12_CENTRE_NOTIF"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "MHWBC Established with Regular Counselling Services",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U12.2",
        "title": "Sports Complex, Gymnasium & Fitness Facilities Maintained (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Counsellor appointment, health camp reports, event photos, sports inventory",
        "canonicalEvidenceType": "EVID_U12_CENTRE_NOTIF",
        "allowedEvidenceTypes": [
          "EVID_U12_CENTRE_NOTIF"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "High-Quality Sports Infrastructure Accessible to Students",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U12.3",
        "title": "Yoga, Meditation & Holistic Health Activities Conducted (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Counsellor appointment, health camp reports, event photos, sports inventory",
        "canonicalEvidenceType": "EVID_U12_CENTRE_NOTIF",
        "allowedEvidenceTypes": [
          "EVID_U12_CENTRE_NOTIF"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Regular Yoga Sessions & Stress-Relief Workshops Organized",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U12.4",
        "title": "Periodic Health Checkup & Blood Donation Camps Organised (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Counsellor appointment, health camp reports, event photos, sports inventory",
        "canonicalEvidenceType": "EVID_U12_CENTRE_NOTIF",
        "allowedEvidenceTypes": [
          "EVID_U12_CENTRE_NOTIF"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Medical Camps Conducted in Partnership with Health Centres",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U12.5",
        "title": "Fit India Movement / Khelo India University Campaigns Implemented (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Counsellor appointment, health camp reports, event photos, sports inventory",
        "canonicalEvidenceType": "EVID_U12_CENTRE_NOTIF",
        "allowedEvidenceTypes": [
          "EVID_U12_CENTRE_NOTIF"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Campus-Wide Participation in National Sports Campaigns",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "U13": {
    "code": "U13",
    "title": "Online Courses / MOOCs Policy and Adoption",
    "maxMarks": 6.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "MAX",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U13_POLICY"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U13.1",
        "title": "Percentage of Regular Students Earning Credits through SWAYAM / MOOCs",
        "maxScore": 6.0,
        "documentaryRequirement": "Policy notification, credit transfer notifications, SWAYAM certificates",
        "canonicalEvidenceType": "EVID_U13_POLICY",
        "allowedEvidenceTypes": [
          "EVID_U13_POLICY"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "regular_mooc_learners",
            "label": "Regular Students Earning SWAYAM/MOOC Credits",
            "type": "number",
            "placeholder": "e.g. 1500"
          },
          {
            "key": "total_regular_learners",
            "label": "Total Regular Enrolled Students in University",
            "type": "number",
            "placeholder": "e.g. 5000"
          }
        ]
      }
    ]
  },
  "U14": {
    "code": "U14",
    "title": "Multidisciplinary Education",
    "maxMarks": 6.0,
    "periodRule": "PERIOD_INSENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U14_CURRICULUM"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U14.A",
        "title": "Percentage of Degree Programmes with Major-Minor & Flexible Choices (4 Marks)",
        "maxScore": 4.0,
        "documentaryRequirement": "Ordinances, course syllabi, curriculum structure showing credit-bearing courses",
        "canonicalEvidenceType": "EVID_U14_CURRICULUM",
        "allowedEvidenceTypes": [
          "EVID_U14_CURRICULUM"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "multidisciplinary_programmes",
            "label": "Programmes Offering Major-Minor / Open Electives",
            "type": "number",
            "placeholder": "e.g. 42"
          },
          {
            "key": "total_programmes",
            "label": "Total Regular Degree Programmes Offered",
            "type": "number",
            "placeholder": "e.g. 45"
          }
        ]
      },
      {
        "code": "U14.B",
        "title": "Embedding of Physical Education / Sports / Yogasan in Curriculum (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Ordinances, course syllabi, curriculum structure showing credit-bearing courses",
        "canonicalEvidenceType": "EVID_U14_CURRICULUM",
        "allowedEvidenceTypes": [
          "EVID_U14_CURRICULUM"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Credit-Bearing Sports/Yoga Modules Embedded in Degree Syllabi",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U14.C",
        "title": "Embedding of Industry-Aligned Value-Added Courses (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Ordinances, course syllabi, curriculum structure showing credit-bearing courses",
        "canonicalEvidenceType": "EVID_U14_CURRICULUM",
        "allowedEvidenceTypes": [
          "EVID_U14_CURRICULUM"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Industry-Endorsed Specializations Embedded",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "U15": {
    "code": "U15",
    "title": "Multiple Entry-Exit Operationalized",
    "maxMarks": 2.0,
    "periodRule": "PERIOD_INSENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U15_ORDINANCE"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U15.1",
        "title": "Multiple Entry-Exit Regulatory Guidelines Formally Approved & Notified (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Approved guidelines/ordinance, list of students awarded exit certificates",
        "canonicalEvidenceType": "EVID_U15_ORDINANCE",
        "allowedEvidenceTypes": [
          "EVID_U15_ORDINANCE"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Statutory Academic Council & Executive Council Approvals Notified",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U15.2",
        "title": "Certificates / Diplomas Formally Conferred to Exit Candidates (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Approved guidelines/ordinance, list of students awarded exit certificates",
        "canonicalEvidenceType": "EVID_U15_ORDINANCE",
        "allowedEvidenceTypes": [
          "EVID_U15_ORDINANCE"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Exit Credentials Awarded with ABC Credit Portability",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "U16": {
    "code": "U16",
    "title": "Research Outcome: Patents Filed and Granted",
    "maxMarks": 8.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "UNRESOLVED_RULE",
    "mandatoryEvidence": [
      "EVID_U16_FILING"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U16.I",
        "title": "Number of Patents Filed by Faculty / Research Scholars (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Patent filing receipts from Indian Patent Office",
        "canonicalEvidenceType": "EVID_U16_FILING",
        "allowedEvidenceTypes": [
          "EVID_U16_FILING"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "patents_filed",
            "label": "Count of Patents Filed in Evaluation Period",
            "type": "number",
            "placeholder": "e.g. 10"
          }
        ]
      },
      {
        "code": "U16.II",
        "title": "Number of Patents Granted / Commercialized / Licensed (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Patent grant certificates / technology transfer agreements",
        "canonicalEvidenceType": "EVID_U16_GRANT",
        "allowedEvidenceTypes": [
          "EVID_U16_GRANT"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "patents_granted",
            "label": "Count of Patents Granted or Commercialized",
            "type": "number",
            "placeholder": "e.g. 4"
          }
        ]
      },
      {
        "code": "U16.III",
        "title": "Scopus-Indexed Publications during Evaluation Period (4 Marks) [UNRESOLVED_MISSING]",
        "maxScore": 4.0,
        "documentaryRequirement": "Documentary proof required as per guidelines.",
        "canonicalEvidenceType": null,
        "allowedEvidenceTypes": [],
        "contractStatus": "UNRESOLVED_MISSING",
        "isSourceSilent": false,
        "isUnresolved": true,
        "fields": [
          {
            "key": "scopus_publications",
            "label": "Count of Scopus Publications",
            "type": "number",
            "placeholder": "e.g. 150"
          }
        ]
      }
    ]
  },
  "U17": {
    "code": "U17",
    "title": "Registration and Performance in NIRF",
    "maxMarks": 2.0,
    "periodRule": "REFERENCE_YEAR_DEPENDENT",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U17_NIRF_2026_PROOF"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U17.1",
        "title": "Timely Registration & Data Submission for NIRF 2026 Rankings (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Proof of submission / acknowledgement of NIRF 2026",
        "canonicalEvidenceType": "EVID_U17_NIRF_2026_PROOF",
        "allowedEvidenceTypes": [
          "EVID_U17_NIRF_2026_PROOF"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "NIRF 2026 Participation Acknowledgement Obtained",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U17.2",
        "title": "Ranked in Top 100 or Placed in Official Rank Band in NIRF 2025 (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Official NIRF 2025 ranking certificate / gazette / rank card",
        "canonicalEvidenceType": "EVID_U17_NIRF_2025_RANK",
        "allowedEvidenceTypes": [
          "EVID_U17_NIRF_2025_RANK"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Secured Top 100 or Rank Band in NIRF 2025",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "U18": {
    "code": "U18",
    "title": "Recognition of Prior Learning (RPL) Adoption and Implementation",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U18_POLICY"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U18.1",
        "title": "Institutional Recognition of Prior Learning (RPL) Policy Approved (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Approved institutional RPL policy/guidelines",
        "canonicalEvidenceType": "EVID_U18_POLICY",
        "allowedEvidenceTypes": [
          "EVID_U18_POLICY"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "RPL Regulatory Framework Passed by Academic Council",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U18.2",
        "title": "Learners Formally Assessed & Awarded Credits under RPL (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Certificates issued to learners under RPL",
        "canonicalEvidenceType": "EVID_U18_LEARNER_CERTS",
        "allowedEvidenceTypes": [
          "EVID_U18_LEARNER_CERTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Credit Certificates Conferred to RPL Candidates",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U18.3",
        "title": "Workshops / Capacity Building Conducted on RPL (2 Marks) [UNRESOLVED_MISSING]",
        "maxScore": 2.0,
        "documentaryRequirement": "Documentary proof required as per guidelines.",
        "canonicalEvidenceType": null,
        "allowedEvidenceTypes": [],
        "contractStatus": "UNRESOLVED_MISSING",
        "isSourceSilent": false,
        "isUnresolved": true,
        "fields": [
          {
            "key": "verified",
            "label": "Stakeholder RPL Sensitization Workshops Held",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "U19": {
    "code": "U19",
    "title": "Adoption of Outcome-Based Education (OBE)",
    "maxMarks": 8.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "CALCULABLE",
    "mandatoryEvidence": [
      "EVID_U19_OBE_FRAMEWORK"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U19.A",
        "title": "Percentage of Programmes with Full Course & Programme Outcome (CO-PO) Mapping (6 Marks)",
        "maxScore": 6.0,
        "documentaryRequirement": "Curriculum with OBE mappings, sample attainment sheets, sample question papers with Bloom levels certified by CoE",
        "canonicalEvidenceType": "EVID_U19_OBE_FRAMEWORK",
        "allowedEvidenceTypes": [
          "EVID_U19_OBE_FRAMEWORK"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "obe_programmes",
            "label": "Programmes with Documented CO-PO Attainment",
            "type": "number",
            "placeholder": "e.g. 40"
          },
          {
            "key": "total_programmes",
            "label": "Total Regular Degree Programmes Offered",
            "type": "number",
            "placeholder": "e.g. 45"
          }
        ]
      },
      {
        "code": "U19.B",
        "title": "Examination Question Papers Mapped to Bloom's Taxonomy & COs (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Curriculum with OBE mappings, sample attainment sheets, sample question papers with Bloom levels certified by CoE",
        "canonicalEvidenceType": "EVID_U19_OBE_FRAMEWORK",
        "allowedEvidenceTypes": [
          "EVID_U19_OBE_FRAMEWORK"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Sample Question Papers Certified with Bloom Levels by CoE",
            "type": "checkbox"
          }
        ]
      }
    ]
  },
  "U20": {
    "code": "U20",
    "title": "Activities Aligned with Sustainable Development Goals (SDGs)",
    "maxMarks": 4.0,
    "periodRule": "PERIOD_SENSITIVE",
    "aggregationStrategy": "SUM",
    "resolutionStatus": "SOURCE_INCONSISTENCY",
    "mandatoryEvidence": [
      "EVID_U20_ACTIVITY_REPORTS"
    ],
    "allowedEvidence": [],
    "subcriteria": [
      {
        "code": "U20.1",
        "title": "Number of Documented Activities Mapped to Sustainable Development Goals (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Activity reports with geo-tagged photos for community/environmental activities mapped to SDGs",
        "canonicalEvidenceType": "EVID_U20_ACTIVITY_REPORTS",
        "allowedEvidenceTypes": [
          "EVID_U20_ACTIVITY_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "activities_count",
            "label": "Count of Geo-Tagged Activities Mapped to UN SDGs",
            "type": "number",
            "placeholder": "e.g. 12"
          }
        ]
      },
      {
        "code": "U20.2",
        "title": "University Curriculum Mapped to UN Sustainable Development Goals (2 Marks)",
        "maxScore": 2.0,
        "documentaryRequirement": "Curriculum mapping document to SDGs",
        "canonicalEvidenceType": "EVID_U20_CURRICULUM_MAP",
        "allowedEvidenceTypes": [
          "EVID_U20_CURRICULUM_MAP",
          "EVID_U20_ACTIVITY_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Formally Mapped SDG Academic Courses Verified",
            "type": "checkbox"
          }
        ]
      },
      {
        "code": "U20.3",
        "title": "Annual Sustainability / Green Audit Report Published on Portal (1 Mark)",
        "maxScore": 1.0,
        "documentaryRequirement": "Published annual sustainability report",
        "canonicalEvidenceType": "EVID_U20_SUSTAINABILITY_REPORT",
        "allowedEvidenceTypes": [
          "EVID_U20_SUSTAINABILITY_REPORT",
          "EVID_U20_ACTIVITY_REPORTS"
        ],
        "contractStatus": "ACTIVE",
        "isSourceSilent": false,
        "isUnresolved": false,
        "fields": [
          {
            "key": "verified",
            "label": "Comprehensive Sustainability Report Certified & Published",
            "type": "checkbox"
          }
        ]
      }
    ]
  }
};

/**
 * Returns authoritative parameter title
 */
export function getParameterTitle(framework, parameterId) {
  const cleanId = String(parameterId || "").trim().toUpperCase();
  const isCollege = String(framework || "").toUpperCase().includes("COLLEGE") || cleanId.startsWith("C");
  if (isCollege) {
    return COLLEGE_PARAMETER_TITLES[cleanId] || `Parameter ${cleanId}`;
  }
  return UNIVERSITY_PARAMETER_TITLES[cleanId] || `Parameter ${cleanId}`;
}

/**
 * Returns authoritative subcriterion title
 */
export function getSubcriterionTitle(subcriterionId, fallbackParamTitle = "") {
  const cleanSub = String(subcriterionId || "").trim().toUpperCase();
  if (cleanSub.startsWith("C")) {
    const pCode = cleanSub.split(".")[0];
    const pData = COLLEGE_FRAMEWORK_DATA[pCode];
    if (pData && Array.isArray(pData.subcriteria)) {
      const sub = pData.subcriteria.find((s) => s.code === cleanSub);
      if (sub) return sub.title;
    }
  } else if (cleanSub.startsWith("U")) {
    const pCode = cleanSub.split(".")[0];
    const pData = UNIVERSITY_FRAMEWORK_DATA[pCode];
    if (pData && Array.isArray(pData.subcriteria)) {
      const sub = pData.subcriteria.find((s) => s.code === cleanSub);
      if (sub) return sub.title;
    }
  }
  return `Subcriterion ${cleanSub}${fallbackParamTitle ? ` — ${fallbackParamTitle}` : ""}`;
}

/**
 * Returns authoritative subcriterion contract metadata
 */
export function getSubcriterionContract(framework, parameterId, subcriterionId) {
  const cleanP = String(parameterId || "").trim().toUpperCase();
  const cleanS = String(subcriterionId || "").trim().toUpperCase();
  const isCollege = String(framework || "").toUpperCase().includes("COLLEGE") || cleanP.startsWith("C");
  const fwData = isCollege ? COLLEGE_FRAMEWORK_DATA : UNIVERSITY_FRAMEWORK_DATA;
  const pData = fwData[cleanP];
  if (!pData || !Array.isArray(pData.subcriteria)) return null;
  return pData.subcriteria.find((s) => s.code === cleanS) || null;
}
