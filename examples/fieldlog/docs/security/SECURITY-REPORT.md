# FieldLog - Security report

_Phase: VERIFY · Build: 0.9.0-rc.1 (commit 4f2a9c1) · Date: 2026-10-22 · Data: `security-report.json`_

## Scope and authorization
Targets: repository at 4f2a9c1; http://localhost:8000 (docker compose, test data only). Active testing: yes - OWASP ZAP baseline, approved by the user on 2026-10-22 10:05 for that target only.

## Coverage
| Check | Tool | Status | Notes |
|---|---|---|---|
| Secrets | gitleaks 8.x | run | no leaks in history |
| SAST | semgrep (owasp-top-ten, python, kotlin) | run | finding F-001 confirmed manually |
| SCA | sancho cve_enrich (OSV, NVD, KEV, EPSS) | run | all sources run |
| Container | trivy | run | 0 HIGH/CRITICAL in OS packages |
| DAST | ZAP baseline (passive) | run | F-003 |
| Mobile | MobSF | **NOT RUN** | not installed; run: `docker run -p 8001:8000 opensecurity/mobile-security-framework-mobsf`, upload app-release.apk |

## Summary (all findings, any status)
blocker 0 · major 2 (1 fixed) · minor 1 · nit 0

## Findings
### F-001 - Account enumeration through sign-in error message - **major** - open
- Location: `api/app/routes/auth.py:58` · CWE-204 · same issue as UAT defect DEF-001
- Evidence: POST /auth/login with an unknown email returns 404 "User not found"; with a wrong password 401 "Wrong password".
- Remediation: identical 401 response and message for both cases; regression test. Task T-010 (in progress).

### F-002 - Insufficiently Protected Credentials in Requests - **major** - fixed
- requests 2.19.0 (PyPI) · GHSA-x84v-xcm2-53pg · CVE-2018-18074 · CWE-522 · CVSS 7.5 (NVD) · EPSS 0.0085 · KEV no
- Remediation applied: upgraded to a fixed version; constraint removed from `api/constraints.txt`.

### F-003 - Missing Content-Security-Policy header - **minor** - open
- http://localhost:8000/app/ · CWE-693 · ZAP passive alert
- Remediation: restrictive CSP from the reverse proxy.

## Conclusion
Checked: secrets, source (SAST), dependencies with KEV/EPSS prioritization, container image, passive DAST on the local build. Found: one open major (F-001, fix in progress), one minor. Not checked: Android binary (MobSF NOT RUN). The VERIFY gate needs F-001 fixed and re-tested.
