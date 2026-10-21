# NEP Haryana Excellence Awards 2026: Server and VM Requirements

| | |
|---|---|
| **Application** | NEP Haryana Excellence Awards 2026 web portal |
| **Purpose** | Request for staging and production hosting (first deployment) |
| **Date** | 21-10-2026 (revised sizing; first issued 19-10-2026) |
| **Detailed reference** | `VM_SIZING_CALCULATIONS.md` (sizing calculations) and `VM_SERVER_REQUIREMENTS.pdf` (full technical assessment) |

## 1. Application overview

- **Users:** higher-education institutions of Haryana, state administrators and review committees. Sized for **at most 150 applications** (about 40 last year) and **250–300 concurrent users**.
- **Front end:** React web application, served as static files.
- **Back end:** Python 3.12 / Django REST API, run by Gunicorn behind Nginx.
- **Database:** PostgreSQL 16.
- **Evidence files:** PDF, image, DOCX and XLSX, up to 5 MB each, stored on a dedicated disk volume.
- **Background jobs:** none.

## 2. Virtual machines

Sizes are calculated for 300 concurrent users and 150 applications (see `VM_SIZING_CALCULATIONS.md`), and are to be confirmed by a load test on staging before the submission window opens.

| # | Role | Env | OS | vCPU | RAM | Storage |
|---|---|---|---|---|---|---|
| 1 | Production server: Nginx, Gunicorn/Django, PostgreSQL 16, Redis | Production | Ubuntu Server 24.04 LTS, 64-bit | 4 | 8 GB | 60 GB SSD (OS, app, database) + 75 GB SSD separate, expandable evidence volume |
| 2 | Staging / UAT: all components on one VM | Staging | Ubuntu Server 24.04 LTS, 64-bit | 2 | 4 GB | 60 GB SSD |
| 3 | Backup storage, separate from the production VM | Shared | n/a | n/a | n/a | 250 GB, expandable |
| | **Total** | | | **6** | **12 GB** | **195 GB SSD + 250 GB backup** |

The production VM should be resizable (to 6–8 vCPU / 12–16 GB) at short notice if the load test or the first week of live use shows sustained CPU or memory use above 70%.

## 3. Server software

| Component | Version | Where |
|---|---|---|
| Python (with venv) | 3.12 | VM 1, VM 2 |
| Nginx | OS package | VM 1, VM 2 |
| Gunicorn (systemd service) | 26.x, from the application's requirements | VM 1, VM 2 |
| PostgreSQL server and client tools | 16 (14 minimum), localhost only | VM 1, VM 2 |
| Redis | 7.x, localhost only, password-protected | VM 1, VM 2 |
| Certbot or state CA tooling | current | VM 1, VM 2 |

Node.js is **not** needed on the servers; the front end is built beforehand.

## 4. Network and firewall

| Direction | From → To | Port | Purpose |
|---|---|---|---|
| Inbound | Internet → VM 1 | 443/TCP | HTTPS portal and API |
| Inbound | Internet → VM 1 | 80/TCP | Redirect to HTTPS only |
| Inbound | Admin VPN / bastion → all VMs | 22/TCP | SSH, key-based only; not open to the internet |
| Local only | VM 1 | 5432, 6379, 8000 | PostgreSQL, Redis, Gunicorn; never exposed |
| Outbound | VM 1 → mail relay | 587/TCP (or 465) | Verification, invitation and password-reset emails |
| Outbound | All VMs → package mirrors | 443/TCP | Security updates (proxy/mirror acceptable) |
| Outbound | All VMs → NTP | 123/UDP | Time synchronisation |

- Firewall, WAF or load balancer must allow request bodies of **at least 10 MB** (evidence uploads of up to 5 MB).
- Bandwidth: **at least 50 Mbps dedicated or 100 Mbps shared** (calculated peak about 21 Mbps).

## 5. Domain, SSL and email

- One sub-domain, e.g. `[app-subdomain].haryana.gov.in`, pointing to VM 1.
- SSL/TLS certificate from a browser-trusted CA, with a renewal arrangement.
- Authenticated **SMTP relay** and an approved sender address. Sign-up cannot be completed without working email.
- **SPF, DKIM and DMARC** DNS records for the sender domain.

## 6. Backup, monitoring and security

- Daily PostgreSQL backups with point-in-time recovery, plus regular backups of the evidence volume, taken together and stored off the production VM.
- Retention and RPO/RTO to be agreed.
- Monitoring of CPU, RAM and disk (alert at **70%** on the evidence volume), uptime checks and certificate-expiry alerts.
- OS hardening and regular security patching; antivirus scanning of the evidence volume if policy requires it.
- Passwords and keys are exchanged through a secure channel, never by email.

## 7. Access needed by the project team

- SSH with sudo on VM 1 and VM 2 via VPN or bastion, key-based.
- An agreed deployment method: SSH from CI, or scheduled manual windows.

## 8. Points for confirmation

1. Hosting facility, and whether Ubuntu 24.04 LTS is permitted (or RHEL/Rocky 9).
2. Availability of managed backups, load balancer or WAF.
3. SMTP relay and sender address; who manages the sender domain's DNS.
4. Backup retention and off-site copy requirement.
5. Approved access and deployment method.
6. Whether a security audit (e.g. a CERT-In empanelled auditor) is required before go-live.
7. Log retention, and whether logs go to a central SIEM.

## 9. Requested sequence

1. **Staging VM (VM 2) first**, for installation, email and load testing.
2. Production VM (VM 1) and backup storage after staging is validated.
