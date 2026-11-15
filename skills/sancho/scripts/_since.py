"""What changed since the last look: commits, team events, phases and documents (team mode helper).

Reads git only. The "last seen" marker is personal and outside the repository history:
<git dir>/sancho/last-seen.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from _common import SANCHO_DIR, now_iso
import _team

HOOK_MARK = "# sancho post-merge hook (installed by state.py hooks install)"
DOC_PATHS = ["docs", f"{SANCHO_DIR}/backlog.json", f"{SANCHO_DIR}/uat.json", f"{SANCHO_DIR}/team.json", f"{SANCHO_DIR}/standards"]


def git_dir(root: Path) -> Optional[Path]:
    d = _team.git(root, "rev-parse", "--git-dir")
    if not d:
        return None
    p = Path(d)
    return p if p.is_absolute() else (root / p).resolve()


def prefix(root: Path) -> str:
    """The project folder relative to the repository top level ('' at the top)."""
    return _team.git(root, "rev-parse", "--show-prefix")


def marker_path(root: Path) -> Optional[Path]:
    g = git_dir(root)
    return g / "sancho" / "last-seen.json" if g else None


def read_marker(root: Path) -> Optional[dict]:
    m = marker_path(root)
    try:
        return json.loads(m.read_text(encoding="utf-8")) if m and m.is_file() else None
    except (OSError, ValueError):
        return None


def write_marker(root: Path, commit: str) -> None:
    m = marker_path(root)
    if m is None:
        return
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text(json.dumps({"commit": commit, "at": now_iso()}) + "\n", encoding="utf-8")


def commit_exists(root: Path, ref: str) -> bool:
    return bool(_team.git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"))


def show_json(root: Path, ref: str, rel: str) -> Optional[dict]:
    text = _team.git(root, "show", f"{ref}:{prefix(root)}{rel}")
    try:
        return json.loads(text) if text else None
    except ValueError:
        return None


def added_events(root: Path, ref: str, head: str) -> List[dict]:
    """Event lines added between ref and head in the members' logs (not the archive)."""
    logs = [f"{SANCHO_DIR}/{_team.LOG_DIR}/{f.name}" for f in _team.log_files(root)]
    if not logs:
        return []
    diff = _team.git(root, "diff", "--no-color", "--unified=0", ref, head, "--", *logs)
    out = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            try:
                ev = json.loads(line[1:])
            except ValueError:
                continue
            if isinstance(ev, dict) and "event" in ev and "by" in ev:
                out.append(ev)
    out.sort(key=lambda e: (str(e.get("at", "")), e["by"]))
    return out


def phrase(ev: dict) -> str:
    kind = ev["event"]
    item = ev.get("task") or ev.get("case") or ev.get("defect") or ""
    if kind == "claim":
        return f"took {item}"
    if kind == "release":
        return f"released {item}"
    if kind == "task_status":
        extra = f" ({ev['blocked_reason']})" if ev.get("blocked_reason") else ""
        return f"{item} -> {ev['status']}{extra}"
    if kind == "review":
        return f"approved {item} in review" if ev["outcome"] == "approved" else f"asked for changes on {item}: {ev.get('note', '')}"
    if kind == "gate_approve":
        return f"approved the {ev['phase'].upper()} gate"
    if kind == "gate_reject":
        return f"rejected the {ev['phase'].upper()} gate: {ev.get('note', '')}"
    if kind == "uat_result":
        d = f" ({', '.join(ev['defects'])})" if ev.get("defects") else ""
        return f"{item} {ev['result']}{d}"
    if kind == "defect_open":
        return f"opened {item} ({ev['severity']}) on {ev['uat']}: {ev['description']}"
    if kind == "defect_status":
        return f"{item} -> {ev['status']}"
    return f"{kind} {item}"


def concerns(ev: dict, me: Optional[str], mine_items: set) -> bool:
    if me is None or ev["by"] == me:
        return False
    item = ev.get("task") or ev.get("case") or ev.get("defect")
    return item in mine_items


def compute(root: Path, ref: Optional[str], me: Optional[str], mine_items: set, my_emails: Optional[set] = None) -> dict:
    """Changes made by others between ref (default: the marker) and HEAD; your own are not news."""
    head = _team.git(root, "rev-parse", "HEAD")
    if not head:
        raise RuntimeError("since needs a git repository with at least one commit")
    marker = read_marker(root)
    if ref is None:
        if marker and commit_exists(root, marker["commit"]):
            ref = marker["commit"]
        elif commit_exists(root, "ORIG_HEAD"):
            ref = "ORIG_HEAD"
        else:
            return {"first_run": True, "from": None, "to": head, "commits": [], "by_member": {}, "mine": [],
                    "phases": [], "files": []}
    elif not commit_exists(root, ref):
        raise RuntimeError(f"unknown git reference: {ref}")
    ref_sha = _team.git(root, "rev-parse", ref)
    mails = {e.lower() for e in (my_emails or set())} | {_team.git(root, "config", "user.email").lower()} - {""}
    pre = prefix(root)
    sep = "\x1e"
    log = _team.git(root, "log", "--no-merges", f"--format={sep}%h|%an|%ae|%s", "--name-status", f"{ref_sha}..{head}",
                    "--", ".")
    commits: List[dict] = []
    files: Dict[str, str] = {}
    state_touched = False
    for block in log.split(sep):
        lines = [x for x in block.splitlines() if x.strip()]
        if not lines:
            continue
        sha, author, email, subject = (lines[0].split("|", 3) + ["", "", "", ""])[:4]
        if email.lower() in mails:
            continue  # your own commit, from this or another clone
        commits.append({"sha": sha, "author": author, "subject": subject})
        for entry in lines[1:]:
            parts = entry.split("\t")
            path = parts[-1][len(pre):] if parts[-1].startswith(pre) else parts[-1]
            if path == f"{SANCHO_DIR}/state.json":
                state_touched = True
            if any(path == d or path.startswith(d + "/") for d in DOC_PATHS):
                files[path] = parts[0][:1]
    events = [ev for ev in added_events(root, ref_sha, head) if ev["by"] != me]
    by_member: Dict[str, List[str]] = {}
    mine: List[str] = []
    for ev in events:
        text = phrase(ev)
        by_member.setdefault(ev["by"], []).append(text)
        if concerns(ev, me, mine_items):
            mine.append(f"{ev['by']} {text}")
    phases = []
    if state_touched:
        old_state = show_json(root, ref_sha, f"{SANCHO_DIR}/state.json") or {}
        new_state = show_json(root, head, f"{SANCHO_DIR}/state.json") or {}
        for ph, val in (new_state.get("phases") or {}).items():
            before = ((old_state.get("phases") or {}).get(ph) or {}).get("status")
            if before != val.get("status"):
                phases.append({"phase": ph, "from": before, "to": val.get("status")})
    files = [{"change": c, "path": f} for f, c in sorted(files.items())]  # type: ignore[assignment]
    return {"first_run": False, "from": ref_sha[:12], "to": head[:12], "commits": commits, "by_member": by_member,
            "mine": mine, "phases": phases, "files": files}


def hook_text(root: Path, state_py: Path) -> str:
    pre = prefix(root)
    candidates = " ".join(f'"{c}"' for c in (Path(sys.executable).as_posix(), "python3", "python"))
    return f"""#!/bin/sh
{HOOK_MARK}
# After a pull: what changed in the Sancho project (state.py since), whether its files are valid and coherent.
# Re-run `state.py hooks install` after moving or updating Sancho. Remove with `state.py hooks remove`.
cd "$(git rev-parse --show-toplevel)/{pre}" 2>/dev/null || exit 0
PY=""
for c in {candidates}; do
  "$c" -c "import sys; sys.exit(sys.version_info < (3, 9))" >/dev/null 2>&1 && PY="$c" && break
done
[ -n "$PY" ] || exit 0
"$PY" -I "{state_py.as_posix()}" since
"$PY" -I "{state_py.as_posix()}" validate >/dev/null 2>&1 || echo "sancho: some project files are invalid - run state.py validate"
"$PY" -I "{state_py.as_posix()}" coherence --quiet
exit 0
"""


def hook_path(root: Path) -> Optional[Path]:
    p = _team.git(root, "rev-parse", "--git-path", "hooks/post-merge")
    if not p:
        return None
    path = Path(p)
    return path if path.is_absolute() else (root / path).resolve()


def install_hook(root: Path, state_py: Path, force: bool) -> Tuple[bool, str]:
    path = hook_path(root)
    if path is None:
        return False, "not a git repository"
    if path.is_file() and HOOK_MARK not in path.read_text(encoding="utf-8", errors="replace") and not force:
        return False, f"{path} already exists and is not Sancho's; pass --force to replace it, or add the lines yourself"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(hook_text(root, state_py))
    try:
        path.chmod(0o755)
    except OSError:
        pass
    return True, str(path)


def remove_hook(root: Path) -> Tuple[bool, str]:
    path = hook_path(root)
    if path is None or not path.is_file():
        return False, "no post-merge hook"
    if HOOK_MARK not in path.read_text(encoding="utf-8", errors="replace"):
        return False, f"{path} is not Sancho's: left alone"
    path.unlink()
    return True, str(path)
