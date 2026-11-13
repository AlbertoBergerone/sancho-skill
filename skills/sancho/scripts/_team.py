"""Team mode for Sancho (standard library only).

Team mode is on when .sancho/team.json exists. Each member appends events to their own
file, .sancho/log/<member>.jsonl, and never edits anyone else's: members never touch the
same state file, so merging their work causes no conflict. The current task state is the
backlog plus every event, applied in time order (see `fold`).

Identity comes from SANCHO_USER=<id> or `git config user.email`. It is for coordination,
not access control.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from _common import SANCHO_DIR, load_json
from _schema import validate

TEAM_FILE = "team.json"
LOG_DIR = "log"
UNION_RULE = ".sancho/log/*.jsonl merge=union"


# ------------------------------------------------------------------------- loading

def team_path(root: Path) -> Path:
    return root / SANCHO_DIR / TEAM_FILE


def load_team(root: Path) -> Optional[dict]:
    p = team_path(root)
    return load_json(p) if p.is_file() else None


def members(team: dict) -> Dict[str, dict]:
    return {m["id"]: m for m in team.get("members", [])}


def git(root: Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True,
                             encoding="utf-8", timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def whoami(root: Path, team: dict) -> Tuple[Optional[str], str]:
    """(member id or None, how it was found)."""
    ms = members(team)
    env = os.environ.get("SANCHO_USER", "").strip()
    if env:
        return (env, "SANCHO_USER") if env in ms else (None, f"SANCHO_USER={env} is not a member of the team")
    email = git(root, "config", "user.email").lower()
    if not email:
        return None, "git config user.email is not set (or set SANCHO_USER=<member id>)"
    for m in ms.values():
        if email in (e.lower() for e in m["emails"]):
            return m["id"], f"git email {email}"
    return None, f"git email {email} is not in .sancho/team.json"


def log_files(root: Path) -> List[Path]:
    d = root / SANCHO_DIR / LOG_DIR
    return sorted(d.glob("*.jsonl")) if d.is_dir() else []


def read_events(root: Path, team: Optional[dict]) -> Tuple[List[dict], List[dict]]:
    """All valid events in time order, and the problems found (as invalid-file entries)."""
    known = set(members(team)) if team else set()
    events: List[dict] = []
    problems: List[dict] = []
    for f in log_files(root):
        rel = f.relative_to(root).as_posix()
        errors: List[str] = []
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as e:
            problems.append({"name": "event-log", "path": rel, "errors": [f"unreadable: {e}"]})
            continue
        for n, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except ValueError as e:
                errors.append(f"line {n}: not valid JSON: {e}")
                continue
            errs = validate(ev, "event")
            if errs:
                errors += [f"line {n}: {e}" for e in errs[:3]]
                continue
            if ev["by"] != f.stem:
                errors.append(f"line {n}: written by {ev['by']} in {f.name} (each member writes only their own log)")
                continue
            if known and ev["by"] not in known:
                errors.append(f"line {n}: {ev['by']} is not a member of the team")
                continue
            events.append({**ev, "_file": rel, "_line": n})
        if errors:
            problems.append({"name": "event-log", "path": rel, "errors": errors})
    events.sort(key=lambda e: (parse_time(e["at"]), e["by"], e["_line"]))
    return events, problems


def parse_time(text: str) -> datetime:
    t = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return t if t.tzinfo else t.astimezone()


# ------------------------------------------------------------------------- folding

def fold(backlog: dict, events: List[dict], leads: Optional[set] = None) -> Tuple[dict, dict]:
    """Apply events to a copy of the backlog.

    Returns (effective backlog, team view). The team view holds, per task, who claimed it
    and the last activity; and the conflicts: claims that lost because the task was
    already claimed (the earliest claim wins, ties by member id). The loser clears a
    conflict with `release`; a coordinator (in `leads`) may release anyone's claim.
    """
    leads = leads or set()
    bl = copy.deepcopy(backlog)
    tasks = {t["id"]: t for t in bl.get("tasks", [])}
    claims: Dict[str, dict] = {}
    worked: Dict[str, set] = {}
    last: Dict[str, str] = {}
    conflicts: List[dict] = []
    ignored: List[dict] = []
    for ev in events:
        tid, who = ev["task"], ev["by"]
        t = tasks.get(tid)
        if t is None:
            ignored.append({"event": ev["event"], "task": tid, "by": who, "reason": "unknown task"})
            continue
        holder = claims.get(tid, {}).get("by")
        kind = ev["event"]
        if kind == "claim":
            if holder and holder != who:
                conflicts.append({"task": tid, "lost": who, "won": holder, "at": ev["at"],
                                  "won_at": claims[tid]["at"]})
                continue
            if t["status"] in ("completed", "ready_for_review"):
                ignored.append({"event": kind, "task": tid, "by": who, "reason": f"task is {t['status']}"})
                continue
            claims[tid] = {"by": who, "at": ev["at"], "branch": ev.get("branch")}
            t["status"] = "in_progress"
            t.pop("blocked_reason", None)
        elif kind == "release":
            mine = [c for c in conflicts if c["task"] == tid and c["lost"] == who]
            if mine and holder != who:
                conflicts = [c for c in conflicts if c not in mine]
            elif holder == who or (holder and who in leads):
                claims.pop(tid, None)
                if t["status"] in ("in_progress", "blocked"):
                    t["status"] = "pending"
                    t.pop("blocked_reason", None)
        elif kind == "task_status":
            t["status"] = ev["status"]
            if ev["status"] == "blocked":
                t["blocked_reason"] = ev["blocked_reason"]
            else:
                t.pop("blocked_reason", None)
            if ev.get("evidence"):
                t["evidence"] = t.get("evidence", []) + ev["evidence"]
        elif kind == "review":
            if ev["outcome"] == "approved":
                t["status"] = "completed"
                t["evidence"] = t.get("evidence", []) + ev["evidence"]
                claims.pop(tid, None)
            else:
                t["status"] = "in_progress"
                t["review_notes"] = ev["note"]
        if kind != "review":
            worked.setdefault(tid, set()).add(who)  # authors: four-eyes reviews exclude them
        last[tid] = ev["at"]
    view = {
        "claims": claims,
        "authors": {k: sorted(v) for k, v in worked.items()},
        "last_event": last,
        "conflicts": conflicts,
        "ignored": ignored,
    }
    return bl, view


def strip_view_fields(backlog: dict) -> dict:
    """The effective backlog without fields that exist only in memory."""
    bl = copy.deepcopy(backlog)
    for t in bl.get("tasks", []):
        t.pop("review_notes", None)
    return bl


def stale(view: dict, team: dict, now: Optional[datetime] = None) -> List[str]:
    days = int(team.get("claim_stale_days", 3))
    now = now or datetime.now().astimezone()
    out = []
    for tid in view["claims"]:
        at = view["last_event"].get(tid)
        if at and now - parse_time(at) > timedelta(days=days):
            out.append(tid)
    return sorted(out)


# ------------------------------------------------------------------------- writing

def append_event(root: Path, event: dict) -> Path:
    """Append one validated event to the member's own log; never rewrites the file."""
    # microseconds: events of different members are ordered by time, so one second is too coarse
    event = {"at": datetime.now().astimezone().isoformat(timespec="microseconds"), **event}
    errs = validate(event, "event")
    if errs:
        raise ValueError("; ".join(errs[:5]))
    path = root / SANCHO_DIR / LOG_DIR / f"{event['by']}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_newline = path.is_file() and path.stat().st_size > 0 and not path.read_bytes().endswith(b"\n")
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        if needs_newline:
            fh.write("\n")
        fh.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    return path


def ensure_union_merge(root: Path) -> bool:
    """Make git merge the event logs line by line (a member working from two computers)."""
    ga = root / ".gitattributes"
    text = ga.read_text(encoding="utf-8") if ga.is_file() else ""
    if UNION_RULE in text:
        return False
    with open(ga, "a", encoding="utf-8", newline="\n") as fh:
        if text and not text.endswith("\n"):
            fh.write("\n")
        fh.write(UNION_RULE + "\n")
    return True


def parse_evidence(items: List[str]) -> List[dict]:
    """--evidence TYPE:VALUE, e.g. commit:a1b2c3d, test:"pytest tests/test_x.py", file:src/x.py."""
    field = {"commit": "commit", "command": "command", "test": "command", "file": "path",
             "screenshot": "path", "uat": "ref", "url": "url", "log": "note"}
    out = []
    for item in items:
        kind, sep, value = item.partition(":")
        kind = kind.strip().lower()
        if not sep or kind not in field or not value.strip():
            raise ValueError(f"bad evidence '{item}': use TYPE:VALUE with TYPE one of {', '.join(field)}")
        out.append({"type": kind, field[kind]: value.strip()})
    return out


# ------------------------------------------------------------------------- next step

def roles_of(team: dict, member: str) -> List[str]:
    return members(team).get(member, {}).get("roles", [])


def holders_of_role(team: dict, role: str) -> List[str]:
    return [m["id"] for m in team["members"] if role in m["roles"]]


def coordinators(team: dict) -> List[str]:
    c = [m["id"] for m in team["members"] if m.get("coordinator")]
    return c or [team["members"][0]["id"]]
