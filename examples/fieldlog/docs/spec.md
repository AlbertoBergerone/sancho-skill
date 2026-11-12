# FieldLog - Specification

_Phase: SPECIFY · Source of truth: `.sancho/backlog.json` · Date: 2026-10-03_

## MVP scope
**IN:** S-001 sign-in, S-002 offline job logging, S-003 back-office dashboard, S-004 customer signature (should, kept by decision D-003).
**OUT (later):** accounting export (R-008), push notifications, iOS app.

## Requirements
| ID | Kind | Statement | Priority | Source |
|---|---|---|---|---|
| R-001 | functional | Technicians sign in with email and password | must | user |
| R-002 | functional | Technicians log a job: customer, address, activity, duration, photos | must | user |
| R-003 | functional | Back-office staff see and filter all jobs on a web dashboard | must | user |
| R-004 | non_functional | Job logging works fully offline and syncs when the network returns | must | user |
| R-005 | non_functional | Sign-in resists brute force (lockout, generic errors) | must | standard (TM-01) |
| R-006 | functional | Customers sign the job report on the phone | should | user |
| R-007 | constraint | Personal data stored and processed in the EU | must | regulation |
| R-008 | functional | Export jobs to accounting | wont | user |

## Stories
### S-001 - Technician signs in _(must · R-001, R-005)_
As a field technician, I want to sign in on my phone, so that I see the jobs assigned to me.

| Criterion | Description | Verified by |
|---|---|---|
| AC-001.1 | Valid credentials open today's job list | automated_test |
| AC-001.2 | A wrong password shows a generic error that does not reveal whether the email exists | uat (UAT-001) |
| AC-001.3 | 5 failed attempts in 15 minutes lock the account for 15 minutes | automated_test |

### S-002 - Technician logs a job offline _(must · R-002, R-004, R-007)_
| Criterion | Description | Verified by |
|---|---|---|
| AC-002.1 | A job saved in airplane mode appears on the dashboard within 1 minute of reconnecting | uat (UAT-002) |
| AC-002.2 | A sync conflict keeps both versions and flags the job | automated_test |
| AC-002.3 | Photos are compressed to at most 10 MB per job | automated_test |

### S-003 - Back-office reviews jobs _(must · R-003, R-007)_
| Criterion | Description | Verified by |
|---|---|---|
| AC-003.1 | Filtering by date range and technician shows only matching jobs | uat (UAT-003) |
| AC-003.2 | Fully usable with the keyboard, visible focus | uat (UAT-004) |
| AC-003.3 | Colors meet WCAG 2.2 AA contrast | static_check |

### S-004 - Customer signs the job report _(should · R-006)_
| Criterion | Description | Verified by |
|---|---|---|
| AC-004.1 | The signature appears in the job PDF downloaded from the dashboard | uat (UAT-005) |

Story contexts (self-contained briefs for the developer) are in the backlog JSON.

## Open questions and assumptions
| # | Question | Assumed default | Status |
|---|---|---|---|
| 1 | Do customers need a copy of the PDF by email? | No, in MVP the office sends it | confirmed by the user |
