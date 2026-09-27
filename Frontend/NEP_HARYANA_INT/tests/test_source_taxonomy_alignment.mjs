import test from 'node:test';
import assert from 'node:assert/strict';
import {
  COLLEGE_PARAMETER_CODES,
  UNIVERSITY_PARAMETER_CODES,
  COLLEGE_PARAMETER_TITLES,
  UNIVERSITY_PARAMETER_TITLES,
  COLLEGE_FRAMEWORK_DATA,
  UNIVERSITY_FRAMEWORK_DATA,
  UNRESOLVED_SPEC_NOTICES,
  getParameterTitle,
  getSubcriterionTitle,
  getSubcriterionContract,
} from '../src/utils/nepTaxonomy.js';

test('NEP 2026 Source Taxonomy Alignment Suite', async (t) => {
  await t.test('1. Parameter Counts & Code Invariants', () => {
    // College = 22
    assert.equal(COLLEGE_PARAMETER_CODES.length, 22, 'College parameter count must be exactly 22');
    const expectedColCodes = Array.from({ length: 22 }, (_, i) => `C${i + 1}`);
    assert.deepEqual(COLLEGE_PARAMETER_CODES, expectedColCodes, 'College codes must strictly be C1 through C22');

    // University = 20
    assert.equal(UNIVERSITY_PARAMETER_CODES.length, 20, 'University parameter count must be exactly 20');
    const expectedUniCodes = Array.from({ length: 20 }, (_, i) => `U${i + 1}`);
    assert.deepEqual(UNIVERSITY_PARAMETER_CODES, expectedUniCodes, 'University codes must strictly be U1 through U20');

    // No duplicates
    assert.equal(new Set(COLLEGE_PARAMETER_CODES).size, 22, 'No duplicate College codes allowed');
    assert.equal(new Set(UNIVERSITY_PARAMETER_CODES).size, 20, 'No duplicate University codes allowed');

    // Framework Isolation
    assert.ok(COLLEGE_PARAMETER_CODES.every((c) => c.startsWith('C')), 'All College codes must start with C');
    assert.ok(!COLLEGE_PARAMETER_CODES.some((c) => c.startsWith('U')), 'No University codes allowed in College');
    assert.ok(UNIVERSITY_PARAMETER_CODES.every((u) => u.startsWith('U')), 'All University codes must start with U');
    assert.ok(!UNIVERSITY_PARAMETER_CODES.some((u) => u.startsWith('C')), 'No College codes allowed in University');
  });

  await t.test('2. College Authoritative Parameter Titles Alignment', () => {
    // Verify exact title alignment against authoritative PDF / NEP Excellence Awards 2026
    const expectedTitles = {
      C1: "Institutional Development Plan (IDP) and NEP Implementation Targets",
      C2: "Apprenticeship / Internships",
      C3: "Academic Bank of Credits (ABC) Registration",
      C4: "Supporting Other Institutes and Schools in Their Development",
      C5: "Student Enrollment against Sanctioned Seats",
      C6: "VAC, AEC, SEC, NSQF-Aligned Courses and Short-Term Certifications",
      C7: "Bridge Courses for SEDGs",
      C8: "Nomination of NEP-SARTHI",
      C9: "Student Career Orientation and Placements",
      C10: "Industry Collaboration, MoUs and Industry-Aligned Academic Activities",
      C11: "Incubation, Startup Cell and Entrepreneurship Promotion",
      C12: "Alumni Connect and External Expert Engagement",
      C13: "Faculty Development and NEP Orientation",
      C14: "Indian Languages and Indian Knowledge System (IKS)",
      C15: "Student Well-being, Physical Fitness, Yoga and Sports",
      C16: "Gender Parity, Safety and Inclusion Initiatives",
      C17: "Outreach, Community Engagement and Social Responsibility",
      C18: "Sustainable Development Goals (SDGs), Green Campus and Environmental Practices",
      C19: "Research, Innovation and Patents",
      C20: "Quality Assurance, NAAC/NIRF/AISHE and Institutional Reporting",
      C21: "Cultural Activities, Constitutional Values and Holistic Development",
      C22: "Governance, Student Feedback and Evidence-Based Improvement",
    };

    for (const [code, expectedTitle] of Object.entries(expectedTitles)) {
      assert.equal(COLLEGE_PARAMETER_TITLES[code], expectedTitle, `College ${code} title mismatch`);
      assert.equal(COLLEGE_FRAMEWORK_DATA[code]?.title, expectedTitle, `College data ${code} title mismatch`);
      assert.equal(getParameterTitle('COLLEGE_2026', code), expectedTitle);
    }

    // Explicit Anti-Regression: Must fail if C1 is reverted to incorrect rubric
    assert.notEqual(COLLEGE_PARAMETER_TITLES.C1, "Admissions Against Sanctioned Intake");
    assert.notEqual(COLLEGE_PARAMETER_TITLES.C10, "Placement and Higher Education Progression");
    assert.notEqual(COLLEGE_PARAMETER_TITLES.C19, "Digital Infrastructure and ICT Enablement");
  });

  await t.test('3. University Authoritative Parameter Titles Alignment', () => {
    // Verify exact title alignment against authoritative PDF / NEP Excellence Awards 2026
    const expectedTitles = {
      U1: "Apprenticeship Embedded Degree Programmes",
      U2: "Courses Offered in Indian Languages",
      U3: "Integration of Indian Knowledge Systems (IKS)",
      U4: "Targets Achieved under Institutional Development Plan (IDP)",
      U5: "Percentage of Students Who Received Placement / Pre-Placement Offers",
      U6: "Academic Reforms",
      U7: "Professor of Practice (PoP) Engagement",
      U8: "Incubation / Startup Cell Performance as per NISP",
      U9: "Academic / Research Collaboration with Foreign HEIs",
      U10: "Functional Alumni Connect Cell",
      U11: "Gender Parity Initiatives",
      U12: "Physical Fitness, Sports, Yoga, Health, Welfare, Psychological Well-being",
      U13: "Online Courses / MOOCs Policy and Adoption",
      U14: "Multidisciplinary Education",
      U15: "Multiple Entry-Exit Operationalized",
      U16: "Research Outcome: Patents Filed and Granted",
      U17: "Registration and Performance in NIRF",
      U18: "Recognition of Prior Learning (RPL) Adoption and Implementation",
      U19: "Adoption of Outcome-Based Education (OBE)",
      U20: "Activities Aligned with Sustainable Development Goals (SDGs)",
    };

    for (const [code, expectedTitle] of Object.entries(expectedTitles)) {
      assert.equal(UNIVERSITY_PARAMETER_TITLES[code], expectedTitle, `University ${code} title mismatch`);
      assert.equal(UNIVERSITY_FRAMEWORK_DATA[code]?.title, expectedTitle, `University data ${code} title mismatch`);
      assert.equal(getParameterTitle('UNIVERSITY_2026', code), expectedTitle);
    }

    // Explicit Anti-Regression: Must fail if U1 is reverted to incorrect rubric
    assert.notEqual(UNIVERSITY_PARAMETER_TITLES.U1, "Curriculum Alignment with NEP 2020");
    assert.notEqual(UNIVERSITY_PARAMETER_TITLES.U5, "Student Diversity, Inclusivity and Support Systems");
  });

  await t.test('4. College Subcriteria Structure & Component Codes Alignment', () => {
    const expectedCollegeSubs = {
      C1: ["C1.1"],
      C2: ["C2.1"],
      C3: ["C3.1"],
      C4: ["C4.A", "C4.B"],
      C5: ["C5.1"],
      C6: ["C6.1"],
      C7: ["C7.1"],
      C8: ["C8.1"],
      C9: ["C9.I", "C9.II"],
      C10: ["C10.1"],
      C11: ["C11.I", "C11.II.a", "C11.II.b"],
      C12: ["C12.1", "C12.2", "C12.3", "C12.4", "C12.5"],
      C13: ["C13.1"],
      C14: ["C14.A", "C14.B"],
      C15: ["C15.1", "C15.2", "C15.3", "C15.4", "C15.5", "C15.6"],
      C16: ["C16.1", "C16.2", "C16.3", "C16.4", "C16.5"],
      C17: ["C17.1"],
      C18: ["C18.1", "C18.2", "C18.3", "C18.4"],
      C19: ["C19.I", "C19.II", "C19.III"],
      C20: ["C20.1", "C20.2", "C20.3", "C20.4"],
      C21: ["C21.1", "C21.2"],
      C22: ["C22.1", "C22.2"],
    };

    for (const [pCode, expectedSubs] of Object.entries(expectedCollegeSubs)) {
      const pData = COLLEGE_FRAMEWORK_DATA[pCode];
      assert.ok(pData, `College ${pCode} must exist in framework data`);
      const actualSubs = (pData.subcriteria || []).map((s) => s.code);
      assert.deepEqual(actualSubs, expectedSubs, `College ${pCode} subcriteria mismatch: expected ${expectedSubs}, got ${actualSubs}`);
      
      // Each subcriterion must have code, title, maxScore, fields
      for (const sub of pData.subcriteria) {
        assert.ok(sub.code.startsWith(pCode), `${sub.code} must start with ${pCode}`);
        assert.ok(sub.title.length > 5, `${sub.code} title must not be empty`);
        assert.ok(sub.maxScore > 0, `${sub.code} maxScore must be > 0`);
        assert.ok(Array.isArray(sub.fields) && sub.fields.length > 0, `${sub.code} must define input fields`);
      }
    }
  });

  await t.test('5. University Subcriteria Structure & Component Codes Alignment', () => {
    const expectedUniversitySubs = {
      U1: ["U1.1"],
      U2: ["U2.1"],
      U3: ["U3.1"],
      U4: ["U4.A", "U4.B"],
      U5: ["U5.A", "U5.B"],
      U6: ["U6.A", "U6.B"],
      U7: ["U7.1", "U7.2", "U7.3", "U7.4"],
      U8: ["U8.A", "U8.B"],
      U9: ["U9.A", "U9.B"],
      U10: ["U10.1", "U10.2", "U10.3", "U10.4"],
      U11: ["U11.1", "U11.2", "U11.3", "U11.4"],
      U12: ["U12.1", "U12.2", "U12.3", "U12.4", "U12.5"],
      U13: ["U13.1"],
      U14: ["U14.A", "U14.B", "U14.C"],
      U15: ["U15.1", "U15.2"],
      U16: ["U16.I", "U16.II", "U16.III"],
      U17: ["U17.1", "U17.2"],
      U18: ["U18.1", "U18.2", "U18.3"],
      U19: ["U19.A", "U19.B"],
      U20: ["U20.1", "U20.2", "U20.3"],
    };

    for (const [pCode, expectedSubs] of Object.entries(expectedUniversitySubs)) {
      const pData = UNIVERSITY_FRAMEWORK_DATA[pCode];
      assert.ok(pData, `University ${pCode} must exist in framework data`);
      const actualSubs = (pData.subcriteria || []).map((s) => s.code);
      assert.deepEqual(actualSubs, expectedSubs, `University ${pCode} subcriteria mismatch: expected ${expectedSubs}, got ${actualSubs}`);

      for (const sub of pData.subcriteria) {
        assert.ok(sub.code.startsWith(pCode), `${sub.code} must start with ${pCode}`);
        assert.ok(sub.title.length > 5, `${sub.code} title must not be empty`);
        assert.ok(sub.maxScore > 0, `${sub.code} maxScore must be > 0`);
        assert.ok(Array.isArray(sub.fields) && sub.fields.length > 0, `${sub.code} must define input fields`);
      }
    }
  });

  await t.test('6. Evidence Contract Layer & Source Ambiguity Preservations', () => {
    // Source Silent verification (U6, C5, C9)
    const silentParams = ['U6', 'C5', 'C9'];
    for (const p of silentParams) {
      const fwData = p.startsWith('C') ? COLLEGE_FRAMEWORK_DATA : UNIVERSITY_FRAMEWORK_DATA;
      for (const sub of fwData[p].subcriteria) {
        assert.equal(sub.isSourceSilent, true, `${sub.code} must be marked isSourceSilent: true`);
        assert.equal(sub.contractStatus, "SOURCE_SILENT");
      }
    }

    // Unresolved metrics verification (U16.III, C19.III, U18.3)
    const u16_3 = getSubcriterionContract('UNIVERSITY_2026', 'U16', 'U16.III');
    assert.equal(u16_3?.isUnresolved, true, 'U16.III must be marked isUnresolved');
    assert.equal(u16_3?.contractStatus, 'UNRESOLVED_MISSING');

    const c19_3 = getSubcriterionContract('COLLEGE_2026', 'C19', 'C19.III');
    assert.equal(c19_3?.isUnresolved, true, 'C19.III must be marked isUnresolved');
    assert.equal(c19_3?.contractStatus, 'UNRESOLVED_MISSING');

    const u18_3 = getSubcriterionContract('UNIVERSITY_2026', 'U18', 'U18.3');
    assert.equal(u18_3?.isUnresolved, true, 'U18.3 must be marked isUnresolved');
    assert.equal(u18_3?.contractStatus, 'UNRESOLVED_MISSING');

    // Canonical Evidence mappings
    const u1_contract = getSubcriterionContract('UNIVERSITY_2026', 'U1', 'U1.1');
    assert.equal(u1_contract?.canonicalEvidenceType, 'EVID_U1_APPROVAL');

    const c1_contract = getSubcriterionContract('COLLEGE_2026', 'C1', 'C1.1');
    assert.equal(c1_contract?.canonicalEvidenceType, 'EVID_C1_APPROVED_IDP');

    const c4_a_contract = getSubcriterionContract('COLLEGE_2026', 'C4', 'C4.A');
    assert.equal(c4_a_contract?.canonicalEvidenceType, 'EVID_C4_INSTITUTE_CERTS');

    const c4_b_contract = getSubcriterionContract('COLLEGE_2026', 'C4', 'C4.B');
    assert.equal(c4_b_contract?.canonicalEvidenceType, 'EVID_C4_INSTITUTE_CERTS');

    // Unresolved notices dictionary
    assert.ok(UNRESOLVED_SPEC_NOTICES.U8, 'U8 notice must exist');
    assert.ok(UNRESOLVED_SPEC_NOTICES.C16, 'C16 notice must exist');
    assert.ok(UNRESOLVED_SPEC_NOTICES.C7, 'C7 notice must exist');
  });

  await t.test('7. Helper Functions Compatibility', () => {
    assert.equal(getSubcriterionTitle('C4.A'), 'Support and Mentorship Provided to Other Higher Education Institutes (2 Marks)');
    assert.equal(getSubcriterionTitle('U7.1'), 'Formal Notification & Selection of Professor of Practice (PoP) (1 Mark)');
    assert.equal(getSubcriterionTitle('UNKNOWN.99', 'Fallback Title'), 'Subcriterion UNKNOWN.99 — Fallback Title');
  });
});
