# Sancho panel

Part of the `sancho` plugin. In the Claude app (Code tab) and in Claude Code it shows:

1. **A band above the prompt**, only in folders with a Sancho project: phase and gate, blockers, a "zip da aggiornare" badge in a repository checkout, the next step and a "dettagli" link.
2. **Notices (toasts)** when the current gate, the next step or the ZIP state changes, and in team mode when something new concerns you. None on the first read.
3. **A details pane**, opened from the band or with `/sancho-panel`, never by itself. In team mode it adds **Squadra** (team) and **Novità** (news).

The data refreshes every 20 seconds, at the end of every turn and with the **Aggiorna** button. The panel text is in Italian.

The panel reads only: it writes nothing in the plugin or in the project. In team mode, **Segna come viste** moves your personal "last seen" marker, kept in the git folder and never committed.

| File | Role |
| --- | --- |
| `hooks.json` | names the hooks module |
| `register.tsx` | band, notices, pane, `/sancho-panel` |
| `sancho_panel.py` | collects the data as one JSON object |
| `../types/index.d.ts` | the panel's state contract |
| `../tests/panel.test.tsx` | tests, run with `claude plugin test .` |

## Where each item comes from

Every value comes from `hooks/sancho_panel.py`, run with `python -I` (or `python3 -I`) in the session's folder. It runs the bundled `skills/sancho/scripts/state.py status --json`, which looks for `.sancho/` in that folder or above.

| Item | Source |
| --- | --- |
| Project, level, folder | `status.project.name`, `status.project.level` (from `.sancho/state.json`); the folder is the session's |
| Phases and gate | `status.current_phase` and `status.phases.<phase>` (from `.sancho/state.json`) |
| Next step | `status.next` (`who`, `action`), the same logic as `state.py next` |
| Blockers and issues | `status.blockers`, `status.invalid_files`, `status.open_defects` (open UAT defects), `status.security` (open findings, closed ones, `not_run` checks), `status.uat` (cases by result) |
| Commands | Fixed list in the plugin form: `/sancho:<current phase>`, `status`, `next`, `checkpoint`, `assess`, `help`. Without a project: `discover`, `assess`, `help`. A click writes the command in the prompt without sending it |
| Team (team mode only) | `status.team`: who you are (`me`, from `git config user.email` or `SANCHO_USER`), what each member holds (`claims`), contested and stale claims, renamed defects, gate votes (`gate`). The next step is yours: `status.next` is computed for you |
| News (team mode only) | `state.py since --json --peek`: the others' commits and events since you last looked, `mine` first. **Segna come viste** runs `state.py since`, which moves your personal marker in the git folder (the only thing the panel writes); a notice appears when something new concerns you |
| ZIP for the Claude apps | Only in a repository checkout (`tools/build.py` and `dist/` present) or with `SANCHO_REPO` set to one: `dist/sancho.zip` compared file by file (SHA-256) with `skills/sancho` plus `LICENSE` and `NOTICE`, with the rules of `tools/build.py`. It cannot see what is uploaded to a claude.ai account. In the plugin as installed this section is hidden |

## Requirements

Python 3.9 or later on the PATH as `python` or `python3`, as for the rest of the plugin.
