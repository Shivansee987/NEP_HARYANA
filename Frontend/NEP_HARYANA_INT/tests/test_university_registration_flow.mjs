/**
 * NEP Excellence Awards 2026 - University Applicant Registration Frontend Flow Tests
 * Covers Phase 8 frontend requirements:
 * 1. University-specific registration component exists and renders correctly
 * 2. Routing configured for /auth/university/signup
 * 3. AISHE verification action and state handling (idle, verifying, verified, invalid, not_found, error)
 * 4. Submit gate enforced until institution is verified
 * 5. Required-field validation and password matching
 * 6. API client integration: verifyUniversityAishe and registerUniversity endpoints
 * 7. Correct post-registration routing to /university for nodal_officer
 * 8. Strict isolation: No College-specific assessment links in University registration experience
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '../src');

describe('University Applicant Registration Frontend Flow Tests', () => {

  const signupPath = path.join(srcDir, 'pages/University/UniversitySignup.jsx');
  const appPath = path.join(srcDir, 'App.jsx');
  const authApiPath = path.join(srcDir, 'api/auth.js');
  const authContextPath = path.join(srcDir, 'context/AuthContext.jsx');

  it('1. Dedicated UniversitySignup component exists and is non-empty', () => {
    assert.ok(fs.existsSync(signupPath), 'UniversitySignup.jsx should exist in pages/University/');
    const content = fs.readFileSync(signupPath, 'utf8');
    assert.ok(content.length > 500, 'UniversitySignup.jsx should contain implementation code');
    assert.ok(content.includes('export default function UniversitySignup'), 'Should default export UniversitySignup');
  });

  it('2. Routing configured in App.jsx for /auth/university/signup', () => {
    const appContent = fs.readFileSync(appPath, 'utf8');
    assert.ok(
      appContent.includes('path="/auth/university/signup"'),
      'App.jsx should contain route for /auth/university/signup'
    );
    assert.ok(
      appContent.includes('UniversitySignup'),
      'App.jsx should import and render UniversitySignup'
    );
  });

  it('3. Required applicant fields and fixed UNIVERSITY institution type are present', () => {
    const content = fs.readFileSync(signupPath, 'utf8');
    // Field checks
    assert.ok(content.includes('id="fullName"'), 'Must contain full name input');
    assert.ok(content.includes('id="designation"'), 'Must contain designation input');
    assert.ok(content.includes('id="email"'), 'Must contain email input');
    assert.ok(content.includes('id="aisheCode"'), 'Must contain AISHE code input');
    assert.ok(content.includes('id="password"'), 'Must contain password input');
    assert.ok(content.includes('id="confirmPassword"'), 'Must contain confirm password input');

    // Institution type fixed
    assert.ok(content.includes('institutionType: "UNIVERSITY"'), 'Must fix institution type to UNIVERSITY');
    assert.ok(content.includes('UNIVERSITY (Fixed for this flow)'), 'Must present fixed University badge to applicant');
    assert.ok(!content.includes('<select id="institutionType"'), 'Institution type must not be a client-selectable dropdown');
  });

  it('4. AISHE code verification action and states are implemented', () => {
    const content = fs.readFileSync(signupPath, 'utf8');
    assert.ok(content.includes('Verify Institution'), 'Must have clearly labelled Verify Institution action');
    assert.ok(content.includes('handleVerifyAishe'), 'Must have handleVerifyAishe action handler');
    assert.ok(content.includes('verifyUniversityAishe'), 'Must call verifyUniversityAishe API function');

    // State machine check
    assert.ok(content.includes('verificationStatus'), 'Must track verificationStatus');
    assert.ok(content.includes('institution-verified-panel'), 'Must display verified institution details panel');
    assert.ok(content.includes('institution-invalid-panel'), 'Must display invalid AISHE state panel');
    assert.ok(content.includes('institution-notfound-panel'), 'Must display institution not found state panel');
  });

  it('5. Registration submission is gated on successful institution verification', () => {
    const content = fs.readFileSync(signupPath, 'utf8');
    // Check submit button disabled condition
    assert.ok(
      content.includes('disabled={isSubmitting || verificationStatus !== "verified"}') ||
      content.includes('verificationStatus !== "verified"'),
      'Submit button must be disabled until verificationStatus === "verified"'
    );
    // Check handleSubmit guard
    assert.ok(
      content.includes('verificationStatus !== "verified" || !verifiedInstitution'),
      'handleSubmit must guard against unverified submission'
    );
  });

  it('6. API client provides verifyUniversityAishe and registerUniversity endpoints', () => {
    const content = fs.readFileSync(authApiPath, 'utf8');
    assert.ok(content.includes('export async function verifyUniversityAishe'), 'api/auth.js must export verifyUniversityAishe');
    assert.ok(content.includes('/auth/university/lookup/'), 'verifyUniversityAishe must call backend lookup endpoint');
    assert.ok(content.includes('export async function registerUniversity'), 'api/auth.js must export registerUniversity');
    assert.ok(content.includes('/auth/university/register/'), 'registerUniversity must call backend registration endpoint');
  });

  it('7. AuthContext provides registerUniversityAccount method', () => {
    const content = fs.readFileSync(authContextPath, 'utf8');
    assert.ok(
      content.includes('registerUniversityAccount'),
      'AuthContext must export registerUniversityAccount'
    );
  });

  it('8. Post-registration routing directs nodal_officer to /university workspace', () => {
    const content = fs.readFileSync(authApiPath, 'utf8');
    assert.ok(
      content.includes('role === "nodal_officer" || role === "university_admin"'),
      'getDashboardPathForUser must recognize nodal_officer'
    );
    assert.ok(
      content.includes('return "/university";'),
      'getDashboardPathForUser must return "/university" for nodal_officer'
    );
  });

  it('9. Isolation: No College C1–C22 links in University Applicant Registration experience', () => {
    const content = fs.readFileSync(signupPath, 'utf8');
    // Ensure no C1-C22 forms are referenced in signup
    assert.ok(!content.includes('C1'), 'Should not reference college parameter C1');
    assert.ok(!content.includes('C22'), 'Should not reference college parameter C22');
    assert.ok(!content.includes('collegeId'), 'Must not bind or submit collegeId');
    assert.ok(content.includes('role: "nodal_officer"'), 'Must enforce nodal_officer role');
  });
});
