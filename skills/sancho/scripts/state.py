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
  validate                                 validate state, backlog and UAT files against the schemas

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

    def backlog(self) -> dict:
        p = self.file("backlog", f"{SANCHO_DIR}/backlog.json")
        return load_json(p) if p.is_file() else {"requirements": [], "stories": [], "tasks": []}

    def uat(self) -> dict:
        p = self.file("uat", f"{SANCHO_DIR}/uat.json")
        return load_json(p) if p.is_file() else {"cases": [], "defects": []}

    def security(self) -> Optional[dict]:
        p = self.file("security_report", "docs/security/security-report.json")
        return load_json(p) if p.is_file() else None

    def documents(self) -> List[Tuple[str, Path]]:
        return [("state", self.state_path),
                ("backlog", self.file("backlog", f"{SANCHO_DIR}/backlog.json")),
                ("uat", self.file("uat", f"{SANCHO_DIR}/uat.json")),
                ("security-report", self.file("security_report", "docs/security/security-report.json"))]

    def invalid_files(self) -> List[dict]:
        out = []
        for name, path in self.documents():
            errors = file_errors(path, name) if path.is_file() else []
            if errors:
                out.append({"name": name, "path": path.relative_to(self.root).as_posix(), "errors": errors})
        return out

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


def compute_next(p: Project) -> dict:
    st = p.state
    invalid = p.invalid_files()
    if invalid:
        paths = ", ".join(f["path"] for f in invalid)
        return {"who": "user", "phase": st.get("current_phase"), "action": f"Repair {paths}: run `state.py validate` to see the errors. The next step cannot be worked out until then."}
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


def cmd_next(a: argparse.Namespace) -> int:
    root = find_root()
    if root is None:
        nxt = {"who": "user", "phase": "discover", "action": "No Sancho project here yet. Run /sancho:help for a tour, or /sancho:discover to start."}
    else:
        nxt = compute_next(Project(root))
    if a.json:
        print(json.dumps(nxt, indent=2, ensure_ascii=False))
    else:
        print(f"NEXT ({nxt['who']}): {nxt['action']}")
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
        "next": compute_next(p),
    }
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


def cmd_submit(a: argparse.Namespace) -> int:
    p = open_project()
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
    phase["gate"] = {"checklist": results, "coherence": a.coherence}
    phase["status"] = "awaiting_approval"
    p.save()
    fails = [r["id"] for r in results if r["result"] == "fail"]
    print(f"{a.phase} submitted for approval" + (f" with FAILED items: {', '.join(fails)}" if fails else ""))
    if a.coherence == "fail":
        print("coherence check FAILED")
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
    ts = now_iso()
    gate["approved_at"] = ts
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
    phase["status"] = "rejected"
    phase["gate"]["rejected_reason"] = a.reason
    p.save()
    print(f"{a.phase} rejected: {a.reason}")
    return 0


def cmd_skip(a: argparse.Namespace) -> int:
    p = open_project()
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
    entry = {"action": a.action, "scope": a.scope, "granted_by": "user", "granted_at": now_iso()}
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
    rec = {"id": did, "summary": a.summary, "decided_by": a.by, "date": now_iso()[:10]}
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
    for name in ("status", "next"):
        s = sub.add_parser(name)
        s.add_argument("--json", action="store_true")
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
