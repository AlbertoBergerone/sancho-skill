#!/usr/bin/env python3
"""Sancho project state: init, status, next step, phase gates, approvals, decisions.

Run from the project root (or any subfolder). State lives in .sancho/state.json.

  init       --name NAME --level L0..L3 --platforms web,android [--language it] [--threshold 7] [--summary TEXT]
  status     [--json]                      where the project is
  next       [--json]                      the single next concrete step and who does it
  checklist  PHASE                         gate checklist items for a phase
  start      PHASE [--reopen]              begin (or reopen) a phase; earlier phases must be closed
  submit     PHASE --results "DIS-1=pass,DIS-2=n/a:no UI, CLI only,..." --coherence pass|fail|not_run|n/a
             (or repeat --result "DIS-1=pass"; n/a needs a note after a colon)
  approve    PHASE [--override REASON]     ONLY after the user explicitly approved in the conversation
  set-level  L0..L3                        change the risk level; level-default skips follow it
  new-iteration                            reopen SPECIFY..EVOLVE for the next iteration (after EVOLVE)
  reject     PHASE --reason TEXT
  skip       PHASE --reason TEXT --adr docs/adr/NNNN-....md
  approval   --action TEXT --scope TEXT [--window START/END]   record an authorization the user granted
  decision   --summary TEXT --by user|agent [--adr PATH]
  checkpoint --file PATH                   record a saved checkpoint
  validate                                 validate state, backlog, UAT, team and event log files
  task       TASK --status S [--reason TEXT] [--evidence TYPE:VALUE ...] [--note TEXT]
                                           set a task's status (evidence: commit:SHA, test:"CMD", file:PATH, ...)

Team mode (when .sancho/team.json exists; see references/team.md):
  team       add --id ID --name NAME --email EMAIL --roles developer,qa [--coordinator]
             | list | suggest               members; suggest lists the authors in git log
  whoami                                   which member you are (SANCHO_USER or git config user.email)
  claim      ITEM [--branch B] [--any-role] take a task, UAT case or defect (T-007, UAT-004, DEF-002)
  release    ITEM                          give it back (or acknowledge a lost claim)
  review     TASK --approve --evidence TYPE:VALUE ... | --changes TEXT   QA review of a ready task
  next       [--json] [--team] [--as ID]   your next step; --team gives one line per member
  uat        CASE --result pass|fail|blocked [--note T] [--defect DEF-1] [--new-defect major:TEXT]
                                           record a UAT result (also without a team; --tester NAME)
  defect     DEF --status open|fixed|verified|wont_fix [--task T-012]   (also without a team)
  compact                                  coordinator: archive the events of settled items, state unchanged
  since      [REF] [--json] [--peek]       what changed since you last looked (git): commits, events, phases, files
  hooks      install|remove|status [--force]   post-merge hook: `since` and `validate` after every pull
  renumber   [--apply]                     rename duplicate ids after a merge (dry run without --apply)
  coherence  [--json] [--quiet]            coherence_check.py at the stage of the current phase
  Gates: the coordinator starts and submits; approvers (team.json approvers/quorum) approve or reject.

Exit codes: 0 ok, 1 refused (gate rules), 2 usage/input error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (LEVEL_DEFAULT_SKIPS, PHASE_LEAD, PHASES, SANCHO_DIR, configure_stdout, die,  # noqa: E402
                     find_root, load_json, now_iso, save_json)
from _schema import validate  # noqa: E402
import _team  # noqa: E402
import _since  # noqa: E402

GATES = load_json(Path(__file__).resolve().parent / "gates.json")["phases"]
CLOSED = ("approved", "skipped")
# Phases whose gate needs a passing coherence check (gates.md); others accept n/a.
COHERENCE_OPTIONAL = {"discover", "evolve"}
PRIORITY = {"must": 0, "should": 1, "could": 2, "wont": 3}


# ----------------------------------------------------------------------------- io

def file_errors(path: Path, name: str) -> List[str]:
    try:
        data = load_json(path)
    except ValueError as e:
        return [f"not valid JSON: {e}"]
    return validate(data, name)


class Project:
    def __init__(self, root: Path):
        self.root = root
        self.dir = root / SANCHO_DIR
        self.state_path = self.dir / "state.json"
        try:
            self.state = load_json(self.state_path)
        except ValueError as e:
            die(f"invalid {self.state_path}: not valid JSON: {e}")

    def file(self, key: str, default: str) -> Path:
        rel = self.state.get("artifacts", {}).get(key, default)
        return self.root / rel

    def backlog_path(self) -> Path:
        return self.file("backlog", f"{SANCHO_DIR}/backlog.json")

    def plan_backlog(self) -> dict:
        """backlog.json as written: the plan, without the team's events."""
        p = self.backlog_path()
        return load_json(p) if p.is_file() else {"requirements": [], "stories": [], "tasks": []}

    def team(self) -> Optional[dict]:
        if not hasattr(self, "_team"):
            try:
                t = _team.load_team(self.root)
            except ValueError:
                t = None
            self._team = t if t is not None and not validate(t, "team") else None
        return self._team

    def folded(self) -> Tuple[dict, dict, List[dict]]:
        """(effective backlog, team view, event-log problems); without a team, the plan as is."""
        if not hasattr(self, "_folded"):
            team = self.team()
            events, problems = _team.read_events(self.root, team) if (team or _team.log_files(self.root)) else ([], [])
            empty = {"claims": {}, "authors": {}, "fixed_by": {}, "last_event": {}, "conflicts": [], "ignored": [],
                     "renamed": [], "gates": {}}
            try:
                plan = self.plan_backlog()
            except ValueError:  # reported by invalid_files
                plan = {"requirements": [], "stories": [], "tasks": []}
            try:
                plan_uat = self.plan_uat()
            except ValueError:
                plan_uat = {"cases": [], "defects": []}
            bl, ua, view = plan, plan_uat, empty
            if team:
                names = {m["id"]: m["name"] for m in team["members"]}
                try:
                    bl, ua, view = _team.fold(plan, plan_uat, events, set(_team.coordinators(team)), names)
                except (KeyError, TypeError):  # an invalid backlog or UAT file: reported by invalid_files
                    pass
            self._uat_folded = ua
            self._folded = (bl, view, problems)
        return self._folded

    def backlog(self) -> dict:
        return self.folded()[0]

    def uat_path(self) -> Path:
        return self.file("uat", f"{SANCHO_DIR}/uat.json")

    def plan_uat(self) -> dict:
        p = self.uat_path()
        return load_json(p) if p.is_file() else {"cases": [], "defects": []}

    def uat(self) -> dict:
        self.folded()
        return self._uat_folded

    def security(self) -> Optional[dict]:
        p = self.file("security_report", "docs/security/security-report.json")
        return load_json(p) if p.is_file() else None

    def documents(self) -> List[Tuple[str, Path]]:
        docs = [("state", self.state_path),
                ("backlog", self.backlog_path()),
                ("uat", self.file("uat", f"{SANCHO_DIR}/uat.json")),
                ("security-report", self.file("security_report", "docs/security/security-report.json"))]
        if _team.team_path(self.root).is_file():
            docs.append(("team", _team.team_path(self.root)))
        return docs

    def invalid_files(self) -> List[dict]:
        out = []
        for name, path in self.documents():
            errors = file_errors(path, name) if path.is_file() else []
            if errors:
                out.append({"name": name, "path": path.relative_to(self.root).as_posix(), "errors": errors})
        return out + self.folded()[2]

    def save(self) -> None:
        self.state["updated_at"] = now_iso()
        errors = validate(self.state, "state")
        if errors:
            die("refusing to write an invalid state:\n  " + "\n  ".join(errors[:10]))
        save_json(self.state_path, self.state)


def open_project() -> Project:
    root = find_root()
    if root is None:
        die("no .sancho/ folder found here or above: run `state.py init` first (or /sancho:discover)")
    return Project(root)  # type: ignore[arg-type]


# ------------------------------------------------------------------------ commands

def cmd_init(a: argparse.Namespace) -> int:
    root = Path.cwd()
    target = root / SANCHO_DIR / "state.json"
    if target.exists():
        die(f"{target} already exists")
    platforms = [p.strip().lower() for p in a.platforms.split(",") if p.strip()] if a.platforms else []
    ts = now_iso()
    phases: Dict[str, dict] = {}
    for ph in PHASES:
        if ph in LEVEL_DEFAULT_SKIPS[a.level]:
            phases[ph] = {"status": "skipped", "skip_reason": "level-default"}
        else:
            phases[ph] = {"status": "not_started", "lead": PHASE_LEAD[ph]}
    phases["discover"].update({"status": "in_progress", "started_at": ts})
    state = {
        "protocol": "sancho/1.0",
        "project": {"name": a.name, "level": a.level, "platforms": platforms},
        "created_at": ts, "updated_at": ts, "current_phase": "discover", "phases": phases,
        "stack": [], "decisions": [], "approvals": [], "checkpoints": [],
        "artifacts": {
            "constitution": "docs/constitution.md", "spec": "docs/spec.md", "plan": "docs/plan.md",
            "adr_dir": "docs/adr", "backlog": f"{SANCHO_DIR}/backlog.json", "uat": f"{SANCHO_DIR}/uat.json",
            "security_report": "docs/security/security-report.json", "standards_dir": f"{SANCHO_DIR}/standards",
            "handoffs_dir": f"{SANCHO_DIR}/handoffs",
        },
        "settings": {"language": a.language, "complexity_threshold": a.threshold, "tdd": True},
        "iteration": 1,
    }
    if a.summary:
        state["project"]["summary"] = a.summary
    errors = validate(state, "state")
    if errors:
        die("invalid init arguments:\n  " + "\n  ".join(errors))
    save_json(target, state)
    save_json(root / SANCHO_DIR / "backlog.json", {"protocol": "sancho/1.0", "requirements": [], "stories": [], "tasks": []})
    save_json(root / SANCHO_DIR / "uat.json", {"protocol": "sancho/1.0", "cases": [], "defects": []})
    for sub in ("standards", "handoffs", "checkpoints"):
        (root / SANCHO_DIR / sub).mkdir(parents=True, exist_ok=True)
    skipped = [p for p in PHASES if phases[p]["status"] == "skipped"]
    print(f"initialized {target}")
    print(f"level {a.level}: phases skipped by default: {', '.join(skipped) or 'none'}")
    print("next: DISCOVER interview (lead: analyst-pm)")
    return 0


def first_open_phase(state: dict) -> Optional[str]:
    for ph in PHASES:
        if state["phases"][ph]["status"] not in CLOSED:
            return ph
    return None


def ready_tasks(backlog: dict) -> List[dict]:
    tasks = {t["id"]: t for t in backlog.get("tasks", [])}
    story_prio = {s["id"]: PRIORITY.get(s.get("priority", "could"), 2) for s in backlog.get("stories", [])}
    parents = {t.get("parent") for t in tasks.values() if t.get("parent")}
    ready = []
    for t in tasks.values():
        if t["status"] != "pending" or t["id"] in parents:
            continue
        if all(tasks.get(d, {}).get("status") == "completed" for d in t.get("depends_on", [])):
            ready.append(t)
    return sorted(ready, key=lambda t: (story_prio.get(t["story"], 2), t["id"]))


def compute_next(p: Project, me: Optional[str] = None) -> dict:
    st = p.state
    invalid = p.invalid_files()
    if invalid:
        paths = ", ".join(f["path"] for f in invalid)
        return {"who": "user", "phase": st.get("current_phase"), "action": f"Repair {paths}: run `state.py validate` to see the errors. The next step cannot be worked out until then."}
    if me is not None and p.team():
        return team_next(p, me)
    ph = first_open_phase(st)
    if ph is None:
        return {"who": "user", "phase": None, "action": "All phases are closed. To start the next iteration run `state.py new-iteration`, then /sancho:specify."}
    phase = st["phases"][ph]
    lead = phase.get("lead", PHASE_LEAD[ph])
    status = phase["status"]
    if status == "not_started":
        return {"who": lead, "phase": ph, "action": f"Start {ph.upper()}: run /sancho:{ph} (lead: {lead})."}
    if status == "awaiting_approval":
        return {"who": "user", "phase": ph, "action": f"Review the {ph.upper()} gate summary and approve or reject it. After approval: {next_phase_hint(st, ph)}"}
    step = phase_step(p, ph, lead)
    if status == "rejected":
        reason = phase.get("gate", {}).get("rejected_reason", "")
        return {**step, "action": f"Rework {ph.upper()} ({reason}): {step['action']} Then resubmit the gate."}
    return step


def phase_step(p: Project, ph: str, lead: str) -> dict:
    """The concrete work left in an open phase."""
    backlog = p.backlog()
    if ph == "tasks" and not backlog.get("tasks"):
        return {"who": "analyst-pm", "phase": ph, "action": "Break the stories into tasks, score complexity, write UAT cases."}
    if ph == "implement":
        running = [t for t in backlog.get("tasks", []) if t["status"] in ("in_progress", "ready_for_review")]
        if running:
            t = running[0]
            who = "qa" if t["status"] == "ready_for_review" else t["owner"]
            return {"who": who, "phase": ph, "action": f"Continue {t['id']} ({t['status']}): {t['title']}"}
        blocked = [t for t in backlog.get("tasks", []) if t["status"] == "blocked"]
        ready = ready_tasks(backlog)
        if ready:
            t = ready[0]
            return {"who": t["owner"], "phase": ph, "action": f"Implement {t['id']} [{t['story']}]: {t['title']} (complexity {t['complexity']['score']})"}
        if blocked:
            t = blocked[0]
            return {"who": "user", "phase": ph, "action": f"Unblock {t['id']}: {t.get('blocked_reason', '')}"}
        return {"who": "developer", "phase": ph, "action": "All tasks done: run the IMPLEMENT gate checklist and submit it."}
    if ph == "verify":
        uat = p.uat()
        open_defects = [d for d in uat.get("defects", []) if d["status"] == "open" and d["severity"] in ("blocker", "major")]
        open_defects.sort(key=lambda d: d["severity"] != "blocker")
        sec_blockers = [f for f in (p.security() or {}).get("findings", [])
                        if f["severity"] == "blocker" and f["status"] in UNRESOLVED_FINDING]
        if open_defects and open_defects[0]["severity"] == "blocker":
            d = open_defects[0]
            return {"who": "developer", "phase": ph, "action": f"Fix {d['id']} ({d['severity']}): {d['description']}"}
        if sec_blockers:
            f = sec_blockers[0]
            return {"who": "developer", "phase": ph, "action": f"Fix security {f['id']} (blocker): {f['title']}"}
        if open_defects:
            d = open_defects[0]
            return {"who": "developer", "phase": ph, "action": f"Fix {d['id']} ({d['severity']}): {d['description']}"}
        todo = [c for c in uat.get("cases", []) if c["result"] in ("not_tested", "blocked")]
        if todo:
            c = todo[0]
            return {"who": "user", "phase": ph, "action": f"Run {c['id']} on {c['platform']}: {c['title']} ({len(todo)} UAT case(s) left). Use /sancho:verify for guided steps."}
        sec = p.security()
        if sec is None:
            return {"who": "security", "phase": ph, "action": "Run the security checks and produce the security report."}
        return {"who": "qa", "phase": ph, "action": "UAT done: run the VERIFY gate checklist and submit it."}
    return {"who": lead, "phase": ph, "action": f"Continue {ph.upper()} (lead: {lead}); when the artifacts are ready, run the gate checklist."}


def next_phase_hint(state: dict, ph: str) -> str:
    idx = PHASES.index(ph)
    for nxt in PHASES[idx + 1:]:
        if state["phases"][nxt]["status"] not in CLOSED:
            return f"next phase is {nxt.upper()} (/sancho:{nxt})."
    return "all phases are closed."


# ------------------------------------------------------------------------ team mode

def parents_of(tasks: List[dict]) -> set:
    return {t.get("parent") for t in tasks if t.get("parent")}


def team_next(p: Project, me: str) -> dict:
    """The next step for one member (references/team.md has the order)."""
    st, team = p.state, p.team()
    assert team is not None
    bl, view, _ = p.folded()
    ph = first_open_phase(st)
    roles = _team.roles_of(team, me)
    tasks = bl.get("tasks", [])
    claims = view["claims"]

    def mk(action: str, who: str = me) -> dict:
        return {"who": who, "member": me, "mine": who == me, "phase": ph, "action": action}

    lost = [c for c in view["conflicts"] if c["lost"] == me]
    if lost:
        c = lost[0]
        return mk(f"{c['item']} was already claimed by {c['won']} ({c['won_at']}) before your claim. Agree with "
                  f"{c['won']}, who keeps it, then run `state.py release {c['item']}` to clear this.")
    if ph and st["phases"][ph]["status"] == "awaiting_approval":
        return gate_next(p, me, ph)
    if ph == "verify" and st["phases"][ph]["status"] in ("in_progress", "rejected"):
        return verify_next(p, me)
    if ph != "implement" or st["phases"][ph]["status"] == "not_started":
        return mapped_next(p, me)
    mine = [t for t in tasks if claims.get(t["id"], {}).get("by") == me]
    for t in mine:
        if t["status"] == "in_progress":
            notes = f" The review asked for changes: {t['review_notes']}" if t.get("review_notes") else ""
            return mk(f"Continue {t['id']} [{t['story']}]: {t['title']}.{notes} When done: "
                      f"`state.py task {t['id']} --status ready_for_review --evidence ...`.")
    for t in mine:
        if t["status"] == "blocked":
            return mk(f"Unblock {t['id']}: {t.get('blocked_reason', '')} (or `state.py release {t['id']}`).")
    if "qa" in roles:
        four = team.get("four_eyes", True)
        for t in tasks:
            authors = view["authors"].get(t["id"], [])
            if t["status"] == "ready_for_review" and not (four and me in authors):
                by = f", by {', '.join(authors)}" if authors else ""
                return mk(f"Review {t['id']} [{t['story']}]: {t['title']}{by}. Then `state.py review {t['id']} "
                          f"--approve --evidence ...` or `--changes \"...\"`.")
    rank = {me: 0, None: 1}
    ready = [t for t in ready_tasks(bl) if t["id"] not in claims and t["owner"] in roles
             and t.get("assignee") in (me, None)]
    ready.sort(key=lambda t: rank[t.get("assignee")])  # stable: keeps the priority order
    if ready:
        t = ready[0]
        return mk(f"Claim {t['id']} [{t['story']}]: {t['title']} (complexity {t['complexity']['score']}): "
                  f"`state.py claim {t['id']}`, then implement it.")
    parents = parents_of(tasks)
    left = [t for t in tasks if t["status"] != "completed" and t["id"] not in parents]
    if not left:
        return mapped_next(p, me)
    busy = [f"{t['id']} ({claims[t['id']]['by']}, {t['status']})" for t in left if t["id"] in claims]
    waiting = [t["id"] for t in mine if t["status"] == "ready_for_review"]
    unclaimed = [f"{t['id']} ({t.get('assignee') or t['owner']})" for t in ready_tasks(bl) if t["id"] not in claims]
    parts = []
    if waiting:
        parts.append(f"your {', '.join(waiting)} waits for review")
    if busy:
        parts.append("in progress: " + ", ".join(busy))
    if unclaimed:
        parts.append("ready for others: " + ", ".join(unclaimed))
    blocked_by_deps = [t["id"] for t in left if t["status"] == "pending" and t["id"] not in claims
                       and t not in ready_tasks(bl)]
    if blocked_by_deps:
        parts.append("waiting on dependencies: " + ", ".join(blocked_by_deps))
    return {**mk("Nothing ready for you right now: " + "; ".join(parts) + "."), "mine": False}


def gate_status(p: Project, ph: str) -> dict:
    """Team mode: who approved the submitted gate of PHASE, who is still awaited, and the quorum."""
    team = p.team()
    assert team is not None
    gate = p.state["phases"][ph].get("gate", {})
    _, view, _ = p.folded()
    votes, rejections = _team.gate_votes(view, team, ph, int(p.state.get("iteration", 1)), gate.get("submitted_at"))
    approvers = _team.approvers_of(team, ph)
    return {"phase": ph, "approved_by": votes, "rejected": rejections, "quorum": _team.quorum_of(team, ph),
            "waiting_for": [m for m in approvers if m not in votes], "approvers": approvers}


def gate_next(p: Project, me: str, ph: str) -> dict:
    g = gate_status(p, ph)
    base = {"member": me, "phase": ph, "role": "user"}
    count = f"{len(g['approved_by'])} of {g['quorum']} approvals"
    if len(g["approved_by"]) >= g["quorum"]:
        leads = _team.coordinators(p.team())  # type: ignore[arg-type]
        action = f"The {ph.upper()} gate has its approvals ({', '.join(g['approved_by'])}): run `state.py approve {ph}` to close it. After that: {next_phase_hint(p.state, ph)}"
        if me in leads or me in g["approvers"]:
            return {**base, "who": me, "mine": True, "action": action}
        return {**base, "who": ", ".join(leads), "mine": False, "action": f"Nothing for you right now: {action}"}
    if me in g["waiting_for"]:
        return {**base, "who": me, "mine": True,
                "action": f"Review the {ph.upper()} gate summary and approve or reject it ({count} so far). After approval: {next_phase_hint(p.state, ph)}"}
    return {**base, "who": ", ".join(g["waiting_for"]), "mine": False,
            "action": f"Nothing for you right now: the {ph.upper()} gate waits for {', '.join(g['waiting_for'])} ({count})."}


def verify_next(p: Project, me: str) -> dict:
    """Team mode, VERIFY: own defects and cases first, then verifications, then free work."""
    team = p.team()
    assert team is not None
    st = p.state
    _, view, _ = p.folded()
    ua = p.uat()
    roles = _team.roles_of(team, me)
    claims = view["claims"]

    def mk(action: str, mine: bool = True) -> dict:
        return {"who": me, "member": me, "mine": mine, "phase": "verify", "action": action}

    holder = lambda iid: claims.get(iid, {}).get("by")  # noqa: E731
    rank = {"blocker": 0, "major": 1, "minor": 2, "nit": 3}
    defects = sorted(ua.get("defects", []), key=lambda d: (rank[d["severity"]], d["id"]))
    cases = ua.get("cases", [])
    for d in defects:
        if holder(d["id"]) == me and d["status"] == "open":
            return mk(f"Fix {d['id']} ({d['severity']}): {d['description']}. When fixed: "
                      f"`state.py defect {d['id']} --status fixed [--task T-...]`.")
    for c in cases:
        if holder(c["id"]) == me and c["result"] in ("not_tested", "blocked"):
            return mk(f"Run {c['id']} on {c['platform']}: {c['title']}. Then `state.py uat {c['id']} --result pass|fail|blocked`"
                      " (/sancho:verify guides you).")
    if "qa" in roles:
        for d in defects:
            if d["status"] == "fixed" and not (team.get("four_eyes", True) and view["fixed_by"].get(d["id"]) == me):
                return mk(f"Verify {d['id']} ({d['severity']}): re-run {d['uat']}; if it passes "
                          f"`state.py defect {d['id']} --status verified`, otherwise `--status open`.")
    if "developer" in roles:
        for d in defects:
            if d["status"] == "open" and d["severity"] in ("blocker", "major") and not holder(d["id"]) \
                    and d.get("assignee") in (me, None):
                return mk(f"Claim {d['id']} ({d['severity']}): {d['description']}: `state.py claim {d['id']}`, then fix it.")
    base = compute_next(p)
    if base["action"].startswith("Fix security"):
        return mapped_next(p, me)
    free = [c for c in cases if c["result"] in ("not_tested", "blocked") and not holder(c["id"])
            and c.get("assignee") in (me, None)]
    free.sort(key=lambda c: c.get("assignee") != me)
    if free:
        c = free[0]
        return mk(f"Claim {c['id']} on {c['platform']}: {c['title']}: `state.py claim {c['id']}`, then run it.")
    open_major = [d for d in defects if d["status"] in ("open", "fixed") and d["severity"] in ("blocker", "major")]
    untested = [c for c in cases if c["result"] in ("not_tested", "blocked")]
    if open_major or untested:
        parts = [f"{d['id']} ({d['status']}, {holder(d['id']) or 'free'})" for d in open_major]
        parts += [f"{c['id']} ({holder(c['id']) or c.get('assignee') or 'free'})" for c in untested]
        return mk("Nothing ready for you right now: " + ", ".join(parts) + ".", mine=False)
    return mapped_next(p, me)


def mapped_next(p: Project, me: str) -> dict:
    """The project's next step, said to one member: theirs, or whose it is."""
    team = p.team()
    assert team is not None
    base = compute_next(p)
    st = p.state
    who = base["who"]
    leads = _team.coordinators(team)
    if who == "user":
        ph = base.get("phase")
        gate = ph and st["phases"].get(ph, {}).get("status") == "awaiting_approval"
        holders = leads if gate or ph is None or base["action"].startswith("Start ") else [m["id"] for m in team["members"]]
    else:
        holders = _team.holders_of_role(team, who) or leads
    if base["action"].startswith("Start "):
        holders = leads  # the coordinator opens phases
    out = {**base, "member": me, "role": who}
    if me in holders:
        return {**out, "who": me, "mine": True}
    return {**out, "who": ", ".join(holders), "mine": False,
            "action": f"Nothing for you right now: {', '.join(holders)} ({who}): {base['action']}"}


def team_overview(p: Project) -> dict:
    team = p.team()
    assert team is not None
    bl, view, _ = p.folded()
    per_member = {m["id"]: team_next(p, m["id"]) for m in team["members"]}
    free = [t["id"] for t in ready_tasks(bl) if t["id"] not in view["claims"]]
    if p.state["current_phase"] == "verify":
        ua = p.uat()
        free += [c["id"] for c in ua.get("cases", []) if c["result"] in ("not_tested", "blocked") and c["id"] not in view["claims"]]
        free += [d["id"] for d in ua.get("defects", []) if d["status"] == "open" and d["id"] not in view["claims"]]
    return {"members": per_member, "free": free, "conflicts": view["conflicts"],
            "stale": _team.stale(view, team), "claims": view["claims"]}


def current_member(p: Project, wanted: Optional[str] = None) -> Tuple[Optional[str], str]:
    team = p.team()
    if team is None:
        return None, "no team"
    if wanted:
        if wanted not in _team.members(team):
            die(f"{wanted} is not a member of the team")
        return wanted, "--as"
    return _team.whoami(p.root, team)


def require_member(p: Project) -> Tuple[dict, str]:
    if _team.team_path(p.root).is_file() and p.team() is None:
        die("invalid .sancho/team.json: run `state.py validate`", 1)
    team = p.team()
    if team is None:
        die("team mode is off: .sancho/team.json does not exist (add members with `state.py team add`)", 1)
    me, how = _team.whoami(p.root, team)
    if me is None:
        die(f"who are you? {how}", 1)
    return team, me  # type: ignore[return-value]


def find_task(bl: dict, tid: str) -> dict:
    for t in bl.get("tasks", []):
        if t["id"] == tid:
            return t
    die(f"task {tid} not found in the backlog")
    raise AssertionError


def cmd_next(a: argparse.Namespace) -> int:
    root = find_root()
    if root is None:
        if a.team or a.as_:
            die("no .sancho/ folder found here or above")
        nxt = {"who": "user", "phase": "discover", "action": "No Sancho project here yet. Run /sancho:help for a tour, or /sancho:discover to start."}
    else:
        p = Project(root)
        if (a.team or a.as_) and p.team() is None:
            die("team mode is off: .sancho/team.json does not exist", 1)
        if a.team:
            ov = team_overview(p)
            if a.json:
                print(json.dumps(ov, indent=2, ensure_ascii=False))
                return 0
            for mid, n in ov["members"].items():
                print(f"{mid}: {n['action']}")
            if ov["free"]:
                print(f"free: {', '.join(ov['free'])} (ready, nobody has claimed them)")
            for c in ov["conflicts"]:
                print(f"CONFLICT: {c['item']} claimed by {c['won']} and later by {c['lost']}; {c['won']} keeps it")
            for tid in ov["stale"]:
                print(f"STALE: {tid} claimed by {ov['claims'][tid]['by']}, no activity for a while")
            return 0
        me, how = current_member(p, a.as_)
        nxt = compute_next(p, me)
        if p.team() is not None and me is None:
            nxt["note"] = f"team mode: {how}; this is the project's next step, not yours"
    if a.json:
        print(json.dumps(nxt, indent=2, ensure_ascii=False))
    else:
        print(f"NEXT ({nxt['who']}): {nxt['action']}")
        if nxt.get("note"):
            print(f"note: {nxt['note']}")
    return 0


def cmd_whoami(a: argparse.Namespace) -> int:
    p = open_project()
    team = p.team()
    if team is None:
        print("team mode is off (no .sancho/team.json): Sancho works for one person")
        return 0
    me, how = _team.whoami(p.root, team)
    if me is None:
        print(f"not a member: {how}")
        return 1
    m = _team.members(team)[me]
    print(f"{me} ({m['name']}) · roles: {', '.join(m['roles'])}" + (" · coordinator" if me in _team.coordinators(team) else "") + f" · from {how}")
    return 0


def cmd_team(a: argparse.Namespace) -> int:
    root = find_root()
    if root is None:
        die("no .sancho/ folder found here or above: run `state.py init` first")
    path = _team.team_path(root)
    if a.action == "suggest":
        log = _team.git(root, "log", "--format=%aN|%aE")
        counts: Dict[Tuple[str, str], int] = {}
        for line in log.splitlines():
            name, _, email = line.partition("|")
            counts[(name, email.lower())] = counts.get((name, email.lower()), 0) + 1
        team = _team.load_team(root) if path.is_file() else None
        known = {e.lower() for m in (team or {}).get("members", []) for e in m["emails"]}
        if not counts:
            print("no git history here: add members with `state.py team add`")
        for (name, email), n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"{name} <{email}> · {n} commit(s)" + (" · already a member" if email in known else ""))
        return 0
    team = _team.load_team(root) if path.is_file() else {"protocol": "sancho/1.1", "members": []}
    if a.action == "list":
        if not team["members"]:
            print("no team (team mode is off)")
            return 0
        me, _ = _team.whoami(root, team)
        leads = _team.coordinators(team)
        for m in team["members"]:
            print(f"{m['id']}: {m['name']} <{', '.join(m['emails'])}> · {', '.join(m['roles'])}"
                  + (" · coordinator" if m["id"] in leads else "") + (" · you" if m["id"] == me else ""))
        return 0
    # add (or update) a member
    if not (a.id and a.name and a.email and a.roles):
        die("team add needs --id, --name, --email and --roles")
    roles = [r.strip() for r in a.roles.split(",") if r.strip()]
    existing = _team.members(team).get(a.id)
    if existing:
        existing.update({"name": a.name, "roles": roles})
        if a.email.lower() not in (e.lower() for e in existing["emails"]):
            existing["emails"].append(a.email)
    else:
        team["members"].append({"id": a.id, "name": a.name, "emails": [a.email], "roles": roles})
    member = _team.members(team)[a.id]
    if a.coordinator:  # without any, the first member coordinates (see _team.coordinators)
        member["coordinator"] = True
    errors = validate(team, "team")
    if errors:
        die("invalid member:\n  " + "\n  ".join(errors[:5]))
    save_json(path, team)
    added = _team.ensure_union_merge(root)
    print(f"{'updated' if existing else 'added'} {a.id} ({', '.join(roles)})" + (" · coordinator" if a.id in _team.coordinators(team) else ""))
    if added:
        print("added `.sancho/log/*.jsonl merge=union` to .gitattributes")
    print("Commit .sancho/team.json and .gitattributes so the others get the team.")
    return 0


ITEM_KEY = {"T": "task", "UAT": "case", "DEF": "defect"}


def item_key(iid: str) -> str:
    key = ITEM_KEY.get(iid.split("-")[0])
    if key is None or not re.match(r"^(T-\d{3,}(\.\d+)?|UAT-\d{3,}|DEF-\d{3,})$", iid):
        die(f"{iid}: expected a task (T-001), a UAT case (UAT-001) or a defect (DEF-001)")
    return key  # type: ignore[return-value]


def find_in(ua: dict, kind: str, iid: str) -> dict:
    for x in ua.get(kind, []):
        if x["id"] == iid:
            return x
    die(f"{iid} not found in the UAT file")
    raise AssertionError


def cmd_claim(a: argparse.Namespace) -> int:
    p = open_project()
    team, me = require_member(p)
    bl, view, _ = p.folded()
    key = item_key(a.task)
    if key != "task":
        holder = view["claims"].get(a.task)
        if holder and holder["by"] != me:
            die(f"{a.task} is already claimed by {holder['by']} since {holder['at']}", 1)
        if holder:
            die(f"{a.task} is already yours", 1)
        if key == "case":
            c = find_in(p.uat(), "cases", a.task)
            if c["result"] not in ("not_tested", "blocked", "fail"):
                die(f"{a.task} already passed", 1)
            planned = c.get("assignee")
        else:
            d = find_in(p.uat(), "defects", a.task)
            if d["status"] != "open":
                die(f"{a.task} is {d['status']}", 1)
            if "developer" not in _team.roles_of(team, me) and not a.any_role:
                die(f"defects are fixed by developers; pass --any-role if the team agreed", 1)
            planned = d.get("assignee")
        path = _team.append_event(p.root, {"by": me, "event": "claim", key: a.task})
        print(f"{a.task} claimed by {me}")
        if planned and planned != me:
            print(f"note: the plan suggested {planned} for {a.task}")
        print(f"Commit and push {path.relative_to(p.root).as_posix()} now, so the others see the claim (ask the user first).")
        return 0
    t = find_task(bl, a.task)
    if a.task in parents_of(bl.get("tasks", [])):
        die(f"{a.task} was split into subtasks: claim one of those", 1)
    holder = view["claims"].get(a.task)
    if holder:
        if holder["by"] == me:
            die(f"{a.task} is already yours", 1)
        die(f"{a.task} is already claimed by {holder['by']} since {holder['at']}" + (f" (branch {holder['branch']})" if holder.get("branch") else ""), 1)
    if t["status"] not in ("pending", "in_progress", "failed"):
        die(f"{a.task} is {t['status']}", 1)
    status_of = {x["id"]: x["status"] for x in bl.get("tasks", [])}
    open_deps = [d for d in t.get("depends_on", []) if status_of.get(d) != "completed"]
    if open_deps:
        die(f"{a.task} depends on {', '.join(open_deps)}, not completed yet", 1)
    roles = _team.roles_of(team, me)
    if t["owner"] not in roles and not a.any_role:
        die(f"{a.task} is a {t['owner']} task and your roles are {', '.join(roles)}; pass --any-role if the team agreed", 1)
    branch = a.branch or _team.git(p.root, "rev-parse", "--abbrev-ref", "HEAD")
    ev = {"by": me, "event": "claim", "task": a.task}
    if branch and branch != "HEAD":
        ev["branch"] = branch
    path = _team.append_event(p.root, ev)
    print(f"{a.task} claimed by {me}: in progress" + (f" on branch {ev['branch']}" if "branch" in ev else ""))
    if t.get("assignee") and t["assignee"] != me:
        print(f"note: the plan suggested {t['assignee']} for {a.task}")
    print(f"Commit and push {path.relative_to(p.root).as_posix()} now, so the others see the claim (ask the user first).")
    return 0


def cmd_release(a: argparse.Namespace) -> int:
    p = open_project()
    team, me = require_member(p)
    bl, view, _ = p.folded()
    key = item_key(a.task)
    if key == "task":
        find_task(bl, a.task)
    else:
        find_in(p.uat(), "cases" if key == "case" else "defects", a.task)
    holder = view["claims"].get(a.task, {}).get("by")
    lost = [c for c in view["conflicts"] if c["item"] == a.task and c["lost"] == me]
    if not (lost or holder == me or (holder and me in _team.coordinators(team))):
        die(f"{a.task} is not yours" + (f" (claimed by {holder})" if holder else " (nobody has claimed it)"), 1)
    _team.append_event(p.root, {"by": me, "event": "release", key: a.task})
    if lost and holder != me:
        print(f"conflict on {a.task} cleared: {holder} keeps it")
    else:
        print(f"{a.task} released" + (f" (it was {holder}'s)" if holder != me else "") + (": back to pending" if key == "task" else ""))
    return 0


def cmd_since(a: argparse.Namespace) -> int:
    """What changed since you last looked (or since REF): commits, team events, phases, documents."""
    p = open_project()
    team = p.team()
    me = _team.whoami(p.root, team)[0] if team else None
    mine_items: set = set()
    if me:
        _, view, _ = p.folded()
        mine_items = {i for i, c in view["claims"].items() if c["by"] == me}
        mine_items |= {i for i, who in view["authors"].items() if me in who}
    try:
        emails = set(_team.members(team)[me]["emails"]) if team and me else set()
        out = _since.compute(p.root, a.ref, me, mine_items, emails)
    except RuntimeError as e:
        die(str(e))
    if not a.peek:
        _since.write_marker(p.root, _team.git(p.root, "rev-parse", "HEAD"))
    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    if out["first_run"]:
        print("since: first look; from now on `since` shows what changed after this point")
        return 0
    if not (out["commits"] or out["phases"] or out["by_member"] or out["files"]):
        print(f"since {out['from']}: nothing new")
        return 0
    authors = sorted({c["author"] for c in out["commits"]})
    print(f"since {out['from']}: {len(out['commits'])} commit(s)" + (f" by {', '.join(authors)}" if authors else ""))
    if out["mine"]:
        print("FOR YOU: " + " · ".join(out["mine"]))
    for ph in out["phases"]:
        print(f"phase:  {ph['phase']} {ph['from'] or '-'} -> {ph['to']}")
    for who, items in out["by_member"].items():
        print(f"{who}: " + " · ".join(items))
    if out["files"]:
        print("files:  " + ", ".join(f"{f['path']} ({f['change']})" for f in out["files"][:12])
              + (f" and {len(out['files']) - 12} more" if len(out["files"]) > 12 else ""))
    return 0


def cmd_hooks(a: argparse.Namespace) -> int:
    p = open_project()
    if a.action == "install":
        ok, msg = _since.install_hook(p.root, Path(__file__).resolve(), a.force)
        if not ok:
            die(msg, 1)
        print(f"post-merge hook installed: {msg}")
        print("After every pull it prints `state.py since` and checks the project files. "
              "Each member installs it in their own clone; re-run after updating Sancho.")
    elif a.action == "remove":
        ok, msg = _since.remove_hook(p.root)
        print(("removed " if ok else "") + msg)
    else:
        path = _since.hook_path(p.root)
        ours = bool(path and path.is_file() and _since.HOOK_MARK in path.read_text(encoding="utf-8", errors="replace"))
        print(f"post-merge hook: {'installed' if ours else 'not installed'}" + (f" ({path})" if ours else ""))
    return 0


ID_KINDS = (("requirements", "R"), ("stories", "S"), ("tasks", "T"))


def cmd_renumber(a: argparse.Namespace) -> int:
    """Rename duplicate ids (two members added S-012 in parallel): the later occurrence gets the next free id."""
    p = open_project()
    if a.apply:
        coordinator_only(p, "renumbers ids")
    bl, ua = p.plan_backlog(), p.plan_uat()
    _, view, _ = p.folded()
    plan: List[Tuple[str, str, str]] = []
    refs: List[str] = []
    docs = [(bl, kind, pfx) for kind, pfx in ID_KINDS] + [(ua, "cases", "UAT"), (ua, "defects", "DEF")]
    for doc, kind, pfx in docs:
        items = doc.get(kind, [])
        taken = {x["id"] for x in items}
        seen: set = set()
        for x in items:
            if x["id"] not in seen:
                seen.add(x["id"])
                continue
            nums = [int(re.match(rf"^{pfx}-(\d+)", i).group(1)) for i in taken if re.match(rf"^{pfx}-(\d+)", i)]  # type: ignore[union-attr]
            new = f"{pfx}-{max(nums) + 1:03d}"
            taken.add(new)
            plan.append((kind, x["id"], new))
            old = x["id"]
            x["id"] = new
            if kind == "stories":
                for c in x.get("acceptance_criteria", []):
                    c["id"] = c["id"].replace(f"AC-{old[2:]}.", f"AC-{new[2:]}.", 1)
            if old in view["claims"] or old in view["authors"]:
                refs.append(f"{old} has team events: they stay with the first {old}; tell whoever worked on the renamed one")
            for other in bl.get("tasks", []) + ua.get("cases", []) + ua.get("defects", []):
                if other is x:
                    continue
                if old in other.get("depends_on", []) or other.get("story") == old or other.get("task") == old \
                        or other.get("parent") == old or old in other.get("defects", []):
                    refs.append(f"{other['id']} refers to {old}: check whether it meant the renamed {new}")
    if not plan:
        print("no duplicate ids")
        return 0
    for kind, old, new in plan:
        print(f"{kind}: second {old} -> {new}")
    for r in refs:
        print(f"CHECK: {r}")
    if not a.apply:
        print("dry run: nothing changed; run again with --apply")
        return 0
    for doc, name in ((bl, "backlog"), (ua, "uat")):
        errors = validate(doc, name)
        if errors:
            die(f"renumbering would make {name} invalid, nothing changed:\n  " + "\n  ".join(errors[:10]))
    save_json(p.backlog_path(), bl)
    if p.uat_path().is_file():
        save_json(p.uat_path(), ua)
    print("renumbered; run the coherence check (`coherence_check.py`) and fix the references listed under CHECK")
    return 0


COHERENCE_STAGE = {"specify": "spec", "plan": "spec", "tasks": "tasks"}


def cmd_coherence(a: argparse.Namespace) -> int:
    """Run coherence_check.py at the stage that fits the current phase (used after merges)."""
    import subprocess
    p = open_project()
    ph = p.state["current_phase"]
    if ph == "discover" or not p.backlog_path().is_file():
        print("coherence: nothing to check yet (no backlog, or still in DISCOVER)")
        return 0
    stage = COHERENCE_STAGE.get(ph, "full")
    cmd = [sys.executable, "-I", str(Path(__file__).resolve().parent / "coherence_check.py"), str(p.backlog_path()), "--stage", stage]
    if stage != "spec" and p.uat_path().is_file():
        cmd += ["--uat", str(p.uat_path())]
    if a.json:
        cmd.append("--json")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    out = r.stdout.strip()
    if a.quiet and r.returncode == 0:
        return 0
    if a.quiet:
        lines = [x for x in out.splitlines() if x.startswith("[blocker]") or x.startswith("[major]")]
        print(f"sancho: coherence ({stage}) found {len(lines)} blocker/major issue(s) after the merge - run state.py coherence")
        for x in lines[:5]:
            print(f"  {x}")
        return r.returncode
    print(out or r.stderr.strip())
    return r.returncode


GATE_EVENTS = ("gate_approve", "gate_reject")


def comparable(p: Project) -> str:
    bl, view, _ = p.folded()
    return json.dumps([bl.get("tasks", []), p.uat(), view["claims"]], sort_keys=True)


def cmd_compact(a: argparse.Namespace) -> int:
    """Team mode: move the events of settled items into backlog.json / uat.json and an archive."""
    p = open_project()
    me = coordinator_only(p, "compacts the event log")
    if me is None:
        die("compact is for team mode", 1)
    team = p.team()
    bl, view, problems = p.folded()
    if problems or p.invalid_files():
        die("repair the invalid files first (`state.py validate`)", 1)
    ua, st = p.uat(), p.state
    claims = view["claims"]
    dstat = {d["id"]: d["status"] for d in ua.get("defects", [])}
    done_def = ("verified", "wont_fix")
    settled = {t["id"] for t in bl.get("tasks", []) if t["status"] == "completed" and t["id"] not in claims}
    settled |= {d for d, s in dstat.items() if s in done_def and d not in claims}
    settled |= {c["id"] for c in ua.get("cases", []) if c["result"] != "not_tested" and c["id"] not in claims
                and all(dstat.get(x) in done_def for x in c.get("defects", []))}
    remap = {(r["by"], r["from"]): r["to"] for r in view["renamed"]}
    iteration = int(st.get("iteration", 1))

    def gate_closed(ev: dict) -> bool:
        return ev["iteration"] < iteration or st["phases"][ev["phase"]]["status"] in CLOSED

    def item(ev: dict) -> Optional[str]:
        if ev.get("defect"):
            return remap.get((ev["by"], ev["defect"]), ev["defect"])
        return ev.get("task") or ev.get("case")

    events, _ = _team.read_events(p.root, team)
    archive = [ev for ev in events if (gate_closed(ev) if ev["event"] in GATE_EVENTS else item(ev) in settled)]
    if not archive:
        print("nothing to compact: no event belongs to a settled item or a closed gate")
        return 0
    before = comparable(p)
    plan_bl, plan_ua = p.plan_backlog(), p.plan_uat()
    eff_tasks = {t["id"]: t for t in bl.get("tasks", [])}
    plan_bl["tasks"] = [{k: v for k, v in eff_tasks[t["id"]].items() if k != "review_notes"} if t["id"] in settled else t
                        for t in plan_bl["tasks"]]
    eff_cases = {c["id"]: c for c in ua.get("cases", [])}
    plan_ua["cases"] = [eff_cases[c["id"]] if c["id"] in settled else c for c in plan_ua.get("cases", [])]
    in_plan = {d["id"] for d in plan_ua.get("defects", [])}
    eff_def = {d["id"]: d for d in ua.get("defects", [])}
    plan_ua["defects"] = [eff_def[d["id"]] if d["id"] in settled else d for d in plan_ua.get("defects", [])]
    plan_ua["defects"] += [eff_def[d] for d in sorted(settled) if d in eff_def and d not in in_plan]
    for doc, name in ((plan_bl, "backlog"), (plan_ua, "uat")):
        errors = validate(doc, name)
        if errors:
            die(f"compaction would make {name} invalid, nothing changed:\n  " + "\n  ".join(errors[:10]))
    drop = {(ev["_file"], ev["_line"]) for ev in archive}
    backups = {path: path.read_bytes() for path in [p.backlog_path(), p.uat_path(), *_team.log_files(p.root)] if path.is_file()}
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    arch = p.root / SANCHO_DIR / _team.LOG_DIR / "archive" / f"{stamp}-{me}.jsonl"
    try:
        save_json(p.backlog_path(), plan_bl)
        save_json(p.uat_path(), plan_ua)
        for f in _team.log_files(p.root):
            rel = f.relative_to(p.root).as_posix()
            lines = f.read_text(encoding="utf-8").splitlines()
            kept = [line for n, line in enumerate(lines, 1) if line.strip() and (rel, n) not in drop]
            with open(f, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("".join(line + "\n" for line in kept))
        arch.parent.mkdir(parents=True, exist_ok=True)
        with open(arch, "w", encoding="utf-8", newline="\n") as fh:
            for ev in archive:
                clean = {k: v for k, v in ev.items() if not k.startswith("_")}
                fh.write(json.dumps(clean, ensure_ascii=False, separators=(",", ":")) + "\n")
        after = comparable(Project(p.root))
        if after != before:
            raise RuntimeError("the state after compaction differs from the state before")
    except Exception as e:  # restore everything: compaction must never change the state
        for path, data in backups.items():
            path.write_bytes(data)
        if arch.exists():
            arch.unlink()
        die(f"compaction undone: {e}", 1)
    kinds: Dict[str, int] = {}
    for ev in archive:
        k = "gates" if ev["event"] in GATE_EVENTS else item_key(item(ev) or "T-000") + "s"
        kinds[k] = kinds.get(k, 0) + 1
    print(f"archived {len(archive)} events ({', '.join(f'{k} {v}' for k, v in sorted(kinds.items()))}) "
          f"to {arch.relative_to(p.root).as_posix()}; the state is unchanged.")
    print("Commit backlog.json, uat.json and .sancho/log/ together: `chore(sancho): compact event log` (ask first).")
    return 0


def new_defects(specs: List[str], case: str, taken: set) -> List[dict]:
    """--new-defect "major:what the tester saw" -> defect records with the next free ids."""
    out = []
    for spec in specs:
        sev, sep, desc = spec.partition(":")
        sev = sev.strip().lower()
        if not sep or sev not in ("blocker", "major", "minor", "nit") or not desc.strip():
            die(f"bad --new-defect '{spec}': use SEVERITY:DESCRIPTION, severity blocker|major|minor|nit")
        did = _team.next_defect_id(taken)
        taken.add(did)
        out.append({"id": did, "uat": case, "severity": sev, "description": desc.strip(), "status": "open"})
    return out


def cmd_uat(a: argparse.Namespace) -> int:
    """Record one UAT result (team: as events; alone: in uat.json)."""
    p = open_project()
    ua = p.uat()
    c = find_in(ua, "cases", a.case)
    known = {d["id"] for d in ua.get("defects", [])}
    unknown = [d for d in (a.defect or []) if d not in known]
    if unknown:
        die(f"unknown defect(s): {', '.join(unknown)} (use --new-defect SEVERITY:DESCRIPTION)")
    created = new_defects(a.new_defect or [], a.case, set(known))
    defect_ids = list(a.defect or []) + [d["id"] for d in created]
    if a.result == "fail" and not defect_ids:
        die("--result fail needs --defect DEF-... or --new-defect SEVERITY:DESCRIPTION")
    if a.result == "blocked" and not a.note:
        die("--result blocked needs --note (why it could not be run)")
    if _team.team_path(p.root).is_file():
        team, me = require_member(p)
        _, view, _ = p.folded()
        holder = view["claims"].get(a.case, {}).get("by")
        if holder and holder != me:
            die(f"{a.case} is claimed by {holder}", 1)
        for d in created:
            ev = {"by": me, "event": "defect_open", "defect": d["id"], "uat": a.case, "severity": d["severity"],
                  "description": d["description"]}
            _team.append_event(p.root, ev)
        ev = {"by": me, "event": "uat_result", "case": a.case, "result": a.result}
        if a.note:
            ev["note"] = a.note
        if defect_ids:
            ev["defects"] = defect_ids
        _team.append_event(p.root, ev)
    else:
        plan = p.plan_uat()
        case = find_in(plan, "cases", a.case)
        case.update({"result": a.result, "executed_by": a.tester or _team.git(p.root, "config", "user.name") or "user",
                     "executed_at": now_iso()})
        for key in ("notes", "defects"):
            case.pop(key, None)
        if a.note:
            case["notes"] = a.note
        if defect_ids:
            case["defects"] = defect_ids
        plan.setdefault("defects", []).extend(created)
        errors = validate(plan, "uat")
        if errors:
            die("refusing to write an invalid UAT file:\n  " + "\n  ".join(errors[:10]))
        save_json(p.uat_path(), plan)
    print(f"{a.case}: {c['result']} -> {a.result}" + (f" · defects {', '.join(defect_ids)}" if defect_ids else ""))
    for d in created:
        print(f"opened {d['id']} ({d['severity']}): {d['description']}")
    return 0


def cmd_defect(a: argparse.Namespace) -> int:
    """Change a defect's status (team: as an event; alone: in uat.json)."""
    p = open_project()
    d = find_in(p.uat(), "defects", a.defect)
    if _team.team_path(p.root).is_file():
        team, me = require_member(p)
        _, view, _ = p.folded()
        holder = view["claims"].get(a.defect, {}).get("by")
        roles = _team.roles_of(team, me)
        if a.status == "fixed" and holder != me:
            die(f"{a.defect} is not yours: " + (f"claimed by {holder}" if holder else f"claim it first (`state.py claim {a.defect}`)"), 1)
        if a.status == "verified":
            if d["status"] != "fixed":
                die(f"{a.defect} is {d['status']}: only a fixed defect can be verified", 1)
            if "qa" not in roles:
                die("verifying a fix is for members with the qa role", 1)
            if team.get("four_eyes", True) and view["fixed_by"].get(a.defect) == me:
                die(f"you fixed {a.defect}: someone else with the qa role verifies it (four eyes)", 1)
        if a.status == "wont_fix" and me not in _team.coordinators(team):
            die("wont_fix accepts a risk: the coordinator records it, after the team agreed", 1)
        ev = {"by": me, "event": "defect_status", "defect": a.defect, "status": a.status}
        if a.task:
            ev["fix_task"] = a.task
        if a.note:
            ev["note"] = a.note
        _team.append_event(p.root, ev)
    else:
        plan = p.plan_uat()
        target = find_in(plan, "defects", a.defect)
        target["status"] = a.status
        if a.task:
            target["task"] = a.task
        errors = validate(plan, "uat")
        if errors:
            die("refusing to write an invalid UAT file:\n  " + "\n  ".join(errors[:10]))
        save_json(p.uat_path(), plan)
    print(f"{a.defect}: {d['status']} -> {a.status}")
    return 0


def cmd_task(a: argparse.Namespace) -> int:
    p = open_project()
    try:
        evidence = _team.parse_evidence(a.evidence or [])
    except ValueError as e:
        die(str(e))
    if a.status == "blocked" and not a.reason:
        die("--status blocked needs --reason")
    if _team.team_path(p.root).is_file():
        team, me = require_member(p)
        bl, view, _ = p.folded()
        t = find_task(bl, a.task)
        holder = view["claims"].get(a.task, {}).get("by")
        if holder != me:
            die(f"{a.task} is not yours: " + (f"claimed by {holder}" if holder else f"claim it first (`state.py claim {a.task}`)"), 1)
        if a.status == "completed":
            die("in a team a task is completed by a review: `state.py review TASK --approve` (by someone else with the qa role)", 1)
        if a.status == "pending":
            die(f"to give a task back use `state.py release {a.task}`", 1)
        if a.status == "ready_for_review" and not evidence:
            die("--status ready_for_review needs --evidence (for example commit:SHA or test:\"CMD\")")
        ev: dict = {"by": me, "event": "task_status", "task": a.task, "status": a.status}
        if a.reason:
            ev["blocked_reason"] = a.reason
        if evidence:
            ev["evidence"] = evidence
        if a.note:
            ev["note"] = a.note
        _team.append_event(p.root, ev)
        print(f"{a.task}: {t['status']} -> {a.status}")
        return 0
    if a.note:
        die("--note is kept only in team mode; put it in the handoff instead")
    bl = p.plan_backlog()
    t = find_task(bl, a.task)
    old = t["status"]
    t["status"] = a.status
    if a.status == "blocked":
        t["blocked_reason"] = a.reason
    else:
        t.pop("blocked_reason", None)
    if evidence:
        t["evidence"] = t.get("evidence", []) + evidence
    if a.status in ("ready_for_review", "completed") and not t.get("evidence"):
        die(f"--status {a.status} needs --evidence (for example commit:SHA or test:\"CMD\")")
    errors = validate(bl, "backlog")
    if errors:
        die("refusing to write an invalid backlog:\n  " + "\n  ".join(errors[:10]))
    save_json(p.backlog_path(), bl)
    print(f"{a.task}: {old} -> {a.status}")
    return 0


def cmd_review(a: argparse.Namespace) -> int:
    p = open_project()
    team, me = require_member(p)
    bl, view, _ = p.folded()
    t = find_task(bl, a.task)
    if "qa" not in _team.roles_of(team, me):
        die(f"reviews are for members with the qa role; {me} has {', '.join(_team.roles_of(team, me))}", 1)
    if t["status"] != "ready_for_review":
        die(f"{a.task} is {t['status']}, not ready_for_review", 1)
    if team.get("four_eyes", True) and me in view["authors"].get(a.task, []):
        die(f"you worked on {a.task}: someone else with the qa role reviews it (four eyes)", 1)
    if bool(a.approve) == bool(a.changes):
        die("pass --approve (with --evidence) or --changes TEXT")
    ev: dict = {"by": me, "event": "review", "task": a.task}
    if a.approve:
        try:
            evidence = _team.parse_evidence(a.evidence or [])
        except ValueError as e:
            die(str(e))
        if not evidence:
            die("--approve needs --evidence: what you re-ran or checked")
        ev.update({"outcome": "approved", "evidence": evidence})
    else:
        ev.update({"outcome": "changes", "note": a.changes})
    _team.append_event(p.root, ev)
    print(f"{a.task}: " + ("completed (review approved)" if a.approve else "back to in_progress with your findings"))
    return 0


UNRESOLVED_FINDING = ("open", "not_verified")


def security_counts(sec: Optional[dict]) -> Optional[dict]:
    """Unresolved findings by severity, closed ones by status, and the NOT RUN list.

    The report summary counts every finding, including fixed ones, so status counts
    from the findings themselves; it falls back to the summary only without findings.
    """
    if not sec:
        return None
    summary = sec.get("summary", {})
    findings = sec.get("findings")
    if findings is None:
        counts = {s: summary.get(s, 0) for s in ("blocker", "major", "minor", "nit")}
        closed: Dict[str, int] = {}
    else:
        counts = {s: 0 for s in ("blocker", "major", "minor", "nit")}
        closed = {}
        for f in findings:
            if f["status"] in UNRESOLVED_FINDING:
                counts[f["severity"]] += 1
            else:
                closed[f["status"]] = closed.get(f["status"], 0) + 1
    counts["closed"] = dict(sorted(closed.items()))
    counts["not_run"] = summary.get("not_run", [])
    return counts


def cmd_status(a: argparse.Namespace) -> int:
    p = open_project()
    st = p.state
    invalid = p.invalid_files()
    bad = {f["name"]: f for f in invalid}
    if "state" in bad:
        die(f"invalid {bad['state']['path']}: " + "; ".join(bad["state"]["errors"][:5]))
    # counts from an invalid file cannot be trusted: leave them out and say so
    backlog = {} if "backlog" in bad else p.backlog()
    uat = {} if "uat" in bad else p.uat()
    sec = None if "security-report" in bad else p.security()
    task_counts: Dict[str, int] = {}
    for t in backlog.get("tasks", []):
        task_counts[t["status"]] = task_counts.get(t["status"], 0) + 1
    uat_counts: Dict[str, int] = {}
    for c in uat.get("cases", []):
        uat_counts[c["result"]] = uat_counts.get(c["result"], 0) + 1
    open_def = [d for d in uat.get("defects", []) if d["status"] == "open"]
    blockers: List[str] = []
    blockers += [f"task {t['id']} blocked: {t.get('blocked_reason', '')}" for t in backlog.get("tasks", []) if t["status"] == "blocked"]
    blockers += [f"defect {d['id']} ({d['severity']}): {d['description']}" for d in open_def if d["severity"] == "blocker"]
    if sec:
        blockers += [f"security {f['id']}: {f['title']}" for f in sec.get("findings", []) if f["severity"] == "blocker" and f["status"] in UNRESOLVED_FINDING]
    data = {
        "project": st["project"], "current_phase": st["current_phase"],
        "phases": {ph: st["phases"][ph]["status"] for ph in PHASES},
        "tasks": task_counts, "uat": uat_counts,
        "open_defects": {s: sum(1 for d in open_def if d["severity"] == s) for s in ("blocker", "major", "minor", "nit")},
        "security": security_counts(sec), "blockers": blockers,
        "approvals": len(st.get("approvals", [])),
        "last_checkpoint": (st.get("checkpoints") or [{}])[-1].get("at"),
        "invalid_files": invalid,
    }
    team = p.team()
    me = None
    if team is not None:
        me, how = _team.whoami(p.root, team)
        _, view, _ = p.folded()
        data["team"] = {
            "me": me, "identity": how,
            "members": [m["id"] for m in team["members"]],
            "claims": {tid: {**c, "status": next((t["status"] for t in backlog.get("tasks", []) if t["id"] == tid), None)}
                       for tid, c in view["claims"].items()},
            "conflicts": view["conflicts"], "stale": _team.stale(view, team), "renamed": view["renamed"],
        }
        if st["phases"][st["current_phase"]]["status"] == "awaiting_approval":
            data["team"]["gate"] = gate_status(p, st["current_phase"])
    data["next"] = compute_next(p, me)
    code = 1 if invalid else 0
    if a.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return code
    pr = st["project"]
    print(f"{pr['name']} · level {pr['level']} · platforms: {', '.join(pr['platforms']) or '-'}")
    marks = {"approved": "✔", "skipped": "–", "in_progress": "▶", "awaiting_approval": "?", "rejected": "✖", "not_started": "·"}
    print("phases: " + "  ".join(f"{marks[data['phases'][ph]]} {ph}" for ph in PHASES))
    print(f"current: {st['current_phase']} ({st['phases'][st['current_phase']]['status']})")
    for f in invalid:
        print(f"INVALID: {f['path']}: {f['errors'][0]} (its counts are left out; details: state.py validate)")
    if task_counts:
        print("tasks:  " + ", ".join(f"{k} {v}" for k, v in sorted(task_counts.items())))
    if uat_counts:
        print("UAT:    " + ", ".join(f"{k} {v}" for k, v in sorted(uat_counts.items())))
    if open_def:
        print("open defects: " + ", ".join(f"{k} {v}" for k, v in data["open_defects"].items() if v))
    if sec:
        s = data["security"]
        print(f"security (open): blocker {s['blocker']}, major {s['major']}, minor {s['minor']}, nit {s['nit']}"
              + (" · closed: " + ", ".join(f"{k} {v}" for k, v in s["closed"].items()) if s["closed"] else "")
              + (f" · NOT RUN: {len(s['not_run'])}" if s["not_run"] else ""))
    for b in blockers:
        print(f"BLOCKER: {b}")
    if "team" in data:
        tm = data["team"]
        by: Dict[str, List[str]] = {}
        for tid, c in sorted(tm["claims"].items()):
            by.setdefault(c["by"], []).append(f"{tid} {c['status']}")
        print("team:   " + " · ".join(f"{m}: {', '.join(by.get(m, [])) or 'free'}" for m in tm["members"])
              + f" (you: {tm['me'] or 'not a member: ' + tm['identity']})")
        for c in tm["conflicts"]:
            print(f"CONFLICT: {c['item']} claimed by {c['won']} and later by {c['lost']}; {c['won']} keeps it")
        for tid in tm["stale"]:
            print(f"STALE: {tid} claimed by {tm['claims'][tid]['by']}, no activity for a while")
        for r in tm["renamed"]:
            print(f"RENAMED: {r['by']}'s {r['from']} is {r['to']} (two members opened the same id)")
        if "gate" in tm:
            g = tm["gate"]
            print(f"gate:   {g['phase']} {len(g['approved_by'])} of {g['quorum']} approvals"
                  + (f" ({', '.join(g['approved_by'])})" if g["approved_by"] else "")
                  + (f"; waiting for {', '.join(g['waiting_for'])}" if g["waiting_for"] else ""))
    if data["last_checkpoint"]:
        print(f"last checkpoint: {data['last_checkpoint']}")
    print(f"NEXT ({data['next']['who']}): {data['next']['action']}")
    return code


def cmd_checklist(a: argparse.Namespace) -> int:
    for item in GATES[a.phase]:
        print(f"{item['id']}: {item['item']}")
    return 0


def cmd_start(a: argparse.Namespace) -> int:
    p = open_project()
    coordinator_only(p, "opens phases")
    st = p.state
    phase = st["phases"][a.phase]
    if phase["status"] == "approved" and not a.reopen:
        die(f"{a.phase} is already approved; use --reopen to work on it again", 1)
    if phase["status"] == "skipped" and not a.reopen:
        die(f"{a.phase} was skipped; use --reopen to run it anyway", 1)
    for earlier in PHASES[:PHASES.index(a.phase)]:
        if st["phases"][earlier]["status"] not in CLOSED:
            die(f"cannot start {a.phase}: {earlier} is {st['phases'][earlier]['status']} (close its gate first)", 1)
    if phase["status"] != "in_progress":
        phase["started_at"] = now_iso()
    phase["status"] = "in_progress"
    phase.setdefault("lead", PHASE_LEAD[a.phase])
    phase.pop("skip_reason", None)
    phase.pop("completed_at", None)
    st["current_phase"] = a.phase
    p.save()
    print(f"{a.phase} in progress (lead: {phase['lead']})")
    return 0


def parse_results(texts: List[str]) -> List[dict]:
    """Parse "ID=result[:note]" items. Items are separated by commas that precede another ID,
    so notes may contain commas; repeated --result flags are also accepted."""
    parts: List[str] = []
    for text in texts:
        parts += [x.strip() for x in re.split(r",(?=\s*[A-Z]{2,4}-\d+\s*=)", text) if x.strip()]
    out = []
    for part in parts:
        m = re.match(r"^([A-Z]{2,4}-\d+)\s*=\s*(pass|fail|n/a)\s*(?::\s*(.*))?$", part, re.S)
        if not m:
            die(f"bad result '{part}': use ID=pass|fail|n/a[:note]")
        item = {"id": m.group(1), "result": m.group(2)}
        note = (m.group(3) or "").strip()
        if item["result"] == "n/a" and not note:
            die(f"{item['id']}=n/a needs a reason: {item['id']}=n/a:<why it does not apply>")
        if note:
            item["note"] = note
        out.append(item)
    return out


def coordinator_only(p: Project, what: str) -> Optional[str]:
    """Team mode: only a coordinator may do this. Returns the member (None without a team)."""
    if not _team.team_path(p.root).is_file():
        return None
    team, me = require_member(p)
    if me not in _team.coordinators(team):
        die(f"in a team the coordinator ({', '.join(_team.coordinators(team))}) {what}", 1)
    return me


def actor(p: Project, default: str) -> str:
    """Who to record as deciding: the member in team mode, else the given default."""
    if not _team.team_path(p.root).is_file():
        return default
    return require_member(p)[1]


def cmd_submit(a: argparse.Namespace) -> int:
    p = open_project()
    me = coordinator_only(p, "submits gates")
    phase = p.state["phases"][a.phase]
    if phase["status"] not in ("in_progress", "rejected"):
        die(f"{a.phase} is {phase['status']}; only an in-progress phase can be submitted", 1)
    if not (a.results or a.result):
        die("pass --results or --result")
    results = parse_results(([a.results] if a.results else []) + (a.result or []))
    given = {r["id"] for r in results}
    expected = [i["id"] for i in GATES[a.phase]]
    missing = [i for i in expected if i not in given]
    unknown = sorted(given - set(expected))
    if missing or unknown:
        die(f"checklist incomplete: missing {missing or '-'}, unknown {unknown or '-'}", 1)
    texts = {i["id"]: i["item"] for i in GATES[a.phase]}
    for r in results:
        r["item"] = texts[r["id"]]
    phase["gate"] = {"checklist": results, "coherence": a.coherence, "submitted_at": now_iso()}
    if me:
        phase["gate"]["submitted_by"] = me
    phase["status"] = "awaiting_approval"
    p.save()
    fails = [r["id"] for r in results if r["result"] == "fail"]
    print(f"{a.phase} submitted for approval" + (f" with FAILED items: {', '.join(fails)}" if fails else ""))
    if a.coherence == "fail":
        print("coherence check FAILED")
    if me:
        team = p.team()
        assert team is not None
        print(f"Approvers: {', '.join(_team.approvers_of(team, a.phase))} ({_team.quorum_of(team, a.phase)} needed). "
              "Each approves with `state.py approve` in their own session. Do not approve on their behalf.")
    else:
        print("Ask the user to approve or reject. Do not approve on their behalf.")
    return 0


def cmd_approve(a: argparse.Namespace) -> int:
    p = open_project()
    st = p.state
    phase = st["phases"][a.phase]
    if phase["status"] != "awaiting_approval":
        die(f"{a.phase} is {phase['status']}; submit the gate first", 1)
    gate = phase["gate"]
    problems = [r["id"] for r in gate["checklist"] if r["result"] == "fail"]
    if a.phase in COHERENCE_OPTIONAL:
        if gate["coherence"] == "fail":
            problems.append("coherence=fail")
    elif gate["coherence"] != "pass":
        problems.append(f"coherence={gate['coherence']} (this gate needs a passing coherence check)")
    if problems and not a.override:
        die(f"gate cannot be approved: {', '.join(problems)}; fix and resubmit, or pass --override with the user's stated reason", 1)
    approved_by: Optional[List[str]] = None
    if _team.team_path(p.root).is_file():
        team, me = require_member(p)
        g = gate_status(p, a.phase)
        closing = len(g["approved_by"]) >= g["quorum"] and me in _team.coordinators(team)
        if me not in g["approvers"] and not closing:
            die(f"the {a.phase.upper()} gate is approved by {', '.join(g['approvers'])}", 1)
        if me not in g["approved_by"] and not closing:
            _team.append_event(p.root, {"by": me, "event": "gate_approve", "phase": a.phase,
                                        "iteration": int(st.get("iteration", 1))})
            p = Project(p.root)  # read the new event
            st, phase = p.state, p.state["phases"][a.phase]
            gate = phase["gate"]
            g = gate_status(p, a.phase)
        if len(g["approved_by"]) < g["quorum"]:
            print(f"{a.phase} approval by {me} recorded ({len(g['approved_by'])} of {g['quorum']}); waiting for "
                  f"{', '.join(g['waiting_for'])}. Commit and push your log so they see it (ask first).")
            return 0
        approved_by = g["approved_by"]
    ts = now_iso()
    gate["approved_at"] = ts
    if approved_by:
        gate["approved_by"] = approved_by
    if a.override:
        gate["notes"] = f"approved with failures by user decision: {a.override}"
    phase["status"] = "approved"
    phase["completed_at"] = ts
    nxt = first_open_phase(st)
    if nxt:
        st["current_phase"] = nxt
    p.save()
    print(f"{a.phase} approved. " + next_phase_hint(st, a.phase))
    return 0


def cmd_reject(a: argparse.Namespace) -> int:
    p = open_project()
    phase = p.state["phases"][a.phase]
    if phase["status"] != "awaiting_approval":
        die(f"{a.phase} is {phase['status']}; nothing to reject", 1)
    if _team.team_path(p.root).is_file():
        team, me = require_member(p)
        if me not in _team.approvers_of(team, a.phase):
            die(f"the {a.phase.upper()} gate is approved or rejected by {', '.join(_team.approvers_of(team, a.phase))}", 1)
        _team.append_event(p.root, {"by": me, "event": "gate_reject", "phase": a.phase,
                                    "iteration": int(p.state.get("iteration", 1)), "note": a.reason})
        phase["gate"]["rejected_by"] = me
    phase["status"] = "rejected"
    phase["gate"]["rejected_reason"] = a.reason
    p.save()
    print(f"{a.phase} rejected: {a.reason}")
    return 0


def cmd_skip(a: argparse.Namespace) -> int:
    p = open_project()
    coordinator_only(p, "skips phases")
    st = p.state
    phase = st["phases"][a.phase]
    if phase["status"] == "approved":
        die(f"{a.phase} is already approved", 1)
    if not (p.root / a.adr).is_file():
        die(f"ADR not found: {a.adr} (write the ADR first, then skip)", 1)
    phase.update({"status": "skipped", "skip_reason": a.reason, "adr": a.adr})
    if st["current_phase"] == a.phase:
        nxt = first_open_phase(st)
        if nxt:
            st["current_phase"] = nxt
    p.save()
    print(f"{a.phase} skipped ({a.reason}); recorded in {a.adr}")
    return 0


def cmd_set_level(a: argparse.Namespace) -> int:
    p = open_project()
    coordinator_only(p, "changes the level")
    st = p.state
    old = st["project"]["level"]
    st["project"]["level"] = a.level
    changes = []
    for ph in PHASES:
        phase = st["phases"][ph]
        default_skip = ph in LEVEL_DEFAULT_SKIPS[a.level]
        if phase["status"] == "skipped" and phase.get("skip_reason") == "level-default" and not default_skip:
            st["phases"][ph] = {"status": "not_started", "lead": PHASE_LEAD[ph]}
            changes.append(f"{ph}: now required")
        elif phase["status"] == "not_started" and default_skip:
            st["phases"][ph] = {"status": "skipped", "skip_reason": "level-default"}
            changes.append(f"{ph}: skipped by level default")
    nxt = first_open_phase(st)
    if nxt and st["phases"][st["current_phase"]]["status"] in CLOSED:
        st["current_phase"] = nxt
    p.save()
    print(f"level {old} -> {a.level}" + ("; " + "; ".join(changes) if changes else "; no phase changes"))
    return 0


def cmd_new_iteration(a: argparse.Namespace) -> int:
    p = open_project()
    coordinator_only(p, "starts a new iteration")
    st = p.state
    open_phases = [ph for ph in PHASES if st["phases"][ph]["status"] not in CLOSED]
    if open_phases and not a.force:
        die(f"phases still open: {', '.join(open_phases)}; close them first, or pass --force", 1)
    for ph in PHASES[1:]:
        if st["phases"][ph]["status"] == "skipped" and st["phases"][ph].get("skip_reason") == "level-default":
            continue
        st["phases"][ph] = {"status": "not_started", "lead": PHASE_LEAD[ph]}
    st["iteration"] = int(st.get("iteration", 1)) + 1
    st["current_phase"] = "specify"
    p.save()
    print(f"iteration {st['iteration']} started: SPECIFY..EVOLVE reopened (previous gates are kept in git history and checkpoints)")
    print("next: /sancho:specify")
    return 0


def cmd_approval(a: argparse.Namespace) -> int:
    p = open_project()
    entry = {"action": a.action, "scope": a.scope, "granted_by": actor(p, "user"), "granted_at": now_iso()}
    if a.window:
        parts = a.window.split("/")
        try:
            start, end = (datetime.fromisoformat(x.strip()) for x in parts)
            ok = (start.tzinfo is None) == (end.tzinfo is None) and end > start
        except ValueError:
            ok = False
        if not ok:
            die("--window must be START/END in ISO 8601 with END after START, e.g. 2026-11-10T22:00+01:00/2026-11-10T23:00+01:00")
        entry["window"] = a.window
    p.state.setdefault("approvals", []).append(entry)
    p.save()
    print(f"approval recorded: {a.action} [{a.scope}]" + (f" window {a.window}" if a.window else ""))
    return 0


def cmd_decision(a: argparse.Namespace) -> int:
    p = open_project()
    decisions = p.state.setdefault("decisions", [])
    did = f"D-{len(decisions) + 1:03d}"
    rec = {"id": did, "summary": a.summary, "decided_by": actor(p, "user") if a.by == "user" else a.by, "date": now_iso()[:10]}
    if a.adr:
        rec["adr"] = a.adr
    decisions.append(rec)
    p.save()
    print(f"{did} recorded")
    return 0


def cmd_checkpoint(a: argparse.Namespace) -> int:
    p = open_project()
    p.state.setdefault("checkpoints", []).append({"at": now_iso(), "file": a.file})
    p.save()
    print(f"checkpoint recorded: {a.file}")
    return 0


def cmd_validate(a: argparse.Namespace) -> int:
    p = open_project()
    ok = True
    for name, path in p.documents():
        if not path.is_file():
            print(f"-    {name}: {path.relative_to(p.root)} not present")
            continue
        errors = file_errors(path, name)
        ok = ok and not errors
        print(f"{'ok  ' if not errors else 'FAIL'} {name}: {path.relative_to(p.root)}")
        for e in errors[:20]:
            print(f"     {e}")
    hdir = p.root / p.state.get("artifacts", {}).get("handoffs_dir", f"{SANCHO_DIR}/handoffs")
    for h in sorted(hdir.glob("*.json")) if hdir.is_dir() else []:
        errors = file_errors(h, "handoff")
        ok = ok and not errors
        print(f"{'ok  ' if not errors else 'FAIL'} handoff: {h.relative_to(p.root)}")
        for e in errors[:10]:
            print(f"     {e}")
    bad_logs = {f["path"]: f["errors"] for f in p.folded()[2]}
    for f in _team.log_files(p.root):
        rel = f.relative_to(p.root).as_posix()
        errors = bad_logs.get(rel, [])
        ok = ok and not errors
        print(f"{'ok  ' if not errors else 'FAIL'} event-log: {rel}")
        for e in errors[:10]:
            print(f"     {e}")
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("--name", required=True)
    s.add_argument("--level", choices=["L0", "L1", "L2", "L3"], required=True)
    s.add_argument("--platforms", default="")
    s.add_argument("--language", default="en")
    s.add_argument("--threshold", type=int, default=7)
    s.add_argument("--summary")
    s = sub.add_parser("status")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("next")
    s.add_argument("--json", action="store_true")
    s.add_argument("--team", action="store_true", help="team mode: one line per member")
    s.add_argument("--as", dest="as_", metavar="ID", help="team mode: the next step of another member")
    s = sub.add_parser("team")
    s.add_argument("action", choices=["add", "list", "suggest"])
    s.add_argument("--id")
    s.add_argument("--name")
    s.add_argument("--email")
    s.add_argument("--roles", help="comma separated: analyst-pm,ux-ui-designer,architect,developer,qa,security,release-manager")
    s.add_argument("--coordinator", action="store_true")
    sub.add_parser("whoami")
    s = sub.add_parser("claim")
    s.add_argument("task")
    s.add_argument("--branch")
    s.add_argument("--any-role", action="store_true")
    s = sub.add_parser("release")
    s.add_argument("task")
    s = sub.add_parser("task")
    s.add_argument("task")
    s.add_argument("--status", required=True, choices=["pending", "in_progress", "blocked", "ready_for_review", "completed", "failed"])
    s.add_argument("--reason")
    s.add_argument("--evidence", action="append")
    s.add_argument("--note")
    s = sub.add_parser("review")
    s.add_argument("task")
    s.add_argument("--approve", action="store_true")
    s.add_argument("--changes")
    s.add_argument("--evidence", action="append")
    s = sub.add_parser("uat")
    s.add_argument("case")
    s.add_argument("--result", required=True, choices=["pass", "fail", "blocked"])
    s.add_argument("--note")
    s.add_argument("--defect", action="append", help="an existing defect id")
    s.add_argument("--new-defect", action="append", dest="new_defect", help="SEVERITY:DESCRIPTION opens a defect")
    s.add_argument("--tester", help="without a team: who ran the case (default: git user.name)")
    s = sub.add_parser("defect")
    s.add_argument("defect")
    s.add_argument("--status", required=True, choices=["open", "fixed", "verified", "wont_fix"])
    s.add_argument("--task", help="the fix task, e.g. T-012")
    s.add_argument("--note")
    sub.add_parser("compact")
    s = sub.add_parser("since")
    s.add_argument("ref", nargs="?", help="a git reference; default: where you last looked")
    s.add_argument("--json", action="store_true")
    s.add_argument("--peek", action="store_true", help="do not move the 'last seen' marker")
    s = sub.add_parser("hooks")
    s.add_argument("action", choices=["install", "remove", "status"])
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("renumber")
    s.add_argument("--apply", action="store_true")
    s = sub.add_parser("coherence")
    s.add_argument("--json", action="store_true")
    s.add_argument("--quiet", action="store_true", help="print only when there are blocker/major issues")
    s = sub.add_parser("checklist")
    s.add_argument("phase", choices=PHASES)
    s = sub.add_parser("start")
    s.add_argument("phase", choices=PHASES)
    s.add_argument("--reopen", action="store_true")
    s = sub.add_parser("submit")
    s.add_argument("phase", choices=PHASES)
    s.add_argument("--results")
    s.add_argument("--result", action="append")
    s.add_argument("--coherence", choices=["pass", "fail", "not_run", "n/a"], required=True)
    s = sub.add_parser("approve")
    s.add_argument("phase", choices=PHASES)
    s.add_argument("--override")
    s = sub.add_parser("set-level")
    s.add_argument("level", choices=["L0", "L1", "L2", "L3"])
    s = sub.add_parser("new-iteration")
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("reject")
    s.add_argument("phase", choices=PHASES)
    s.add_argument("--reason", required=True)
    s = sub.add_parser("skip")
    s.add_argument("phase", choices=PHASES)
    s.add_argument("--reason", required=True)
    s.add_argument("--adr", required=True)
    s = sub.add_parser("approval")
    s.add_argument("--action", required=True)
    s.add_argument("--scope", required=True)
    s.add_argument("--window", help="agreed time window START/END (ISO 8601), required for active tests on production")
    s = sub.add_parser("decision")
    s.add_argument("--summary", required=True)
    s.add_argument("--by", choices=["user", "agent"], required=True)
    s.add_argument("--adr")
    s = sub.add_parser("checkpoint")
    s.add_argument("--file", required=True)
    sub.add_parser("validate")
    a = ap.parse_args(argv)
    handler = globals()[f"cmd_{a.cmd.replace('-', '_')}"]
    return handler(a)


if __name__ == "__main__":
    sys.exit(main())
