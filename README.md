The ChatGPT Link with all the work - https://chatgpt.com/share/6ab7cd81-895c-83ee-9114-93d458a872bf

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:600b0b,50:8a1c1c,100:c29b68&height=210&section=header&text=NEP%20Excellence%20Awards%202026&fontSize=44&fontColor=ffffff&fontAlignY=36&desc=Haryana%20%E2%80%A2%20DHE%20%26%20HSHEC&descAlignY=58&descSize=18&animation=fadeIn" alt="NEP Excellence Awards 2026, Haryana" width="100%" />

<a href="https://git.io/typing-svg">
  <img src="https://readme-typing-svg.demolab.com?font=Outfit&weight=700&size=24&duration=2600&pause=900&color=600B0B&center=true&vCenter=true&width=900&lines=Institutions+fill+in+their+NEP+2026+self-assessment;They+upload+proof+for+every+claim;The+Screening+Committee+verifies+the+proof;The+server+calculates+the+marks+%E2%80%94+not+a+person;The+Chair+certifies+the+result+%F0%9F%8F%85;The+State+Admin+watches+the+whole+state" alt="Animated summary of the workflow" />
</a>

<p>
  <img src="https://img.shields.io/badge/Django-6.0-0c4b33?style=for-the-badge&logo=django&logoColor=white" alt="Django 6.0" />
  <img src="https://img.shields.io/badge/DRF-3.17-a30000?style=for-the-badge&logo=django&logoColor=white" alt="Django REST Framework" />
  <img src="https://img.shields.io/badge/React-19-149eca?style=for-the-badge&logo=react&logoColor=white" alt="React 19" />
  <img src="https://img.shields.io/badge/Vite-8-646cff?style=for-the-badge&logo=vite&logoColor=white" alt="Vite 8" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL 16" />
  <img src="https://img.shields.io/badge/Redis-7-dc382d?style=for-the-badge&logo=redis&logoColor=white" alt="Redis 7" />
</p>
<p>
  <img src="https://img.shields.io/badge/Session-2025--26-600b0b?style=flat-square" alt="Session 2025-26" />
  <img src="https://img.shields.io/badge/Rubric-C1--C22%20%7C%20U1--U20-c29b68?style=flat-square" alt="Rubrics C1-C22 and U1-U20" />
  <img src="https://img.shields.io/badge/Marks-Server%20calculated-0c4b33?style=flat-square" alt="Server calculated marks" />
  <img src="https://img.shields.io/badge/Registry-AISHE%20%2B%20DHE-336791?style=flat-square" alt="AISHE and DHE registry" />
</p>

</div>

---

## 📑 Contents

- [What is this?](#-what-is-this)
- [Who does what](#-who-does-what)
- [System architecture](#%EF%B8%8F-system-architecture)
- [Workflow 1 · Sign-up and onboarding](#-workflow-1--sign-up-and-onboarding)
- [Workflow 2 · The assessment lifecycle](#-workflow-2--the-assessment-lifecycle)
- [Workflow 3 · Evidence (proof) lifecycle](#-workflow-3--evidence-proof-lifecycle)
- [Workflow 4 · Scoring, awards and certification](#-workflow-4--scoring-awards-and-certification)
- [The institution registry (AISHE + DHE)](#%EF%B8%8F-the-institution-registry-aishe--dhe)
- [Project structure](#-project-structure)
- [Run it locally](#-run-it-locally)
- [Demo data and logins](#-demo-data-and-logins)
- [Tests and quality gates](#-tests-and-quality-gates)
- [Configuration](#%EF%B8%8F-configuration)
- [Deployment](#-deployment)
- [API reference](#-api-reference)
- [Security highlights](#%EF%B8%8F-security-highlights)
- [Video tour](#-video-tour)

---

## 🤔 What is this?

The Government of Haryana gives **NEP Excellence Awards** to its universities and colleges for how well they implement the National Education Policy. This portal runs the whole process online, for the assessment year **1 July 2025 – 30 June 2026**:

| Step | Who | What happens |
|:---:|---|---|
| 1️⃣ | 🏫 Institution | Registers with its **AISHE code**, verifies its email, and is approved by the State Admin |
| 2️⃣ | 🏫 Institution | Fills in the NEP 2026 self-assessment: **C1–C22** for colleges, **U1–U20** for universities |
| 3️⃣ | 🏫 Institution | Uploads **proof documents** for every claim, then submits; the form locks |
| 4️⃣ | 🔍 Screening Committee | Checks every document and **verifies** or **rejects** it, with a reason |
| 5️⃣ | 🖥️ Server | Calculates the marks from the official rubric, using **verified proof only** |
| 6️⃣ | ⚖️ Committee Chair | Accepts or adjusts each parameter's marks (adjustments need a written reason), completes the review and **certifies** |
| 7️⃣ | 🗺️ State Admin | Watches every institution's stage, assigns reviewers, manages users and committees, and pulls reports |

> [!IMPORTANT]
> **Golden rule: `NO VERIFIED PROOF = NO MARKS`.** The browser never calculates marks. People can only *verify*, *accept*, or *adjust with a written reason*, and every action is recorded in an append-only audit log.

---

## 🧭 Who does what

```mermaid
flowchart TD
    SA["🗺️ STATE ADMIN<br/>approves institutions · manages users & committees<br/>assigns reviewers · reports"]
    SA -.oversees.-> U["🏛️ UNIVERSITIES"]
    SA -.oversees.-> C["🏫 COLLEGES"]
    U --> NO["Nodal Officer<br/>fills U1–U20"]
    C --> P["Principal<br/>fills C1–C22"]
    NO -->|submits| Q["📥 COMMITTEE REVIEW QUEUE"]
    P -->|submits| Q
    Q --> R["🔍 Committee Member<br/>verifies / rejects proof"]
    R --> CH["⚖️ Committee Chair<br/>accepts / adjusts marks"]
    CH -->|"Complete Review → Certify"| CERT["🏅 CERTIFIED<br/>score frozen, award tier"]

    style SA fill:#600b0b,color:#fff,stroke:#600b0b
    style CERT fill:#c29b68,color:#fff,stroke:#8a6a3e
    style Q fill:#f5efe6,stroke:#c29b68
```

| Role (`User.role`) | Who | Works in |
|---|---|---|
| `principal` | 🏫 College Principal: fills the college assessment (C1–C22) | `/institution/<name>/<aishe>/dashboard` |
| `nodal_officer`, `university_admin` | 🏛️ University Nodal Officer / Administrator: fills the university assessment (U1–U20) | `/university` |
| `committee` | 🔍 Screening Committee Member: verifies proof, reviews assessments | `/checker/queue` |
| `committee_chair` | ⚖️ Screening Committee Chair: approves marks, **the only role that can certify** | `/checker/queue` |
| `head_admin`, `state_admin`, `admin` | 🗺️ State / DHE administration: oversight, users, committees, reviewer assignment, reports | `/admin` |
| `empowered_committee`, `empowered_committee_chair` | 🏛️ Empowered Committee | `/empowered` |

### 🗺️ What the State Admin can and cannot do

| ✅ Can | ❌ Cannot |
|---|---|
| See **every** institution and its stage, including those that have not started | Fill in an institution's form |
| Approve or reject institution access requests from new sign-ups | Verify or reject evidence (the Committee's job) |
| Create users, invite them, reset passwords, and set up committees and chairs | Accept or change marks outside the workflow |
| Assign or reassign a reviewer (a reason is required for reassignment) | **Certify**; only the Committee Chair can, and the server enforces it |
| Open any assessment read-only; export CSV; read the audit trail | |

**Admin console pages:** Overview (`/admin`) · Institutions (`/admin/institutions`) · Institution requests (`/admin/institution-requests`) · Users (`/admin/users`) · Committees (`/admin/committees`) · Reports (`/admin/reports`).

---

## 🏗️ System architecture

```mermaid
flowchart LR
    B(["🌐 Browser"]) -->|HTTPS| N["Nginx<br/>TLS · static SPA · /api proxy"]
    N -->|"/*"| SPA["⚛️ React 19 SPA<br/>(built with Vite)"]
    N -->|"/api/*"| G["🦄 Gunicorn<br/>Django 6 + DRF"]
    G --> PG[("🐘 PostgreSQL 16<br/>system of record")]
    G --> RD[("⚡ Redis<br/>cache · throttles · lockouts")]
    G --> FS[("📁 Evidence vault<br/>local disk volume")]
    G --> SMTP["✉️ SMTP relay<br/>codes · invitations · resets"]
```

**Django apps:** `authentication` · `college` · `university` · `evidence` · `scoring` · `admin_panel` · `reports` (plus the legacy `nominations` / `forms`).

| Layer | Technology |
|---|---|
| **Frontend** | React 19, React Router 7, Vite 8, Tailwind CSS 3, Framer Motion, Recharts, Lucide icons |
| **Backend** | Django 6.0, Django REST Framework 3.17, custom JWT auth (PyJWT), WhiteNoise, Gunicorn |
| **Database** | PostgreSQL (required in production); SQLite for local development |
| **Cache** | Redis (required in production); in-memory locally |
| **Files** | Evidence vault on the server's disk, with atomic writes, magic-byte type checks and PDF structure checks (pypdf) |
| **Email** | SMTP: sign-up verification codes, invitations, password resets |

---

## 🔐 Workflow 1 · Sign-up and onboarding

New applicants (College Principals and University Nodal Officers) pass **three gates** before they can touch an assessment: the AISHE code check, email verification, and admin approval.

```mermaid
sequenceDiagram
    autonumber
    actor U as Applicant
    participant FE as React app
    participant API as Django API
    participant DB as PostgreSQL
    participant M as SMTP relay
    actor A as State Admin

    U->>FE: Enter AISHE code
    FE->>API: GET /api/auth/college/lookup/ (or university/lookup/)
    API->>DB: Find institution in the AISHE + DHE registry
    API-->>FE: Institution name and district ✔
    U->>FE: Fill the sign-up form
    FE->>API: POST /api/auth/signup/ (or university/register/)
    API->>DB: Create user (email unverified, institution PENDING)
    API->>M: Send verification code by email
    U->>FE: Enter the code
    FE->>API: POST /api/auth/verify-email/otp/
    API->>DB: Mark email verified
    Note over DB,A: The account can sign in, but is NOT yet bound to the institution
    A->>API: Approve request (Admin → Institution requests)
    API->>DB: Bind user to institution, status VERIFIED
    API-->>U: ✅ Access to the institution's assessment
```

- **Verification codes** expire after **10 minutes**, allow **5 attempts**, have a **60-second resend cooldown** and a limit of **5 sends per hour**. All of these can be configured.
- If the email cannot be sent, sign-up returns HTTP 503 and is **rolled back**. The portal never claims it sent an email it did not send.
- Staff accounts (committee members, admins) are created by an administrator and activated through an **invitation link**.
- Logins are protected by a **lockout after repeated failures** and by API throttling (anonymous 120/min, signed-in 240/min).

---

## 🔄 Workflow 2 · The assessment lifecycle

```mermaid
stateDiagram-v2
    direction LR
    [*] --> DRAFT: institution starts the 2025-26 assessment
    DRAFT --> SUBMITTED: every parameter filled + proof uploaded
    SUBMITTED --> UNDER_REVIEW: Committee starts review
    SUBMITTED --> DRAFT: Return for Correction
    UNDER_REVIEW --> DRAFT: Return for Correction (reason required)
    UNDER_REVIEW --> REJECTED: Block (reason required)
    UNDER_REVIEW --> CERTIFIED: Chair completes review and certifies 🏅
    CERTIFIED --> [*]
```

| # | Step | Who | Details |
|:---:|---|---|---|
| 1 | **Fill in** | Principal / Nodal Officer | The form checks the numbers before accepting a submission, e.g. *students placed* cannot exceed *students who took part* |
| 2 | **Upload proof** | Principal / Nodal Officer | Each sub-criterion asks for a specific kind of document. PDF, PNG, JPG, WEBP, DOCX and XLSX are accepted, up to 5 MB each. Uploading alone gives **no** marks |
| 3 | **Submit** | Principal / Nodal Officer | The server checks readiness, then the form locks |
| 4 | **Start Review** | Committee | The assessment moves to `UNDER_REVIEW` |
| 5 | **Verify proof** | Committee | Each document is viewed beside its claim → **Verify** or **Reject** with a structured reason (illegible, incomplete, out of period, mismatched, unsigned…) |
| 6 | **Approve marks** | Chair | For each parameter: **Accept** the calculated score, or **Adjust** it with a written reason |
| 7 | **Return or block** | Committee | **Return for Correction** sends it back to `DRAFT` to fix; **Block** stops it (`REJECTED`) |
| 8 | **Complete Review → Certify** | Chair only | All certification gates must pass; the score and parameter data are then **frozen** |
| 9 | **Watch** | State Admin | Stages shown: *Not started → Filling in → Submitted → Under review → Awaiting certification → Certified* (or *Returned*) |

---

## 📎 Workflow 3 · Evidence (proof) lifecycle

```mermaid
stateDiagram-v2
    direction LR
    [*] --> EVIDENCE_PRESENT: uploaded and linked to a sub-criterion
    EVIDENCE_PRESENT --> EVIDENCE_PENDING: submitted for verification
    EVIDENCE_PENDING --> EVIDENCE_VERIFIED: Committee verifies ✔
    EVIDENCE_PENDING --> EVIDENCE_REJECTED: Committee rejects ✖
    EVIDENCE_VERIFIED --> EVIDENCE_SUPERSEDED: replaced by a new version
    EVIDENCE_REJECTED --> EVIDENCE_SUPERSEDED: corrected document uploaded
    EVIDENCE_PRESENT --> EVIDENCE_WITHDRAWN
    EVIDENCE_PENDING --> EVIDENCE_WITHDRAWN
    EVIDENCE_SUPERSEDED --> [*]
    EVIDENCE_WITHDRAWN --> [*]
```

- Only **`EVIDENCE_VERIFIED`** proof unlocks marks in the scoring engine.
- Files are checked by **magic bytes**, not file names; PDFs are **structurally parsed**; and a content hash is stored to detect tampering.
- Evidence is served **only through authenticated API views**, checked against the user's institution or review assignment. The storage folder is never exposed directly.
- Every action (upload, submit, verify, reject, assign, supersede, withdraw) is written to an **append-only audit log**.

---

## 🧮 Workflow 4 · Scoring, awards and certification

```mermaid
flowchart LR
    I["📝 Claimed values<br/>(form fields)"] --> E{"🧮 Scoring engine<br/>official rubric"}
    V["✅ Verified evidence<br/>per sub-criterion"] --> E
    E --> S["Calculated marks<br/>per parameter"]
    S --> CH{"⚖️ Chair"}
    CH -->|Accept| F["Approved marks"]
    CH -->|"Adjust + reason"| F
    F --> G{"🔒 Certification gates"}
    G -->|all pass| C["🏅 CERTIFIED<br/>total frozen · award tier"]
    G -->|any fails| X["⛔ Blocked with<br/>an explanation"]
```

| | 🏛️ University | 🏫 College |
|---|---|---|
| Framework | `UNIVERSITY_2026` | `COLLEGE_2026` |
| Parameters | **U1 – U20** | **C1 – C22** |
| Maximum | 100 marks | 100 marks |
| Filled by | Nodal Officer | Principal |

- A university is never marked with the college rubric, and a college is never marked with the university rubric. The server rejects any framework mismatch.
- **Certification gates** include:
  - the assessment is not already certified or blocked, and its framework matches;
  - the person certifying is the **Committee Chair**;
  - every parameter is approved, and the scoring engine produces a certified total;
  - the Committee has recorded **Complete Review** for the current submission;
  - no council policy decision is pending.
- **Award tiers** are **Platinum / Gold / Bronze**. The cut-off scores come from the State Council (`NEP_2026_AWARD_THRESHOLDS`). Until they are configured, the portal shows the score and says the thresholds are missing; it does not guess a tier.

---

## 🗂️ The institution registry (AISHE + DHE)

Sign-up only works for institutions that exist in the official registry. Two sources are loaded, **in this order**:

```mermaid
flowchart LR
    D["📄 DHE scholarship registry<br/>1,152 institutions"] -->|import_haryana_institutions| DB[("Registry<br/>College · University")]
    X["📊 AISHE portal exports<br/>1,241 colleges · 382 standalone · 60 universities"] -->|build_aishe_registry| J["aishe_haryana_registry.json"]
    J -->|import_aishe_registry| DB
    L["🔗 aishe_dhe_links.csv<br/>confirmed code corrections"] -->|import_aishe_registry| DB
```

```bash
cd Backend
python manage.py import_haryana_institutions   # 1. DHE registry
python manage.py import_aishe_registry         # 2. AISHE list (re-run after any DHE re-import)
```

- **`C-` and `S-`** codes register as colleges; **`U-`** codes register as universities.
- To refresh the AISHE list from new portal exports, see [`Backend/data/aishe_import/README.md`](Backend/data/aishe_import/README.md).

---

## 📁 Project structure

```text
NEP_HARYANA/
├── Backend/                      # Django 6 + DRF API
│   ├── config/settings/          # base · development · production · ci
│   ├── apps/
│   │   ├── authentication/       # users, roles, JWT, email codes, invitations, AISHE lookup, registry imports
│   │   ├── college/              # college assessments (C1–C22) and the review workflow
│   │   ├── university/           # university assessments (U1–U20) and the review workflow
│   │   ├── evidence/             # evidence vault, validation, verification, assignments, audit log
│   │   ├── scoring/              # rubric engine, field schemas, policy gates, award tiers
│   │   ├── admin_panel/          # State Admin APIs: users, committees, queue, institutions
│   │   ├── reports/              # state and assessment reports, CSV export
│   │   └── nominations/, forms/  # legacy nomination flow
│   └── data/aishe_import/        # DHE + AISHE registry data
├── Frontend/NEP_HARYANA_INT/     # React 19 + Vite single-page app
│   └── src/                      # pages · components · api · context · hooks · utils
├── demo_tools/                   # demo seeding and reset scripts (development only)
├── docs/
│   ├── deployment/               # server / VM requirements (PDF + Markdown)
│   ├── audits/                   # audit and readiness reports
│   └── *.xlsx                    # AISHE source exports
└── package.json                  # `npm run dev` starts the backend and frontend together
```

---

## ⚡ Run it locally

**Prerequisites:** Python 3.12+, Node.js 20+ (CI uses Node 24), Git.

**1 · Backend (Django on port 8000)**

```bash
python -m venv venv
venv\Scripts\activate                     # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r Backend/requirements.txt
cd Backend
python manage.py migrate
python manage.py import_haryana_institutions
python manage.py import_aishe_registry
python manage.py create_dev_users         # development logins only
python manage.py runserver 8000
```

**2 · Frontend (Vite on port 5173)**

```bash
cd Frontend/NEP_HARYANA_INT
npm install
npm run dev
```

Or start both at once from the repository root with **`npm run dev`** (after running `npm install` there). Then open **http://localhost:5173**.

---

## 🧪 Demo data and logins

<details>
<summary><b>▶ Seed a full demo: 5 colleges + 3 universities at different stages</b></summary>

<br/>

`demo_tools/seed_demo.py` drives real assessments through the live API, so **the backend must be running**.

```bash
# from the repo root, with the backend running on :8000
venv\Scripts\python.exe demo_tools\wipe_institutions.py      # ⚠️ deletes ALL institutions and submissions (dev only)
set PYTHONPATH=demo_tools && venv\Scripts\python.exe demo_tools\seed_demo.py
```

| Institution | Login (password `Demo@1234`) | Seeded at | Try |
|---|---|---|---|
| Govt. College, Sector 9, Gurugram | `principal.gurugram@demo.local` | Not started | Fill the form from scratch |
| Dayanand College, Hisar | `principal.hisar@demo.local` | Filled + proof uploaded | **Submit** |
| Govt. College for Women, Rohtak | `principal.rohtak@demo.local` | Submitted | Committee: start review, verify proof |
| Hindu College, Sonepat | `principal.sonepat@demo.local` | Under review, proof verified | Chair: accept / adjust marks |
| Dyal Singh College, Karnal | `principal.karnal@demo.local` | All marks approved | Chair: **Complete Review → Certify** |
| Kurukshetra University | `nodal.kuk@demo.local` | Not started | Fill U1–U20 |
| Maharshi Dayanand University, Rohtak | `nodal.mdu@demo.local` | Submitted | Committee review |
| Guru Jambheshwar University, Hisar | `nodal.gju@demo.local` | All marks approved | Chair: certify |

To make the **Dev College / Dev University** blank again without touching the demo institutions:

```bash
venv\Scripts\python.exe demo_tools\reset_dev_institutions.py
```

</details>

<details>
<summary><b>▶ Development logins (created by <code>create_dev_users</code>)</b></summary>

<br/>

| Role | Email | Password |
|---|---|---|
| 🗺️ Admin | `admin@dev.local` | `DevAdmin@123` |
| 🔍 Committee Member | `committee@dev.local` | `DevCommittee@123` |
| ⚖️ Committee Chair | `chair@dev.local` | `DevChair@123` |
| 🏫 Principal (Dev College) | `principal@dev.local` | `DevPrincipal@123` |
| 🏛️ Nodal Officer (Dev University) | `nodal@dev.local` | `DevNodal@123` |
| 🏛️ University Admin (Dev University) | `univadmin@dev.local` | `DevUnivAdmin@123` |

</details>

> [!WARNING]
> These accounts and scripts are for **local development only**. Never run `create_dev_users`, `seed_demo.py` or the reset scripts against production.

---

## ✅ Tests and quality gates

```bash
# Backend: unit and integration tests
cd Backend
python manage.py test apps

# Frontend: tests, lint gate, build and bundle credential scan
cd Frontend/NEP_HARYANA_INT
npm test
npm run lint:gate
npm run build && npm run check:bundle
```

The CI workflow (`.github/workflows/master_nep-excellence.yml`) runs the same checks as a release gate: migration completeness, `check --deploy` under production settings, backend tests, frontend tests, the lint gate, the build and the bundle scan.

---

## ⚙️ Configuration

Local settings are read from `Backend/.env` (start from `Backend/.env.example`). Production reads them from the service environment and **refuses to start** without the required ones.

| Variable | Purpose | Required in production |
|---|---|:---:|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` on servers (`manage.py` defaults to development) | ✅ |
| `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY` | Signing keys (at least 50 random characters) | ✅ |
| `DATABASE_URL` | PostgreSQL connection string; SQLite is refused | ✅ |
| `REDIS_URL` | Shared cache for lockouts, throttles and sessions | ✅ |
| `ALLOWED_HOSTS`, `FRONTEND_URL` | Public domain; base URL used in email links | ✅ |
| `MEDIA_ROOT` / `EVIDENCE_STORAGE_VAULT` | Evidence folder on a persistent volume | ✅ |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | SMTP relay | ✅ |
| `SECURE_PROXY_SSL_HEADER` | `true` behind Nginx | ✅ |
| `MAX_EVIDENCE_FILE_SIZE` | Upload limit, default 5 MB | optional |
| `EMAIL_OTP_TTL_MINUTES`, `EMAIL_OTP_MAX_ATTEMPTS`, … | Verification code policy | optional |
| `VITE_API_BASE_URL` | Frontend build only, if the API is on another domain | optional |

> [!CAUTION]
> Never commit `.env` files, passwords or keys.

---

## 🚀 Deployment

The portal has **not been deployed yet**. The planned hosting is a set of Ubuntu 24.04 VMs: an application server (Nginx + Gunicorn + Redis), a PostgreSQL server, a staging server, and separate backup storage.

| Document | What it covers |
|---|---|
| [`SERVER_REQUIREMENTS_SUMMARY.pdf`](docs/deployment/SERVER_REQUIREMENTS_SUMMARY.pdf) | 2-page server and VM requirements, for the infrastructure team |
| [`VM_SERVER_REQUIREMENTS.md`](docs/deployment/VM_SERVER_REQUIREMENTS.md) | Full technical assessment: architecture, ports, environment variables, backups, open gaps |
| [`VM_SERVER_REQUIREMENTS_EMAIL.md`](docs/deployment/VM_SERVER_REQUIREMENTS_EMAIL.md) | Covering email for the server request |

---

## 📡 API reference

<details>
<summary><b>▶ Authentication and onboarding</b> · <code>/api/auth/</code></summary>

<br/>

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `college/lookup/?aishe_code=` · `university/lookup/?aishe_code=` | Check an AISHE code against the registry |
| POST | `signup/` · `university/register/` | Register a principal / nodal officer |
| POST | `verify-email/otp/` · `verify-email/otp/resend/` | Verify the emailed code / send a new one |
| POST | `login/` · `refresh/` · `logout/` | JWT sign-in, refresh, sign-out |
| GET | `me/` | Current user and institution binding |
| POST | `forgot-password/` · `reset-password/` | Password reset |
| POST | `activate/verify/` · `activate/confirm/` | Staff invitation activation |

</details>

<details>
<summary><b>▶ College assessments</b> · <code>/api/v1/college/</code></summary>

<br/>

| Method | Endpoint | Purpose |
|---|---|---|
| GET / POST | `colleges/<pk>/assessments/` | List / start a college's assessments |
| GET / PATCH | `college/assessments/<id>/parameters/<code>/` | Read / save a parameter |
| GET | `college/assessments/<id>/readiness/` · `coverage/` | Submission readiness, evidence coverage |
| POST | `college/assessments/<id>/submit/` | Submit (locks the form) |
| GET | `college/review/queue/` | Committee review queue |
| POST | `college/assessments/<id>/review/start/` · `complete/` · `return/` · `block/` | Review workflow |
| POST | `college/assessments/<id>/parameters/<code>/accept-score/` · `adjust-score/` | Chair approves / adjusts marks |
| POST | `college/assessments/<id>/certify/` | Chair certifies |

</details>

<details>
<summary><b>▶ University assessments</b> · <code>/api/v1/university/</code></summary>

<br/>

| Method | Endpoint | Purpose |
|---|---|---|
| GET / POST | `universities/<pk>/assessments/` | List / start a university's assessments |
| GET / PATCH | `university-assessments/<id>/parameters/<code>/` | Read / save a parameter |
| POST | `university-assessments/<id>/submit/` | Submit |
| GET | `university-assessments/review-queue/` | Committee review queue |
| POST | `university-assessments/<id>/start-review/` · `complete-review/` · `return-for-correction/` · `block-review/` | Review workflow |
| POST | `university-assessments/<id>/parameters/<code>/accept-score/` · `adjust-score/` | Chair approves / adjusts marks |
| POST | `university-assessments/<id>/certify/` | Chair certifies |

</details>

<details>
<summary><b>▶ Evidence</b> · <code>/api/evidence/</code></summary>

<br/>

| Method | Endpoint | Purpose |
|---|---|---|
| GET / POST | `/api/evidence/` | List / upload evidence |
| GET | `<id>/document/` · `<id>/download/` | View / download (authorised users only) |
| POST | `<id>/associate/` · `<id>/submit/` · `<id>/withdraw/` | Link to a sub-criterion, submit, withdraw |
| POST | `<id>/verify/` · `<id>/reject/` | Committee decision on a document |
| POST | `associations/<id>/verify/` · `associations/<id>/reject/` | Committee decision per sub-criterion |
| POST | `<id>/assign/` · `<id>/unassign/` | Reviewer assignment |
| GET | `review-queue/` · `coverage/` · `readiness/` · `<id>/history/` | Queue, coverage, audit history |

</details>

<details>
<summary><b>▶ State admin and reports</b> · <code>/api/v1/</code></summary>

<br/>

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `admin/control-centre/summary/` | State overview and "needs attention" lists |
| GET | `admin/institutions/` | Every institution and its stage |
| GET / POST | `admin/users/` · `admin/users/<id>/…` | Users, invitations, password resets, audit, institution access |
| GET / POST | `admin/committees/` · `…/chair/` · `…/members/` | Committees |
| GET | `admin/review-queue/` | State-wide review queue |
| POST | `admin/assessments/<id>/assign/` | Assign / reassign a reviewer |
| GET | `reports/admin/summary/` · `reports/assessments/<id>/…` · `…/export/` | Reports and CSV export |

</details>

---

## 🛡️ Security highlights

- 🔑 **JWT sessions with version stamps.** A password reset, deactivation or role change ends every open session.
- 🚦 **Login lockout and throttling**, backed by Redis in production so all workers share the counters.
- 🧾 **Append-only audit logs** for evidence, reviews, scores and admin actions.
- 🧱 **Permissions enforced by the server.** The UI hides buttons, but the API is what enforces permissions; for example, only the Chair can certify.
- 📁 **Evidence validation and isolation:** magic-byte type checks, PDF parsing, hashing, an atomic-write vault, and access only through authorised views.
- 🏭 **Production refuses unsafe settings:** the development secret key, SQLite, a missing Redis, or console email.

---

## 🎬 Video tour

<div align="center">
  <a href="./website_full_tour.mp4">
    <img src="./website_full_tour.webp" alt="Animated walkthrough of the portal" width="880" />
  </a>
  <p><em>Landing page, institution dashboard, evidence upload, committee review and the State Admin console. Click for the full video.</em></p>
</div>

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:c29b68,50:8a1c1c,100:600b0b&height=120&section=footer" alt="" width="100%" />

<sub>Department of Higher Education (DHE), Government of Haryana • Haryana State Higher Education Council (HSHEC)</sub>

</div>
