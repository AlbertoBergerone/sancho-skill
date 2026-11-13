# Team mode

Read this when `.sancho/team.json` exists: several people work on the project, each in their own clone of the repository. Without that file Sancho works for one person and none of this applies.

## How it works

- `.sancho/team.json` lists the members: `id`, `name`, `emails`, `roles` (which role hats they wear), `coordinator`. Without a flagged coordinator, the first member coordinates.
- **Who is speaking** is the member whose email matches `git config user.email`, or `SANCHO_USER=<id>`. Check it with `scripts/state.py whoami`. If the person is not a member, say so, show the project's next step, and do not change task states for them. Identity is for coordination, not security: do not present it as access control.
- **Task states live in an event log, one file per member**: `.sancho/log/<id>.jsonl`. The scripts append to the speaker's own file and never edit anyone else's, so merging the members' work never conflicts on Sancho's state. `backlog.json` stays the plan: in team mode **never edit task statuses in `backlog.json` by hand**; use the commands below. The current state is the plan plus every event (`status` and `next` compute it).
- Events are ordered by their timestamps, so the members' computer clocks matter: a clock that is minutes off can make a later claim look earlier. If a conflict looks wrong, check the clocks.
- Sancho sees the others' work only after they push and this person pulls. Before `status` or `next`, suggest `git pull` if the clone may be behind.

## Commands

| What | Command |
|---|---|
| Who am I | `scripts/state.py whoami` |
| The team | `scripts/state.py team list`; `team suggest` lists the authors in `git log`; `team add --id ID --name NAME --email EMAIL --roles developer,qa [--coordinator]` |
| My next step | `scripts/state.py next` (for the speaker) |
| Everyone's next step | `scripts/state.py next --team` |
| Take a task | `scripts/state.py claim T-007` (refused if someone else has it, dependencies are open, or the task's role is not one of yours; `--any-role` only if the team agreed) |
| Give it back | `scripts/state.py release T-007` |
| Update my task | `scripts/state.py task T-007 --status in_progress|blocked|ready_for_review|failed [--reason TEXT] [--evidence commit:SHA] [--note TEXT]` |
| Review a task (qa role) | `scripts/state.py review T-007 --approve --evidence test:"CMD"` or `--changes "what to fix"` |
| Take a UAT case or a defect | `scripts/state.py claim UAT-004`, `scripts/state.py claim DEF-002` (defects: developer role) |
| Record a UAT result | `scripts/state.py uat UAT-004 --result pass|fail|blocked [--note TEXT] [--new-defect major:WHAT THEY SAW] [--defect DEF-002]` |
| Defect status | `scripts/state.py defect DEF-002 --status fixed [--task T-012]` (the one who claimed it); `--status verified` (qa role, not who fixed it); `--status wont_fix` (coordinator, after the team agreed) |
| Gates | coordinator: `start`, `submit`; approvers: `approve PHASE` / `reject PHASE --reason TEXT` |
| Compact the log | coordinator, after a gate: `scripts/state.py compact` |

Evidence is `TYPE:VALUE`: `commit:SHA`, `test:"CMD"`, `command:"CMD"`, `file:PATH`, `uat:UAT-004`, `url:URL`, `screenshot:PATH`, `log:TEXT`.

## Rules

1. **One task, one person.** Before implementing, the speaker claims the task. Do not implement a task claimed by someone else; tell the person who has it.
2. **Make claims visible.** After `claim`, offer to commit and push the speaker's log file right away (`git add .sancho/log/<id>.jsonl`, commit `chore(sancho): claim T-007`, push). Ask first; never push without the person's yes.
3. **Contested claims.** If two members claimed the same task before seeing each other's push, the earliest claim wins. The loser sees it at the top of `next`: tell them who keeps the task, suggest they agree, and run `release` to clear it. Work already done on the losing branch is theirs to hand over; do not discard it.
4. **Four eyes.** A task is `completed` only through `review --approve` by a member with the `qa` role who did not work on it (`four_eyes`, on by default). `task --status completed` is refused in team mode. If the team has no second qa member, say so and suggest adding the role to someone.
5. **Changes requested.** After `review --changes`, the task goes back to `in_progress` for the same member, and their `next` shows the findings.
6. **Phases stay shared.** The coordinator opens phases, submits gates and asks for approval; the others are told whose step it is. Interviews (DISCOVER, SPECIFY, PLAN) are run with one person; the others review the documents in pull requests.
7. **Relaying `next`.** Say the step for the speaker. When it is not theirs, say whose it is and what they can do meanwhile (a free task, a review). Use member names, not role names, when the team has them.
8. **Branches.** One branch per task, for example `t-007-offline-login`; `claim` records the current branch. Commits keep the Conventional Commits rule with the task id.

## Gates

- The coordinator opens phases (`start`), submits gates (`submit`), skips phases and changes the level. Others get "the coordinator does this".
- Approvers and quorum are in `team.json`: `"approvers": {"default": ["danilo"], "release": ["danilo", "luca"]}`, `"quorum": {"release": 2}`. Without them the coordinators approve and one approval is enough. Edit `team.json` only when the team agreed, and commit it.
- Each approver approves in their own session with `approve PHASE`, after reading the gate summary themselves; never approve for someone else. Below the quorum the approval is recorded and the gate stays open; `next` tells the others who is still awaited. When the approvals arrive with a pull, the coordinator (or any approver) runs `approve PHASE` again to close the gate; `gate.approved_by` lists the members.
- One `reject` by an approver sends the gate back, with the reason.
- `decision --by user` and `approval` record the speaking member's id, not "user".

## VERIFY in a team

- Testers claim UAT cases (`claim UAT-004`), run them (guided in chat as in `references/uat.md`) and record the result with `state.py uat`. A failing case opens a defect with `--new-defect SEVERITY:TEXT`.
- Two testers may open the same defect id before seeing each other's push: the later one is renamed to the next free id (`status` shows `RENAMED`); tell the tester the new id.
- Developers claim defects (`claim DEF-002`), fix them (IMPLEMENT loop rules) and mark them `fixed`; someone else with the qa role re-runs the case and marks them `verified` (or back to `open`). `next` gives blocker defects first.
- `wont_fix` accepts a risk: only the coordinator records it, after the team (and the gate approvers) agreed.

## Compaction

After a gate closes, the coordinator runs `state.py compact`: events of settled items (completed tasks, executed cases whose defects are closed, verified or wont_fix defects, votes of closed gates) move into `backlog.json` / `uat.json` and `.sancho/log/archive/`. The state is identical before and after (the command checks it and undoes itself otherwise). Commit the result in one commit and push it soon, so the others pull it before appending much more.
