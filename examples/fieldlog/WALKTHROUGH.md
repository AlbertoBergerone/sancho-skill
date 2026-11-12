# FieldLog - an end-to-end walkthrough

FieldLog is a **fictional** project used to show what Sancho produces. A lift-maintenance company wants technicians to log jobs on Android (often without signal) and the office to see them on a web dashboard. The folder is a snapshot taken in the middle of VERIFY. All names, data and scan results are illustrative.

Try it from this folder (adjust the path to the skill):

```bash
python ../../skills/sancho/scripts/state.py status
python ../../skills/sancho/scripts/state.py next
python ../../skills/sancho/scripts/coherence_check.py .sancho/backlog.json --uat .sancho/uat.json
python ../../skills/sancho/scripts/complexity.py .sancho/backlog.json
python ../../skills/sancho/scripts/contrast_check.py design/tokens.json
```

## Session by session

| # | Command | What happened | Artifacts |
|---|---|---|---|
| 1 | `/sancho:discover` | Five short rounds of questions: problem, personas, platforms (Android + web), constraints, GDPR. The UX/UI role proposed four names, the user chose FieldLog. Level L2 confirmed. Gate approved. | `docs/constitution.md`, `.sancho/state.json` |
| 2 | `/sancho:specify` | Eight requirements (one won't-have), four stories with self-contained context, ten acceptance criteria with verification methods. The user moved the signature story into the MVP (D-003). Coherence `--stage spec` passed. | `.sancho/backlog.json`, `docs/spec.md` |
| 3 | `/sancho:plan` | The architect showed a weighted matrix (Kotlin vs Flutter vs React Native...). The user chose native Kotlin and FastAPI (ADR 0001) and containers (ADR 0002). In parallel the UX/UI role built tokens (6/6 contrast pairs pass) and three logos; the security role wrote the STRIDE model, which added requirement R-005. | `docs/plan.md`, `docs/adr/`, `Dockerfile`, `docker-compose.yml`, `design/`, `docs/security/threat-model.md`, `.sancho/standards/` |
| 4 | `/sancho:tasks` | Eleven tasks with dependencies. `complexity.py` scored T-005 at 8 (above 7), so it was split into T-005.1 and T-005.2. QA wrote five UAT cases, exported to Markdown and CSV. | backlog tasks, `.sancho/uat.json`, `docs/uat/` |
| 5-8 | `/sancho:implement` (repeated) | One task per loop with TDD; each task reached `completed` only after QA re-ran its key test. Example handoff: `.sancho/handoffs/20261020-1530-developer-T-009.json`. | code (not included), handoffs |
| 9 | `/sancho:verify` | Automated suites run. Security: the user approved a ZAP baseline on `http://localhost:8000` only; gitleaks, semgrep, SCA with KEV/EPSS, trivy run; MobSF NOT RUN. Guided UAT: UAT-001 **failed** -> DEF-001 (major) -> fix task T-010; UAT-002 and UAT-003 passed. | `docs/security/`, updated `.sancho/uat.json` |
| 10 | `/sancho:checkpoint` | Session saved before stopping. | `.sancho/checkpoints/2026-10-23-1740.md` |

## What `next` says now

```
NEXT (developer): Fix DEF-001 (major): Sign-in error reveals that an email is not registered ('User not found'), enabling account enumeration (TM-01)
```

After the fix: the user re-runs UAT-001, then UAT-004 and UAT-005; the VERIFY gate can be approved only when no blocker/major defect or security finding is open. RELEASE and EVOLVE follow.

## Files

```
.sancho/state.json, backlog.json, uat.json     machine-readable source of truth
.sancho/handoffs/  standards/  checkpoints/
docs/constitution.md  spec.md  plan.md  adr/0001-stack.md  adr/0002-containers.md
docs/uat/UAT.md  uat.csv                         printable checklist + spreadsheet (Italian, ';')
docs/security/threat-model.md  SECURITY-REPORT.md  security-report.json
design/tokens.json  logo.svg
Dockerfile  docker-compose.yml  .dockerignore  .env.example
```
