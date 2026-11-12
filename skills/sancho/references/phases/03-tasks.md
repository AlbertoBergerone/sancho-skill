# Phase 3 - TASKS

**Lead:** Analyst/PM. **Supporting:** QA (UAT cases), Architect (technical dependencies, standards per task).
**Goal:** an ordered, right-sized plan of work and the list of checks the user will run at the end.
**Output:** tasks in `.sancho/backlog.json`; UAT cases in `.sancho/uat.json`; `docs/uat/UAT.md` and `docs/uat/uat.csv`.

## Steps

1. **Break stories into tasks** (`T-nnn`), each small enough for one focused session, each with: story, title, description, owner role, `depends_on`, `criteria` it covers, `standards` to load, `complexity.factors` (files, integrations, unknowns, ui_screens, data_migration, security_sensitive, no_existing_tests).
   Include non-feature work: project setup, CI, container setup, security fixes from the threat model, documentation.
2. **Score:** `scripts/complexity.py .sancho/backlog.json --write`. Every task above the threshold (default 7, `settings.complexity_threshold`) is split into subtasks `T-nnn.1`, `T-nnn.2` with `"parent": "T-nnn"`; re-run until `--strict` passes.
3. **Dependencies:** set them; no cycles (coherence check finds them).
4. **UAT cases** (QA): for every criterion verified by `uat`, per `references/uat.md`; then export: `scripts/uat_export.py .sancho/uat.json --md docs/uat/UAT.md --csv docs/uat/uat.csv` (case text and labels in the project language, see `references/uat.md`).
5. **Order and milestones:** propose an execution order (must-haves first, risk-first for unknowns, walking skeleton early) and milestones; the user agrees.
6. **Coherence:** `scripts/coherence_check.py .sancho/backlog.json --uat .sancho/uat.json --stage tasks` - fix every blocker/major.
7. **Gate.**

## The user decides
Execution order, milestones, which should/could items enter this iteration.

## Pitfalls
- Tasks that are layers ("all the backend") instead of slices of user value.
- UAT steps written for developers ("call the API"): rewrite for a non-technical tester.
- Ignoring the split recommendation: big tasks are where hallucinated progress hides.
