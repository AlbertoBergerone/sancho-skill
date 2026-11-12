# Taxonomy

Shared vocabulary for all roles. The evidence states, risk levels, normative force and trust order are adapted from ACP v1.1 (MIT, see NOTICE).

## Evidence states

| State | Meaning | Example |
|---|---|---|
| VERIFIED | Observed in this session, with a reference | `npm test` exit 0, output excerpt; file read at lines 10-30 |
| REPORTED | Stated by someone else (user, another role, a handoff, a document), not re-checked | "Developer handoff says auth tests pass" |
| HYPOTHESIS | An inference not yet checked | "The timeout is probably caused by the N+1 query" |
| NOT RUN | A planned check that was not executed, with reason and the command to run it | "ZAP baseline NOT RUN: Docker not available. Run: docker run ..." |

Rules: a role receiving a handoff treats its findings as REPORTED until it re-checks the key evidence. Summaries keep the labels. "Tested", "works", "secure", "compliant" are only allowed for VERIFIED claims, and only with their scope ("unit tests for auth pass", not "the app works").

## Risk levels

| Level | Typical signals | Process |
|---|---|---|
| L0 Minimal | prototype, script, demo, throwaway | DISCOVER short (3 questions), SPECIFY reduced, TASKS, IMPLEMENT, VERIFY reduced. Spoken gates. |
| L1 Standard | small app, one platform, no sensitive data | Phases 0,1,3,4,5; PLAN folded into a lightweight stack decision in DISCOVER |
| L2 Engineering | real product, several platforms, personal data, integrations | All eight phases |
| L3 Critical | payments, health, safety, large personal data, regulated, migrations of real data | All phases + impact analysis, rollback plans, security review of every migration, explicit approval of irreversible steps |

Risk depends on effect, not on size: "delete the users table in production" is short and L3. Raise the level when you discover higher risk, and say so.

## Normative force

MUST (required, violation makes the work unacceptable), MUST NOT (forbidden), SHOULD (recommended; deviation allowed with a stated reason), MAY (optional). Use them in specs, standards, checklists and briefs.

## Severity (single scale)

| Severity | Meaning | Gate effect |
|---|---|---|
| blocker | Wrong behavior, data loss, security hole, unmet must-have criterion | Blocks the gate |
| major | Significant problem with a workaround | Blocks the gate unless the user accepts the risk |
| minor | Should be fixed, not urgent | Does not block |
| nit | Style or preference | Does not block |

Security mapping (first rule that matches): CISA KEV listed -> blocker; CVSS >= 9.0 or EPSS >= 0.5 -> blocker; CVSS >= 7.0 or EPSS >= 0.1 -> major; CVSS >= 4.0 -> minor; CVSS < 4.0 -> nit; no score -> advisory severity (CRITICAL/HIGH/MODERATE/LOW -> blocker/major/minor/nit), else minor with "triage required". A security role MAY raise severity with a stated reason (exposure, data sensitivity) and SHOULD NOT lower it below the mapping without the user's risk acceptance.

No numeric quality scores ("8/10"): they are not evidence.

## Statuses

| Object | Statuses |
|---|---|
| Phase | not_started, in_progress, awaiting_approval, approved, rejected, skipped |
| Task | pending, in_progress, blocked (with reason), ready_for_review, completed (with evidence), failed |
| Acceptance criterion | met (with evidence), not_met, not_verified |
| UAT case | pass, fail (with defect), blocked (with note), not_tested |
| Defect | open, fixed, verified (re-tested), wont_fix |
| Security finding | open, fixed, accepted_risk (with who accepted), false_positive, not_verified |
| Handoff | in_progress, blocked (with open issue), ready_for_review, completed, failed |

## Ids

`R-001` requirement · `S-001` story · `AC-001.2` criterion 2 of story 001 · `T-001` task, `T-001.1` subtask · `UAT-001` · `DEF-001` · `F-001` security finding · `D-001` decision · ADR files `docs/adr/0001-<slug>.md`.

## Glossary rule

One term, one concept. The project glossary lives in `.sancho/standards/glossary.md` (template `templates/glossary.md`): preferred term, definition, terms to avoid. Every role uses the preferred term in code, UI copy and documents, and flags the avoided ones in review.
