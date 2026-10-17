/**
 * NEP Excellence Awards 2026 - University Name Registration & Lookup Frontend Tests
 * Verifies that universities without an AISHE code can register using their University Name
 * across both the Unified Signup and the dedicated University Signup pages.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '../src');

describe('University Registration by Name Without AISHE Code Suite', () => {
  const unifiedSignupPath = path.join(srcDir, 'pages/Signup/Signup.jsx');
  const universitySignupPath = path.join(srcDir, 'pages/University/UniversitySignup.jsx');
  const authApiPath = path.join(srcDir, 'api/auth.js');

  it('1. auth.js exports fetchUniversities and updated verifyUniversityAishe', () => {
    assert.ok(fs.existsSync(authApiPath), 'auth.js must exist');
    const content = fs.readFileSync(authApiPath, 'utf8');

    assert.ok(
      content.includes('export function fetchUniversities()') ||
        content.includes('export const fetchUniversities'),
      'auth.js must export fetchUniversities function'
    );
    assert.ok(
      content.includes('/auth/universities/'),
      'fetchUniversities must call the /auth/universities/ endpoint'
    );
    assert.ok(
      content.includes('export async function verifyUniversityAishe(aisheCode, options = {})'),
      'verifyUniversityAishe must accept options including name and universityId'
    );
    assert.ok(
      content.includes('university_id') && content.includes('name'),
      'verifyUniversityAishe should support university_id and name in query parameters'
    );
  });

  it('2. Unified Signup renders universityName field with datalist populated from registry', () => {
    assert.ok(fs.existsSync(unifiedSignupPath), 'Signup.jsx must exist');
    const content = fs.readFileSync(unifiedSignupPath, 'utf8');

    // Imports fetchUniversities
    assert.ok(
      content.includes('fetchUniversities'),
      'Signup.jsx must import fetchUniversities'
    );

    // University name input and datalist
    assert.ok(
      content.includes('id="universityName"'),
      'Signup.jsx must render universityName input'
    );
    assert.ok(
      content.includes('list="registered-universities-list"'),
      'Signup.jsx universityName input must link to registered-universities-list datalist'
    );
    assert.ok(
      content.includes('<datalist id="registered-universities-list">'),
      'Signup.jsx must render registered-universities-list datalist element'
    );

    // AISHE optional indicator and fallback text
    assert.ok(
      content.includes('Optional if registering by University Name'),
      'Signup.jsx must indicate AISHE code is optional when registering by University Name'
    );
    assert.ok(
      content.includes('Not Assigned (Registered by Name)'),
      'Signup.jsx must display friendly text when AISHE code is not assigned'
    );
  });

  it('3. Dedicated UniversitySignup renders universityName field with datalist', () => {
    assert.ok(fs.existsSync(universitySignupPath), 'UniversitySignup.jsx must exist');
    const content = fs.readFileSync(universitySignupPath, 'utf8');

    // Imports fetchUniversities
    assert.ok(
      content.includes('fetchUniversities'),
      'UniversitySignup.jsx must import fetchUniversities'
    );

    // University name input and datalist
    assert.ok(
      content.includes('id="universityName"'),
      'UniversitySignup.jsx must render universityName input'
    );
    assert.ok(
      content.includes('list="registered-universities-list-uni"'),
      'UniversitySignup.jsx universityName input must link to registered-universities-list-uni datalist'
    );
    assert.ok(
      content.includes('<datalist id="registered-universities-list-uni">'),
      'UniversitySignup.jsx must render registered-universities-list-uni datalist element'
    );

    // AISHE optional indicator and fallback text
    assert.ok(
      content.includes('Optional if registering by University Name'),
      'UniversitySignup.jsx must indicate AISHE code is optional when registering by University Name'
    );
    assert.ok(
      content.includes('Not Assigned (Registered by Name)'),
      'UniversitySignup.jsx must display friendly text when AISHE code is not assigned'
    );
  });

  it('4. Both forms pass universityName and universityId in payload without forcing AISHE code', () => {
    const uniContent = fs.readFileSync(universitySignupPath, 'utf8');
    const unifiedContent = fs.readFileSync(unifiedSignupPath, 'utf8');

    // Dedicated University Signup payload checks
    assert.ok(
      uniContent.includes('universityName: verifiedInstitution.name'),
      'UniversitySignup payload must include verified universityName'
    );
    assert.ok(
      uniContent.includes('universityId: verifiedInstitution.id'),
      'UniversitySignup payload must include verified universityId'
    );
    assert.ok(
      uniContent.includes('aisheCode: verifiedInstitution.aishe_code || ""'),
      'UniversitySignup payload must allow empty string for aisheCode'
    );

    // Unified Signup payload checks
    assert.ok(
      unifiedContent.includes('universityName: uniVerifiedInstitution.name'),
      'Unified Signup payload must include verified universityName'
    );
    assert.ok(
      unifiedContent.includes('universityId: uniVerifiedInstitution.id'),
      'Unified Signup payload must include verified universityId'
    );
    assert.ok(
      unifiedContent.includes('aisheCode: uniVerifiedInstitution.aishe_code || ""'),
      'Unified Signup payload must allow empty string for aisheCode'
    );
  });

  it('5. Verification handlers allow verification with either AISHE code or University Name', () => {
    const uniContent = fs.readFileSync(universitySignupPath, 'utf8');
    const unifiedContent = fs.readFileSync(unifiedSignupPath, 'utf8');

    // Dedicated University Signup verify check
    assert.ok(
      uniContent.includes('!formData.aisheCode.trim() && !formData.universityName.trim()'),
      'UniversitySignup button disable logic must check both aisheCode and universityName'
    );

    // Unified Signup verify check
    assert.ok(
      unifiedContent.includes('!uniFields.aisheCode.trim() && !uniFields.universityName.trim()'),
      'Unified Signup button disable logic must check both aisheCode and universityName'
    );
  });
});
