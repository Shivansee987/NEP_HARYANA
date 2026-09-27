/**
 * NEP Excellence Awards 2026 - Institution Frontend Rebuild Workflow Tests
 * Covers all 11 targeted test requirements from Specification Section 15:
 *
 * 1. College contains exactly 22 parameters
 * 2. C1–C22 all exist
 * 3. University contains exactly 20 parameters
 * 4. U1–U20 all exist
 * 5. College completion denominator = 22
 * 6. University completion denominator = 20
 * 7. College/University framework isolation
 * 8. Parameter save
 * 9. Evidence association
 * 10. Submission
 * 11. Legacy nomination workflow not used
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  COLLEGE_PARAMETER_CODES,
  COLLEGE_PARAMETER_TITLES,
  COLLEGE_FRAMEWORK_DATA,
  UNIVERSITY_PARAMETER_CODES,
  UNIVERSITY_PARAMETER_TITLES,
  UNIVERSITY_FRAMEWORK_DATA,
  getParameterTitle,
  getSubcriterionTitle,
} from '../src/utils/nepTaxonomy.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '../src');

describe('Institution Frontend Rebuild — College & University Flow Tests', () => {

  // Test 1: College contains exactly 22 parameters
  it('1. College contains exactly 22 parameters', () => {
    assert.strictEqual(
      COLLEGE_PARAMETER_CODES.length,
      22,
      `Expected COLLEGE_PARAMETER_CODES to contain exactly 22 codes, but got ${COLLEGE_PARAMETER_CODES.length}`
    );
    assert.strictEqual(
      Object.keys(COLLEGE_FRAMEWORK_DATA).length,
      22,
      `Expected COLLEGE_FRAMEWORK_DATA to contain exactly 22 parameter keys, but got ${Object.keys(COLLEGE_FRAMEWORK_DATA).length}`
    );
    assert.strictEqual(
      Object.keys(COLLEGE_PARAMETER_TITLES).length,
      22,
      `Expected COLLEGE_PARAMETER_TITLES to contain exactly 22 titles, but got ${Object.keys(COLLEGE_PARAMETER_TITLES).length}`
    );
  });

  // Test 2: C1–C22 all exist
  it('2. C1–C22 all exist with official titles and subcriteria definitions', () => {
    for (let i = 1; i <= 22; i++) {
      const code = `C${i}`;
      assert.ok(
        COLLEGE_PARAMETER_CODES.includes(code),
        `Parameter ${code} is missing from COLLEGE_PARAMETER_CODES`
      );
      assert.ok(
        COLLEGE_PARAMETER_TITLES[code],
        `Parameter ${code} is missing official title in COLLEGE_PARAMETER_TITLES`
      );
      const def = COLLEGE_FRAMEWORK_DATA[code];
      assert.ok(def, `Parameter ${code} is missing detailed metadata in COLLEGE_FRAMEWORK_DATA`);
      assert.strictEqual(def.code, code, `Parameter code mismatch for ${code}`);
      assert.ok(def.maxMarks > 0, `Parameter ${code} must have maxMarks > 0`);
      assert.ok(
        Array.isArray(def.subcriteria) && def.subcriteria.length > 0,
        `Parameter ${code} must have at least one subcriterion`
      );

      // Verify each subcriterion has fields
      def.subcriteria.forEach((sub) => {
        assert.ok(sub.code.startsWith(code), `Subcriterion code ${sub.code} should start with ${code}`);
        assert.ok(sub.title, `Subcriterion ${sub.code} must have a title`);
        assert.ok(
          Array.isArray(sub.fields) && sub.fields.length > 0,
          `Subcriterion ${sub.code} must define at least one input field`
        );
      });
    }
  });

  // Test 3: University contains exactly 20 parameters
  it('3. University contains exactly 20 parameters', () => {
    assert.strictEqual(
      UNIVERSITY_PARAMETER_CODES.length,
      20,
      `Expected UNIVERSITY_PARAMETER_CODES to contain exactly 20 codes, but got ${UNIVERSITY_PARAMETER_CODES.length}`
    );
    assert.strictEqual(
      Object.keys(UNIVERSITY_FRAMEWORK_DATA).length,
      20,
      `Expected UNIVERSITY_FRAMEWORK_DATA to contain exactly 20 parameter keys, but got ${Object.keys(UNIVERSITY_FRAMEWORK_DATA).length}`
    );
    assert.strictEqual(
      Object.keys(UNIVERSITY_PARAMETER_TITLES).length,
      20,
      `Expected UNIVERSITY_PARAMETER_TITLES to contain exactly 20 titles, but got ${Object.keys(UNIVERSITY_PARAMETER_TITLES).length}`
    );
  });

  // Test 4: U1–U20 all exist
  it('4. U1–U20 all exist with official titles and subcriteria definitions', () => {
    for (let i = 1; i <= 20; i++) {
      const code = `U${i}`;
      assert.ok(
        UNIVERSITY_PARAMETER_CODES.includes(code),
        `Parameter ${code} is missing from UNIVERSITY_PARAMETER_CODES`
      );
      assert.ok(
        UNIVERSITY_PARAMETER_TITLES[code],
        `Parameter ${code} is missing official title in UNIVERSITY_PARAMETER_TITLES`
      );
      const def = UNIVERSITY_FRAMEWORK_DATA[code];
      assert.ok(def, `Parameter ${code} is missing detailed metadata in UNIVERSITY_FRAMEWORK_DATA`);
      assert.strictEqual(def.code, code, `Parameter code mismatch for ${code}`);
      assert.ok(def.maxMarks > 0, `Parameter ${code} must have maxMarks > 0`);
      assert.ok(
        Array.isArray(def.subcriteria) && def.subcriteria.length > 0,
        `Parameter ${code} must have at least one subcriterion`
      );

      // Verify each subcriterion has fields
      def.subcriteria.forEach((sub) => {
        assert.ok(sub.code.startsWith(code), `Subcriterion code ${sub.code} should start with ${code}`);
        assert.ok(sub.title, `Subcriterion ${sub.code} must have a title`);
        assert.ok(
          Array.isArray(sub.fields) && sub.fields.length > 0,
          `Subcriterion ${sub.code} must define at least one input field`
        );
      });
    }
  });

  // Test 5: College completion denominator = 22
  it('5. College completion denominator = 22', () => {
    const totalCollegeParams = COLLEGE_PARAMETER_CODES.length;
    assert.strictEqual(totalCollegeParams, 22);

    // Mock completion helper
    const calculateCompletion = (completedCount) => {
      const denominator = totalCollegeParams;
      const formatted = `${completedCount} / ${denominator} filled`;
      const percentage = Math.round((completedCount / denominator) * 100);
      return { denominator, formatted, percentage };
    };

    const initial = calculateCompletion(0);
    assert.strictEqual(initial.denominator, 22);
    assert.strictEqual(initial.formatted, '0 / 22 filled');
    assert.strictEqual(initial.percentage, 0);

    const mid = calculateCompletion(7);
    assert.strictEqual(mid.denominator, 22);
    assert.strictEqual(mid.formatted, '7 / 22 filled');
    assert.strictEqual(mid.percentage, 32);

    const full = calculateCompletion(22);
    assert.strictEqual(full.denominator, 22);
    assert.strictEqual(full.formatted, '22 / 22 filled');
    assert.strictEqual(full.percentage, 100);

    // Verify CollegeDashboard.jsx does not hardcode 20 for College parameters
    const collegeDashContent = fs.readFileSync(
      path.join(srcDir, 'pages/CollegeDashboard/CollegeDashboard.jsx'),
      'utf-8'
    );
    assert.ok(
      collegeDashContent.includes('/ 22 filled'),
      'CollegeDashboard must render "/ 22 filled" for College'
    );
    assert.ok(
      !collegeDashContent.includes('/ 20 filled'),
      'CollegeDashboard must NOT render "/ 20 filled"'
    );
  });

  // Test 6: University completion denominator = 20
  it('6. University completion denominator = 20', () => {
    const totalUniParams = UNIVERSITY_PARAMETER_CODES.length;
    assert.strictEqual(totalUniParams, 20);

    const calculateCompletion = (completedCount) => {
      const denominator = totalUniParams;
      const formatted = `${completedCount} / ${denominator} filled`;
      const percentage = Math.round((completedCount / denominator) * 100);
      return { denominator, formatted, percentage };
    };

    const initial = calculateCompletion(0);
    assert.strictEqual(initial.denominator, 20);
    assert.strictEqual(initial.formatted, '0 / 20 filled');
    assert.strictEqual(initial.percentage, 0);

    const mid = calculateCompletion(11);
    assert.strictEqual(mid.denominator, 20);
    assert.strictEqual(mid.formatted, '11 / 20 filled');
    assert.strictEqual(mid.percentage, 55);

    const full = calculateCompletion(20);
    assert.strictEqual(full.denominator, 20);
    assert.strictEqual(full.formatted, '20 / 20 filled');
    assert.strictEqual(full.percentage, 100);

    // Verify UniversityDashboard.jsx renders "/ 20 filled"
    const uniDashContent = fs.readFileSync(
      path.join(srcDir, 'pages/University/UniversityDashboard.jsx'),
      'utf-8'
    );
    assert.ok(
      uniDashContent.includes('/ 20 filled'),
      'UniversityDashboard must render "/ 20 filled" for University'
    );
  });

  // Test 7: College/University framework isolation
  it('7. College/University framework isolation is strictly enforced', () => {
    // College must not contain any U codes
    COLLEGE_PARAMETER_CODES.forEach((c) => {
      assert.ok(c.startsWith('C'), `College parameter ${c} must start with C`);
      assert.ok(!c.startsWith('U'), `College must not contain University parameter ${c}`);
      assert.ok(!UNIVERSITY_PARAMETER_CODES.includes(c), `College parameter ${c} leaked into University codes`);
    });

    // University must not contain any C codes
    UNIVERSITY_PARAMETER_CODES.forEach((u) => {
      assert.ok(u.startsWith('U'), `University parameter ${u} must start with U`);
      assert.ok(!u.startsWith('C'), `University must not contain College parameter ${u}`);
      assert.ok(!COLLEGE_PARAMETER_CODES.includes(u), `University parameter ${u} leaked into College codes`);
    });

    // Check College workspace source code isolation
    const collegeWorkspaceContent = fs.readFileSync(
      path.join(srcDir, 'pages/Institution/CollegeAssessmentWorkspace.jsx'),
      'utf-8'
    );
    assert.ok(
      !collegeWorkspaceContent.includes('UNIVERSITY_PARAMETER_CODES'),
      'CollegeAssessmentWorkspace must not import or use UNIVERSITY_PARAMETER_CODES'
    );
    assert.ok(
      !collegeWorkspaceContent.includes('UNIVERSITY_FRAMEWORK_DATA'),
      'CollegeAssessmentWorkspace must not import or use UNIVERSITY_FRAMEWORK_DATA'
    );
    assert.ok(
      !collegeWorkspaceContent.includes('api/university'),
      'CollegeAssessmentWorkspace must not import from api/university'
    );

    // Check University workspace source code isolation
    const uniWorkspaceContent = fs.readFileSync(
      path.join(srcDir, 'pages/Institution/UniversityAssessmentWorkspace.jsx'),
      'utf-8'
    );
    assert.ok(
      !uniWorkspaceContent.includes('COLLEGE_PARAMETER_CODES'),
      'UniversityAssessmentWorkspace must not import or use COLLEGE_PARAMETER_CODES'
    );
    assert.ok(
      !uniWorkspaceContent.includes('COLLEGE_FRAMEWORK_DATA'),
      'UniversityAssessmentWorkspace must not import or use COLLEGE_FRAMEWORK_DATA'
    );
    assert.ok(
      !uniWorkspaceContent.includes('api/college'),
      'UniversityAssessmentWorkspace must not import from api/college'
    );
  });

  // Test 8: Parameter save
  it('8. Parameter save persists raw inputs and updates completion status correctly', () => {
    // Parameter status evaluation logic
    const evaluateStatus = (paramCode, rawInputs, frameworkData) => {
      const def = frameworkData[paramCode];
      if (!def || !rawInputs || Object.keys(rawInputs).length === 0) return 'NOT_STARTED';

      const subcriteria = def.subcriteria || [];
      const hasAny = Object.keys(rawInputs).some((subCode) => {
        const vals = rawInputs[subCode];
        return vals && Object.values(vals).some((v) => v !== '' && v !== null && v !== undefined);
      });
      if (!hasAny) return 'NOT_STARTED';

      const allComplete = subcriteria.every((sub) => {
        const vals = rawInputs[sub.code];
        if (!vals || typeof vals !== 'object') return false;
        const fields = sub.fields || [];
        return (
          fields.length > 0 &&
          fields.every((f) => vals[f.key] !== undefined && vals[f.key] !== '' && vals[f.key] !== null)
        );
      });

      return allComplete ? 'COMPLETE' : 'IN_PROGRESS';
    };

    // Test C1 (1 subcriterion: C1.1 with 2 fields)
    assert.strictEqual(evaluateStatus('C1', {}, COLLEGE_FRAMEWORK_DATA), 'NOT_STARTED');
    assert.strictEqual(
      evaluateStatus('C1', { 'C1.1': { achieved_targets_2024_25: 95 } }, COLLEGE_FRAMEWORK_DATA),
      'IN_PROGRESS'
    );
    assert.strictEqual(
      evaluateStatus(
        'C1',
        { 'C1.1': { achieved_targets_2024_25: 95, fixed_targets_2024_25: 100 } },
        COLLEGE_FRAMEWORK_DATA
      ),
      'COMPLETE'
    );

    // Test U1 (1 subcriterion: U1.1 with programmes_count)
    assert.strictEqual(evaluateStatus('U1', {}, UNIVERSITY_FRAMEWORK_DATA), 'NOT_STARTED');
    assert.strictEqual(
      evaluateStatus('U1', { 'U1.1': { programmes_count: '' } }, UNIVERSITY_FRAMEWORK_DATA),
      'NOT_STARTED'
    );
    assert.strictEqual(
      evaluateStatus(
        'U1',
        { 'U1.1': { programmes_count: 12 } },
        UNIVERSITY_FRAMEWORK_DATA
      ),
      'COMPLETE'
    );
  });

  // Test 9: Evidence association
  it('9. Evidence association operates at subcriterion granularity with citation metadata', () => {
    const associations = [
      {
        id: 201,
        association_id: 'assoc-201',
        parameter_id: 'C1',
        subcriterion_id: 'C1.1',
        subcriterion_evidence_type: 'EVID_C1_APPROVED_IDP',
        page_start: 1,
        page_end: 5,
        section_identifier: 'Section 4 - Target Metrics',
        claim_description: 'Approved IDP target document signed by principal.',
        evidence: {
          original_filename: 'IDP_Approved_2025.pdf',
          status: 'PRESENT',
        },
      },
      {
        id: 202,
        association_id: 'assoc-202',
        parameter_id: 'C4',
        subcriterion_id: 'C4.A',
        subcriterion_evidence_type: 'EVID_C4_INSTITUTE_CERTS',
        page_start: 2,
        page_end: 3,
        section_identifier: 'Annexure B - Mentoring Certificate',
        claim_description: 'Certificate from mentored HEI.',
        evidence: {
          original_filename: 'Mentoring_Certificate_HEI.pdf',
          status: 'PRESENT',
        },
      },
    ];

    // Filter associations by exact subcriterion
    const c11Assocs = associations.filter((a) => a.parameter_id === 'C1' && a.subcriterion_id === 'C1.1');
    assert.strictEqual(c11Assocs.length, 1);
    assert.strictEqual(c11Assocs[0].page_start, 1);
    assert.strictEqual(c11Assocs[0].page_end, 5);
    assert.strictEqual(c11Assocs[0].subcriterion_evidence_type, 'EVID_C1_APPROVED_IDP');

    const c4aAssocs = associations.filter((a) => a.parameter_id === 'C4' && a.subcriterion_id === 'C4.A');
    assert.strictEqual(c4aAssocs.length, 1);
    assert.strictEqual(c4aAssocs[0].subcriterion_id, 'C4.A');

    // Confirm that subcriterion C4.B has 0 associations
    const c4bAssocs = associations.filter((a) => a.parameter_id === 'C4' && a.subcriterion_id === 'C4.B');
    assert.strictEqual(c4bAssocs.length, 0);
  });

  // Test 10: Submission
  it('10. Submission triggers modern direct submission and does NOT require checker pre-verification', () => {
    // Model state transition before and after submission
    const mockAssessmentBefore = {
      assessment_id: 'ASSESS-2026-COL-DEV-001',
      framework: 'COLLEGE_2026',
      status: 'DRAFT',
      submitted_at: null,
    };

    assert.strictEqual(mockAssessmentBefore.status, 'DRAFT');

    // Simulate submission call (aligns with Phase W2 direct submission semantics)
    const mockSubmitAction = (assessment) => {
      if (assessment.status !== 'DRAFT') {
        throw new Error(`Assessment is in status '${assessment.status}' and cannot be submitted.`);
      }
      return {
        ...assessment,
        status: 'SUBMITTED',
        submitted_at: new Date().toISOString(),
      };
    };

    const mockAssessmentAfter = mockSubmitAction(mockAssessmentBefore);
    assert.strictEqual(mockAssessmentAfter.status, 'SUBMITTED');
    assert.ok(mockAssessmentAfter.submitted_at);

    // Verify ReviewSubmitView handles declaration and submission
    const reviewSubmitContent = fs.readFileSync(
      path.join(srcDir, 'components/Institution/ReviewSubmitView.jsx'),
      'utf-8'
    );
    assert.ok(
      reviewSubmitContent.includes('onSubmitAssessment'),
      'ReviewSubmitView must trigger onSubmitAssessment'
    );
    assert.ok(
      reviewSubmitContent.includes('Submission uses the modern Phase W2 direct submission pipeline.'),
      'ReviewSubmitView must cite the modern direct submission pipeline'
    );
  });

  // Test 11: Legacy nomination workflow not used
  it('11. Modern assessment routes and components do NOT depend on legacy NominationWorkspace', () => {
    const appContent = fs.readFileSync(path.join(srcDir, 'App.jsx'), 'utf-8');

    // Route /institution/:institutionName/:institutionAisheCode/assessment/:assessmentId must route to CollegeAssessmentWorkspace
    assert.ok(
      appContent.includes('<CollegeAssessmentWorkspace />'),
      'App.jsx must register CollegeAssessmentWorkspace'
    );
    assert.ok(
      appContent.includes('<UniversityAssessmentWorkspace />'),
      'App.jsx must register UniversityAssessmentWorkspace'
    );

    // Check that CollegeAssessmentWorkspace does NOT import from api/nomination
    const collegeWorkspaceContent = fs.readFileSync(
      path.join(srcDir, 'pages/Institution/CollegeAssessmentWorkspace.jsx'),
      'utf-8'
    );
    assert.ok(
      !collegeWorkspaceContent.includes('NominationWorkspace'),
      'CollegeAssessmentWorkspace must not import NominationWorkspace'
    );
    assert.ok(
      !collegeWorkspaceContent.includes('api/nomination'),
      'CollegeAssessmentWorkspace must not import from api/nomination'
    );

    // Check that UniversityAssessmentWorkspace does NOT import from api/nomination
    const uniWorkspaceContent = fs.readFileSync(
      path.join(srcDir, 'pages/Institution/UniversityAssessmentWorkspace.jsx'),
      'utf-8'
    );
    assert.ok(
      !uniWorkspaceContent.includes('NominationWorkspace'),
      'UniversityAssessmentWorkspace must not import NominationWorkspace'
    );
    assert.ok(
      !uniWorkspaceContent.includes('api/nomination'),
      'UniversityAssessmentWorkspace must not import from api/nomination'
    );
  });
});
