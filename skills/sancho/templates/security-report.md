# {{Product name}} - Security report

_Phase: VERIFY · Build: {{version/commit}} · Date: {{YYYY-MM-DD}} · Data: `docs/security/security-report.json`_

## Scope and authorization
Targets: {{...}} · Environment: {{source-only | local | test | staging}} · Active testing: {{yes/no}}
Approval: {{granted by the user on <date> for <scope>}}

## Coverage
| Check | Tool & version | Status | Notes |
|---|---|---|---|
| Secrets | gitleaks {{x.y}} | run / NOT RUN | |
| SAST | semgrep {{x.y}} | | |
| SCA | sancho cve_enrich + osv-scanner | | sources: OSV {{run}}, NVD {{...}}, KEV {{...}}, EPSS {{...}} |
| Container | trivy | | |
| DAST | ZAP baseline | | |
| Mobile | MobSF | | |
| Manual | ASVS / MASVS / API Top 10 | | |

**NOT RUN:** {{list with reason and command}}

## Summary
blocker {{n}} · major {{n}} · minor {{n}} · nit {{n}}

## Findings
### F-001 - {{title}} - **{{severity}}**
- Component / location: {{...}}
- References: {{CVE, CWE, GHSA}} · CVSS {{score (vector)}} · EPSS {{score}} · KEV {{yes/no}}
- Evidence: {{command + output excerpt, file:line}}
- Remediation: {{...}} · Owner/task: {{T-...}} · Status: {{open}}

## Accepted risks
| Finding | Accepted by | Date | Reason | Review by |
|---|---|---|---|---|

## Conclusion
{{What was checked, what was found, what remains unknown. Never "the app is secure".}}
