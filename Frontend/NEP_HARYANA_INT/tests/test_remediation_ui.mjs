// Regression tests for the production-readiness remediation (FIN-02, FIN-04, FIN-05, FIN-06, FIN-15, FIN-28).
// Source-level contract checks; the browser E2E run verifies the same screens end to end.
import { describe, it } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (...p) => fs.readFileSync(path.join(rootDir, "src", ...p), "utf8");

describe("Production-readiness remediation: frontend contracts", () => {
  it("FIN-02: quick-login credentials exist only in development builds", () => {
    const src = read("pages", "Signin", "Signin.jsx");
    assert.match(src, /const APPLICANT_DEV_ACCOUNTS = import\.meta\.env\.DEV \? \[/, "dev accounts gated by import.meta.env.DEV");
    assert.match(src, /\] : \[\];/, "production value is an empty list");
    assert.match(src, /\{import\.meta\.env\.DEV && APPLICANT_DEV_ACCOUNTS\.length > 0 && \(/, "quick-login section gated by DEV");
    const pkg = JSON.parse(fs.readFileSync(path.join(rootDir, "package.json"), "utf8"));
    assert.ok(pkg.scripts["check:bundle"], "bundle credential scan is an npm script");
  });

  it("FIN-06: committee review page offers Return for Correction and Reject with a mandatory reason", () => {
    const api = read("api", "checker.js");
    assert.ok(api.includes("export function returnAssessmentForCorrection("), "return API helper");
    assert.ok(api.includes("export function rejectAssessment("), "reject API helper");
    assert.ok(api.includes("/return-for-correction/") && api.includes("/block-review/"), "calls the review endpoints");
    const page = read("pages", "Checker", "CheckerAssessmentReview.jsx");
    assert.ok(page.includes('openDecisionModal("return")') && page.includes('openDecisionModal("reject")'), "both actions wired");
    assert.ok(page.includes("decisionReason.trim().length < MIN_DECISION_REASON"), "reason length enforced before submit");
    assert.ok(page.includes('decisionMode === "reject" && !decisionConfirmed'), "rejection needs explicit confirmation");
    assert.match(page, /const isReviewer = user\?\.role === "committee" \|\| user\?\.role === "committee_chair";/,
      "only committee roles see the actions (oversight is read-only)");
  });

  it("FIN-03: official certification hold is shown and blocks the Certify button", () => {
    const page = read("pages", "Checker", "CheckerAssessmentReview.jsx");
    assert.ok(page.includes('p.certification_impact === "BLOCKS_OFFICIAL_CERTIFICATION"'), "reads the policy register");
    assert.ok(page.includes("disabled={certifyingAssessment || certificationHolds.length > 0}"), "Certify disabled while held");
  });

  it("FIN-04: administrators can approve or reject institution access requests", () => {
    const api = read("api", "admin.js");
    assert.ok(api.includes("export function fetchPendingInstitutionRequests("), "pending list helper");
    assert.ok(api.includes('institution_status: "PENDING"'), "filters PENDING applicants");
    assert.ok(api.includes("export function decideInstitutionAccess(") && api.includes("/institution-access/"), "decision helper");
    const page = read("pages", "Admin", "InstitutionRequests.jsx");
    assert.ok(page.includes("decide(row, 'approve')") && page.includes("'reject', reason.trim()"), "approve and reject wired");
    assert.ok(page.includes("const INSTITUTION_APPROVER_ROLES = ['head_admin', 'state_admin', 'sub_admin', 'admin'];"),
      "Council Admin gets a read-only view");
    const app = read("App.jsx");
    assert.ok(app.includes('path="/admin/institution-requests"'), "route registered in the admin console");
    assert.ok(read("components", "Admin", "Sidebar.jsx").includes("/admin/institution-requests"), "sidebar link");
  });

  it("FIN-28: pending and rejected applicants see their request status", () => {
    for (const file of [["pages", "CollegeDashboard", "CollegeDashboard.jsx"], ["pages", "University", "UniversityDashboard.jsx"]]) {
      const src = read(...file);
      assert.ok(src.includes('user?.institution_status === "PENDING"'), `${file.at(-1)} handles PENDING`);
      assert.ok(src.includes("Institution access awaiting approval"), `${file.at(-1)} explains the wait`);
    }
  });

  it("FIN-05: empowered committee roles land on their own page instead of a redirect loop", () => {
    const auth = read("api", "auth.js");
    assert.match(auth, /role === "empowered_committee" \|\| role === "empowered_committee_chair"\) \{\s*return "\/empowered";/);
    assert.doesNotMatch(auth, /role === "empowered_committee"[\s\S]{0,80}return "\/checker\/queue"/, "no longer sent to the checker console");
    const app = read("App.jsx");
    assert.match(app, /path="\/empowered"[\s\S]{0,200}allowedRoles=\{\["empowered_committee", "empowered_committee_chair"\]\}/);
    const page = read("pages", "Empowered", "EmpoweredCommitteeHome.jsx");
    assert.ok(page.includes("not active yet"), "states that the stage is not enabled");
    assert.doesNotMatch(page, /from "\.\.\/\.\.\/api\/(checker|college|university)"/, "offers no review actions");
  });

  it("FIN-15: Admin Overview navigation helper is defined", () => {
    const src = read("pages", "Admin", "AdminOverview.jsx");
    assert.match(src, /const goTo = \(query\) => navigate\(/);
  });
});
