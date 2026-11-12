# Commands: help, status, next, checkpoint, first run

All output in the language of the user's latest message; a message that shows no clear language keeps the language of the conversation so far (that of the most recent message that had one), and `settings.language` applies only when there is none. Command names stay in English.

## First run

Shown when no `.sancho/state.json` exists and the user only called Sancho (`/sancho`, "sancho, help"). If the first message already describes a project or brings a brief, skip the tour: start DISCOVER, with one line pointing to `help`. Keep it under 25 lines, translate it, then ask whether to start DISCOVER. The tour answers a bare call only, never for `status` or another command (see `status` for that case).

```
Sancho - your squire for software projects.

How it works: eight phases, each closed by a gate you approve.
  0 DISCOVER   idea, users, platforms, constraints, name     (Analyst/PM)
  1 SPECIFY    requirements, user stories, acceptance criteria (Analyst/PM)
  2 PLAN       stack, architecture, containers, brand, threats (Architect, UX/UI, Security)
  3 TASKS      tasks with dependencies and complexity, UAT list (Analyst/PM, QA)
  4 IMPLEMENT  code with tests first, task by task           (Developer)
  5 VERIFY     tests, your guided UAT, security, accessibility (QA, Security, UX/UI)
  6 RELEASE    version, deploy, stores, monitoring, rollback   (Release manager)
  7 EVOLVE     standards from real code, retrospective, next round

You decide: name, platforms, stack, brand, scope, every gate, go-live.
Small projects (L0-L1) skip PLAN, RELEASE and EVOLVE.

Commands: help [topic] · status · next · checkpoint · assess · one per phase
Lost? Type "next".
```

Command syntax by installation (show the user the form of their environment, see SKILL.md section 1):
- Claude Code with the plugin: `/sancho:<command>`, for example `/sancho:help`, `/sancho:status`, `/sancho:next`, `/sancho:discover` (or `/sancho:sancho next`)
- Claude apps (web, desktop, mobile) and Claude Code with the skill only: `/sancho <command>`, for example `/sancho help`, `/sancho status`, `/sancho next`. The slash menu adds a space after `/sancho`: type the command after it. `/sancho:status` does not exist there; a leading colon (`/sancho :status`) is tolerated.
- Anywhere: plain language ("sancho, what's next?")

## help [topic]

Without a topic: the first-run text plus the current project line (from `scripts/state.py status`) when a project exists.

Topics (answer from these sources, one screen each):

| Topic | Source |
|---|---|
| phases | the phase table above + gate rule |
| a phase name | that file in `references/phases/`: purpose, lead role, outputs, what the user decides, gate items |
| roles / agents | the table in SKILL.md section 4 + one line on how subagents vs. role-play work |
| commands | the syntax block above |
| uat | `references/uat.md` "For the tester" section |
| security | `references/security.md` scope rule + list of checks |
| gates | `references/gates.md` summary |
| files | SKILL.md section 6 |
| levels | `references/taxonomy.md` risk levels |

End every help answer with the current `next` line when a project exists.

## status

Run `scripts/state.py status` (or `--json` and format it). Show:
1. project line: name, level, platforms;
2. phase strip with symbols (approved, skipped, in progress, awaiting approval, rejected, not started);
3. counts: tasks by status, UAT by result, open defects by severity, unresolved security findings by severity (open or not_verified; the script counts them from the findings, not from the report summary, which also includes fixed ones), closed findings by status, NOT RUN count, last checkpoint;
4. blockers, each on its own line;
5. the NEXT line.

Copy this template, fill it from the script output and translate the labels and free text (the Next action, blocker titles, statuses such as fixed) into the reply language; ids, phase names, severities and quoted UI strings stay as they are. The script's current-phase line is already in the phase strip. Put it in a code block, one line per item, nothing before it except at most one short sentence, nothing after it:

```
FieldLog · level L2 · platforms: android, web, api
Phases: ✔ discover  ✔ specify  ✔ plan  ✔ tasks  ✔ implement  ▶ verify  · release  · evolve
Tasks: completed 11, in progress 1
UAT: pass 2, fail 1, not tested 2
Open defects: major 1
Security (open): blocker 0, major 1, minor 1, nit 0 · closed: fixed 1 · NOT RUN: 1
Last checkpoint: 2026-10-23 17:40
Blockers: none
Next (developer): Fix DEF-001 (major): sign-in error reveals that an email is not registered (TM-01)
```

Blockers are only the `BLOCKER:` lines the script prints, one per line; when it prints none, write "none", and never promote a major defect or finding to a blocker. Use only the output of `scripts/state.py status`: do not open the backlog, UAT, security or code files to enrich it (reading a recent checkpoint to resume, as described under checkpoint, is the only exception). Keep the same layout every time, also when the user asks again or in another language, and end with exactly one NEXT line, never a list of actions. Do not add analysis the user did not ask for: no tables of cases, no links between findings, no recommendations, no notes on where the data comes from. If the user wants details, they ask: add nothing after the NEXT line.

No project (`.sancho/state.json` missing): say in one line that there is no Sancho project in this folder, ask whether the project is in another folder, and offer DISCOVER. Do not show the tour and do not create files.

`status` checks the core files itself (`state.json`, `backlog.json`, `uat.json`, the security report); handoffs are checked by `validate` only. When one is invalid it prints an `INVALID:` line, leaves out the counts from that file, replaces NEXT with the repair step and exits 1 (`status --json` lists them in `invalid_files`). Say which file is invalid and why, never present the partial counts as a complete status, and run `scripts/state.py validate` for the full list of errors. If `state.json` itself is invalid there is no status to show: report the error.

A question that asks both where things stand and what to do ("a che punto siamo? cosa devo fare adesso?") is one `status`, not two commands: show it and close with the single NEXT step, who does it, and the offer to start it, on the NEXT line itself ("Next (developer): fix DEF-001. Shall I start?"). Do not list other actions unless asked.

## next

Run `scripts/state.py next`. Present the single step, who does it, and the command to run. If the step is the user's (approve a gate, run a UAT case, make a decision), say exactly what they need to do. If it is a role's, offer to start it now.

## checkpoint

Write `.sancho/checkpoints/<YYYY-MM-DD-HHMM>.md` from `templates/checkpoint.md`, then run `scripts/state.py checkpoint --file <path>`. Keep: objective, phase and gate status, constraints, decisions (with ADR links), files changed, VERIFIED results with evidence, open issues with severity, approvals granted, next actions. Drop chat history and dead ends unless they prevent repeating a mistake. A checkpoint is not memory: tell the user it must be read at the start of the next session (Sancho does it automatically when `status` runs and a recent checkpoint exists).

When resuming: if the latest checkpoint is newer than the last state update, read it before doing anything else, and re-check its VERIFIED claims that the next step depends on.
