# Gates

Every phase ends with a gate. The checklist items live in `scripts/gates.json` (single source); print them with `scripts/state.py checklist <phase>`.

## Procedure

1. **Evaluate each item** as `pass`, `fail` or `n/a` (n/a needs a short note: `PLA-7=n/a:CLI only`). Judge on evidence: an item passes only if you can point to the artifact, command output or user decision that satisfies it.
2. **Coherence check** for the phase:

| Phase | Command | Required result |
|---|---|---|
| discover | none | `n/a` |
| specify | `coherence_check.py .sancho/backlog.json --stage spec` | pass |
| plan | `coherence_check.py .sancho/backlog.json --stage spec` (stories may have changed) | pass |
| tasks | `coherence_check.py .sancho/backlog.json --uat .sancho/uat.json --stage tasks` | pass |
| implement | same as tasks | pass |
| verify, release | `... --stage full` | pass |
| evolve | `n/a` | |

3. **Submit:** `scripts/state.py submit <phase> --results "ID=pass,ID=n/a:note,..." --coherence pass`.
4. **Gate summary for the user** (their language, about one screen):

```
GATE <PHASE> - ready for your approval
Produced:     <artifacts with paths>
Checklist:    <n> pass · <n> n/a · <n> fail  (list fails and n/a reasons)
Coherence:    pass | fail (issues)
Decisions:    <decisions taken in this phase, by whom>
Not verified: <REPORTED/HYPOTHESIS/NOT RUN items that matter>
Open issues:  <severity - description>
Next phase:   <PHASE> - <what happens, who leads>
Approve, or tell me what to change?
```

5. **Approval is the user's.** Accept only an explicit yes for this gate ("ok", "approvo", "go ahead" in answer to this summary). Then run `scripts/state.py approve <phase>`.
   - Rejected: `scripts/state.py reject <phase> --reason "<their words>"`, fix, resubmit.
   - The user wants to proceed despite failed items: `approve --override "<their reason>"`; the reason is stored in the gate notes.
6. **One-line reminder** of the next step.

## Skipping a phase

Only at the user's request. Level-default skips are handled by `scripts/state.py init` and `set-level` and need no ADR. Write an ADR explaining why and what is lost (template `templates/adr.md`), then `scripts/state.py skip <phase> --reason "..." --adr docs/adr/NNNN-skip-<phase>.md`.

## Going back

Requirements change. Reopen an earlier approved phase with `scripts/state.py start <phase> --reopen` (phases before it must still be closed), make the change, re-run its gate. Later phases keep their status, but the orchestrator must check the impact (coherence check, affected tasks and UAT cases) and tell the user. After approval, `current_phase` returns to the first open phase.

A whole new round of work after EVOLVE: `scripts/state.py new-iteration`.

## Rules enforced by `state.py`

- `submit` needs every checklist item; `n/a` needs a note (`ID=n/a:reason`; notes may contain commas).
- `approve` refuses failed items and, except for DISCOVER and EVOLVE, any coherence result other than `pass` (including `not_run`). The only way past is `--override "<the user's stated reason>"`.

## Level adjustments

- L0: gates are a short spoken confirmation; still run `submit`/`approve` so the state stays truthful. Checklist items that do not apply are `n/a`.
- L1: full checklist for the phases that run; PLAN, RELEASE, EVOLVE skipped by default.
- L2: all phases.
- L3: all phases, plus impact analysis and rollback plan in PLAN and RELEASE, and a security review of every data migration.
