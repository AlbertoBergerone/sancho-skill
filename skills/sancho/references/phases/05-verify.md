# Phase 5 - VERIFY

**Lead:** QA. **Supporting:** Security (security testing), UX/UI (UX and accessibility review), Developer (fixes).
**Goal:** evidence that the product meets its criteria, is acceptable to the user, and has no unacceptable security risk.
**Output:** test results, criteria statuses, executed UAT with defects, `docs/security/security-report.json` + `SECURITY-REPORT.md`, UX/accessibility review.

Arguments: `verify uat` (guided UAT only), `verify security`, `verify a11y`, `verify UAT-007` (one case).

## Steps

1. **Automated tests** (QA): run the full suite and the build; record commands and results; set every criterion verified by `automated_test`/`static_check` to met/not_met with evidence.
2. **Security** (Security role, `references/security.md`):
   a. passive checks: secrets, SAST, SCA with `scripts/cve_enrich.py`, SBOM, container scan, mobile static analysis;
   b. active checks (DAST) only after the user approved target and scope -> `scripts/state.py approval ...`;
   c. report; blocker findings become fix tasks (back to IMPLEMENT loop); majors fixed or risk explicitly accepted by the user.
3. **UX and accessibility** (UX/UI): review each platform against the wireframes and WCAG 2.2 AA (keyboard, screen reader, contrast, focus, target size, text scaling); findings on the severity scale.
4. **UAT with the user** (QA): guided in chat or via spreadsheet (`references/uat.md`). Each fail -> defect -> fix task -> re-test.
5. **Fix loop:** developer fixes defects and findings task by task (IMPLEMENT loop rules); QA re-tests; defects become `verified`.
6. **Coherence:** `--stage full` with the UAT file.
7. **Gate:** no open blocker/major defects or blocker security findings (unless the user accepted the risk), every criterion met or explicitly deferred by the user.

## The user decides
Active testing approval (target and scope), UAT verdicts, risk acceptance for open majors, deferring a criterion.

## Pitfalls
- Reporting "no vulnerabilities" when OSV or other sources were NOT RUN.
- Marking UAT pass on the user's behalf.
- Treating accessibility as optional for public-facing apps (in the EU the European Accessibility Act applies to many consumer services - flag it as a check for the user, not legal advice).
