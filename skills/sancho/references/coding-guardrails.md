# Coding guardrails

Adapted from ACP v1.1 CODING mode (MIT, see NOTICE). They apply to every code change, in any phase.

| ID | Rule |
|---|---|
| G1 | Do not remove functionality without authorization. |
| G2 | Do not introduce intentional regressions that were not approved. |
| G3 | Do not change API contracts (public signatures, endpoints, data formats, database schema) unless the task requires it. |
| G4 | Do not replace working components without a stated reason. |
| G5 | Do not rewrite whole modules when a targeted change is enough. |
| G6 | Do not claim tests passed unless they were run in this session. |
| G7 | Do not modify files outside the task scope without disclosing and justifying it. |
| G8 | Do not hide problems, warnings or failing tests you found. |
| G9 | Do not disable, skip or weaken tests to make them pass. |
| G10 | Do not add unnecessary dependencies; every new dependency needs a reason, a license check and a pinned version. |

## Protection against regressions (executable, not promised)

In order of preference:
1. Existing tests of the area: run them before (baseline) and after the change.
2. Characterization tests: if behavior to preserve is not covered, pin it with a test before changing code.
3. Regression test for a bug: fails before the fix, passes after.
4. Static checks: typecheck, lint, build.
5. Diff review: `git diff --stat` shows only relevant files.

A baseline failure that existed before your change is not your regression, but it MUST be reported.

## Without tools or repository access

Deliver the code and the commands to verify it; mark verification NOT RUN; never write "tested" or "works".

## Final summary of a task

```
Changes:   <files and what changed>
Verified:  <command> -> <observed result> | NOT RUN (<reason>, run: <command>)
Preserved: <behaviors checked>            (L2+)
Open:      <issues, limits, hypotheses>
```

## Scope changes during IMPLEMENT

If the task cannot be done as specified (missing requirement, wrong assumption, conflict with an ADR), stop and report it as a blocked task with the reason. The orchestrator decides with the user whether to change the story (reopen SPECIFY), the plan (new ADR) or the task.
