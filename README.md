# Sancho

**Your loyal squire for software projects.** A Claude skill and Claude Code plugin with a team of seven specialist agents. It takes a project from the first idea to release through eight phases, and you approve every step.

[English](README.md) · [Italiano](README.it.md) · [Español](README.es.md)

**Documentation:** [Installation guide](docs/install.en.md) · [Usage guide](docs/guide.en.md) · [Example project](examples/fieldlog/WALKTHROUGH.md)

> Don Quixote dreams. Sancho keeps the road straight, remembers the budget, and never claims a battle was won without proof.

## Why

AI coding assistants are fast but forgetful. They skip planning, invent requirements, say "all tests pass" without running them, and drift from the project's conventions. Sancho adds the missing project discipline without burying small projects in process:

- **Eight phases, each closed by a gate you approve.** Every gate has a quality checklist and a traceability check.
- **Seven specialist roles** that hand work to each other with structured, verifiable handoffs.
- **Evidence over claims.** Every status is VERIFIED, REPORTED, HYPOTHESIS or NOT RUN.
- **Guided UAT.** You get step-by-step acceptance tests written for non-technical testers, as Markdown and as a spreadsheet.
- **Security testing with real prioritization:** OWASP checklists, OSV and NVD, CISA KEV and FIRST EPSS. Active tests run only on targets you own and approved.
- **Consistency over time.** Project standards are extracted from the real code and loaded per task.
- **Proportionality.** A throwaway script (L0) gets three questions. A regulated product (L3) gets impact analysis and rollback plans.

## The phases

| # | Phase | Lead | You decide |
|---|---|---|---|
| 0 | **DISCOVER** principles, personas, platforms, constraints, GDPR, name | Analyst/PM | name, platforms, risk level |
| 1 | **SPECIFY** requirements, self-contained stories, acceptance criteria, MVP scope | Analyst/PM | priorities, IN/OUT |
| 2 | **PLAN** stack matrix, architecture, ADRs, containers, brand, threat model | Architect + UX/UI + Security | stack, palette, logo |
| 3 | **TASKS** tasks with dependencies and complexity 1-10, UAT checklist | Analyst/PM + QA | order, milestones |
| 4 | **IMPLEMENT** one task at a time, test-driven, standards applied | Developer | scope questions |
| 5 | **VERIFY** tests, your guided UAT, security, accessibility | QA + Security + UX/UI | UAT verdicts, risk acceptance |
| 6 | **RELEASE** SemVer, changelog, deploy and rollback, stores, monitoring | Release manager | go-live |
| 7 | **EVOLVE** standards from code, retrospective, next iteration | Release manager + Architect | what changes next |

L0-L1 projects skip PLAN, RELEASE and EVOLVE by default. You can skip any phase, but the reason is recorded in an ADR.

## The team

Analyst/PM (orchestrator) · UX/UI designer · Architect · Developer · QA · Security engineer · Release manager.
In Claude Code they run as subagents (`sancho:developer`, ...). In the Claude apps the main conversation plays each role in turn.

## Install

Full step-by-step instructions, including updates, uninstalling, optional security tools and troubleshooting, are in the **[installation guide](docs/install.en.md)**. The short version:

| You use | Do this |
|---|---|
| Claude Code (recommended: plugin) | `/plugin marketplace add AlbertoBergerone/sancho-skill`, then `/plugin install sancho@sancho` |
| Claude Code (skill only) | copy `skills/sancho` to `~/.claude/skills/sancho` |
| Claude app (web, desktop) | enable code execution, then **Customize -> Skills -> + -> Upload a skill** with `sancho.zip` from [Releases](https://github.com/AlbertoBergerone/sancho-skill/releases) |

Requirements: Python 3.9+ (standard library only) where Claude Code runs. Security tools are optional.

Then read the **[usage guide](docs/guide.en.md)**: the journey, a commands cheat sheet, an example session, what you decide in each phase, UAT, security.

## Which Sancho to use

Sancho comes in three forms. The skill is the same in all of them: what changes is where you use it, how you call it and what comes with it.

| | Plugin | Skill only | ZIP for the Claude apps |
|---|---|---|---|
| **Where** | Claude Code: terminal, desktop app Code tab, VS Code, JetBrains | Claude Code | claude.ai chat, desktop and mobile apps |
| **How you call it** | `/sancho:status`, `/sancho:verify` ... | `/sancho status`, `/sancho verify` ... | `/sancho status`, or in plain words |
| **The team** | Work goes to the 7 subagents `sancho:<role>`; questions and approvals stay with you in the chat | The main conversation plays one role at a time | As skill only |
| **Panel** | Band above the prompt, notices, `/sancho-panel` | No | No |
| **Scripts** | Python on your computer | Python on your computer | In Claude's environment, with code execution on |
| **Installed by** | `/plugin install sancho@sancho` | Copying `skills/sancho` | Uploading `sancho.zip` |

### With the plugin (recommended in Claude Code)

1. Open the project folder in Claude Code, empty or existing.
2. Type `/sancho:discover` for a new project, or `/sancho:assess` to analyze an existing one.
3. Once there is a Sancho project, the band appears above the prompt: phase, gate state and next step. "dettagli" (or `/sancho-panel`) opens the pane with the eight phases, open issues and command buttons.
4. At every gate read the summary and answer "approve" or say what to change. Then `/sancho:next` tells you what comes next.

### With the skill only (Claude Code)

For a minimal install without the plugin. You work as with the plugin, but commands take a space (`/sancho discover`, `/sancho next`), there is no panel, and the main conversation plays the roles, announcing each switch ("Architect hat on."). Plugin and skill only use the same `.sancho/` folder, so you can switch between them on the same project. Install only one of them in Claude Code, so Sancho is not there twice.

### In the Claude app (chat)

For people who do not use Claude Code. Upload `sancho.zip` once (see the [installation guide](docs/install.en.md)), then open a new chat and write "sancho, I want to build..." or `/sancho discover`. The scripts run in Claude's environment, so you need nothing on your computer, but code execution must be on. There is no panel here: ask for the state with `/sancho status`. To write and test code in your own repository you need Claude Code.

## Commands

| Plugin | What it does |
|---|---|
| `/sancho:help [topic]` | One-screen guide; topics: phases, roles, commands, uat, security, gates, files |
| `/sancho:status` | Phases, tasks, UAT, defects, security, blockers, next step |
| `/sancho:next` | The single next step and who does it |
| `/sancho:discover` ... `/sancho:evolve` | Run a phase |
| `/sancho:checkpoint` | Save a resumable summary of the session |
| `/sancho:assess` | Analyze an existing project: risks first, then roadmap or reuse ideas (read-only) |

Claude apps (web, desktop, mobile) and Claude Code with the skill only: `/sancho <command>` with a space, for example `/sancho status`, `/sancho verify uat`. Or just write "sancho, what's next?".

## Panel (plugin only)

With the plugin, the Claude app (Code tab) and Claude Code also get the Sancho panel. It needs nothing from you and appears only in folders with a Sancho project:

- **a band above the prompt**: phase and gate, blockers, the next step and who does it, a "dettagli" link;
- **a notice** when the gate, the next step or the ZIP state changes;
- **a details pane**, opened from the band or with `/sancho-panel`: the eight phases, the next step, defects and security findings by severity, tasks and UAT, buttons that write a command in the prompt.

It reads only `state.py status --json`. The ZIP for the Claude apps has no panel: those apps cannot show one. Data sources: [hooks/README.md](hooks/README.md).

## What it writes in your project

```
.sancho/state.json  backlog.json  uat.json  handoffs/  standards/  checkpoints/
docs/constitution.md  spec.md  plan.md  adr/  uat/UAT.md  uat/uat.csv  security/
design/tokens.json  logo.svg  wireframes/
```

See the complete fictional example in [examples/fieldlog](examples/fieldlog/WALKTHROUGH.md): an Android and web app with a containerized backend, captured in the middle of VERIFY.

## Helper scripts

| Script | Purpose |
|---|---|
| `state.py` | init, status, next, gate checklist/submit/approve/reject, skip with ADR, level changes, new iterations, approvals, decisions |
| `coherence_check.py` | requirement -> story -> criterion -> test/UAT traceability, dependency cycles |
| `complexity.py` | deterministic 1-10 task scores, split recommendations |
| `uat_export.py` | UAT to Markdown and CSV (EN/IT/ES), import results back |
| `cve_enrich.py` | lockfile or SBOM -> OSV -> NVD, KEV, EPSS -> report; works offline with honest NOT RUN |
| `contrast_check.py` | WCAG 2.x contrast of design-token pairs |

## Development

```bash
python -I tests/validate.py      # 37 offline checks: schemas, fixtures, scripts, example, evals
claude plugin test .            # panel tests (band, pane, notices)
python tools/build.py            # regenerate agents/ from roles/ and build dist/sancho.zip
python tools/set_owner.py --user <github-user> --name "<Your Name>"   # fill the placeholders once
```

`skills/sancho/roles/*.md` is the single source for the subagents in `agents/`; CI fails if they drift. Behavioral evals are in `tests/evals.json` (23 scenarios).

## Credits

Sancho incorporates and adapts rules from **[ACP - Agent Communication Protocol](https://github.com/flaz78/agent-communication-protocol)** (MIT): evidence states, risk levels, coding guardrails, the handoff schema and trust rules (see [NOTICE](NOTICE)). Ideas, but no code, from BMAD-METHOD (role-based agents, self-contained stories), GitHub Spec Kit (spec -> plan -> tasks -> implement, cross-artifact checks), obra/superpowers (TDD, plans on disk, verification before completion), Agent OS (project standards), and Task Master (complexity scoring and task expansion). Security guidance builds on OWASP ASVS, MASVS and API Security Top 10, the NVD, CVE.org, OSV.dev, CISA KEV and FIRST EPSS.

Sancho is an independent project, not affiliated with any of the above or with Anthropic.

## License

[MIT](LICENSE)
