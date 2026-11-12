# FieldLog - Constitution

_Phase: DISCOVER · Level: L2 · Date: 2026-10-01 · Status: approved_

## Purpose
Field technicians of a lift-maintenance company log jobs on paper and the office re-types them, late and with errors. FieldLog lets technicians record each job on their phone, even without signal, and gives the office an always-current list of jobs.

## Success in 3 months
- All 12 technicians log every job in FieldLog; paper forms are retired.
- The office invoices from the dashboard without re-typing.

## Principles
1. **Offline first** - every technician flow works without network; sync is automatic. _Why:_ lift shafts and basements have no signal.
2. **One tap fewer** - a routine job is logged in under 60 seconds. _Why:_ adoption depends on speed.
3. **Minimal personal data** - only customer name and site address. _Why:_ GDPR data minimization.
4. **Accessible by default** - WCAG 2.2 AA on the dashboard. _Why:_ office staff includes a low-vision colleague.
5. **Boring technology** - mature, well-known tools the team can maintain. _Why:_ two-person IT team.

## Non-goals
- Scheduling and route planning (existing tool stays).
- Accounting export (next iteration, R-008).

## Personas
| Persona | Context | Goals | Pain points |
|---|---|---|---|
| Marco, technician | company Android phone, gloves, often no signal | log fast, never lose work | paper forms, double entry |
| Giulia, back-office | desktop Chrome/Edge | see jobs same day, invoice | illegible forms, late data |
| Customer | on site, signs on the phone | proof of the visit | none today |

## Platforms
android (technicians), web (back-office), api (backend).

## Constraints
| Area | Constraint |
|---|---|
| Budget | internal team + EUR 3,000 for hosting/tools in year 1 |
| Timeline | MVP in 8 weeks |
| Hosting | EU data center (GDPR) |
| Team & skills | 2 developers: Python, Kotlin; some React |
| Imposed technology | none |

## Data and compliance
- Personal data: customer name, site address, signature image. No special categories.
- Legal basis: contract performance; retention 10 years for job records (accounting), signatures with the job.
- Users in Italy -> GDPR applies; hosting and processing in the EU.

## Quality bars
- Accessibility: WCAG 2.2 AA (dashboard). Languages: Italian (UI), English (code).
- Performance: job list opens in under 1 s on a mid-range Android phone.

## Risk level
**L2** - personal data, two platforms, offline sync. Phases skipped by default: none.
