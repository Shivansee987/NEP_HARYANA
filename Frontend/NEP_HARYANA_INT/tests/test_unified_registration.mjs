/**
 * NEP Excellence Awards 2026 - Unified Applicant Registration Test Suite
 * Tests Frontend Section 7 requirements:
 * 1. Both institution types (University & College) are available in the selector
 * 2. No form appears before institution type selection (clean prompt card displayed)
 * 3. University selection renders the correct fields and verification workflow
 * 4. College selection renders the correct fields and institution dropdown
 * 5. Switching types dynamically displays the correct form and isolates type-specific state
 * 6. Validation rules and API payloads match the selected institution type
 * 7. Loading, success, error, and duplicate-submission prevention work correctly
 * 8. Strict isolation: University payload never contains collegeId; College never contains university fields
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '../src');

describe('Unified Applicant Registration Frontend Suite', () => {
  const unifiedSignupPath = path.join(srcDir, 'pages/Signup/Signup.jsx');
  const signupCssPath = path.join(srcDir, 'pages/Signup/Signup.module.css');
  const appPath = path.join(srcDir, 'App.jsx');

  it('1. Unified registration component exists at /pages/Signup/Signup.jsx', () => {
    assert.ok(fs.existsSync(unifiedSignupPath), 'Signup.jsx must exist');
    const content = fs.readFileSync(unifiedSignupPath, 'utf8');
    assert.ok(content.length > 1000, 'Signup.jsx must contain comprehensive unified registration implementation');
    assert.ok(content.includes('export default function Signup'), 'Must export default Signup');
  });

  it('2. Top heading is "Create Applicant Account" and both institution types are available', () => {
    const content = fs.readFileSync(unifiedSignupPath, 'utf8');
    // Top heading
    assert.ok(content.includes('Create Applicant Account'), 'Heading must be Create Applicant Account');

    // Mutually exclusive selector with University and College radio buttons
    assert.ok(content.includes('role="radiogroup"'), 'Selector must use accessible radiogroup');
    assert.ok(content.includes('id="type-university"'), 'Must have university radio option');
    assert.ok(content.includes('value="UNIVERSITY"'), 'Must have value UNIVERSITY');
    assert.ok(content.includes('id="type-college"'), 'Must have college radio option');
    assert.ok(content.includes('value="COLLEGE"'), 'Must have value COLLEGE');
    assert.ok(content.includes('U1–U20 Awards'), 'Must indicate U1-U20 awards for University');
    assert.ok(content.includes('C1–C22 Awards'), 'Must indicate C1-C22 awards for College');
  });

  it('3. Initial page load displays prompt and does NOT render any institution form until selected', () => {
    const content = fs.readFileSync(unifiedSignupPath, 'utf8');
    // Default state does not silently pick a type
    assert.ok(
      content.includes('initialType || normalizedQueryType || null'),
      'Must default to null when no prop or query param is passed'
    );
    // Prompt rendered when !institutionType
    assert.ok(content.includes('!institutionType &&'), 'Must conditionally check !institutionType');
    assert.ok(content.includes('id="institution-prompt-card"'), 'Must render prompt card when no type selected');
    assert.ok(
      content.includes('Please Select Your Institution Type'),
      'Prompt must instruct user to select institution type'
    );
  });

  it('4. Selecting University renders University applicant form and verification fields', () => {
    const content = fs.readFileSync(unifiedSignupPath, 'utf8');
    assert.ok(content.includes('institutionType === "UNIVERSITY" &&'), 'Must conditionally render University form');
    assert.ok(content.includes('id="university-registration-form"'), 'Must have university-registration-form');

    // Required university applicant fields
    assert.ok(content.includes('id="fullName"'), 'Must have applicant full name field');
    assert.ok(content.includes('id="designation"'), 'Must have official designation field');
    assert.ok(content.includes('id="email"'), 'Must have official email field');
    assert.ok(content.includes('UNIVERSITY (Fixed for this flow)'), 'Must indicate fixed UNIVERSITY institution type');
    assert.ok(content.includes('id="aisheCode"'), 'Must have AISHE code input');
    assert.ok(content.includes('id="verify-aishe-btn"'), 'Must have Verify Institution action button');
    assert.ok(content.includes('Verify Institution'), 'Button must be labelled Verify Institution');

    // Canonical details and state feedback panels
    assert.ok(content.includes('id="institution-verified-panel"'), 'Must render verified institution panel');
    assert.ok(content.includes('id="institution-invalid-panel"'), 'Must render invalid AISHE code panel');
    assert.ok(content.includes('id="institution-notfound-panel"'), 'Must render institution not found panel');
    assert.ok(content.includes('id="institution-error-panel"'), 'Must render service error panel');

    // Submission button and gate
    assert.ok(content.includes('id="university-register-submit-btn"'), 'Must have university submit button');
    assert.ok(
      content.includes('uniVerificationStatus !== "verified"') &&
      content.includes('id="university-register-submit-btn"'),
      'University submit button must be disabled until verified'
    );
  });

  it('5. Selecting College renders College applicant form with AISHE verification and autofilled institution name without dropdown', () => {
    const content = fs.readFileSync(unifiedSignupPath, 'utf8');
    assert.ok(content.includes('institutionType === "COLLEGE" &&'), 'Must conditionally render College form');
    assert.ok(content.includes('id="college-registration-form"'), 'Must have college-registration-form');

    // College fields
    assert.ok(content.includes('id="institutionName"'), 'Must have autofilled institutionName field');
    assert.ok(!content.includes('<select'), 'Dropdown category must be removed');
    assert.ok(content.includes('College Principal'), 'Must designate College Principal role');
    assert.ok(content.includes('C1–C22 Awards'), 'Must reference C1-C22 framework');

    // First-class AISHE code verification for College
    assert.ok(content.includes('id="aisheCode"'), 'Must have AISHE code input for College');
    assert.ok(content.includes('id="verify-college-aishe-btn"'), 'Must have College Verify Institution action button');
    assert.ok(content.includes('verifyCollegeAishe'), 'Must call verifyCollegeAishe API');
    assert.ok(content.includes('id="college-verified-panel"'), 'Must display verified college confirmation panel');

    // Submission button
    assert.ok(content.includes('id="college-register-submit-btn"'), 'Must have college submit button');
    assert.ok(
      content.includes('collegeVerificationStatus !== "verified"'),
      'College submit button must gate on institution verification'
    );
  });

  it('6. Dynamic form switching safely isolates type-specific state and retains common details', () => {
    const content = fs.readFileSync(unifiedSignupPath, 'utf8');
    // Switching handler
    assert.ok(content.includes('handleTypeChange'), 'Must have handleTypeChange handler');
    // Isolation: uni state is not used in college submit
    assert.ok(
      content.includes('handleCollegeSubmit'),
      'Must have dedicated handleCollegeSubmit'
    );
    // College payload must NOT include university fields
    assert.ok(
      content.includes('role: "principal"') &&
      content.includes('collegeId: Number(collegeFields.collegeId)'),
      'College submission must strictly use role principal and collegeId'
    );
    // University payload must NOT include collegeId
    assert.ok(
      content.includes('institutionType: "UNIVERSITY"') &&
      content.includes('role: "nodal_officer"'),
      'University submission must strictly enforce institutionType UNIVERSITY and role nodal_officer'
    );
  });

  it('7. Prototype-only copy is completely absent from production UI', () => {
    const content = fs.readFileSync(unifiedSignupPath, 'utf8');
    assert.ok(!content.includes('Proposed layout'), 'Must not contain "Proposed layout"');
    assert.ok(!content.includes('The real page should validate'), 'Must not contain prototype disclaimer');
    assert.ok(!content.includes('Prepare implementation prompt'), 'Must not contain "Prepare implementation prompt"');
  });

  it('8. Duplicate submission prevention and loading state indicators are active', () => {
    const content = fs.readFileSync(unifiedSignupPath, 'utf8');
    assert.ok(content.includes('isSubmitting'), 'Must manage isSubmitting state');
    assert.ok(content.includes('disabled={isSubmitting'), 'Controls must be disabled while isSubmitting');
    assert.ok(content.includes('Creating Account...'), 'Must show loading indicator during submission');
  });

  it('9. Routing configured in App.jsx connects /auth/signup to unified component', () => {
    const appContent = fs.readFileSync(appPath, 'utf8');
    assert.ok(appContent.includes('path="/auth/signup"'), 'App.jsx must configure route for /auth/signup');
    assert.ok(appContent.includes('<Signup />'), 'Route /auth/signup must render Signup component');
  });

  it('10. Onboarding flow uses optional applicant phone number and email verification (phone OTP removed)', () => {
    const content = fs.readFileSync(unifiedSignupPath, 'utf8');
    const authApiPath = path.join(srcDir, 'api/auth.js');
    const authApiContent = fs.readFileSync(authApiPath, 'utf8');

    // Phone number field is present in UI as optional input
    assert.ok(content.includes('id="phoneNumber"'), 'Must have phoneNumber input field');
    assert.ok(content.includes('renderPhoneNumberSection'), 'Must render phone number section');

    // Verification redirect to email verification workflow
    assert.ok(content.includes('/auth/verify-email'), 'Must redirect to email verification upon registration');

    // Active signup must NOT gate on phoneVerified or dev-otp
    assert.ok(!content.includes('phoneVerified'), 'Active signup must not gate on phoneVerified');
    assert.ok(!content.includes('devOtp'), 'Active signup must not retain devOtp hints');

    // Email verification API client exports
    assert.ok(authApiContent.includes('export async function verifyEmailToken'), 'auth.js must export verifyEmailToken');
    assert.ok(authApiContent.includes('export async function resendEmailVerification'), 'auth.js must export resendEmailVerification');
  });
});
