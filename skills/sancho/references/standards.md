# Project standards (consistency over time)

Inspired by Agent OS (MIT): document how this project does things, and give each task only the standards it needs.

## Where

`.sancho/standards/`, one short Markdown file per topic, plus `glossary.md`. Suggested set (create only what the project uses):

| File | Content |
|---|---|
| `glossary.md` | preferred terms, definitions, terms to avoid (template `templates/glossary.md`) |
| `architecture.md` | layers, module boundaries, where things go, dependency direction |
| `code-style.md` | formatting/lint config, naming, error handling, logging, comments |
| `api.md` | endpoint naming, versioning, errors format, pagination, auth headers |
| `data.md` | migrations, naming, soft delete, timestamps, personal data handling |
| `ui.md` | components, design tokens usage, accessibility rules, copy tone |
| `testing.md` | test layout, naming, fixtures, what each level covers, coverage target |
| `mobile.md` | platform conventions, permissions, offline behavior |
| `security.md` | input validation, authz checks, secrets, dependency policy |

Each file uses the template `templates/standard.md`: rules with MUST/SHOULD, a short good example, a short bad example, and "why". Keep each under about 80 lines: standards are loaded into context.

## Lifecycle

1. **Create (PLAN):** the Architect writes the initial set from the ADRs and the chosen stack's community conventions. The UX/UI designer writes `ui.md`.
2. **Assign (TASKS):** each task lists the standards to load in its `standards` field (for example `["api.md", "testing.md"]`). Only those are loaded by the developer - this keeps context small and relevant.
3. **Apply (IMPLEMENT):** the developer follows them; QA flags deviations in review.
4. **Extract and refresh (EVOLVE, and when joining an existing codebase):** read the real code and compare it with the standards:
   - pattern used consistently but not documented -> document it;
   - standard not followed anywhere -> ask the user: update the standard or create refactoring tasks;
   - two competing patterns -> pick one with the user, record an ADR, create tasks to converge.
   Look at: folder structure, naming, error handling, logging, test layout, API shapes, UI component usage, lint configs.

## Existing codebases

When Sancho starts on a repository that already has code, run the extraction step during DISCOVER (Architect role) before proposing anything, so new work matches what is there.
