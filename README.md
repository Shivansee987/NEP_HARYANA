The Chatpt Link with all the phases work for refrence - https://chatgpt.com/c/6aa39c79-3f48-83ee-a64c-2c4e7c233f5b

````markdown
# NEP Excellence Awards 2026 — Haryana Platform

> Institutional assessment, evidence verification, scoring, review, certification and reporting platform for the NEP Excellence Awards 2026 framework.

---

# 🚧 CURRENT PROJECT STATUS

## Overall Status

**Backend:** Functionally implemented through Phase 9  
**Frontend:** Functional, but requires substantial UI/UX work  
**Scoring Engine:** FROZEN  
**Evidence Engine:** FROZEN  
**Reports:** Implemented and tested  
**Final Audit:** Pending

### Current Phase Status

| Phase | Area | Status |
|---|---|---|
| Phase 1 | Architecture & Specification | ✅ CLOSED |
| Phase 2 | Database & Domain Model | ✅ CLOSED |
| Phase 3 | Parameter/Subcriterion Specification | ✅ CLOSED |
| Phase 4 | Scoring Engine | ✅ CLOSED / FROZEN |
| Phase 5A | Evidence Domain | ✅ CLOSED |
| Phase 5B | Evidence Upload & Storage | ✅ CLOSED |
| Phase 5C | Evidence Verification | ✅ CLOSED |
| Phase 5D | Evidence Coverage & Assessment Period | ✅ CLOSED |
| Phase 5E | Evidence API Integration | ✅ CLOSED |
| Phase 6A | University Domain | ✅ CLOSED |
| Phase 6B | University API | ✅ CLOSED |
| Phase 6C | University Review & Certification | ✅ CLOSED |
| Phase 7A | College Domain | ✅ CLOSED |
| Phase 7B | College API | ✅ CLOSED |
| Phase 7C | College Review & Certification | ✅ CLOSED |
| Phase 8 | Admin / Control Plane | ✅ CLOSED |
| Phase 8.5 | UI Forensic Recovery | ✅ CLOSED |
| Phase 9 | Reports & Analytics | ✅ CLOSED / PASS |
| Frontend UI/UX | Dashboard & Product Polish | ⚠️ MAJOR WORK REQUIRED |
| Phase 10 | Final Forensic Audit & Release Readiness | ⏳ PENDING |

---

# 1. PROJECT OBJECTIVE

The platform implements the **NEP Excellence Awards 2026** assessment framework for:

- Universities
- Colleges

The system is designed around four core principles:

1. **Evidence-backed scoring**
2. **Server-authoritative evaluation**
3. **Strict framework and tenant isolation**
4. **Immutable review and certification workflows**

The platform is not intended to be a generic scoring dashboard.

The intended workflow is:

```text
Institution
    ↓
Assessment
    ↓
Parameter Inputs
    ↓
Documentary Evidence
    ↓
Evidence Verification
    ↓
Scoring Engine
    ↓
Review
    ↓
Certification
    ↓
Reporting
````

---

# 2. FRAMEWORKS

## University Framework

The University framework contains:

```text
U1 – U20
```

Maximum:

```text
100 marks
```

## College Framework

The College framework contains:

```text
C1 – C22
```

Maximum:

```text
100 marks
```

The two frameworks are strictly separated.

A University assessment must never be evaluated using College parameters.

A College assessment must never be evaluated using University parameters.

---

# 3. ASSESSMENT PERIOD

The authoritative assessment period is:

```text
01 July 2025
        ↓
30 June 2026
```

Academic year:

```text
2025–26
```

The system does not silently fall back to previous assessment periods.

Evidence outside the statutory assessment period must not automatically become valid evidence.

---

# 4. EVIDENCE PRINCIPLE

The core rule is:

> **NO VERIFIED EVIDENCE = NO EARNED MARKS**

Uploading a document does not make it verified.

Evidence follows:

```text
UPLOAD
  ↓
VALIDATE
  ↓
HASH
  ↓
STORE
  ↓
CREATE EVIDENCE RECORD
  ↓
ASSOCIATE
  ↓
SUBMIT
  ↓
VERIFY / REJECT
  ↓
SCORING
```

The evidence system maintains:

* Evidence documents
* Evidence associations
* Verification records
* Verification history
* Audit logs
* Coverage states
* Rejection reasons
* Assessment-period validation

---

# 5. SCORING ENGINE

The authoritative scoring implementation exists under:

```text
Backend/apps/scoring/
```

The scoring engine is currently:

```text
FROZEN
```

It is the single authoritative source for:

* parameter scoring
* subcriterion scoring
* thresholds
* evidence gating
* assessment-period validation
* double-counting detection
* scoring traces
* specification blocking
* final score calculation

## Critical Rule

The frontend must NEVER independently calculate NEP marks.

Frontend components must consume server-authoritative results.

Do not create:

```text
React scoring logic
Client-side thresholds
Client-side score aggregation
Client-side classification
Client-side score caps
```

---

# 6. SCORING INTEGRITY

The scoring engine has undergone multiple forensic correction passes.

Previously identified issues included:

* incorrect patent scoring
* incorrect scoring boundaries
* insufficient evidence gating
* evidence document requirement problems
* double-counting bypasses
* date fallback behavior
* NAAC metadata inconsistencies
* review adjustment trace overwrites
* certification invalidation after evidence rejection

These issues were corrected before the scoring layer was frozen.

Final scoring regression:

```text
117 / 117 tests passed
```

The scoring engine should not be modified during frontend work.

---

# 7. UNRESOLVED COLLEGE SPECIFICATIONS

The following College parameters remain intentionally unresolved:

```text
C5
C7
C8
C16
```

Current resolution states:

```text
C5  → BOUNDARY_UNRESOLVED
C7  → UNRESOLVED_RULE
C8  → UNRESOLVED_RULE
C16 → UNRESOLVED_RULE
```

These rules must NOT be invented by developers.

They must remain visibly unresolved.

Where applicable, unresolved specifications block certification.

---

# 8. UNIVERSITY DOMAIN

University functionality exists under:

```text
Backend/apps/university/
```

The University domain includes:

* University
* UniversityAssessment
* assessment lifecycle
* parameter inputs
* assessment period
* framework identity
* evidence integration
* readiness
* evaluation
* submission
* review
* certification

Parameters:

```text
U1–U20
```

---

# 9. COLLEGE DOMAIN

College functionality exists under:

```text
Backend/apps/college/
```

The College domain includes:

* CollegeAssessment
* assessment lifecycle
* parameter inputs
* assessment period
* framework identity
* evidence integration
* readiness
* evaluation
* submission
* review
* certification

Parameters:

```text
C1–C22
```

---

# 10. REVIEW & CERTIFICATION

University and College assessments use dedicated review services.

Review functionality includes:

```text
START_REVIEW
EVALUATE
COMPLETE_REVIEW
RETURN_FOR_CORRECTION
BLOCK_REVIEW
CERTIFY
```

Review histories are append-only.

Certification must pass the applicable validation and evidence gates.

The frontend cannot directly write:

```text
certified_score
final_score
marks
certification status
```

Certified assessments are locked against unauthorized modification.

---

# 11. ADMIN CONTROL PLANE

Administrative functionality exists under:

```text
/api/v1/admin/
```

The control plane provides:

* review queue
* assessment inspection
* reviewer assignment
* certification
* reviewer authorizations

The admin layer does not replace the scoring engine.

Certification is delegated to the appropriate framework review service.

---

# 12. ROLE MODEL

Current roles include:

```text
admin
committee
committee_chair
university_admin
nodal_officer
principal
```

## Admin

Authorized administrative visibility.

## Committee Chair

Authorized cross-framework review/report visibility.

## Committee Reviewer

Restricted to authorized assessments.

## University Users

Restricted to their authorized university.

## College Principal

Restricted to their authorized college.

---

# 13. TENANT ISOLATION

Tenant isolation is enforced at the backend.

Expected boundaries:

```text
University A
    ✕ University B

College A
    ✕ College B

University
    ✕ College
```

Forged assessment IDs must not bypass these boundaries.

IDOR protection has been explicitly tested.

---

# 14. REPORTS & ANALYTICS

Phase 9 introduced:

```text
Backend/apps/reports/
```

Reports are:

> **READ-ONLY PROJECTIONS OF THE AUTHORITATIVE NEP 2026 DOMAIN**

Reports consume:

* UniversityAssessment
* CollegeAssessment
* verified evidence
* frozen scoring results
* review records
* certification state

Reports do not create a second scoring engine.

---

# 15. REPORT CAPABILITIES

Current reports support:

### Assessment Overview

* institution
* framework
* assessment ID
* academic year
* assessment period
* lifecycle
* reviewer
* evidence readiness
* scoring status
* certification status

### Parameter Report

University:

```text
U1–U20
```

College:

```text
C1–C22
```

Includes:

* parameter
* maximum marks
* input status
* evidence coverage
* earned marks
* blocking reason

### Subcriterion Report

Includes:

* subcriterion
* maximum marks
* evidence state
* scoring state
* earned marks
* trace information
* blocking reason

### Evidence Report

Includes:

* applicable subcriteria
* verified evidence
* pending evidence
* rejected evidence
* invalid evidence
* readiness
* blockers

### Scoring Report

Includes authoritative:

* raw score
* evidence-gated score
* final/certified score
* specification blockers
* scoring conflicts

### Review Report

Includes:

* reviewer assignment
* lifecycle
* review history
* review actions
* certification state
* audit history

### Admin Summary

Includes aggregate:

* assessment counts
* framework distribution
* lifecycle distribution
* specification-blocked assessments

No synthetic institutional ranking is generated.

---

# 16. REPORTING API

Reports are mounted at:

```text
/api/v1/reports/
```

Reports are read-only.

Expected behavior:

```text
GET      → allowed where authorized
POST     → 405
PUT      → 405
PATCH    → 405
DELETE   → 405
```

---

# 17. REPORTING FRONTEND

Current components include:

```text
Frontend/NEP_HARYANA_INT/src/api/reports.js

Frontend/NEP_HARYANA_INT/src/components/Reports/
    AssessmentReportModal.jsx

Frontend/NEP_HARYANA_INT/src/pages/Admin/Reports.jsx
```

The report modal currently contains:

* Overview
* Parameters
* Subcriteria Traces
* Evidence Readiness
* Scoring Engine Output
* Review & Audit
* CSV Export
* Print

---

# 18. FRONTEND STATUS — IMPORTANT

## ⚠️ THE FRONTEND NEEDS A LOT OF ATTENTION

The backend architecture is substantially mature.

The frontend is currently the weakest part of the product.

The application is functional, but the current University and College dashboards do not yet provide the level of visual polish, hierarchy, clarity and UX quality expected from a finished institutional platform.

This is now a major development priority.

---

# 19. FRONTEND WORK REQUIRED

The frontend needs a dedicated UI/UX refinement phase.

The goal is NOT to redesign the backend.

The goal is to transform the existing functional frontend into a polished, coherent institutional product.

## Areas requiring attention

### 19.1 University Dashboard

The University dashboard needs improvement in:

* visual hierarchy
* spacing
* typography
* card composition
* assessment status presentation
* progress visualization
* evidence readiness
* parameter navigation
* primary actions
* information density
* responsive layout
* empty states
* loading states
* error states

The current dashboard should not feel like a collection of backend data cards.

It should feel like a coherent institutional assessment workspace.

---

### 19.2 College Dashboard

The College dashboard requires the same level of attention.

Improve:

* hierarchy
* navigation
* assessment overview
* parameter progress
* evidence readiness
* action buttons
* status indicators
* visual grouping
* spacing
* responsiveness
* loading states
* error states

The College dashboard should be visually consistent with the University dashboard while maintaining College-specific content.

---

### 19.3 Design System

The frontend should have a consistent design system.

Standardize:

* spacing
* border radius
* shadows
* typography
* buttons
* badges
* cards
* tables
* tabs
* modals
* alerts
* progress indicators
* status states
* icons

Do not randomly style individual components.

Build reusable visual primitives where appropriate.

---

### 19.4 Visual Hierarchy

Every dashboard should clearly communicate:

```text
WHO AM I?
      ↓
WHAT ASSESSMENT AM I WORKING ON?
      ↓
WHAT IS ITS CURRENT STATUS?
      ↓
WHAT NEEDS MY ATTENTION?
      ↓
WHAT SHOULD I DO NEXT?
```

The user should not have to interpret a wall of cards and numbers.

---

### 19.5 Assessment Progress

Assessment progress should feel like a process.

For example:

```text
Assessment
    ↓
Parameters
    ↓
Evidence
    ↓
Verification
    ↓
Evaluation
    ↓
Review
    ↓
Certification
```

Do not imply completion when the backend says otherwise.

All progress indicators must remain server-authoritative.

---

### 19.6 Evidence Presentation

Evidence should be visually understandable.

Clearly distinguish:

```text
Missing
Uploaded
Pending Verification
Verified
Rejected
Invalid
Blocked
```

Avoid presenting these states as generic numerical statistics without context.

---

### 19.7 Status Design

Lifecycle states should be visually distinct.

Examples:

```text
DRAFT
SUBMITTED
UNDER REVIEW
RETURNED
BLOCKED
CERTIFIED
REJECTED
```

Status styling must communicate meaning without relying solely on color.

---

### 19.8 Primary Actions

The UI should clearly distinguish primary actions from secondary actions.

Examples:

```text
Continue Assessment
Upload Evidence
Submit Assessment
View Report
Review Assessment
```

Actions must respect backend permissions.

The UI must never display an action the backend will reject merely because the frontend guessed the role incorrectly.

---

# 20. FRONTEND DESIGN DIRECTION

The frontend should feel:

```text
Modern
Professional
Institutional
Clean
Calm
Data-driven
Premium
```

Avoid:

```text
Generic SaaS template
Overloaded dashboard
Excessive gradients
Random card grids
Huge decorative elements
Unnecessary animations
Dense tables everywhere
Visual noise
```

The interface should prioritize usability over decoration.

---

# 21. FRONTEND MUST NOT CHANGE BUSINESS LOGIC

During UI work, DO NOT modify:

```text
Backend/apps/scoring/
Backend/apps/evidence/
```

Do not change:

* scoring rules
* thresholds
* evidence gating
* certification rules
* assessment period
* parameter definitions
* unresolved specifications
* reviewer authorization
* tenant isolation

UI work should consume existing APIs.

---

# 22. PHASE 8.5 — UI FORENSIC RECOVERY

Phase 8.5 resolved role-routing and dashboard integration issues.

Verified routes include:

```text
Admin
    → /admin

Committee
    → /committee

Committee Chair
    → /committee

University
    → /university

College Principal
    → College Dashboard
```

Committee Chair compatibility was fixed without weakening backend RBAC.

Phase 8.5 is CLOSED.

However:

> Functional recovery is complete; visual refinement is still required.

---

# 23. LEGACY SYSTEM ISOLATION

The original system contained a legacy:

```text
P1–P20
```

indicator model.

This is NOT the NEP Excellence Awards 2026 scoring model.

The current NEP system must not map:

```text
P1 → U1
P2 → U2
...
```

or any similar synthetic mapping.

Legacy functionality may remain in deprecated nomination-related workflows, but it must remain isolated from NEP 2026 assessment and reporting.

---

# 24. TESTING STATUS

Phase 9 reporting tests:

```text
18 / 18 passed
```

Full backend regression:

```text
apps.scoring
apps.evidence
apps.university
apps.college
apps.nominations
apps.admin_panel
apps.reports
```

Result:

```text
578 / 578 passed
0 failed
0 skipped
```

Exit status:

```text
OK
```

---

# 25. FRONTEND BUILD

Production build:

```bash
npm run build
```

Result:

```text
Exit Code: 0
Errors: 0
Warnings: 0
```

The frontend builds successfully.

Important:

> A successful build does NOT mean the frontend is visually complete.

The current frontend still requires significant UI/UX refinement.

---

# 26. BROWSER VERIFICATION

Verified:

```text
/admin/reports
/committee/submissions
/university
/college
```

Report functionality verified:

* Overview
* Parameters
* Evidence
* Scoring
* Review History
* CSV Export

No known runtime routing failures were reported during the latest smoke test.

---

# 27. FROZEN LAYER VERIFICATION

Phase 9 verified:

```bash
git diff -- Backend/apps/scoring Backend/apps/evidence
```

Result:

```text
0 lines changed
```

Therefore:

```text
apps.scoring  → FROZEN
apps.evidence → FROZEN
```

This must remain true during frontend refinement.

---

# 28. CURRENT GIT CHANGES

Current Phase 9 changes include:

## Backend

```text
Backend/config/settings/base.py
Backend/config/urls.py
Backend/apps/reports/
```

## Frontend

```text
Frontend/NEP_HARYANA_INT/src/api/reports.js

Frontend/NEP_HARYANA_INT/src/components/Reports/

Frontend/NEP_HARYANA_INT/src/pages/Admin/Reports.jsx

Frontend/NEP_HARYANA_INT/src/pages/CollegeDashboard/CollegeDashboard.jsx

Frontend/NEP_HARYANA_INT/src/pages/University/UniversityDashboard.jsx
```

Scoring and evidence engines were not modified during Phase 9.

---

# 29. CURRENT ARCHITECTURE

```text
                         ┌─────────────────────┐
                         │      FRONTEND       │
                         │    React / Vite     │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
        University              College                Admin
        Dashboard              Dashboard              Reports
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    ▼
                            Reporting / API Layer
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       University Domain     College Domain        Admin Control
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    ▼
                             Evidence Domain
                                    │
                                    ▼
                           Frozen Scoring Engine
                                    │
                                    ▼
                         Review & Certification
                                    │
                                    ▼
                           Authoritative Result
```

---

# 30. DEVELOPMENT RULES

## DO NOT

* Create a second scoring engine
* Calculate NEP marks in React
* Bypass evidence verification
* Invent unresolved scoring rules
* Mix University and College parameters
* Allow cross-tenant access
* Directly write certified scores
* Weaken reviewer authorization
* Map P1–P20 to NEP parameters
* Modify the frozen scoring engine
* Modify the frozen evidence engine
* Introduce institution rankings without specification
* Sacrifice usability for decorative UI
* Add random UI patterns without a design system

## DO

* Use backend-authoritative data
* Preserve auditability
* Preserve append-only histories
* Preserve framework isolation
* Preserve evidence gating
* Preserve assessment-period validation
* Add tests with substantive changes
* Verify regression after changes
* Keep reports read-only
* Build reusable frontend components
* Maintain visual consistency
* Prioritize institutional usability
* Keep frontend and backend responsibilities clearly separated

---

# 31. IMMEDIATE NEXT WORK

## PRIORITY 1 — FRONTEND UI/UX REFINEMENT

The frontend requires substantial attention before final release.

Primary targets:

```text
University Dashboard
College Dashboard
Shared Navigation
Assessment Workspace
Evidence Workspace
Parameter Views
Status Components
Cards
Tables
Modals
Responsive Layout
Loading States
Empty States
Error States
```

This should be treated as a dedicated UI refinement effort.

### Important

Do not redesign backend architecture.

Do not modify scoring.

Do not modify evidence.

Do not modify certification.

Do not modify RBAC.

Use the existing APIs and make the existing product substantially better.

---

# 32. FRONTEND QUALITY BAR

Before declaring the frontend ready, it should satisfy:

```text
✓ Clear hierarchy
✓ Consistent spacing
✓ Consistent typography
✓ Consistent components
✓ Clear assessment state
✓ Clear evidence state
✓ Clear next action
✓ No unnecessary information overload
✓ Responsive layout
✓ Accessible interaction states
✓ Professional institutional appearance
✓ No console errors
✓ No unauthorized API requests
✓ No client-side scoring
```

---

# 33. PHASE 10

After frontend refinement is complete:

```text
PHASE 10
Final Testing
Forensic Audit
Security Audit
Regression
Performance Review
Release Readiness
```

Phase 10 should primarily be an audit.

No major new functionality should be introduced unless the audit discovers a blocking defect.

---

# 34. FINAL VERIFIED BACKEND STATE

```text
Architecture                 ✅
Database / Domain            ✅
Parameter Specification      ✅
Scoring Engine               ✅ FROZEN
Evidence System              ✅ FROZEN
University                   ✅
College                      ✅
Review / Certification       ✅
Admin Control Plane           ✅
UI Role Recovery             ✅
Reports & Analytics          ✅
Backend Regression           ✅ 578/578
Phase 9 Tests                ✅ 18/18
Frontend Build               ✅
Tenant Isolation             ✅
Framework Isolation          ✅
Read-only Reports            ✅
```

---

# 35. CURRENT OUTSTANDING WORK

```text
Frontend UI/UX refinement    ⚠️ MAJOR PRIORITY
University Dashboard         ⚠️ NEEDS REDESIGN/POLISH
College Dashboard            ⚠️ NEEDS REDESIGN/POLISH
Shared Frontend Design       ⚠️ NEEDS ATTENTION
Phase 10 Final Audit         ⏳ PENDING
```

---

# 36. PROJECT STATE

The NEP Excellence Awards 2026 platform is **functionally implemented through Phase 9**.

The backend architecture is mature and extensively regression-tested.

The remaining major product-development task before the final audit is the frontend.

The frontend should now be treated as a first-class engineering task, not a cosmetic afterthought.

The immediate objective is:

> **Turn the currently functional frontend into a polished, coherent, professional institutional assessment product without disturbing the verified backend architecture.**

After that:

```text
Frontend Refinement
        ↓
Phase 10
        ↓
Final Forensic Audit
        ↓
Release Readiness
```

**Do not begin Phase 10 until the frontend refinement pass is complete.**

```
```
