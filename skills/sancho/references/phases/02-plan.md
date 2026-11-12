# Phase 2 - PLAN

**Lead:** Architect. **Supporting:** UX/UI designer (brand, flows, wireframes), Security (threat model), Release manager (environments, CI/CD).
**Goal:** decide how to build it, with the user choosing the stack and the brand, and write it down so every later step is consistent.
**Output:** `docs/plan.md` (`templates/plan.md`), ADRs in `docs/adr/`, container files if chosen, `design/tokens.json`, logo, wireframes, `docs/security/threat-model.md`, initial `.sancho/standards/`.

Skipped by default at L0-L1 (a lightweight stack decision was taken in DISCOVER).

## Steps (parallel where independent)

1. **Stack** (Architect): decision matrix per `references/stack-decision.md`; present; the user chooses; one ADR per significant choice; record each choice (orchestrator updates `state.json` `stack`).
2. **Architecture** (Architect): components, boundaries, data flow, data model, integrations and external services, environments (dev, test/staging, prod), branching (trunk-based or GitFlow light), Conventional Commits, SemVer, CI pipeline (lint, typecheck, test, build, security scans). Include a diagram (Mermaid in Markdown is fine).
3. **Containers** (Architect): run the decision tree; record the ADR either way; if yes, Dockerfile(s) and docker-compose for development following the hardening checklist.
4. **Brand and UX** (UX/UI): palette as tokens (contrast check must pass), typography, at least three logo directions as SVG, user flows and wireframes for key stories on each platform. The user chooses palette and logo.
5. **Threat model** (Security): STRIDE + privacy (`references/security.md`), mitigations mapped to requirements/tasks/standards. New security requirements go into the backlog as `source: standard`.
6. **Standards** (Architect, UX/UI for ui.md): initial `.sancho/standards/` per `references/standards.md`; seed the glossary.
7. **Risks** (Architect + PM): risk register in `docs/plan.md` (probability x impact, mitigation, owner).
8. **Licenses:** check that chosen dependencies are compatible with the project license.
9. Coherence (`--stage spec`) because stories may have changed; then the **gate**.

L3 additions: impact analysis and rollback strategy for data and infrastructure decisions; security review of the architecture by the Security role.

## The user decides
Every stack choice, container approach when there is a real trade-off, palette, logo, typography, accepted risks.

## Pitfalls
- Choosing technology by habit: show the matrix, even briefly.
- Over-architecture (microservices, queues, Kubernetes) for an MVP that one service handles.
- Brand without contrast checking; wireframes only for the happy path.
