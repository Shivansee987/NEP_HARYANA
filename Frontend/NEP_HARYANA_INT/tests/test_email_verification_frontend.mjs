/**
 * NEP Excellence Awards 2026 - Email Verification & Committee Safeguards Frontend Test Suite
 * Tests frontend verification workflow, UI states, routing, and Empowered Committee inactive screen.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '../src');

describe('Email Verification & Frontend Safeguards Suite', () => {
  const emailVerificationPage = path.join(srcDir, 'pages/AuthRecovery/EmailVerification.jsx');
  const appPath = path.join(srcDir, 'App.jsx');
  const authApiPath = path.join(srcDir, 'api/auth.js');
  const signinPath = path.join(srcDir, 'pages/Signin/Signin.jsx');
  const signupPath = path.join(srcDir, 'pages/Signup/Signup.jsx');
  const uniSignupPath = path.join(srcDir, 'pages/University/UniversitySignup.jsx');
  const empoweredHomePath = path.join(srcDir, 'pages/Empowered/EmpoweredCommitteeHome.jsx');

  it('1. EmailVerification.jsx exists and implements the 5 verification lifecycle states', () => {
    assert.ok(fs.existsSync(emailVerificationPage), 'EmailVerification.jsx must exist');
    const content = fs.readFileSync(emailVerificationPage, 'utf8');

    // State 1: Verifying
    assert.ok(content.includes('Validating Verification Link') || content.includes('Validating'), 'Must support validating state');
    // State 2: Verified & Pending Admin Approval
    assert.ok(content.includes('Email Address Verified') || content.includes('Email Verified'), 'Must show email verified header');
    assert.ok(content.includes('Institutional Access Pending Approval') || content.includes('Pending Approval'), 'Must explain institutional access requires admin approval');
    // State 3: Expired link
    assert.ok(content.includes('Verification Link Expired'), 'Must handle expired link state');
    assert.ok(content.includes('Request New Link') || content.includes('Resend Verification Email'), 'Must provide resend action');
    // State 4: Invalid link
    assert.ok(content.includes('Invalid or Used Link') || content.includes('Invalid Verification Link'), 'Must handle invalid link state');
    // State 5: Verification email sent
    assert.ok(content.includes('Verification Link Dispatched') || content.includes('Verification Email Sent'), 'Must handle verification email sent state');
  });

  it('2. App.jsx registers /auth/verify-email routes', () => {
    const content = fs.readFileSync(appPath, 'utf8');
    assert.ok(content.includes('path="/auth/verify-email/:token"'), 'Must register token route');
    assert.ok(content.includes('path="/auth/verify-email"'), 'Must register base verify-email route');
    assert.ok(content.includes('<EmailVerification />'), 'Must mount EmailVerification component');
  });

  it('3. api/auth.js exports email verification client helpers with error status/code preservation', () => {
    const content = fs.readFileSync(authApiPath, 'utf8');
    assert.ok(content.includes('export async function verifyEmailToken'), 'Must export verifyEmailToken');
    assert.ok(content.includes('export async function confirmEmailVerification'), 'Must export confirmEmailVerification');
    assert.ok(content.includes('export async function resendEmailVerification'), 'Must export resendEmailVerification');
    assert.ok(content.includes('err.code = data?.code'), 'Must attach error code from backend response');
  });

  it('4. Signin.jsx catches EMAIL_NOT_VERIFIED and renders direct verification/resend navigation', () => {
    const content = fs.readFileSync(signinPath, 'utf8');
    assert.ok(content.includes('EMAIL_NOT_VERIFIED'), 'Must catch EMAIL_NOT_VERIFIED error code');
    assert.ok(content.includes('/auth/verify-email'), 'Must provide link to email verification');
  });

  it('5. Unified Signup and University Signup redirect to email verification workflow', () => {
    const signupContent = fs.readFileSync(signupPath, 'utf8');
    const uniSignupContent = fs.readFileSync(uniSignupPath, 'utf8');

    assert.ok(signupContent.includes('/auth/verify-email'), 'Unified Signup must redirect to /auth/verify-email');
    assert.ok(uniSignupContent.includes('/auth/verify-email'), 'University Signup must redirect to /auth/verify-email');
  });

  it('6. Empowered Committee Home explicitly marks stage inactive with no unsupported decision buttons', () => {
    assert.ok(fs.existsSync(empoweredHomePath), 'EmpoweredCommitteeHome.jsx must exist');
    const content = fs.readFileSync(empoweredHomePath, 'utf8');

    assert.ok(content.includes('The Empowered Committee stage is not active yet') || content.includes('stage is not active'), 'Must state stage is inactive');
    assert.ok(content.includes('HSHEC has not yet approved the rules') || content.includes('not yet approved'), 'Must state decision is pending');
    assert.ok(!content.includes('Approve Assessment'), 'Must NOT have approve decision button');
    assert.ok(!content.includes('Certify Final Score'), 'Must NOT have certify button');
  });
});
