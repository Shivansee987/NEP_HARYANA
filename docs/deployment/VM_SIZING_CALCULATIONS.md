# NEP Haryana Excellence Awards 2026: Revised VM Sizing and Calculations

| | |
|---|---|
| **Prepared** | 2026-10-21 |
| **Replaces** | The sizing in `VM_SERVER_REQUIREMENTS.md` §3–§4 and `SERVER_REQUIREMENTS_SUMMARY.md` §2 (2026-10-18/19). Those figures were made without any user or volume data. |
| **New inputs** | At most **250–300 concurrent users**. About **40 applications last year**, so this year is planned for **at most 150 applications**. Upload limits (decided 2026-10-22): **PDFs 5 MB**, other evidence formats (images, DOCX, XLSX) **25 MB**. |

Labels used below: **[VERIFIED]** means read from the code or the demo database. **[ASSUMPTION]** means an input that the calculation depends on, which HSHEC should confirm. **[ESTIMATE]** means a typical figure for this software stack, to be confirmed by the load test (§9).

---

## 1. Result

| # | Role | vCPU | RAM | Storage | Change from the earlier proposal |
|---|---|---|---|---|---|
| 1 | **Production**: Nginx, Gunicorn/Django, PostgreSQL 16 and Redis on one VM | **4** | **8 GB** | **60 GB** SSD (OS, app, database) + **100 GB** SSD separate, expandable evidence volume | Replaces two VMs (App 4/8 + DB 4/8). The separate database VM is dropped. |
| 2 | **Staging / UAT**: all components | **2** | **4 GB** | **60 GB** SSD | was 2 / 4–8 GB / 100 GB |
| 3 | **Backup storage**, off the production VM | – | – | **250 GB** | was 1 TB |
| | **Total** | **6** | **12 GB** | **220 GB SSD + 250 GB backup** | was 10 vCPU, 20–24 GB, ~550 GB SSD + 1 TB backup |

That is **40% fewer vCPU, 40–50% less RAM, 60% less SSD and 75% less backup storage**. All servers run Ubuntu Server 24.04 LTS, and the software list is unchanged.

---

## 2. Inputs

| # | Input | Value used | Source |
|---|---|---|---|
| I1 | Applications | **150** (last year: 40) | HSHEC, 2026-10-21 |
| I2 | Peak concurrent logged-in users | **300** | HSHEC, 2026-10-21 (upper end of 250–300) |
| I3 | Evidence files per complete application | **50** | **[VERIFIED]** The complete demo applications hold 46 (college) and 48 (university) evidence documents. Rounded up to 50. |
| I4 | Average evidence file size | **3 MB** | **[ASSUMPTION]** Scanned PDFs are typically 1–5 MB. PDFs are limited to **5 MB** (`MAX_PDF_FILE_SIZE`) and other formats to **25 MB** (`MAX_EVIDENCE_FILE_SIZE`) **[VERIFIED]**, enforced in the browser and on the server. 146 of the 151 evidence slots also accept images or Office files **[VERIFIED]** (evidence taxonomy). |
| I5 | Re-upload / version headroom | **× 1.5** | **[ASSUMPTION]** Replaced files are kept as superseded versions **[VERIFIED]** (`EvidenceDocument.superseded_by`), and rejected files go to `quarantine/`. |
| I6 | Time between requests for one active user | **10 s** at peak (20 s normal) | **[ASSUMPTION]**, conservative for form filling |
| I7 | API response time / CPU time per request | **200 ms / 50 ms** | **[ESTIMATE]** for Django REST Framework with PostgreSQL on the same host |
| I8 | Memory per Gunicorn worker process | **150 MB** | **[ESTIMATE]** for Django 6 + DRF + pypdf |
| I9 | Submission peak | **40% of applications on the final day**, over 8 working hours, with the busiest hour at **3×** the average | **[ASSUMPTION]**, typical deadline behaviour |
| I10 | Backup retention | **35 days** | Existing operations checklist (to be confirmed, Q8) |

---

## 3. Request load

```
Peak request rate   = concurrent users ÷ time between requests
                    = 300 ÷ 10 s                = 30 requests/second
Normal request rate = 300 ÷ 20 s                = 15 requests/second

Evidence uploads on the final day = 150 × 40% × 50 files     = 3,000 files
Average upload rate               = 3,000 ÷ (8 h × 3,600 s)   = 0.10 files/second
Busiest-hour upload rate          = 0.10 × 3                  = 0.31 files/second
```

30 requests per second means every one of the 300 users clicks or saves every 10 seconds at the same time. This is a deliberately high figure.

---

## 4. CPU

```
Django CPU      = 30 req/s × 0.05 s                       = 1.50 cores
PostgreSQL CPU  ≈ 40% of Django CPU                       = 0.60 cores
Upload checks   = 0.31 files/s × 0.5 s (PDF parse, hash)  = 0.16 cores
Nginx + Redis + OS                                        ≈ 0.25 cores
                                                         -------------
Peak demand                                              ≈ 2.5 cores
```

| VM size | Peak utilisation | Assessment |
|---|---|---|
| 2 vCPU | 2.5 ÷ 2 = **125%** | Overloaded at the deadline peak. Requests queue and slow down. |
| **4 vCPU** | 2.5 ÷ 4 = **63%** | **Within the 70% planning limit.** Normal load (15 req/s) is about 1.3 cores, or 33%. |
| 8 vCPU (earlier proposal, single-VM option) | 31% | More than needed |

**Result: 4 vCPU.**

---

## 5. Concurrency (Gunicorn workers)

By Little's law, the number of requests in progress equals the arrival rate multiplied by the response time:

```
API requests in progress = 30 req/s × 0.2 s                       = 6
Uploads in progress      = 0.31 files/s × 2 s (incl. PDF parse)   = 0.6 → allow a burst of 5
                                                                  ---
Request slots needed                                              ≈ 11
```

Configuration: **5 worker processes × 3 threads = 15 slots** (`gunicorn --workers 5 --threads 3`). This leaves about 35% spare. Nginx receives the whole upload before passing it to Gunicorn, so a user's slow connection does not hold a worker.

---

## 6. Memory

| Component | Calculation | RAM |
|---|---|---|
| Operating system, monitoring agents | | 1.00 GB |
| Gunicorn workers | 5 × 150 MB | 0.75 GB |
| Files held in memory (worst case) | 15 slots × 25 MB × 2 (parsing overhead). Downloads are read fully into memory **[VERIFIED]**. | 0.75 GB |
| PostgreSQL | shared_buffers 512 MB + 20 connections × 4 MB work_mem + 128 MB maintenance | 0.75 GB |
| Redis | lockout, throttle counters and a user cache for 300 users | 0.10 GB |
| Nginx | | 0.05 GB |
| **Total at peak** | | **≈ 3.4 GB** |

| VM size | Peak use | Assessment |
|---|---|---|
| 4 GB | **85%** | Too little room. A worst-case burst of large uploads could cause swapping or an out-of-memory kill. |
| **8 GB** | **43%** | **Recommended.** The remainder is used as disk cache, which keeps the whole database and recently used evidence in memory. A 4 vCPU VM normally comes with 8 GB anyway. |

**Result: 8 GB.**

---

## 7. Storage

### 7.1 Evidence volume

```
Evidence = applications × files per application × average size × version headroom
         = 150 × 50 × 3 MB × 1.5
         = 33,750 MB  ≈ 34 GB
```

| Scenario | Calculation | Size |
|---|---|---|
| Last year's volume (40 applications) | 40 × 50 × 3 MB × 1.5 | 9 GB |
| **Planning case** | 150 × 50 × 3 MB × 1.5 | **34 GB** |
| Larger files (5 MB average) | 150 × 50 × 5 MB × 1.5 | 56 GB |
| Theoretical ceiling (every file at its limit, no re-uploads) | 150 × (49 × 25 MB + 1 × 5 MB) | 185 GB (not realistic) |

Because almost every slot accepts 25 MB image or Office files, the limits do not cap storage at a small figure. **Allocate 100 GB** on an expandable volume (LVM or cloud disk), with an alert at 70%. 100 GB holds the planning case three times over and still fits an average file size of up to about 9 MB. The earlier 250 GB was based on all 1,152 institutions applying.

### 7.2 OS / application / database disk

| Item | Size |
|---|---|
| Ubuntu, packages, Python virtual environment, built frontend | 15 GB |
| PostgreSQL data + WAL. The demo database is 2.5 MB for 3,769 rows including 8 complete demo applications **[VERIFIED]**. Even at 5 MB per application: 150 × 5 MB = 0.75 GB, doubled for indexes and WAL. | 2 GB |
| Local copy of the latest backup before it is shipped off the VM | 5 GB |
| Logs, 30 days compressed (≈ 160 MB/day uncompressed at 15 req/s for 10 h) | 2 GB |
| Temporary space for uploads larger than 2.5 MB **[VERIFIED]** | 5 GB |
| Free space for upgrades, at least 50% | 31 GB |
| **Total** | **60 GB** |

### 7.3 Backup storage

```
Database: daily compressed dump ≤ 0.5 GB × 35 days                     ≈ 18 GB
Evidence: weekly full copies without deduplication, 34 GB × 5 weeks    ≈ 170 GB
                                                                       --------
Required (simple backup tool, no deduplication)                        ≈ 188 GB
```

With a deduplicating tool (restic, borg or storage snapshots), the evidence needs only about 1.2 × 34 GB ≈ 41 GB. **250 GB** covers the simple method with a 30% margin. It also covers deduplicated backups if the evidence volume fills to 100 GB (120 GB + 18 GB). If files turn out much larger than planned, use a deduplicating tool.

---

## 8. Bandwidth

| Traffic in the busiest hour | Calculation | Rate |
|---|---|---|
| Evidence uploads | 0.31 files/s × 3 MB × 8 bits | 7.4 Mbps |
| Evidence downloads by reviewers (assumed equal to uploads) | | 7.4 Mbps |
| First page load (2.7 MB application, before compression) for all 300 users in one hour | 300 × 2.7 MB × 8 ÷ 3,600 s | 1.8 Mbps |
| API traffic | 30 req/s × 20 KB × 8 bits | 4.8 Mbps |
| **Total** | | **≈ 21 Mbps** |

**At least 50 Mbps dedicated, or 100 Mbps shared.** At 50 Mbps, a 5 MB PDF takes under 1 second of line time and a 25 MB file about 4 seconds. In practice, the user's own connection is usually the limit.

---

## 9. Why one production VM is enough

- **The database is small.** About 1–2 GB at the end of the cycle, so it sits entirely in memory on the same VM. A second VM adds a network hop, a second server to patch and a second firewall rule set, but no extra capacity is needed.
- **Availability is unchanged.** The earlier two-VM design also had a single application server and a single database server. Either one failing stopped the service. Recovery in both designs relies on the backups in §7.3.
- **Scaling is simple if needed.** The VM can be resized to 6–8 vCPU / 12–16 GB without code changes. PostgreSQL can move to its own VM or a managed service later by changing `DATABASE_URL`.
- **Two separate disks are still kept.** Evidence lives on its own volume, so it can grow and be backed up separately from the OS disk.

The VM must be allowed to resize quickly (a reboot within an hour) if the load test or the first week of live use shows CPU or memory above 70%.

---

## 10. Confirming these figures

The **[ESTIMATE]** figures (I7, I8) are typical values, not measurements from this application. Before the submission window opens, run a load test on staging:

| Item | Target |
|---|---|
| Virtual users | 300, each acting every 10 s: login, open the assessment, save, upload a 3–5 MB PDF and a 25 MB image, download evidence |
| Response time | 95% of requests under 1 s; uploads under 5 s |
| Error rate | Under 1% |
| CPU / memory | Under 70%. Staging is half the size of production, so judge staging at 150 users and expect production to handle 300. |

**One figure from HSHEC would replace the main assumption:** the total size of last year's evidence for the 40 applications. Dividing it by 40 gives the actual size per application, which replaces the estimate of 50 × 3 MB × 1.5 = 225 MB.

---

## 11. Not changed

The software stack, network ports, domain/SSL/email requirements, security baseline and open points (Q3–Q13) in `VM_SERVER_REQUIREMENTS.md` still apply, with two changes:

- On the single VM, PostgreSQL listens on localhost only, so the internal port 5432 rule between VMs is no longer needed.
- The request size allowed by Nginx and any firewall or WAF stays at **30 MB** (`client_max_body_size 30M`: a 25 MB file plus form overhead).
