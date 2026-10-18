**To:** [Recipient Name], [Designation], [Department / Data Centre, e.g. State Data Centre / NIC / HARTRON]
**Cc:** [Project Nodal Officer, HSHEC]; [Technical Lead]
**Subject:** Request for VM provisioning – NEP Haryana Excellence Awards 2026 web portal (Production and Staging)

---

Dear [Recipient Name],

On behalf of [Department / HSHEC], I am writing to request server capacity for the **NEP Haryana Excellence Awards 2026** portal. Higher-education institutions in Haryana will use the portal to register, submit their NEP 2026 self-assessments and supporting evidence documents, and track review by state committees and administrators.

The application is a React web front end served as static files, a Python/Django REST API, and a PostgreSQL database. Evidence documents (PDF, images, DOCX and XLSX, up to 25 MB each) are stored on the application server's disk. The system needs no background workers or scheduled jobs. This is a new application with no existing hosting, so these servers will be its first production and staging environments.

**1. Requested virtual machines (initial sizing)**

We do not yet have confirmed user-load figures. The sizes below are a conservative starting point, to be confirmed by a load test on the staging VM before the submission window opens.

| # | Role | Environment | OS | vCPU | RAM | Storage |
|---|---|---|---|---|---|---|
| 1 | Application / web server (Nginx, Gunicorn/Django, Redis) | Production | Ubuntu Server 24.04 LTS, 64-bit | 4 | 8 GB | 60 GB SSD (OS/app) + 250 GB SSD separate expandable data volume (evidence files) |
| 2 | Database server (PostgreSQL 16) | Production | Ubuntu Server 24.04 LTS, 64-bit | 4 | 8 GB | 40 GB SSD (OS) + 100 GB SSD (database) |
| 3 | Staging / UAT (all components) | Staging | Ubuntu Server 24.04 LTS, 64-bit | 2 | 4 GB (8 GB preferred) | 100 GB SSD |
| 4 | Backup storage, separate from the production VMs | Shared | n/a | n/a | n/a | 1 TB to start, expandable |

If a managed PostgreSQL service is available in the data centre, it may replace VM 2. If only one production VM can be allocated, 8 vCPU / 16 GB RAM with separate OS, database and evidence volumes would be workable.

**2. Software**
Python 3.12, Nginx, PostgreSQL 16 (version 14 at minimum), Redis 7 and PostgreSQL client tools, from standard OS repositories. Node.js is not needed on the servers.

**3. Network and access**
- Inbound: HTTPS (443) from the internet to VM 1; HTTP (80) only to redirect to HTTPS.
- Inbound: SSH (22) only from the administration network, VPN or bastion. Key-based access, not open to the internet.
- Internal: PostgreSQL (5432) from VM 1 to VM 2 only. Redis and the application port stay local to VM 1.
- Outbound from VM 1: SMTP submission (587 with STARTTLS, or 465) to the approved mail relay; HTTPS (443) to OS and package repositories, or a local mirror or proxy; NTP (123).
- Firewall/WAF or load-balancer limits on request size must allow uploads of at least 30 MB.
- Bandwidth: at least 100 Mbps shared uplink to start, to be reviewed after load testing.

**4. Domain, certificate and email**
- One sub-domain, e.g. [app-subdomain].haryana.gov.in, pointing to VM 1, with a TLS certificate from a browser-trusted CA and a renewal arrangement.
- An authenticated SMTP relay and an approved sender address for account verification, invitation and password-reset emails, with SPF, DKIM and DMARC records for the sender domain. Account sign-up cannot be completed without working email delivery.

**5. Backup, monitoring and security**
- Daily PostgreSQL backups with point-in-time recovery, and regular backups of the evidence volume, kept together and stored off the production VMs. Retention and RPO/RTO to be agreed.
- Host monitoring (CPU, memory, disk, with an alert at 70% on the evidence volume), uptime checks and certificate-expiry alerts.
- Standard OS hardening and security patching. Antivirus scanning of the evidence volume if your policy requires it.
- All application secrets (database, mail and signing keys) will be supplied by our team through a secure channel and will not be sent by email.

**6. Points for your confirmation**
1. The hosting facility, and whether Ubuntu 24.04 LTS is permitted (or RHEL/Rocky 9 if mandated).
2. Availability of managed PostgreSQL, a managed backup service, a load balancer or WAF.
3. The SMTP relay to be used, and who manages the sender domain's DNS records.
4. Backup retention requirements and any off-site copy requirement.
5. The approved deployment access method (VPN/bastion, CI-based SSH, or scheduled manual windows).
6. Any security audit (e.g. by a CERT-In empanelled auditor) required before go-live.
7. Log retention requirements, and whether logs should be forwarded to a central SIEM.

We would be grateful if the staging VM could be provisioned first, so that migration, email and load testing can begin while the production VMs are prepared. Our team will share a detailed technical requirements document and is available for a call to coordinate the provisioning timeline.

Thank you for your support.

Yours sincerely,

[Sender Name]
[Designation]
[Department / Organisation]
[Phone] | [Official Email]
