# NEP Haryana Excellence Awards 2026: Server and VM Requirements

| | |
|---|---|
| **Application** | NEP Haryana Excellence Awards 2026 web portal |
| **Purpose** | Request for staging and production hosting (first deployment) |
| **Date** | 19-10-2026 |
| **Detailed reference** | `VM_SERVER_REQUIREMENTS.pdf` (full technical assessment) |

## 1. Application overview

- **Users:** higher-education institutions of Haryana (about 1,700 on the AISHE list), state administrators and review committees.
- **Front end:** React web application, served as static files.
- **Back end:** Python 3.12 / Django REST API, run by Gunicorn behind Nginx.
- **Database:** PostgreSQL 16.
- **Evidence files:** PDF, image, DOCX and XLSX, up to 25 MB each, stored on a dedicated disk volume.
- **Background jobs:** none.

## 2. Virtual machines

Sizes are a conservative starting point, to be confirmed by a load test on staging before the submission window opens.

| # | Role | Env | OS | vCPU | RAM | Storage |
|---|---|---|---|---|---|---|
| 1 | Application / web server: Nginx, Gunicorn/Django, Redis | Production | Ubuntu Server 24.04 LTS, 64-bit | 4 | 8 GB | 60 GB SSD (OS + app) + 250 GB SSD separate, expandable evidence volume |
| 2 | Database server: PostgreSQL 16 | Production | Ubuntu Server 24.04 LTS, 64-bit | 4 | 8 GB | 40 GB SSD (OS) + 100 GB SSD (database) |
| 3 | Staging / UAT: all components on one VM | Staging | Ubuntu Server 24.04 LTS, 64-bit | 2 | 4 GB (8 GB preferred) | 100 GB SSD |
| 4 | Backup storage, separate from production VMs | Shared | n/a | n/a | n/a | 1 TB to start, expandable |
| | **Total** | | | **10** | **20 GB** (24 GB preferred) | **~550 GB SSD + 1 TB backup** |

**Alternatives:** a managed PostgreSQL service can replace VM 2. If only one production VM is possible: 8 vCPU / 16 GB RAM with separate OS, database and evidence volumes.

## 3. Server software

| Component | Version | Where |
|---|---|---|
| Python (with venv) | 3.12 | VM 1, VM 3 |
| Nginx | OS package | VM 1, VM 3 |
| Gunicorn (systemd service) | 26.x, from the application's requirements | VM 1, VM 3 |
| PostgreSQL server | 16 (14 minimum) | VM 2, VM 3 |
| PostgreSQL client tools | same major version | VM 1 (backups) |
| Redis | 7.x, localhost only, password-protected | VM 1, VM 3 |
| Certbot or state CA tooling | current | VM 1, VM 3 |

Node.js is **not** needed on the servers; the front end is built beforehand.

## 4. Network and firewall

| Direction | From → To | Port | Purpose |
|---|---|---|---|
| Inbound | Internet → VM 1 | 443/TCP | HTTPS portal and API |
| Inbound | Internet → VM 1 | 80/TCP | Redirect to HTTPS only |
| Inbound | Admin VPN / bastion → all VMs | 22/TCP | SSH, key-based only; not open to the internet |
| Internal | VM 1 → VM 2 | 5432/TCP | PostgreSQL |
| Local only | VM 1 | 6379, 8000 | Redis, Gunicorn; never exposed |
| Outbound | VM 1 → mail relay | 587/TCP (or 465) | Verification, invitation and password-reset emails |
| Outbound | All VMs → package mirrors | 443/TCP | Security updates (proxy/mirror acceptable) |
| Outbound | All VMs → NTP | 123/UDP | Time synchronisation |

- Firewall, WAF or load balancer must allow request bodies of **at least 30 MB** (evidence uploads).
- Bandwidth: **at least 100 Mbps** shared uplink to start.

## 5. Domain, SSL and email

- One sub-domain, e.g. `[app-subdomain].haryana.gov.in`, pointing to VM 1.
- SSL/TLS certificate from a browser-trusted CA, with a renewal arrangement.
- Authenticated **SMTP relay** and an approved sender address. Sign-up cannot be completed without working email.
- **SPF, DKIM and DMARC** DNS records for the sender domain.

## 6. Backup, monitoring and security

- Daily PostgreSQL backups with point-in-time recovery, plus regular backups of the evidence volume, taken together and stored off the production VMs.
- Retention and RPO/RTO to be agreed.
- Monitoring of CPU, RAM and disk (alert at **70%** on the evidence volume), uptime checks and certificate-expiry alerts.
- OS hardening and regular security patching; antivirus scanning of the evidence volume if policy requires it.
- Passwords and keys are exchanged through a secure channel, never by email.

## 7. Access needed by the project team

- SSH with sudo on VM 1 and VM 3 via VPN or bastion, key-based.
- Database administrator access on VM 2 (or the managed database) to create the application database and user.
- An agreed deployment method: SSH from CI, or scheduled manual windows.

## 8. Points for confirmation

1. Hosting facility, and whether Ubuntu 24.04 LTS is permitted (or RHEL/Rocky 9).
2. Availability of managed PostgreSQL, managed backups, load balancer or WAF.
3. SMTP relay and sender address; who manages the sender domain's DNS.
4. Backup retention and off-site copy requirement.
5. Approved access and deployment method.
6. Whether a security audit (e.g. a CERT-In empanelled auditor) is required before go-live.
7. Log retention, and whether logs go to a central SIEM.

## 9. Requested sequence

1. **Staging VM (VM 3) first**, for installation, email and load testing.
2. Production VMs (VM 1, VM 2) and backup storage after staging is validated.
