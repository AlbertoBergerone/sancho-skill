# Phase 4 - IMPLEMENT

**Lead:** Developer. **Supporting:** QA (reviews each task), Architect (questions on design), Security (fixes for threat-model items).
**Goal:** working, tested code, one task at a time, consistent with the standards.
**Output:** code, tests, CI configuration, task statuses with evidence, handoffs.

## Loop (per task)

1. `scripts/state.py next` (or the task the user named) gives the next ready task: pending, all dependencies completed, highest story priority first.
2. Set it `in_progress`: `scripts/state.py task T-007 --status in_progress` (it validates the backlog). In team mode (`.sancho/team.json` exists) the member claims it instead, `scripts/state.py claim T-007`, and every later status change goes through `task` and `review`, never by editing `backlog.json` (`references/team.md`).
3. Brief the developer (subagent or role-play) with: the task, its story `context`, the criteria, the standards listed in the task, `references/coding-guardrails.md`, and the TDD rule (`roles/developer.md`).
4. Developer: baseline tests -> red -> green -> refactor -> lint/typecheck/tests/build -> task `ready_for_review` with evidence -> handoff to QA.
5. QA (or the orchestrator wearing the QA hat): re-run the key test, review the diff for scope and standards -> `completed` with evidence, or back to `in_progress` with findings.
6. Update the related acceptance criteria when an automated test now proves them (`met` with evidence).
7. Tell the user in 2-4 lines: task done, what was verified, what is next. Offer a checkpoint every few tasks.

Blocked task: set `blocked` with `blocked_reason`; ask the user only if the decision is theirs; otherwise continue with another ready task.

## Commits (if the project uses git)

One task -> one or more Conventional Commits (`feat(auth): ...`, `fix(sync): ...`) referencing the task id. Never commit secrets; never force-push without approval.

## Gate
When all must-have tasks are completed: checklist (IMP items), coherence `--stage tasks`, summary with test evidence, approval.

## Pitfalls
- Several tasks in one go with one vague "all done": keep one task per loop with evidence.
- Tests written after the code that only confirm what the code does.
- Silent changes to API contracts or the data schema: they need an ADR or a story change.
