import { describe, it } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

describe('Phase 1 — User Management & Role Governance Frontend Tests', () => {
  it('1. UserManagement component exists with required controls and 4 profile hierarchy', () => {
    const filePath = path.join(rootDir, 'src', 'pages', 'Admin', 'UserManagement.jsx');
    assert.ok(fs.existsSync(filePath), 'UserManagement.jsx must exist');

    const content = fs.readFileSync(filePath, 'utf8');
    assert.ok(content.includes('User & Role Management'), 'Renders page title');
    assert.ok(content.includes('head_admin'), 'Contains head_admin role handling');
    assert.ok(content.includes('state_admin'), 'Contains state_admin role handling');
    assert.ok(content.includes('committee_chair'), 'Contains committee_chair role handling');
    assert.ok(content.includes('council_admin'), 'Contains council_admin role handling');
    assert.ok(content.includes('isHeadAdmin'), 'Checks isHeadAdmin for role assignments and status changes');
    assert.ok(content.includes('PRIVILEGED_ROLES'), 'Enforces privileged roles restrictions');
    assert.ok(content.includes('Chronological Audit Trail'), 'Renders append-only audit trail modal section');
    assert.ok(content.includes('Secure Password Reset'), 'Supports secure password reset modal');
    assert.ok(content.includes('Committee Framework Authorization'), 'Supports committee framework assignment modal');
  });

  it('2. Sidebar navigation includes Users link', () => {
    const sidebarPath = path.join(rootDir, 'src', 'components', 'Admin', 'Sidebar.jsx');
    assert.ok(fs.existsSync(sidebarPath), 'Sidebar.jsx must exist');

    const content = fs.readFileSync(sidebarPath, 'utf8');
    assert.ok(content.includes("path: '/admin/users'"), 'Contains link to /admin/users');
    assert.ok(content.includes("name: 'Users'"), 'Link is labeled Users');
    assert.ok(content.includes('head_admin'), 'Sidebar supports head_admin label');
  });

  it('3. App.jsx protects /admin/users with authorized admin tiers', () => {
    const appPath = path.join(rootDir, 'src', 'App.jsx');
    const content = fs.readFileSync(appPath, 'utf8');

    assert.ok(content.includes('import UserManagement from "./pages/Admin/UserManagement";'), 'Imports UserManagement');
    assert.ok(content.includes('<Route path="/admin/users" element={<UserManagement />} />'), 'Mounts /admin/users route');
    assert.ok(
      content.includes('allowedRoles={["admin", "head_admin", "sub_admin", "state_admin", "council_admin"]}'),
      'Admin layout protected for authorized admin profiles'
    );
  });

  it('4. auth.js routes all admin tiers to /admin, and committee roles to /checker/queue', () => {
    const authPath = path.join(rootDir, 'src', 'api', 'auth.js');
    const content = fs.readFileSync(authPath, 'utf8');

    assert.ok(
      content.includes('role === "state_admin"'),
      'Routes state_admin to /admin'
    );
    assert.ok(
      content.includes('role === "council_admin"'),
      'Routes council_admin to /admin'
    );
    assert.ok(
      content.includes('role === "committee_chair"'),
      'Routes committee_chair to checker queue'
    );
  });

  it('5. api/admin.js exports centralized user management and security endpoints', () => {
    const adminApiPath = path.join(rootDir, 'src', 'api', 'admin.js');
    const content = fs.readFileSync(adminApiPath, 'utf8');

    assert.ok(content.includes('export function fetchAdminUsers('), 'Exports fetchAdminUsers');
    assert.ok(content.includes('export function fetchAdminUserDetail('), 'Exports fetchAdminUserDetail');
    assert.ok(content.includes('export function createAdminUser('), 'Exports createAdminUser');
    assert.ok(content.includes('export function updateAdminUser('), 'Exports updateAdminUser');
    assert.ok(content.includes('export function resetAdminUserPassword('), 'Exports resetAdminUserPassword');
    assert.ok(content.includes('export function manageAdminUserCommittee('), 'Exports manageAdminUserCommittee');
    assert.ok(content.includes('export function fetchAdminUserAuditLogs('), 'Exports fetchAdminUserAuditLogs');
    assert.ok(content.includes('/v1/admin/users/'), 'Calls correct REST endpoint path');
  });

  it('6. AdminSignin.jsx provides unified Head Administrator login consolidating all administrative modules', () => {
    const signinPath = path.join(rootDir, 'src', 'pages', 'Signin', 'AdminSignin.jsx');
    assert.ok(fs.existsSync(signinPath), 'AdminSignin.jsx must exist');

    const content = fs.readFileSync(signinPath, 'utf8');
    // Ensure mock dev accounts are removed
    assert.ok(!content.includes('admin@dev.local'), 'No hardcoded admin@dev.local');
    assert.ok(!content.includes('DevAdmin@123'), 'No hardcoded DevAdmin@123');
    assert.ok(!content.includes('ADMIN_DEV_ACCOUNTS'), 'ADMIN_DEV_ACCOUNTS removed');

    // Ensure unified Head Administrator entry exists with consolidated modules
    assert.ok(content.includes('Head Administrator'), 'Has Head Administrator login');
    assert.ok(content.includes('HEAD ADMINISTRATOR'), 'Has HEAD ADMINISTRATOR badge');
    assert.ok(content.includes('head.admin@dhe.haryana.gov.in'), 'Has official Head Admin email hint');
    assert.ok(content.includes('State Administration'), 'Has State Administration module under Head Admin');
    assert.ok(content.includes('Committees & Review Operations'), 'Has Committees module under Head Admin');
    assert.ok(content.includes('User & Role Governance'), 'Has User Governance module under Head Admin');
    assert.ok(content.includes('Institution Registries'), 'Has Institution Registries module under Head Admin');
  });
});
