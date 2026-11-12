# Phase 0 - DISCOVER

**Lead:** Analyst/PM (main session). **Supporting:** UX/UI (name proposals), Architect (only for an existing codebase or L0-L1 stack choice).
**Goal:** understand the idea well enough to specify it, and set the risk level that sizes the rest of the process.
**Output:** `docs/constitution.md` (`templates/constitution.md`), `.sancho/state.json` initialized.

## Steps

1. **Initialize** if needed: `scripts/state.py init --name "<working title>" --level L2 --platforms web,android --language <project language>` (the language of testers and end users, used for UAT cases and release notes; default: the language the user writes in). Provisional values are fine: change the level later with `scripts/state.py set-level L1` (it applies the level-default skips), and other `project` fields by editing state, then `scripts/state.py validate`.
   Accepted platform values: `web`, `pwa`, `android`, `ios`, `desktop-windows`, `desktop-macos`, `desktop-linux`, `cli`, `api`, `embedded`.
2. **Existing code?** If the folder already contains a codebase, run the standards extraction (`references/standards.md`) before the interview and summarize what exists.
3. **Interview** in rounds of at most 4 questions (AskUserQuestion when available, recommended option first). Cover:

| Round | Topics |
|---|---|
| 1 Idea | the problem, who has it, what success looks like in 3 months, what exists today |
| 2 Users & platforms | personas (2-3), main use cases, target platforms: web, PWA, Android, iOS, desktop (Windows/macOS/Linux), CLI, API |
| 3 Constraints | budget, deadline, hosting preferences or obligations, team and skills, stack already imposed |
| 4 Data & compliance | personal data categories, special categories (health, minors...), where users are (EU -> GDPR), retention, accessibility target (default WCAG 2.2 AA), languages |
| 5 Name & level | product name (3-5 proposals from the UX/UI role, or the user's), risk level proposal with reasons |

   Skip questions already answered. For L0 projects, ask at most three questions in total: what, for whom/where, how it is judged done. Do not add a question for the level or the stack: state them as defaults in the same message, for the user to correct.
4. **Risk level.** Propose L0-L3 with the signals that led to it (`references/taxonomy.md`); the user confirms. If it differs from the provisional one, run `scripts/state.py set-level <Lx>`: phases skipped by level default follow the new level automatically (no ADR needed for level-default skips).
5. **L0-L1 only:** a lightweight stack decision (one recommendation + one alternative per area, the user picks; at L0 the recommendation stands unless the user corrects it, see step 3), recorded as decision D-nnn - PLAN is skipped.
6. **Write the constitution:** purpose, principles (5-8, each actionable: "Offline first: every core flow works without network"), non-goals, personas, platforms, constraints, data and compliance, quality bars (accessibility, performance targets), risk level, glossary seed.
7. **Gate:** `scripts/state.py checklist discover`, then the gate procedure (`references/gates.md`).

## The user decides
Product name, platforms, risk level, principles and non-goals, constraints.

## Pitfalls
- Jumping to features or technology: DISCOVER is about the problem and the boundaries.
- Accepting "everyone" as the user: push for 2-3 concrete personas.
- Forgetting GDPR when there is any account, email, location or photo of a person.
