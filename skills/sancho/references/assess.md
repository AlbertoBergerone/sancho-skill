# assess - analysis of an existing project

Use `assess` when the user asks Sancho to look at code that already exists: a project to take over, review, plan a roadmap for, or mine for ideas to reuse. It is not a phase and has no gate; it needs no `.sancho/` folder and creates none unless the user asks.

Lead role: Architect, with Security and QA. The user's question (roadmap, reuse, takeover, due diligence) decides the answer section; the rest of the procedure is the same every time.

## Rules

- **read-only by default.** Read files and run only commands that change nothing in the project: listing, `git log`/`git ls-files`/`git grep`, the project's analyzer in check mode (`flutter analyze`, `pint --test`, `eslint` without `--fix`), tests with caches off (`phpunit --do-not-cache-result`). Do not install packages, migrate, start servers, or edit files. The only external calls allowed are those of `scripts/cve_enrich.py`, which sends package names and versions to public vulnerability databases.
- **Tests only when isolated.** Run a test suite only if it cannot reach a real database or service. If the test configuration points at a real database (for example `phpunit.xml` without an in-memory database, or a `.env` used by the tests) or needs network or credentials, it is NOT RUN, with the reason and the command.
- **Working tree, not just the last commit.** Analyze the files as they are on disk; report the number of uncommitted changes (`git status --short | wc -l`) in the brief. When a finding exists only in the working tree or only in `HEAD`, say which.
- **Evidence labels on every claim** (`references/taxonomy.md`): VERIFIED (seen in code or command output in this session, with file:line or the command), REPORTED (stated by docs, comments or README, not checked), HYPOTHESIS (inference), NOT RUN (a check you did not do, with the command to do it). Project documents describe intent, not facts. A security flaw seen in the code but not exploited is VERIFIED for the code and HYPOTHESIS for exploitability: rate its severity by the damage if exploited (`references/taxonomy.md`), and say that it was not exploited.
- **One severity scale** for findings: blocker, major, minor, nit. Whatever the user asked, blocker and major findings, security ones above all, go first under "Act first", with the action to take. Do not bury a leaked credential under "lessons learned".
- **Never print secrets.** Look for them by file and key names only: `git ls-files` for `.env`, keys and config files, `git grep -l` for password/token/secret patterns (file names, not lines), `cut -d= -f1` on env files. Never print values, value lengths or partial values. Name the file and the kind of secret, say whether it is tracked by git and since how many commits, and recommend rotation.
- **No invented requirements.** Strengths and gaps are judged against what the project says it wants to be (README, docs, the user's words), not against an ideal product.

## Procedure

1. **Frame.** One line restating the question and the output the user will get. If the folder is not a project (no code), say so and stop.
2. **Map.** Stack and versions (manifest files), size (files, lines per language), history (`git log` count and date range), uncommitted changes, structure (top folders, modules), entry points, docs, tests and CI. A short table.
3. **Read the core.** The few files everything depends on: entry point, base classes, data layer, auth, configuration. Follow one real feature end to end. Record what you read; list the large areas you did not read.
4. **Checks** (run what applies, list the rest as NOT RUN):
   - secrets: names only, as above;
   - dependencies: `scripts/cve_enrich.py <lockfiles> --no-nvd --out <scratch>/sca.json --md <scratch>/sca.md` on the files it reads (`package-lock.json`, `requirements*.txt`, CycloneDX SBOM). Use `--no-nvd` by default: with NVD a large lockfile takes many minutes; run NVD only if the user asks. Write the output outside the project unless the user wants `docs/security/`. Lockfiles the script does not read (`composer.lock`, `pubspec.lock`, `Gemfile.lock`...) are NOT RUN: name them and the way to cover them (generate a CycloneDX SBOM with the ecosystem's tool, then run `cve_enrich.py` on it);
   - security by reading: authentication and password reset, authorization checks (and endpoints that skip them), file paths and SQL or shell built from request input, multi-tenant boundaries, broadcast/channel authorization, error handling;
   - quality: analyzer/linter in check mode, isolated tests, TODO/FIXME count, debug leftovers (`die(`, `dd(`, `console.log`, `print(`) in tracked code;
   - operations: scheduler, CI, deploy scripts, backups, monitoring - present or not.
5. **Judge.** Strengths (what to keep or reuse, with why and where), weaknesses (what breaks or costs), risks (what could hurt users or the business). Each item with evidence label and file:line.
6. **Answer the question asked:**
   - roadmap: next steps mapped to Sancho phases (what DISCOVER/SPECIFY must settle, the first tasks), smallest useful milestone first; when the user asks for prompts, one self-contained prompt per step;
   - reuse: a short "starter kit" list (what to extract, what to fix before reusing);
   - takeover or due diligence: go/no-go conditions.
7. **Reply** with `templates/assessment.md`: "Act first" (at most 6 rows), then the answer to the question, then the details. Keep the reply readable in chat (about 60 lines); put long lists (all dependency findings, every TODO) in the saved report or the `sca.md` file, not in the reply. Offer once to save the full report as `docs/assessment.md`, and to continue with Sancho: `discover` using the report as the brief (the analysis is input, not approved requirements).

## Dependency findings in "Act first"

A large lockfile can produce dozens of blocker and major findings, many from transitive packages. In "Act first" use one row per package with a blocker finding (KEV listed, CVSS 9 or more, EPSS 0.5 or more), naming the package, version and the reason, and one summary row with the totals by severity and the path of `sca.md`. Say when a package matters only in development (for example a dev server) and is not shipped.

## What NOT to do

- Do not re-score or rewrite the project's own documents; quote them as REPORTED.
- Do not present "reads well" as "works": without a run, say it.
- Do not list every file you saw; list what you checked and what you did not.
