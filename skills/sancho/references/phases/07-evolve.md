# Phase 7 - EVOLVE

**Lead:** Release manager. **Supporting:** Architect (standards extraction), Analyst/PM (next backlog), all roles (retrospective).
**Goal:** keep the project coherent and set up the next iteration.
**Output:** refreshed `.sancho/standards/` and glossary, `docs/retrospective-<version>.md` (`templates/retrospective.md`), next-iteration backlog draft, checkpoint.

Skipped by default at L0-L1. Can also be run on its own at any time to re-align standards with the code.

## Steps

1. **Standards extraction** (Architect, `references/standards.md`): compare code and standards; document consistent undocumented patterns; for deviations ask the user "update the standard or refactor?" and create tasks for refactors.
2. **Glossary:** add new domain terms; flag inconsistent naming found in code or UI.
3. **Retrospective** with the user: what worked, what did not, what to change in the process (for example the complexity threshold, the level, the UAT approach). Record changes to settings.
4. **Metrics** (if available): lead time per task, defects found in UAT vs. in production, security findings by severity - only real numbers with their source.
5. **Next iteration:** OUT-list items, deferred criteria, accepted risks to revisit, user feedback -> draft requirements/stories (they are approved in the next SPECIFY).
6. **Checkpoint**, then **gate**.

After the EVOLVE gate, the next iteration starts with `scripts/state.py new-iteration` (it reopens SPECIFY to EVOLVE, keeps DISCOVER and level-default skips, and increments `iteration`), then `/sancho:specify`. Previous gates remain in git history and checkpoints.
