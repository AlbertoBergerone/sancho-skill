# Phase 6 - RELEASE

**Lead:** Release manager. **Supporting:** Security (final scan of the release build), QA (smoke tests), Architect (infrastructure).
**Goal:** a reproducible, reversible release that the user explicitly approved.
**Output:** version tag, `CHANGELOG.md`, `docs/release/deploy-checklist.md`, store checklists, observability and backup setup, updated README/runbook/user docs, privacy documentation.

Skipped by default at L0-L1.

## Steps

1. **Version:** SemVer bump from Conventional Commits; `CHANGELOG.md` in Keep a Changelog format; release notes for users in their language.
2. **Release build:** reproducible (pinned dependencies, recorded build command), final SCA/container scan on the exact artifact.
3. **Deploy checklist:** environments and configuration, secrets in place (names only in docs), database migrations with backup first and a tested rollback, smoke tests, monitoring dashboards and alerts with owners, backup and restore test, communication plan.
4. **Stores** (mobile): Google Play and App Store checklists - verify current requirements with a search before listing them (target API levels, privacy declarations, permissions justification, signing, review guidelines); mark unverified items HYPOTHESIS.
5. **Privacy and legal (GDPR when applicable):** privacy notice, records of processing, retention and deletion paths, cookie consent for web, data processing agreements with providers. Sancho prepares drafts and checklists; it does not give legal advice - suggest a review by a professional for L2-L3 products.
6. **Documentation:** README (install, run, configure), runbook (deploy, rollback, incident basics), user guide.
7. **Go-live approval:** present the checklist; the user explicitly approves; record it (`scripts/state.py approval --action "deploy v1.0.0 to production" --scope "<target>"`); only then deploy or submit. Each further irreversible step (store submission, DNS switch, data migration) needs its own approval unless already covered by that scope.
8. Smoke tests after deploy; record results; **gate**.

## Pitfalls
- Rollback written but never tested.
- Store rejection for missing privacy declarations or permission explanations.
- Releasing with open blockers "to fix later" without the user's recorded acceptance.
