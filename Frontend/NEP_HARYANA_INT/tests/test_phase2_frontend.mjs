import { describe, it } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

describe('Head Admin Phase 2 — Secure Activation & Committee Management Frontend Tests', () => {
  it('1. AccountActivation component exists with token validation, error states, and responsive styling', () => {
    const filePath = path.join(rootDir, 'src', 'pages', 'AuthRecovery', 'AccountActivation.jsx');
    assert.ok(fs.existsSync(filePath), 'AccountActivation.jsx must exist');

    const content = fs.readFileSync(filePath, 'utf8');
    assert.ok(content.includes('verifyAccountActivation'), 'Imports verifyAccountActivation API');
    assert.ok(content.includes('confirmAccountActivation'), 'Imports confirmAccountActivation API');
    assert.ok(content.includes('Official Account Activation'), 'Renders title for official account activation');
    assert.ok(content.includes('Invalid or Expired Activation Link'), 'Handles invalid or expired activation link state');
    assert.ok(content.includes('Set Up Your Security Credentials'), 'Provides password establishment view');
    assert.ok(content.includes('at least 8 characters'), 'Enforces minimum 8 characters validation hint');
    assert.ok(content.includes('AuthRecovery.module.css'), 'Reuses existing site authentication theme stylesheet');
  });

  it('2. CommitteeManagement component exists with complete lifecycle, search, and framework filters', () => {
    const filePath = path.join(rootDir, 'src', 'pages', 'Admin', 'CommitteeManagement.jsx');
    assert.ok(fs.existsSync(filePath), 'CommitteeManagement.jsx must exist');

    const content = fs.readFileSync(filePath, 'utf8');
    assert.ok(content.includes('Committee Management'), 'Renders Committee Management heading');
    assert.ok(content.includes('fetchAdminCommittees'), 'Imports fetchAdminCommittees API');
    assert.ok(content.includes('createAdminCommittee'), 'Imports createAdminCommittee API');
    assert.ok(content.includes('assignAdminCommitteeChair'), 'Imports assignAdminCommitteeChair API');
    assert.ok(content.includes('addAdminCommitteeMember'), 'Imports addAdminCommitteeMember API');
    assert.ok(content.includes('removeAdminCommitteeMember'), 'Imports removeAdminCommitteeMember API');
    assert.ok(content.includes('COLLEGE_2026'), 'Supports COLLEGE_2026 framework');
    assert.ok(content.includes('UNIVERSITY_2026'), 'Supports UNIVERSITY_2026 framework');
    assert.ok(content.includes('Assign Committee Chair'), 'Includes chair assignment action modal');
    assert.ok(content.includes('Add Committee Member'), 'Includes member addition action modal');
    assert.ok(content.includes('Create Assessment Committee'), 'Includes committee creation modal');
  });

  it('3. UserManagement includes Pending Activation badge and Resend/Revoke actions', () => {
    const filePath = path.join(rootDir, 'src', 'pages', 'Admin', 'UserManagement.jsx');
    assert.ok(fs.existsSync(filePath), 'UserManagement.jsx must exist');

    const content = fs.readFileSync(filePath, 'utf8');
    assert.ok(content.includes('Pending Activation'), 'Renders Pending Activation status badge');
    assert.ok(content.includes('resendAdminUserInvitation'), 'Imports resendAdminUserInvitation');
    assert.ok(content.includes('revokeAdminUserInvitation'), 'Imports revokeAdminUserInvitation');
    assert.ok(content.includes('handleResendInvitation'), 'Implements handleResendInvitation action');
    assert.ok(content.includes('handleRevokeInvitation'), 'Implements handleRevokeInvitation action');
    assert.ok(content.includes('sendActivationEmail'), 'Supports secure activation email in create modal');
  });

  it('4. App.jsx mounts activation routes and /admin/committees route', () => {
    const appPath = path.join(rootDir, 'src', 'App.jsx');
    const content = fs.readFileSync(appPath, 'utf8');

    assert.ok(content.includes('AccountActivation'), 'Imports AccountActivation page');
    assert.ok(content.includes('CommitteeManagement'), 'Imports CommitteeManagement page');
    assert.ok(content.includes('path="/auth/activate/:token"'), 'Mounts /auth/activate/:token route');
    assert.ok(content.includes('path="/auth/activate"'), 'Mounts /auth/activate route');
    assert.ok(content.includes('path="/admin/committees"'), 'Mounts /admin/committees route');
  });

  it('5. Sidebar.jsx navigation includes link to /admin/committees', () => {
    const sidebarPath = path.join(rootDir, 'src', 'components', 'Admin', 'Sidebar.jsx');
    const content = fs.readFileSync(sidebarPath, 'utf8');

    assert.ok(content.includes("path: '/admin/committees'"), 'Contains link to /admin/committees');
    assert.ok(content.includes("name: 'Committees'"), 'Link is labeled Committees');
  });

  it('6. api/auth.js exports account activation API functions', () => {
    const authPath = path.join(rootDir, 'src', 'api', 'auth.js');
    const content = fs.readFileSync(authPath, 'utf8');

    assert.ok(content.includes('export function verifyAccountActivation('), 'Exports verifyAccountActivation');
    assert.ok(content.includes('export function confirmAccountActivation('), 'Exports confirmAccountActivation');
  });

  it('7. api/admin.js exports committee and invitation endpoints', () => {
    const adminApiPath = path.join(rootDir, 'src', 'api', 'admin.js');
    const content = fs.readFileSync(adminApiPath, 'utf8');

    assert.ok(content.includes('export function resendAdminUserInvitation('), 'Exports resendAdminUserInvitation');
    assert.ok(content.includes('export function revokeAdminUserInvitation('), 'Exports revokeAdminUserInvitation');
    assert.ok(content.includes('export function fetchAdminCommittees('), 'Exports fetchAdminCommittees');
    assert.ok(content.includes('export function fetchAdminCommitteeDetail('), 'Exports fetchAdminCommitteeDetail');
    assert.ok(content.includes('export function createAdminCommittee('), 'Exports createAdminCommittee');
    assert.ok(content.includes('export function updateAdminCommittee('), 'Exports updateAdminCommittee');
    assert.ok(content.includes('export function assignAdminCommitteeChair('), 'Exports assignAdminCommitteeChair');
    assert.ok(content.includes('export function addAdminCommitteeMember('), 'Exports addAdminCommitteeMember');
    assert.ok(content.includes('export function removeAdminCommitteeMember('), 'Exports removeAdminCommitteeMember');
  });
});
