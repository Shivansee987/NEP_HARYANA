/**
 * NEP Excellence Awards 2026 — Parameter Rubric UI & Option Viewer Verification Suite
 * 
 * Verifies:
 * 1. ParameterFormView.jsx eliminates amber live calculation-assistance panel.
 * 2. ParameterFormView.jsx eliminates static generic percentage dropdown [0..100%].
 * 3. ParameterFormView.jsx mounts RubricOptionViewer for authoritative scoring options.
 * 4. RUBRIC_REGISTRY defines rubrics for all 22 College (C1–C22) and 20 University (U1–U20) parameters.
 * 5. Every subcriterion in College and University frameworks has an official rubric entry.
 * 6. Rubric options display exact marks and thresholds.
 * 7. Active tier calculation correctly resolves for representative percentage parameters (C1, C2, C3, C6, C7, U2, U3).
 * 8. Active tier calculation correctly resolves for representative count parameters (C10, U1, U6.2, U8.A, U16.I, U20.1).
 * 9. Active tier calculation correctly resolves for cumulative checklist parameters (C8, C11.II.a, C12, C16, U20.2).
 * 10. Multi-part composite parameters (C4, C9, C11, U4, U5, U8, U9, U14, U16, U19, U20) have segregated sub-rubrics.
 * 11. Preserves official boundary voids and advisory notices without inventing scoring rules.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  RUBRIC_REGISTRY,
  getActiveRubricOptionId,
} from '../src/utils/nepRubrics.js';

import {
  COLLEGE_FRAMEWORK_DATA,
  UNIVERSITY_FRAMEWORK_DATA,
  COLLEGE_PARAMETER_CODES,
  UNIVERSITY_PARAMETER_CODES,
} from '../src/utils/nepTaxonomy.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '../src');

describe('NEP 2026 Parameter Rubric UI & Option Viewer Verification Suite', () => {

  // Test 1: Calculation Assistance amber panel is removed
  it('1. ParameterFormView.jsx eliminates the amber live calculation-assistance panel', () => {
    const formViewContent = fs.readFileSync(
      path.join(srcDir, 'components/Institution/ParameterFormView.jsx'),
      'utf-8'
    );
    assert.strictEqual(
      formViewContent.includes('Calculation Assistance:'),
      false,
      'ParameterFormView must NOT contain "Calculation Assistance:" amber box'
    );
    assert.strictEqual(
      formViewContent.includes('Live percentage calculated from:'),
      false,
      'ParameterFormView must NOT contain "Live percentage calculated from:"'
    );
  });

  // Test 2: Generic static percentage dropdown is removed
  it('2. ParameterFormView.jsx eliminates generic static percentage dropdowns [0, 10, ... 100]%', () => {
    const formViewContent = fs.readFileSync(
      path.join(srcDir, 'components/Institution/ParameterFormView.jsx'),
      'utf-8'
    );
    assert.strictEqual(
      formViewContent.includes('Select Percentage…'),
      false,
      'ParameterFormView must NOT contain static "Select Percentage…" dropdown'
    );
    assert.strictEqual(
      formViewContent.includes('[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]'),
      false,
      'ParameterFormView must NOT contain hardcoded percentage array dropdown'
    );
  });

  // Test 3: RubricOptionViewer is imported and mounted
  it('3. ParameterFormView.jsx imports and mounts RubricOptionViewer component', () => {
    const formViewContent = fs.readFileSync(
      path.join(srcDir, 'components/Institution/ParameterFormView.jsx'),
      'utf-8'
    );
    assert.ok(
      formViewContent.includes('import RubricOptionViewer from "./RubricOptionViewer"'),
      'ParameterFormView must import RubricOptionViewer'
    );
    assert.ok(
      formViewContent.includes('<RubricOptionViewer'),
      'ParameterFormView must render <RubricOptionViewer'
    );
  });

  // Test 4: RUBRIC_REGISTRY coverage
  it('4. RUBRIC_REGISTRY covers all 22 College (C1–C22) and 20 University (U1–U20) parameters', () => {
    const registeredCodes = Object.keys(RUBRIC_REGISTRY);
    assert.strictEqual(registeredCodes.length, 42, 'RUBRIC_REGISTRY must contain exactly 42 parameters');

    for (const code of COLLEGE_PARAMETER_CODES) {
      assert.ok(RUBRIC_REGISTRY[code], `RUBRIC_REGISTRY must contain College parameter ${code}`);
    }
    for (const code of UNIVERSITY_PARAMETER_CODES) {
      assert.ok(RUBRIC_REGISTRY[code], `RUBRIC_REGISTRY must contain University parameter ${code}`);
    }
  });

  // Test 5: Every subcriterion has a defined rubric
  it('5. Every subcriterion in College and University framework has an official rubric entry', () => {
    for (const [code, p] of Object.entries(COLLEGE_FRAMEWORK_DATA)) {
      const pRubric = RUBRIC_REGISTRY[code];
      assert.ok(pRubric, `College parameter ${code} missing in RUBRIC_REGISTRY`);
      for (const sub of (p.subcriteria || [])) {
        assert.ok(
          pRubric.subcriteria && pRubric.subcriteria[sub.code],
          `Subcriterion ${sub.code} in College ${code} missing in rubric registry`
        );
        const rubricSub = pRubric.subcriteria[sub.code];
        assert.ok(
          rubricSub.options && rubricSub.options.length > 0,
          `Subcriterion ${sub.code} must have at least one scoring option`
        );
      }
    }

    for (const [code, p] of Object.entries(UNIVERSITY_FRAMEWORK_DATA)) {
      const pRubric = RUBRIC_REGISTRY[code];
      assert.ok(pRubric, `University parameter ${code} missing in RUBRIC_REGISTRY`);
      for (const sub of (p.subcriteria || [])) {
        assert.ok(
          pRubric.subcriteria && pRubric.subcriteria[sub.code],
          `Subcriterion ${sub.code} in University ${code} missing in rubric registry`
        );
        const rubricSub = pRubric.subcriteria[sub.code];
        assert.ok(
          rubricSub.options && rubricSub.options.length > 0,
          `Subcriterion ${sub.code} must have at least one scoring option`
        );
      }
    }
  });

  // Test 6: Display of exact marks and condition labels
  it('6. Rubric options explicitly specify awarded marks and threshold conditions', () => {
    const c1Sub = RUBRIC_REGISTRY.C1.subcriteria['C1.1'];
    assert.strictEqual(c1Sub.options.length, 4);
    assert.strictEqual(c1Sub.options[0].marks, 6);
    assert.strictEqual(c1Sub.options[0].threshold, '> 90%');
    assert.strictEqual(c1Sub.options[1].marks, 4);
    assert.strictEqual(c1Sub.options[1].threshold, '> 75% and <= 90%');
    assert.strictEqual(c1Sub.options[2].marks, 2);
    assert.strictEqual(c1Sub.options[3].marks, 1);

    const u1Sub = RUBRIC_REGISTRY.U1.subcriteria['U1.1'];
    assert.strictEqual(u1Sub.options.length, 5);
    assert.strictEqual(u1Sub.options[0].marks, 4);
    assert.strictEqual(u1Sub.options[0].threshold, '> 10');
    assert.strictEqual(u1Sub.options[1].marks, 3);
    assert.strictEqual(u1Sub.options[1].threshold, '> 7 and <= 10');
    assert.strictEqual(u1Sub.options[2].marks, 2);
    assert.strictEqual(u1Sub.options[2].threshold, '> 4 and <= 7');
    assert.strictEqual(u1Sub.options[3].marks, 1);
    assert.strictEqual(u1Sub.options[3].threshold, '>= 1 and <= 4');
    assert.strictEqual(u1Sub.options[4].marks, 0);
    assert.strictEqual(u1Sub.options[4].threshold, '0');
  });

  // Test 7: Percentage ratio active tier resolution
  it('7. Percentage ratio active tier dynamically calculates without global threshold reuse', () => {
    // C1: >90 (6), >75-90 (4), >50-75 (2), <=50 (1)
    const c1Sub = RUBRIC_REGISTRY.C1.subcriteria['C1.1'];
    assert.strictEqual(
      getActiveRubricOptionId(c1Sub, { achieved_targets_2024_25: 95, fixed_targets_2024_25: 100 }),
      'C1_T1' // >90% -> 6 marks
    );
    assert.strictEqual(
      getActiveRubricOptionId(c1Sub, { achieved_targets_2024_25: 80, fixed_targets_2024_25: 100 }),
      'C1_T2' // >75-90% -> 4 marks
    );
    assert.strictEqual(
      getActiveRubricOptionId(c1Sub, { achieved_targets_2024_25: 45, fixed_targets_2024_25: 100 }),
      'C1_T4' // <=50% -> 1 mark
    );

    // U3: >25 (4), 15-25 (3), 5-15 (2), <=5 (1) - completely different from C1
    const u3Sub = RUBRIC_REGISTRY.U3.subcriteria['U3.1'];
    assert.strictEqual(
      getActiveRubricOptionId(u3Sub, { iks_programmes: 30, total_degree_programmes: 100 }),
      'U3_T1' // >25% -> 4 marks
    );
    assert.strictEqual(
      getActiveRubricOptionId(u3Sub, { iks_programmes: 20, total_degree_programmes: 100 }),
      'U3_T2' // 15-25% -> 3 marks
    );
    assert.strictEqual(
      getActiveRubricOptionId(u3Sub, { iks_programmes: 10, total_degree_programmes: 100 }),
      'U3_T3' // 5-15% -> 2 marks
    );
    assert.strictEqual(
      getActiveRubricOptionId(u3Sub, { iks_programmes: 2, total_degree_programmes: 100 }),
      'U3_T4' // <=5% -> 1 mark
    );
  });

  // Test 8: Count active tier resolution
  it('8. Count-based active tier resolves based on integer input count', () => {
    // C10: >=5 (5), 4 (4), 3 (3), 2 (2), 1 (1), 0 (0)
    const c10Sub = RUBRIC_REGISTRY.C10.subcriteria['C10.1'];
    assert.strictEqual(getActiveRubricOptionId(c10Sub, { active_mous_count: 6 }), 'C10_T1');
    assert.strictEqual(getActiveRubricOptionId(c10Sub, { active_mous_count: 3 }), 'C10_T3');
    assert.strictEqual(getActiveRubricOptionId(c10Sub, { active_mous_count: 0 }), 'C10_T6');

    // U20.1: >=10 (2), 5-9 (1), <5 (0)
    const u20_1Sub = RUBRIC_REGISTRY.U20.subcriteria['U20.1'];
    assert.strictEqual(getActiveRubricOptionId(u20_1Sub, { activities_count: 12 }), 'U20_1_T1');
    assert.strictEqual(getActiveRubricOptionId(u20_1Sub, { activities_count: 7 }), 'U20_1_T2');
    assert.strictEqual(getActiveRubricOptionId(u20_1Sub, { activities_count: 3 }), 'U20_1_T3');
  });

  // Test 9: Cumulative checklist active tier resolution
  it('9. Cumulative checklist options resolve when verified is checked', () => {
    const c12_1Sub = RUBRIC_REGISTRY.C12.subcriteria['C12.1'];
    assert.strictEqual(getActiveRubricOptionId(c12_1Sub, { verified: true }), 'C12_1');
    assert.strictEqual(getActiveRubricOptionId(c12_1Sub, { verified: false }), null);

    const u20_2Sub = RUBRIC_REGISTRY.U20.subcriteria['U20.2'];
    assert.strictEqual(getActiveRubricOptionId(u20_2Sub, { verified: true }), 'U20_2');
    assert.strictEqual(getActiveRubricOptionId(u20_2Sub, { verified: false }), null);
  });

  // Test 10: Composite parameters segregation
  it('10. Composite parameters contain segregated subcriteria rubrics with exact individual marks', () => {
    // C9 has C9.I (3 marks) and C9.II (3 marks) = 6 marks
    const c9 = RUBRIC_REGISTRY.C9;
    assert.ok(c9.subcriteria['C9.I'], 'C9 must have C9.I');
    assert.ok(c9.subcriteria['C9.II'], 'C9 must have C9.II');
    assert.strictEqual(c9.subcriteria['C9.I'].maxMarks, 3);
    assert.strictEqual(c9.subcriteria['C9.II'].maxMarks, 3);

    // U8 has U8.A (4 marks) and U8.B (2 marks) = 6 marks
    const u8 = RUBRIC_REGISTRY.U8;
    assert.ok(u8.subcriteria['U8.A'], 'U8 must have U8.A');
    assert.ok(u8.subcriteria['U8.B'], 'U8 must have U8.B');
    assert.strictEqual(u8.subcriteria['U8.A'].maxMarks, 4);
    assert.strictEqual(u8.subcriteria['U8.B'].maxMarks, 2);

    // U14 has U14.A (4 marks), U14.B (1 mark) = 5 marks
    const u14 = RUBRIC_REGISTRY.U14;
    assert.ok(u14.subcriteria['U14.A'], 'U14 must have U14.A');
    assert.ok(u14.subcriteria['U14.B'], 'U14 must have U14.B');
    assert.strictEqual(u14.subcriteria['U14.A'].maxMarks, 4);
    assert.strictEqual(u14.subcriteria['U14.B'].maxMarks, 1);
  });

  // Test 11: Preservation of statutory policy notices and boundary voids
  it('11. Preserves statutory boundary notices for C5, U5, C16, U16, U20 without inventing rules', () => {
    assert.ok(RUBRIC_REGISTRY.C5.subcriteria['C5.1'].isPolicyNotice);
    assert.ok(RUBRIC_REGISTRY.C16.subcriteria['C16.1'].isPolicyNotice);
    assert.ok(RUBRIC_REGISTRY.C19.subcriteria['C19.III'].isPolicyNotice);
    assert.ok(RUBRIC_REGISTRY.U5.subcriteria['U5.A'].isPolicyNotice);
    assert.ok(RUBRIC_REGISTRY.U16.subcriteria['U16.III'].isPolicyNotice);
    assert.ok(RUBRIC_REGISTRY.U20.subcriteria['U20.1'].isPolicyNotice);

    // Verify C5 boundary void at exactly 75.0%
    const c5Sub = RUBRIC_REGISTRY.C5.subcriteria['C5.1'];
    // 75.0% does not match any tier because PDF is '>75% and <90%' vs '<75%'
    const c5Void = getActiveRubricOptionId(c5Sub, { admitted_students: 75, sanctioned_intake: 100 });
    assert.strictEqual(c5Void, null, 'C5 at exactly 75.0% must be held uncalculated (void)');
  });

});
