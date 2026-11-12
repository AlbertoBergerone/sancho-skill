# Sancho - installation guide

[English](install.en.md) · [Italiano](install.it.md) · [Español](install.es.md) · Next: [usage guide](guide.en.md)

## 1. Choose your setup

| You use | Install | What you get |
|---|---|---|
| **Claude Code** (terminal, desktop app Code tab, VS Code, JetBrains) | **A. Plugin** (recommended) | skill + 7 subagents + `/sancho:...` commands + the Sancho panel |
| Claude Code, but you want a minimal install | **B. Skill only** | skill; the roles are played by the main conversation; command `/sancho` |
| **Claude app** (claude.ai web, desktop, mobile) | **C. Upload the ZIP** | skill; you talk to it in plain language |

All three use the same skill. You can install it in more than one place.

## 2. Requirements

- **Python 3.9 or later** on the computer where Claude Code runs. The helper scripts use only the standard library, so you don't need `pip install`. In the Claude app, scripts run in Claude's own sandbox, and you need nothing locally.
  - Check: `python --version` (Windows) or `python3 --version` (macOS/Linux).
  - Windows: install from [python.org](https://www.python.org/downloads/) and tick **Add python.exe to PATH**, or run `winget install Python.Python.3.12`.
- **Claude Code**, for options A and B. The plugin commands below need a recent version.
- **Claude app**, for option C: any plan. **Code execution** must be enabled (see 5).
- **Optional:** git, and the security tools in section 6.

## 3. Option A - Claude Code plugin (recommended)

### From GitHub

> **Where to type the commands.** Commands that start with `/` (like `/plugin ...`) are typed **inside a Claude Code session**, not in PowerShell or Terminal: first run `claude`, then type them at its prompt. From PowerShell or Terminal use the equivalent `claude plugin ...` commands shown below. If `claude` is not recognized, Claude Code is not installed yet: see the official Claude Code setup page (on Windows: `irm https://claude.ai/install.ps1 | iex`).

1. Open a terminal in your project folder and start Claude Code: `claude`
2. Add the Sancho marketplace (once per computer):
   ```
   /plugin marketplace add AlbertoBergerone/sancho-skill
   ```
   You should see `Successfully added marketplace: sancho`.
3. Install the plugin:
   ```
   /plugin install sancho@sancho
   ```
   The plugin panel opens. Choose a scope:
   - **Install for you (user scope)**: Sancho is available in every project. Recommended.
   - **Install for all collaborators on this repository (project scope)**: the whole team gets it. Each colleague also runs the install once.
   - **Install for you, in this repo only (local scope)**.
4. If the summary says `Run /reload-plugins to apply`, Claude Code runs the reload for you. Otherwise the plugin is active right away.
5. Check: type `/sancho:` and the commands appear (`/sancho:help`, `/sancho:next`, ...). Then run `/sancho:help`.

From your shell, without opening a session:

```bash
claude plugin marketplace add AlbertoBergerone/sancho-skill
claude plugin install sancho@sancho
```

In the **desktop app** (Code tab, local session): add the marketplace as above, then click **+** next to the prompt box, choose **Add plugins** (or **Plugins**, then **Browse plugins**) and select Sancho.

### The Sancho panel

The plugin also adds a panel in the Claude app (Code tab) and in Claude Code: a band above the prompt with phase, gate and next step, notices when they change, and a details pane (`/sancho-panel`). It appears by itself in folders with a Sancho project and uses the same Python. Options B and C do not have it.

### From a local copy (testing before you publish)

```
/plugin marketplace add ./sancho-skill
/plugin install sancho@sancho
```

Start a relative path with `./` or `../`: a bare `name/name` is read as a GitHub repository. To load it for one session only, without installing, start Claude Code with `claude --plugin-dir ./sancho-skill`.

## 4. Option B - skill only (Claude Code)

Copy the folder `skills/sancho` from this repository into your skills folder.

**Windows (PowerShell)**, from the repository folder:
```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\sancho "$env:USERPROFILE\.claude\skills\sancho"
```

**macOS / Linux**:
```bash
mkdir -p ~/.claude/skills && cp -R skills/sancho ~/.claude/skills/
```

For one project only, copy it to `<project>/.claude/skills/sancho` instead. Restart Claude Code, then type `/sancho help`.

Without the plugin there are no subagents and no `/sancho:...` commands. The main conversation plays the seven roles in turn, and you type `/sancho next`, `/sancho verify uat` and so on.

## 5. Option C - Claude app (claude.ai, desktop, mobile)

1. Get `sancho.zip`:
   - from the repository's [Releases](https://github.com/AlbertoBergerone/sancho-skill/releases) page, or
   - by building it: `python tools/build.py` creates `dist/sancho.zip`.

   **Do not** use GitHub's green "Code -> Download ZIP" button: that archive contains the whole repository, and the upload fails because `SKILL.md` is not in a top-level `sancho/` folder.
2. Enable code execution: **Settings -> Capabilities -> Code execution and file creation** (called **Create and edit files** in the newer layout).
3. Upload: **Customize -> Skills -> "+" -> Create skill -> Upload a skill**, then choose `sancho.zip`.
4. Make sure the switch next to Sancho is on.
5. Test in a new chat: "sancho, help".

Team and Enterprise plans: skills and code execution must be allowed for the organization. On Enterprise an owner enables them under **Organization settings -> Plugins & skills**. An owner can also turn off skill creation for users. Menu names may change between app versions.

## 6. Optional tools for security testing

Sancho works without them. Whatever is missing is reported as **NOT RUN**, with the command to run it later. Install from the official pages:

| Tool | Used for | Official site |
|---|---|---|
| gitleaks | secrets in the repository and its history | github.com/gitleaks/gitleaks |
| Semgrep | static analysis (SAST) | semgrep.dev |
| osv-scanner | dependency vulnerabilities | google.github.io/osv-scanner |
| Syft | SBOM in CycloneDX format | github.com/anchore/syft |
| Trivy | container image and configuration scanning | trivy.dev |
| OWASP ZAP | DAST on your own local or test environment (Docker image) | zaproxy.org |
| MobSF | Android/iOS app analysis (Docker image) | github.com/MobSF/Mobile-Security-Framework-MobSF |
| Docker Desktop | runs containers, ZAP and MobSF | docker.com |

**NVD API key (optional).** With a key, the NVD rate limit is higher. Request it at nvd.nist.gov (Developers -> Request an API key), then set it as an environment variable. Never paste it into the chat.
- Windows: `setx NVD_API_KEY "your-key"`, then open a new terminal.
- macOS/Linux: add `export NVD_API_KEY="your-key"` to your shell profile.

## 7. Check the installation

- In Claude Code: `/sancho:help` (plugin) or `/sancho help` (skill only). You should see the tour of the 8 phases.
- In the Claude app: write "sancho, help".
- From a clone of the repository: `python -I tests/validate.py` should report all checks passed.

## 8. Update

| Setup | How |
|---|---|
| Plugin | `/plugin` -> **Marketplaces** tab -> sancho -> **Update marketplace**, or `claude plugin update sancho@sancho` in your shell. Auto-update is off by default for third-party marketplaces; you can turn it on in the same tab. |
| Skill only | Replace the folder `~/.claude/skills/sancho` with the new one. |
| Claude app | Remove the old skill in **Customize -> Skills** and upload the new ZIP. |

Your project files (`.sancho/`, `docs/`, `design/`) are not touched by updates.

## 9. Uninstall

- Plugin: `/plugin uninstall sancho@sancho` (or `claude plugin uninstall sancho@sancho`). To also forget the marketplace: `/plugin marketplace remove sancho`.
- Skill only: delete `~/.claude/skills/sancho`.
- Claude app: turn the switch off, or delete the skill in **Customize -> Skills**.

The `.sancho/` folders in your projects stay where they are: they belong to your projects.

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| `/plugin : The term '/plugin' is not recognized` in PowerShell | You typed a Claude Code command in PowerShell. Run `claude` first and type it there, or use `claude plugin marketplace add .\sancho-skill` from PowerShell. |
| `/sancho:` commands do not appear | Run `/reload-plugins`; open `/plugin` and check the **Errors** tab; verify that `claude plugin list` shows sancho as enabled. |
| `/plugin marketplace add sancho-skill` fails | For a local folder, start the path with `./`. For GitHub, use `user/repo` without `https://github.com/`. |
| "python not found" or `python3` opens the Microsoft Store (Windows) | Install Python from python.org with **Add to PATH**. Sancho uses `python` when `python3` is not available. |
| ZIP upload rejected | Use `sancho.zip` from Releases or from `tools/build.py`: the archive must contain `sancho/SKILL.md`. |
| Security checks say NOT RUN | The tool is not installed or the network is blocked. Install it (section 6) and run `/sancho:verify security` again. |
| Subagents are never used | They exist only with the plugin (option A). With option B the roles are played in the main conversation, which is expected. |

Next: [usage guide](guide.en.md).
