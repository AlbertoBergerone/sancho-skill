# Sancho - usage guide

[English](guide.en.md) · [Italiano](guide.it.md) · [Español](guide.es.md) · Not installed yet? [Installation guide](install.en.md)

This guide is for the person who leads the project: you, not the agents. It explains what Sancho will ask you, what you decide, and how to find your way back after a break.

## 1. Getting started

1. Install Sancho (see the [installation guide](install.en.md)).
2. Open an empty folder, or your existing project, in Claude Code (or start a chat in the Claude app).
3. Type `/sancho:discover` (Claude Code with the plugin), `/sancho discover` (Claude apps or skill only) or simply "sancho, I want to build...".

On the first run Sancho shows a short tour and creates a `.sancho/` folder, which holds the memory of the project. **Commit it to git**: it is how the next session knows where you are.

Lost at any time? Type **`next`** for the single next step, or **`status`** for the full picture.

## 2. A typical journey

```
discover -> gate -> specify -> gate -> plan -> gate -> tasks -> gate
        -> implement (task by task) -> gate -> verify (you run the UAT) -> gate
        -> release (you approve go-live) -> gate -> evolve -> gate
```

Each phase ends with a **gate summary**: what was produced, checklist results, open issues, and what was *not* verified. Reply "approve", or say what to change. Sancho never approves on your behalf.

## 3. Commands cheat sheet

| What you want | Claude Code with the plugin | Claude apps (and Claude Code with the skill only) | Plain language, anywhere |
|---|---|---|---|
| Tour and help | `/sancho:help` | `/sancho help` | "sancho, help" |
| Help on a topic | `/sancho:help uat` | `/sancho help uat` | "sancho, explain UAT" |
| Where are we? | `/sancho:status` | `/sancho status` | "sancho, status" |
| What do I do now? | `/sancho:next` | `/sancho next` | "sancho, what's next?" |
| Run a phase | `/sancho:discover` ... `/sancho:evolve` | `/sancho plan` | "sancho, let's do the plan" |
| Implement a given task | `/sancho:implement T-007` | `/sancho implement T-007` | "sancho, implement T-007" |
| Guided UAT | `/sancho:verify uat` | `/sancho verify uat` | "sancho, let's run the UAT" |
| Security checks only | `/sancho:verify security` | `/sancho verify security` | "sancho, run the security checks" |
| Save before stopping | `/sancho:checkpoint` | `/sancho checkpoint` | "sancho, checkpoint" |
| Analyze an existing project | `/sancho:assess` | `/sancho assess` | "sancho, analyze this project" |

<!-- invocation-forms -->
**Two forms, depending on where you use Sancho.**
- **Claude Code with the plugin:** `/sancho:<command>`, no space (`/sancho:status`). The plugin registers one command per entry, and `plugin:command` is the Claude Code standard.
- **Claude apps** (web, desktop, mobile) **and Claude Code with the skill only:** `/sancho <command>`, with a space (`/sancho status`). There is a single `/sancho` command: when you pick it from the menu the app adds a space, and you type the command right after it. `/sancho:status` does not exist there; if you type `/sancho :status` out of habit, Sancho still understands.

Your answers at a gate: "approve" (or "ok", "go ahead") · "reject: <reason>" · "approve anyway, I accept <risk>" (recorded as an override).

## 4. Your first session (example)

```
You:    /sancho:discover I want an app for our technicians to log maintenance jobs
Sancho: Sancho at your service. Four quick questions to start:
        1. Who logs the jobs, and on which device? ...
You:    (answers)
Sancho: (two more rounds: constraints, personal data; four name proposals)
        I propose level L2: personal data of customers, two platforms. Agree?
You:    yes, and I like "FieldLog"
Sancho: GATE DISCOVER - ready for your approval
        Produced: docs/constitution.md · Checklist: 8 pass, 1 n/a · Decisions: name, L2
        Not verified: hosting costs (HYPOTHESIS)
        Approve, or tell me what to change?
You:    approve
Sancho: Gate approved. Next: SPECIFY - requirements and user stories (/sancho:specify).
```

A complete project snapshot is in [examples/fieldlog](../examples/fieldlog/WALKTHROUGH.md).

## 5. What you decide, phase by phase

| Phase | Sancho asks you about | Tips |
|---|---|---|
| DISCOVER | the problem, users, platforms, budget and deadline, personal data, the product name, the risk level | Name 2-3 real kinds of user, not "everyone". If there are accounts, emails or photos of people, GDPR applies. |
| SPECIFY | priorities (must/should/could/won't), what stays OUT of the first version, open questions | Read the OUT list carefully: it is your scope protection. |
| PLAN | stack (you get a recommendation and two alternatives with scores), containers, palette, logo, accepted risks | If you already know the technology, say so: Sancho accepts it and only lists the risks. |
| TASKS | execution order and milestones | Big tasks are split automatically (complexity above 7). |
| IMPLEMENT | only scope questions and blocked tasks | Ask for `status` every few tasks; offer a checkpoint before stopping. |
| VERIFY | approval for active security tests, UAT results, accepting residual risks | You run the UAT: Sancho guides you one case at a time. |
| RELEASE | go-live, store submission, production migrations | Every irreversible step needs your explicit yes. |
| EVOLVE | retrospective, how to resolve differences between code and standards | It keeps the project consistent for the next round. |

## 6. Levels: how much process

| Level | When | What changes |
|---|---|---|
| L0 | throwaway script, demo | three questions, spoken gates, no PLAN/RELEASE/EVOLVE |
| L1 | small app, one platform, no sensitive data | PLAN, RELEASE, EVOLVE skipped; a quick stack choice in DISCOVER |
| L2 | real product, several platforms, personal data | all eight phases |
| L3 | payments, health, regulated, real-data migrations | all phases + impact analysis, rollback plans, extra security review |

You can change the level later; Sancho explains what that changes.

## 7. UAT: testing the product yourself

In TASKS, QA writes acceptance tests in plain language: preconditions, test data, numbered steps, expected result, one platform or device per case. You get them as `docs/uat/UAT.md` (printable, with checkboxes) and `docs/uat/uat.csv` (spreadsheet).

In VERIFY you can choose between two ways:
- **Guided:** `/sancho:verify uat`. Sancho shows one case, you do it on the device and answer pass, fail or blocked, with notes.
- **Spreadsheet:** fill in the CSV (Result, Executed by, Notes), maybe with colleagues, and send it back. Sancho imports it.

Every failure becomes a defect with a severity, a fix task and a re-test. The phase cannot be closed with open blocker or major defects unless you explicitly accept the risk.

## 8. Security: what to expect

- In PLAN, a threat model lists what could go wrong and how it is prevented.
- In VERIFY, Sancho runs (or asks you to install) secret scanning, static analysis, dependency checks, container scans and, for mobile, app analysis. Vulnerabilities are prioritized by **CISA KEV** (exploited in the wild), then **EPSS** (likelihood of exploitation), then **CVSS**.
- **Active tests** (for example an OWASP ZAP scan) run on your own local, test or staging environment after you approve the exact target. On your own production only with your explicit approval and an agreed time window, both recorded. Sancho refuses third-party targets.
- Anything that could not run is listed as **NOT RUN** with the command to run it later. "No findings" is never presented as "secure".

## 9. Going back, pausing, resuming

- **Change of mind:** "reopen SPECIFY, I want to add X". Sancho reopens the phase, updates the backlog and checks the impact on tasks and UAT.
- **Skip a phase:** possible. Sancho records the reason in an ADR (decision record).
- **Pause:** `/sancho:checkpoint` saves a short summary. Next time, `status` picks it up.

## 10. Brand and images

Sancho designs logos as SVG and palettes as design tokens with checked contrast. For photos or rich illustrations it can use an image-generation service you have configured (API key in an environment variable, or an MCP server). Otherwise it gives you a ready-to-paste prompt for the tool you prefer.

## 11. FAQ

**Does it need internet?** Only for research and vulnerability data (OSV, NVD, KEV, EPSS). Without internet those checks are marked NOT RUN.

**Python is missing (Windows).** Install Python 3.9+ from python.org and tick "Add to PATH", or use the `py` launcher. The scripts need no extra packages.

**Can I use it on an existing codebase?** Yes. DISCOVER first extracts the existing conventions as standards, so new work matches the code you already have.

**Who owns the decisions?** You do. Name, platforms, stack, brand, scope, every gate and go-live are your calls. Sancho proposes, explains and records.
