import { describe, it } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

describe('Head Admin Control Centre — Frontend Integration Tests', () => {
  it('1. api/admin.js exports fetchAdminControlCentreSummary and fetchGlobalUserAuditLogs', () => {
    const adminApiPath = path.join(rootDir, 'src', 'api', 'admin.js');
    assert.ok(fs.existsSync(adminApiPath), 'admin.js must exist');

    const content = fs.readFileSync(adminApiPath, 'utf8');
    assert.ok(content.includes('export function fetchAdminControlCentreSummary('), 'Exports fetchAdminControlCentreSummary');
    assert.ok(content.includes('export function fetchGlobalUserAuditLogs('), 'Exports fetchGlobalUserAuditLogs');
    assert.ok(content.includes('/v1/admin/control-centre/summary/'), 'Points to control-centre summary endpoint');
    assert.ok(content.includes('/v1/admin/users/audit-trail/'), 'Points to global user audit trail endpoint');
  });

  it('2. Sidebar.jsx dynamically adapts for Head Admin Control Centre', () => {
    const sidebarPath = path.join(rootDir, 'src', 'components', 'Admin', 'Sidebar.jsx');
    assert.ok(fs.existsSync(sidebarPath), 'Sidebar.jsx must exist');

    const content = fs.readFileSync(sidebarPath, 'utf8');
    assert.ok(content.includes('isHeadAdmin'), 'Checks isHeadAdmin for role-aware sidebar labels');
    assert.ok(content.includes('Head Admin Control Centre'), 'Displays Head Admin Control Centre console heading');
    assert.ok(content.includes("name: isHeadAdmin ? 'Control Centre' : 'Overview'"), 'Overview link renames to Control Centre for Head Admin');
  });

  it('3. AdminOverview.jsx integrates Head Admin Control Centre with governance, staffing, and warnings', () => {
    const overviewPath = path.join(rootDir, 'src', 'pages', 'Admin', 'AdminOverview.jsx');
    assert.ok(fs.existsSync(overviewPath), 'AdminOverview.jsx must exist');

    const content = fs.readFileSync(overviewPath, 'utf8');
    assert.ok(content.includes('fetchAdminControlCentreSummary'), 'Imports and calls fetchAdminControlCentreSummary');
    assert.ok(content.includes('isHeadAdmin'), 'Detects isHeadAdmin from AuthContext');
    assert.ok(content.includes('Head Admin Control Centre'), 'Renders Head Admin Control Centre title');
    assert.ok(content.includes('Platform Administrators'), 'Renders Platform Administrators staffing card');
    assert.ok(content.includes('Screening Committee'), 'Renders Screening Committee staffing card');
    assert.ok(content.includes('Empowered Committee'), 'Renders Empowered Committee staffing card');
    assert.ok(content.includes('Operational Bottlenecks & Exceptions'), 'Renders Operational Bottlenecks card');
    assert.ok(content.includes('Privileged Security & Account Audit Stream'), 'Renders Privileged Security Audit Stream');
    assert.ok(content.includes('UNASSIGNED_SUBMISSIONS'), 'Handles unassigned submissions alert');
    assert.ok(content.includes('SINGLE_HEAD_ADMIN'), 'Handles single head administrator warning');
  });

  it('4. AdminOverview.jsx preserves standard State Overview for non-HeadAdmins and via view tabs', () => {
    const overviewPath = path.join(rootDir, 'src', 'pages', 'Admin', 'AdminOverview.jsx');
    const content = fs.readFileSync(overviewPath, 'utf8');

    assert.ok(content.includes('State Overview'), 'Preserves State Overview heading for sub_admin or institution tab');
    assert.ok(content.includes('Needs Attention'), 'Preserves Needs Attention table');
    assert.ok(content.includes('Scores So Far'), 'Preserves Scores So Far card');
    assert.ok(content.includes('Recent Assessment Activity'), 'Preserves Recent Assessment Activity feed');
  });

  it('5. AdminOverview.jsx includes loading, error, empty, and retry states without fabricated counts', () => {
    const overviewPath = path.join(rootDir, 'src', 'pages', 'Admin', 'AdminOverview.jsx');
    const content = fs.readFileSync(overviewPath, 'utf8');

    assert.ok(content.includes('Loading Head Admin Control Centre...'), 'Has role-aware loading state');
    assert.ok(content.includes('Failed to load Control Centre'), 'Has role-aware error state');
    assert.ok(content.includes('Retry'), 'Has retry button on error');
    assert.ok(content.includes('No privileged audit activity recorded yet.'), 'Has empty state for audit feed');
    assert.ok(content.includes('No unassigned submissions in queue.'), 'Has empty state for unassigned items');
  });
});
