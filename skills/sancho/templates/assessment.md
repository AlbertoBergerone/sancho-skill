# Assessment - {{project}}

_Date: {{YYYY-MM-DD}} · Question: {{what the user asked}} · Read-only analysis: {{what was run / not run}}_

## Act first
Blocker and major findings, most severe first, at most 6 rows (dependency findings: one row per package with a blocker, plus one summary row). Write "none found" if there are none, and say which checks that rests on.

| Severity | Finding | Where | Evidence label | Action |
|---|---|---|---|---|
| {{blocker/major}} | {{...}} | {{file:line or command}} | {{VERIFIED / REPORTED / HYPOTHESIS}} | {{rotate / fix / restrict}} |

## Answer: {{Roadmap | Starter kit | Go/no-go}}
{{the section that answers the user's question}}

## The project in brief
| | |
|---|---|
| Purpose | {{from README/docs - REPORTED}} |
| Stack | {{languages, frameworks, versions}} |
| Size and history | {{files, lines, commits, date range, uncommitted changes}} |
| Tests and CI | {{what exists, what ran}} |

## Strengths
| What | Why it is worth keeping | Where | Evidence label |
|---|---|---|---|

## Weaknesses and risks
| Severity | What | Where | Evidence label |
|---|---|---|---|

## Checks
| Check | Result | Command |
|---|---|---|
| Secrets in git (names only) | | |
| Dependencies (cve_enrich) | | |
| Analyzer / linter | | |
| Tests | | |

## Not verified
- {{each NOT RUN check, with the command to run it}}
