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

EMPTY_UAT = {"cases": [], "defects": []}


def item_of(ev: dict) -> Optional[str]:
    return ev.get("task") or ev.get("case") or ev.get("defect")


def next_defect_id(taken: set) -> str:
    n = max([int(d.split("-")[1]) for d in taken] or [0]) + 1
    return f"DEF-{n:03d}"


def fold(backlog: dict, uat: dict, events: List[dict], leads: Optional[set] = None,
         names: Optional[Dict[str, str]] = None) -> Tuple[dict, dict, dict]:
    """Apply events to copies of the backlog and the UAT file.

    Returns (effective backlog, effective UAT, team view). Claims work the same for tasks,
    UAT cases and defects: the earliest claim wins (ties by member id); a later claim is a
    conflict the loser clears with `release`; a coordinator (in `leads`) may release anyone's
    claim. Two members opening the same defect id: the later one gets the next free id
    (view["renamed"]), and that member's later events follow the new id.
    """
    leads = leads or set()
    names = names or {}
    bl = copy.deepcopy(backlog)
    ua = copy.deepcopy(uat) if uat else copy.deepcopy(EMPTY_UAT)
    ua.setdefault("defects", [])
    tasks = {t["id"]: t for t in bl.get("tasks", [])}
    cases = {c["id"]: c for c in ua.get("cases", [])}
    defects = {d["id"]: d for d in ua["defects"]}
    claims: Dict[str, dict] = {}
    worked: Dict[str, set] = {}
    last: Dict[str, str] = {}
    conflicts: List[dict] = []
    ignored: List[dict] = []
    renamed: List[dict] = []
    remap: Dict[Tuple[str, str], str] = {}
    gates: Dict[str, dict] = {}
    for ev in events:
        who, kind = ev["by"], ev["event"]
        if ev.get("defect"):
            ev = {**ev, "defect": remap.get((who, ev["defect"]), ev["defect"])}
        if ev.get("defects"):
            ev = {**ev, "defects": [remap.get((who, d), d) for d in ev["defects"]]}
        if kind in ("gate_approve", "gate_reject"):
            g = gates.setdefault(f"{ev['phase']}#{ev['iteration']}", {"approved_by": [], "rejected": []})
            if kind == "gate_approve" and who not in g["approved_by"]:
                g["approved_by"].append(who)
                g.setdefault("approved_at", {})[who] = ev["at"]
            elif kind == "gate_reject":
                g["rejected"].append({"by": who, "at": ev["at"], "note": ev["note"]})
            continue
        if kind == "defect_open":
            did = ev["defect"]
            if did in defects:
                new = next_defect_id(set(defects))
                remap[(who, did)] = new
                renamed.append({"from": did, "to": new, "by": who})
                did = new
            defects[did] = {"id": did, "uat": ev["uat"], "severity": ev["severity"],
                            "description": ev["description"], "status": "open"}
            if ev.get("steps_to_reproduce"):
                defects[did]["steps_to_reproduce"] = ev["steps_to_reproduce"]
            if ev.get("fix_task"):
                defects[did]["task"] = ev["fix_task"]
            ua["defects"].append(defects[did])
            worked.setdefault(did, set()).add(who)
            last[did] = ev["at"]
            continue
        iid = item_of(ev)
        target = tasks.get(iid) or cases.get(iid) or defects.get(iid)  # type: ignore[arg-type]
        if iid is None or target is None:
            ignored.append({"event": kind, "item": iid, "by": who, "reason": "unknown item"})
            continue
        holder = claims.get(iid, {}).get("by")
        if kind == "claim":
            if holder and holder != who:
                conflicts.append({"item": iid, "lost": who, "won": holder, "at": ev["at"], "won_at": claims[iid]["at"]})
                continue
            if iid in tasks and target["status"] in ("completed", "ready_for_review"):
                ignored.append({"event": kind, "item": iid, "by": who, "reason": f"task is {target['status']}"})
                continue
            claims[iid] = {"by": who, "at": ev["at"], "branch": ev.get("branch")}
            if iid in tasks:
                target["status"] = "in_progress"
                target.pop("blocked_reason", None)
        elif kind == "release":
            mine = [c for c in conflicts if c["item"] == iid and c["lost"] == who]
            if mine and holder != who:
                conflicts = [c for c in conflicts if c not in mine]
            elif holder == who or (holder and who in leads):
                claims.pop(iid, None)
                if iid in tasks and target["status"] in ("in_progress", "blocked"):
                    target["status"] = "pending"
                    target.pop("blocked_reason", None)
        elif kind == "task_status":
            target["status"] = ev["status"]
            if ev["status"] == "blocked":
                target["blocked_reason"] = ev["blocked_reason"]
            else:
                target.pop("blocked_reason", None)
            if ev.get("evidence"):
                target["evidence"] = target.get("evidence", []) + ev["evidence"]
        elif kind == "review":
            if ev["outcome"] == "approved":
                target["status"] = "completed"
                target["evidence"] = target.get("evidence", []) + ev["evidence"]
                claims.pop(iid, None)
            else:
                target["status"] = "in_progress"
                target["review_notes"] = ev["note"]
        elif kind == "uat_result":
            target.update({"result": ev["result"], "executed_by": names.get(who, who), "executed_at": ev["at"]})
            for key in ("notes", "defects"):
                target.pop(key, None)
            if ev.get("note"):
                target["notes"] = ev["note"]
            if ev.get("defects"):
                target["defects"] = ev["defects"]
            claims.pop(iid, None)
        elif kind == "defect_status":
            target["status"] = ev["status"]
            if ev.get("fix_task"):
                target["task"] = ev["fix_task"]
            if ev["status"] in ("verified", "wont_fix"):
                claims.pop(iid, None)
            if ev["status"] == "fixed":
                target["_fixed_by"] = who
        if kind not in ("review", "uat_result") and not (kind == "defect_status" and ev["status"] == "verified"):
            worked.setdefault(iid, set()).add(who)  # authors: four-eyes reviews and verifications exclude them
        last[iid] = ev["at"]
    view = {
        "claims": claims,
        "authors": {k: sorted(v) for k, v in worked.items()},
        "fixed_by": {d["id"]: d.pop("_fixed_by") for d in ua["defects"] if "_fixed_by" in d},
        "last_event": last,
        "conflicts": conflicts,
        "ignored": ignored,
        "renamed": renamed,
        "gates": gates,
    }
    return bl, ua, view


def strip_view_fields(backlog: dict) -> dict:
    """The effective backlog without fields that exist only in memory."""
    bl = copy.deepcopy(backlog)
    for t in bl.get("tasks", []):
        t.pop("review_notes", None)
    return bl


def approvers_of(team: dict, phase: str) -> List[str]:
    a = team.get("approvers", {})
    return a.get(phase) or a.get("default") or coordinators(team)


def quorum_of(team: dict, phase: str) -> int:
    q = team.get("quorum", {})
    return int(q.get(phase) or q.get("default") or 1)


def gate_votes(view: dict, team: dict, phase: str, iteration: int, since: Optional[str]) -> Tuple[List[str], List[dict]]:
    """Distinct approvals (by allowed approvers, after the submission) and rejections for a gate."""
    g = view["gates"].get(f"{phase}#{iteration}", {"approved_by": [], "rejected": [], "approved_at": {}})
    allowed = set(approvers_of(team, phase))
    after = (lambda at: parse_time(at) >= parse_time(since)) if since else (lambda at: True)
    ok = [m for m in g["approved_by"] if m in allowed and after(g.get("approved_at", {}).get(m, since or ""))]
    rej = [r for r in g["rejected"] if r["by"] in allowed and after(r["at"])]
    return ok, rej


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
