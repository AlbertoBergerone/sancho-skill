#!/usr/bin/env python3
"""Cross-artifact coherence check for a Sancho backlog (and optional UAT file).

Traceability chain enforced:  requirement -> story -> acceptance criterion -> test or UAT case
and                            story -> task, with valid and acyclic task dependencies.

Usage:
  python coherence_check.py .sancho/backlog.json [--uat .sancho/uat.json]
                            [--stage spec|tasks|full] [--json]

Stages:
  spec   requirement/story/criterion checks only (end of SPECIFY)
  tasks  + task coverage, dependencies and UAT coverage (end of TASKS)
  full   same as tasks; also run at VERIFY and RELEASE (default)

Exit code: 0 no blocker/major issue, 1 issues found, 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import configure_stdout, die, load_json  # noqa: E402


def find_cycles(graph: Dict[str, List[str]]) -> List[List[str]]:
    """Return dependency cycles (each as a list of ids, first id repeated at the end)."""
    white, grey, black = 0, 1, 2
    color = {n: white for n in graph}
    stack: List[str] = []
    cycles: List[List[str]] = []

    def visit(node: str) -> None:
        color[node] = grey
        stack.append(node)
        for dep in graph.get(node, []):
            if dep not in color:
                continue
            if color[dep] == grey:
                cycles.append(stack[stack.index(dep):] + [dep])
            elif color[dep] == white:
                visit(dep)
        stack.pop()
        color[node] = black

    for n in sorted(graph):
        if color[n] == white:
            visit(n)
    return cycles


def check(backlog: dict, uat: Optional[dict] = None, stage: str = "full") -> List[dict]:
    issues: List[dict] = []

    def add(code: str, severity: str, ref: str, message: str) -> None:
        issues.append({"code": code, "severity": severity, "ref": ref, "message": message})

    # C0 duplicate ids would silently hide items in every other check
    for kind, items in (("requirement", backlog.get("requirements", [])), ("story", backlog.get("stories", [])),
                        ("task", backlog.get("tasks", [])), ("UAT case", (uat or {}).get("cases", []))):
        seen_ids: Dict[str, int] = {}
        for item in items:
            seen_ids[item.get("id", "?")] = seen_ids.get(item.get("id", "?"), 0) + 1
        for ident, n in sorted(seen_ids.items()):
            if n > 1:
                add("C0", "blocker", ident, f"duplicate {kind} id ({n} times)")
    seen_ac: Dict[str, int] = {}
    for s in backlog.get("stories", []):
        for c in s.get("acceptance_criteria", []):
            seen_ac[c["id"]] = seen_ac.get(c["id"], 0) + 1
    for ident, n in sorted(seen_ac.items()):
        if n > 1:
            add("C0", "blocker", ident, f"duplicate criterion id ({n} times)")

    reqs = {r["id"]: r for r in backlog.get("requirements", [])}
    stories = {s["id"]: s for s in backlog.get("stories", [])}
    tasks = {t["id"]: t for t in backlog.get("tasks", [])}
    criteria = {c["id"]: (sid, c) for sid, s in stories.items() for c in s.get("acceptance_criteria", [])}
    uat_cases = {c["id"]: c for c in (uat or {}).get("cases", [])}
    uat_by_criterion: Dict[str, List[str]] = {}
    for cid, case in uat_cases.items():
        for ac in case.get("criteria", []):
            uat_by_criterion.setdefault(ac, []).append(cid)

    # C1 requirement without story (wont-have requirements are exempt)
    covered = {r for s in stories.values() for r in s.get("requirements", [])}
    for rid, req in reqs.items():
        if req.get("priority") != "wont" and rid not in covered:
            add("C1", "major", rid, "requirement is not covered by any story")
    # C2 story references unknown requirement
    for sid, story in stories.items():
        for rid in story.get("requirements", []):
            if rid not in reqs:
                add("C2", "major", sid, f"references unknown requirement {rid}")
        # C3 story without acceptance criteria
        if not story.get("acceptance_criteria"):
            add("C3", "blocker", sid, "story has no acceptance criteria")
    # C4 criterion without a way to verify it
    for acid, (sid, crit) in criteria.items():
        ver = crit.get("verification") or {}
        method = ver.get("method")
        if not method:
            add("C4", "major", acid, "criterion has no verification method")
            continue
        if method == "uat":
            if stage == "spec":
                continue
            if uat is None:
                add("C4", "major", acid, "verified by UAT but no UAT file was provided")
            elif acid not in uat_by_criterion:
                add("C4", "major", acid, "verified by UAT but no UAT case covers it")
        elif not ver.get("ref") and stage != "spec":
            add("C4", "major", acid, f"verification method '{method}' has no ref (test, command or check)")

    if stage == "spec":
        return issues

    # C5 tasks <-> stories
    stories_with_tasks = set()
    for tid, task in tasks.items():
        sid = task.get("story")
        if sid not in stories:
            add("C5", "major", tid, f"task references unknown story {sid}")
        else:
            stories_with_tasks.add(sid)
        for acid in task.get("criteria", []):
            if acid not in criteria:
                add("C8", "minor", tid, f"task references unknown criterion {acid}")
    for sid, story in stories.items():
        if story.get("priority") != "wont" and sid not in stories_with_tasks:
            add("C5", "major", sid, "story has no tasks")
    # C6 unknown dependencies, C7 cycles
    graph: Dict[str, List[str]] = {}
    for tid, task in tasks.items():
        deps = task.get("depends_on", [])
        for dep in deps:
            if dep not in tasks:
                add("C6", "major", tid, f"depends on unknown task {dep}")
            if dep == tid:
                add("C7", "blocker", tid, "task depends on itself")
        graph[tid] = [d for d in deps if d in tasks and d != tid]
    for cycle in find_cycles(graph):
        add("C7", "blocker", cycle[0], "circular dependency: " + " -> ".join(cycle))
    # C9 UAT cases point to real stories/criteria
    for cid, case in uat_cases.items():
        if case.get("story") not in stories:
            add("C9", "major", cid, f"UAT case references unknown story {case.get('story')}")
        for acid in case.get("criteria", []):
            if acid not in criteria:
                add("C9", "major", cid, f"UAT case references unknown criterion {acid}")
            elif criteria[acid][0] != case.get("story"):
                add("C9", "minor", cid, f"criterion {acid} belongs to {criteria[acid][0]}, not {case.get('story')}")
    return issues


def main(argv: Optional[List[str]] = None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("backlog", type=Path)
    ap.add_argument("--uat", type=Path)
    ap.add_argument("--stage", choices=["spec", "tasks", "full"], default="full")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    if not args.backlog.is_file():
        die(f"backlog not found: {args.backlog}")
    uat = load_json(args.uat) if args.uat else None
    issues = check(load_json(args.backlog), uat, args.stage)
    failing = [i for i in issues if i["severity"] in ("blocker", "major")]
    if args.json:
        print(json.dumps({"stage": args.stage, "result": "fail" if failing else "pass", "issues": issues}, indent=2))
    else:
        if not issues:
            print(f"coherence ({args.stage}): PASS - no issues")
        for i in issues:
            print(f"[{i['severity']}] {i['code']} {i['ref']}: {i['message']}")
        if issues:
            print(f"coherence ({args.stage}): {'FAIL' if failing else 'PASS with minor issues'} - {len(issues)} issue(s)")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
