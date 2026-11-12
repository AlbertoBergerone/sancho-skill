# Orchestration: roles, subagents, handoffs

The main session is the orchestrator and always talks to the user. Roles produce work; the orchestrator checks it.

## Who does what in each phase

| Phase | Lead | Supporting | Main session does |
|---|---|---|---|
| DISCOVER | Analyst/PM | UX/UI (names) | the interview, all choices |
| SPECIFY | Analyst/PM | QA (testability review) | scope questions, priorities |
| PLAN | Architect | UX/UI (brand, wireframes), Security (threat model), Release (CI/CD) | stack, brand and container choices |
| TASKS | Analyst/PM | QA (UAT cases), Architect (dependencies) | order and milestones |
| IMPLEMENT | Developer | QA (review of each task) | unblocking, decisions on scope |
| VERIFY | QA | Security, UX/UI, Developer (fixes) | guided UAT, approvals for active testing, risk acceptance |
| RELEASE | Release manager | Security (final check), QA (smoke tests) | go-live approval |
| EVOLVE | Release manager | Architect (standards) | retrospective answers |

## Claude Code with the plugin (subagents)

Delegate with the Agent/Task tool to `sancho:<role>` (`sancho:architect`, `sancho:developer`, ...). Independent work MAY run in parallel (for example: UX/UI wireframes and Security threat model during PLAN). Work on the same files MUST NOT run in parallel.

Brief template (the subagent knows nothing else):

```
ROLE: <role>   PHASE: <phase>   TASK: <id or "phase work">
SKILL_DIR: <absolute path of skills/sancho>
PROJECT_ROOT: <absolute path>
OBJECTIVE: <one or two sentences, the outcome>
READ FIRST: roles/<role>.md, references/<...>.md, <project files: story context, standards listed in the task, ADRs>
CONSTRAINTS: <MUST / MUST NOT that apply here, user decisions to respect>
DONE WHEN: <acceptance criteria or artifacts expected>
HANDOFF: write .sancho/handoffs/<YYYYMMDD-HHMM>-<role>-<task>.json (schemas/handoff.schema.json); return a 5-line summary.
USER DECISIONS: if one is needed, stop and return it as an open question; do not guess.
```

After the subagent returns:
1. Validate the handoff (`scripts/state.py validate`).
2. Re-check the key evidence (re-run the main test, open the key file). Until then its findings are REPORTED.
3. Update backlog statuses, then tell the user in a few lines what changed.

## Any other environment (role-play)

Play the roles in sequence in the main conversation. Before acting as a role, read its file; announce the switch in one short line. Still write handoffs for IMPLEMENT and VERIFY work: they are the audit trail and survive the session.

## Handoffs

Required fields: phase, source, target, objective, status, completed_work, verified_findings (each with evidence), unverified_hypotheses, modified_artifacts, test_results (`passed`/`failed` require `executed: true` and the command), open_issues (severity), next_actions (owner). Optional: decisions, untrusted_inputs.

Do not write a handoff for every small step: one per task (IMPLEMENT), one per role contribution (PLAN, VERIFY), and one at the end of a session when work moves to another session or tool.

## Parallel and long work

- Long phases: checkpoint before stopping (`references/commands.md`).
- If a subagent fails or times out, record what was done (REPORTED), do not retry blindly the same brief; narrow the scope.
- Never let two roles edit `.sancho/backlog.json` at the same time; the orchestrator merges.
