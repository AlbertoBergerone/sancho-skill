# Phase 1 - SPECIFY

**Lead:** Analyst/PM. **Supporting:** QA (testability of criteria), UX/UI (user flows when they clarify scope).
**Goal:** what to build and why, precise enough to plan and test. No technology choices here except constraints the user imposed.
**Output:** `.sancho/backlog.json` requirements and stories; `docs/spec.md` (`templates/spec.md`).

## Steps

1. Read `docs/constitution.md` and decisions so far.
2. **Requirements** (`R-nnn`): functional, non-functional (performance, availability, security, privacy, accessibility, localization), constraints. Each: statement, MoSCoW priority, source (`user`, `derived`, `regulation`, `standard`). Derived ones are proposals: list them for the user to confirm.
3. **Stories** (`S-nnn`): As a / I want / So that; linked requirements; priority; platforms if not all; and a **self-contained `context`** paragraph (relevant principles, constraints, related stories, edge cases, data involved) so that later roles never need the conversation.
4. **Acceptance criteria** (`AC-nnn.k`): observable outcomes, Given/When/Then where it helps, and a verification method: `automated_test`, `uat`, `static_check`, `review`. Rule of thumb: user-visible behavior on a device -> at least one `uat`; logic -> `automated_test`; must-haves get negative cases.
5. **MVP scope:** IN list (must + agreed should) and OUT list (later iterations). Show the user the OUT list explicitly.
6. **Open questions:** ask the user; anything unresolved becomes a HYPOTHESIS in `docs/spec.md` with the default you will assume.
7. **Coherence:** `scripts/coherence_check.py .sancho/backlog.json --stage spec` - fix all blocker/major issues.
8. Write `docs/spec.md` as the readable view (grouped by epic or user journey; ids kept).
9. **Gate** (`references/gates.md`).

## The user decides
Priorities, MVP IN/OUT, every derived requirement, answers to open questions.

## Pitfalls
- Criteria like "works well", "fast", "user friendly": rewrite as measurable ("list of 500 items renders in under 1 s on a mid-range Android phone").
- Stories that are tasks ("create the database"): rewrite from the user's point of view.
- Hidden scope in non-functional requirements (offline sync, multi-tenant, real-time): surface them, they change the plan.
