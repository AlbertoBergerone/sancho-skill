# FieldLog - Threat model

_Phase: PLAN · Method: STRIDE + privacy · Date: 2026-10-07_

Assets: technician accounts, customer names and addresses, signatures, job records. Actors: technicians, office staff, anonymous internet, lost/stolen phones. Trust boundaries: phone <-> API, browser <-> API, API <-> database/object storage.

| ID | Component / flow | STRIDE | Threat | L | I | Mitigation | Maps to |
|---|---|---|---|---|---|---|---|
| TM-01 | sign-in | S | credential stuffing, account enumeration | H | H | lockout 5/15 min, generic errors, rate limit | R-005, T-003, T-010 |
| TM-02 | lost phone | I | offline jobs readable on a stolen device | M | M | encrypted storage, token revocation from dashboard | T-005.1 |
| TM-03 | sync API | T | forged job updates | M | H | authz per technician, server-side validation | T-005.2, standards/api.md |
| TM-04 | dashboard | I | XSS exposing customer data | L | H | React escaping, CSP | F-003 |
| TM-05 | API | D | upload abuse (photos) | M | M | size limits, compression, rate limit | AC-002.3 |

## Privacy (GDPR)
| Data | Purpose | Legal basis | Retention | Deletion path | Transfers |
|---|---|---|---|---|---|
| Customer name, site address | job record, invoicing | contract | 10 years | admin delete + backups rotation | none (EU) |
| Signature | proof of service | contract | with the job | with the job | none |
