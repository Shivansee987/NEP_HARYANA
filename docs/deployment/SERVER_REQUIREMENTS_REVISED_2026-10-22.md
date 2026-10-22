# NEP Haryana Excellence Awards 2026: Revised Server Requirements and Sizing Calculations

| | |
|---|---|
| **Application** | NEP Haryana Excellence Awards 2026 web portal |
| **Date** | 22-10-2026 |
| **Replaces** | The sizing issued on 19-10-2026 (two production VMs, about 550 GB SSD and 1 TB backup) |
| **Planning load** | At most **150 applications** (about 40 last year) and **250–300 concurrent users** (HSHEC, 21-10-2026) |

At 150 applications and 300 concurrent users, the requirement drops to **one production VM, one staging VM and 250 GB of backup**. That is about 40% fewer vCPUs and less than half the storage of the earlier proposal.

## 1. Revised requirement

| # | Server | vCPU | RAM | Storage |
|---|---|---|---|---|
| 1 | **Production**: web server, application, PostgreSQL 16 database and Redis cache on one VM | **4** | **8 GB** | **60 GB** SSD system disk + **100 GB** SSD separate, expandable evidence disk |
| 2 | **Staging / UAT**: all components on one VM | **2** | **4 GB** | **60 GB** SSD |
| 3 | **Backup storage**, separate from the production VM | – | – | **250 GB**, expandable |
| | **Total** | **6** (was 10) | **12 GB** (was 20–24) | **220 GB SSD + 250 GB backup** (was ~550 GB + 1 TB) |

- All servers: Ubuntu Server 24.04 LTS, 64-bit.
- The production VM must be **resizable to 6–8 vCPU / 12–16 GB within a few hours** if the load test or the first week of live use shows CPU or memory above 70%.
- Bandwidth: **50 Mbps dedicated or 100 Mbps shared**.

## 2. Calculation inputs

| # | Input | Value used | Basis |
|---|---|---|---|
| I1 | Applications | **150** (last year: 40) | Given by HSHEC |
| I2 | Peak concurrent users | **300** | Given by HSHEC (upper end of 250–300) |
| I3 | Evidence files per application | **50** | Measured: a complete demo application in the code has 46–48 evidence files, rounded up |
| I4 | Average evidence file size | **3 MB** | Assumption. Upload limits are PDF 5 MB; images, DOCX and XLSX 25 MB |
| I5 | Re-upload headroom | **× 1.5** | Assumption. Replaced files are kept as older versions |
| I6 | Time between actions for one user | **10 s** at peak (20 s normal) | Assumption, deliberately high |
| I7 | Response time / processor time per request | **0.2 s / 0.05 s** | Typical for this software stack (Django, PostgreSQL); to be measured |
| I8 | Memory per application worker process | **150 MB** | Typical for this software stack; to be measured |
| I9 | Deadline peak | 40% of applications on the last day, over 8 hours; busiest hour 3× the average | Assumption, typical deadline behaviour |
| I10 | Backup retention | **35 days** | To be confirmed by the data centre |

## 3. Calculations

### 3.1 Requests

```
Peak request rate   = 300 users ÷ one action every 10 s   = 30 requests/second
Normal request rate = 300 users ÷ one action every 20 s   = 15 requests/second

Uploads on the last day = 150 × 40% × 50 files            = 3,000 files
Average upload rate     = 3,000 ÷ (8 h × 3,600 s)         = 0.10 files/second
Busiest-hour upload rate = 0.10 × 3                       = 0.31 files/second
```

30 requests per second means everyone clicking at once. This is deliberately high.

### 3.2 CPU

```
Application   = 30 requests/s × 0.05 s                    = 1.50 cores
Database      ≈ 40% of application CPU                    = 0.60 cores
Upload checks = 0.31 files/s × 0.5 s (PDF check, hash)    = 0.16 cores
Web server, cache and operating system                    ≈ 0.25 cores
                                                          ------------
Peak demand                                               ≈ 2.5 cores
```

| VM size | Peak use | Assessment |
|---|---|---|
| 2 vCPU | 125% | Overloaded; the portal would slow down at the deadline |
| **4 vCPU** | **63%** | **Inside the usual 70% planning limit.** Normal load is about 33% |

### 3.3 Concurrent requests

```
API requests in progress = 30 requests/s × 0.2 s          = 6
Room for uploads at the same time                          = 5
                                                          ---
Requests in progress at peak                               ≈ 11
```

Suggested configuration: **5 worker processes × 3 threads = 15 at once**, about 35% spare. The web server receives the whole upload before handing it to the application, so a slow user connection does not hold a worker.

### 3.4 Memory

| Component | Calculation | RAM |
|---|---|---|
| Operating system and monitoring | | 1.00 GB |
| Application workers | 5 × 150 MB | 0.75 GB |
| Files held in memory (worst case) | 15 at once × 25 MB × 2 | 0.75 GB |
| PostgreSQL | 512 MB buffers + connections + maintenance | 0.75 GB |
| Redis cache and Nginx web server | | 0.15 GB |
| **Total at peak** | | **≈ 3.4 GB** |

| VM size | Use at peak | Assessment |
|---|---|---|
| 4 GB | 85% | Too little room; a burst of large uploads could crash the service |
| **8 GB** | **43%** | **Recommended.** The rest is used as disk cache, which keeps the whole database in memory |

### 3.5 Evidence storage

```
Evidence = applications × files × average size × re-upload headroom
         = 150 × 50 × 3 MB × 1.5                           ≈ 34 GB
```

| Case | Calculation | Size |
|---|---|---|
| Last year's volume | 40 × 50 × 3 MB × 1.5 | 9 GB |
| **Planning case** | 150 × 50 × 3 MB × 1.5 | **34 GB** |
| Larger files (5 MB average) | 150 × 50 × 5 MB × 1.5 | 56 GB |

**Allocated: 100 GB** on an expandable disk, with an alert at 70%. It still fits if the average file turns out to be about 9 MB.

### 3.6 Database

The demo database holds 8 complete applications in 2.5 MB. Even at 150 applications × 5 MB, doubled for indexes and logs, the database is **under 2 GB**. It fits in memory on the same VM, so **a separate database VM is not needed**.

### 3.7 System disk (60 GB)

| Item | Size |
|---|---|
| Ubuntu, packages, application and built front end | 15 GB |
| PostgreSQL data and transaction logs | 2 GB |
| Local copy of the latest backup before it is shipped off the VM | 5 GB |
| Logs, 30 days compressed | 2 GB |
| Temporary space for uploads | 5 GB |
| Free space for upgrades (at least 50%) | 31 GB |
| **Total** | **60 GB** |

### 3.8 Backup storage

Evidence is backed up **daily**, not weekly. Weekly copies would lose up to a week of colleges' uploads if the disk failed near the deadline. Daily full copies would need about 1.2 TB, so the evidence uses a **deduplicating backup tool** (restic, borg or storage snapshots), which stores each file once plus about 20% overhead.

```
Database: daily compressed copy ≤ 0.5 GB × 35 days, plus transaction logs   ≈ 20 GB
Evidence: daily deduplicated backups, 34 GB × 1.2                          ≈ 41 GB
                                                                           --------
Planning case                                                              ≈ 61 GB
If the evidence disk fills (100 GB × 1.2 + 20 GB)                          ≈ 140 GB
```

**Allocated: 250 GB**, which covers a full evidence disk with about 45% to spare.

### 3.9 Bandwidth

| Traffic in the busiest hour | Calculation | Rate |
|---|---|---|
| Evidence uploads | 0.31 files/s × 3 MB × 8 bits | 7.4 Mbps |
| Evidence downloads by reviewers (assumed equal to uploads) | | 7.4 Mbps |
| API traffic | 30 requests/s × 20 KB × 8 bits | 4.8 Mbps |
| First page loads (2.7 MB, 300 users in one hour) | 300 × 2.7 MB × 8 ÷ 3,600 s | 1.8 Mbps |
| **Total** | | **≈ 21 Mbps** |

So **50 Mbps dedicated or 100 Mbps shared** is enough. At 50 Mbps a 5 MB PDF takes under 1 second and a 25 MB file about 4 seconds.

### 3.10 Why one production VM is enough

- **The database is small** (under 2 GB) and fits in memory on the same VM. A second VM adds a server to patch and a network hop, but no capacity that is needed.
- **Availability does not get worse.** The old design also had a single application server and a single database server, so either one failing stopped the service. Recovery in both designs depends on backups (§5).
- **Scaling is simple.** The VM can be resized without code changes, and the database can move to its own server later if needed.
- **Evidence stays on its own disk**, so it can grow and be backed up separately.

## 4. Network and firewall

| Direction | From → To | Port | Purpose |
|---|---|---|---|
| Inbound | Internet → VM 1 | 443/TCP | HTTPS portal and API |
| Inbound | Internet → VM 1 | 80/TCP | Redirect to HTTPS only |
| Inbound | Admin VPN / bastion → all VMs | 22/TCP | SSH, key-based only |
| Local only | VM 1 | 5432, 6379, 8000 | PostgreSQL, Redis, application; never exposed |
| Outbound | VM 1 → mail relay | 587/TCP (or 465) | Verification and password-reset emails |
| Outbound | **VM 1, VM 2 → Cloudinary API (`api.cloudinary.com`)** | **443/TCP** | **Nomination document uploads. Without this rule those uploads fail.** Proxy acceptable. |
| Outbound | All VMs → package mirrors | 443/TCP | Security updates |
| Outbound | All VMs → NTP | 123/UDP | Time synchronisation |

- Firewall, WAF or load balancer must allow request bodies of **at least 30 MB** (a 25 MB file plus form data).
- One `haryana.gov.in` sub-domain with a trusted SSL certificate, an authenticated **SMTP relay**, and SPF/DKIM/DMARC records for the sender domain.

## 5. Backup and recovery

The production server is a single VM with no automatic failover. Recovery depends on the following, which must be in place **before the submission window opens**.

| Item | Requirement |
|---|---|
| Database backup | Daily backup plus continuous transaction-log (WAL) archiving, for point-in-time recovery |
| Evidence backup | **Daily** incremental backup with a deduplicating tool |
| Retention | 35 days, stored off the production VM |
| Maximum data loss (RPO) | **1 hour** for the database, **24 hours** for evidence files |
| Recovery time (RTO) | **4 hours** to rebuild the service on a new VM from backup |
| VM snapshot | Just before the submission window opens, and before every deployment |
| Restore drill | A full restore practised on staging before go-live |

## 6. Load test before go-live

The processor time per request (0.05 s) and memory per worker (150 MB) are typical values, not measurements. They must be confirmed before submissions open.

1. **Staging, 150 users:** a trial run to find errors and tune the test. Staging has half the capacity of production, so it would fail a 300-user test whatever production can do.
2. **Production, 300 users:** the real test, run before go-live while the VM holds no real data. Test data is removed afterwards.

| Pass target | Value |
|---|---|
| Test scenario | 300 users, each acting every 10 s: log in, open the assessment, save, upload a 3–5 MB PDF and a 25 MB image, download evidence |
| Response time | 95% of requests under 1 s; uploads under 5 s, including Cloudinary uploads |
| Error rate | Under 1% |
| CPU and memory | Under 70% on the production VM |

## 7. Assumptions to confirm

- **Average file size (3 MB)** is an assumption. If HSHEC can give the total size of last year's evidence for the 40 applications, dividing it by 40 gives the real size per application and replaces the estimate of 50 × 3 MB × 1.5 = 225 MB.
- **Processor time and memory per request** are typical values; the load test in §6 confirms them.
- **The production VM must be resizable at short notice** in case real use turns out heavier.

## 8. Points for confirmation

1. **Cloudinary:** approval of outbound HTTPS to `api.cloudinary.com`, and whether nomination documents may be stored with a third-party provider whose servers may be outside India. If not, the portal must be changed to keep them on the evidence disk, which needs development time before go-live.
2. **Recovery:** agreement to the 1-hour / 24-hour data-loss limits and the 4-hour recovery time; availability of VM snapshots.
3. **Resizing:** whether the production VM can be resized within a few hours during the submission window.
4. **Evidence size:** last year's total evidence size (see §7).
5. Hosting facility, and whether Ubuntu 24.04 LTS is permitted.
6. SMTP relay and sender address; who manages the sender domain's DNS.
7. Whether a security audit (e.g. a CERT-In empanelled auditor) is required before go-live.

## 9. Requested sequence

1. **Staging VM first**, for installation, email, the restore drill and the 150-user trial.
2. **Production VM and backup storage** once staging is validated.
3. **300-user load test on production**, then go-live.
