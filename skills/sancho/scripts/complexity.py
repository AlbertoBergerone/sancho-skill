#!/usr/bin/env python3
"""Deterministic complexity scoring (1-10) for backlog tasks, with split recommendations.

Score = 1 + points from the task's complexity.factors (and its dependency count):

  files touched        0 -> 0 | 1-2 -> 1 | 3-5 -> 2 | 6+ -> 3
  integrations         1 point each, max 2
  unknowns             1 point each, max 2
  ui_screens           0 -> 0 | 1-2 -> 1 | 3+ -> 2
  data_migration       +2
  security_sensitive   +1
  no_existing_tests    +1
  depends_on >= 3      +1
  clamped to 1..10

Tasks without factors keep the score already in the backlog (set by a human or agent).
Tasks scoring above the threshold get a split recommendation; the Analyst/PM then
creates subtasks T-xxx.1, T-xxx.2 ... with "parent": "T-xxx".

Usage:
  python complexity.py .sancho/backlog.json [--threshold 7] [--write] [--json] [--strict]

--threshold defaults to settings.complexity_threshold in .sancho/state.json next to the
backlog, else 7. --write stores computed scores and rationales back into the backlog.
--strict exits 1 when a task above threshold has no subtasks yet.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import configure_stdout, die, load_json, save_json  # noqa: E402

DEFAULT_THRESHOLD = 7


def _band(value: int, bands: List[Tuple[int, int]]) -> int:
    """bands: list of (min_value, points) sorted ascending."""
    pts = 0
    for minimum, points in bands:
        if value >= minimum:
            pts = points
    return pts


def score_task(task: dict) -> Tuple[int, List[str], bool]:
    """Return (score, rationale parts, computed). computed=False when no factors exist."""
    cx = task.get("complexity") or {}
    factors = cx.get("factors")
    if not factors:
        return int(cx.get("score", 1)), ["manual score (no factors)"], False
    parts: List[str] = []
    total = 1
    files = int(factors.get("files", 0))
    p = _band(files, [(1, 1), (3, 2), (6, 3)])
    if p:
        parts.append(f"files={files}:+{p}")
    total += p
    for key, cap in (("integrations", 2), ("unknowns", 2)):
        n = int(factors.get(key, 0))
        p = min(n, cap)
        if p:
            parts.append(f"{key}={n}:+{p}")
        total += p
    screens = int(factors.get("ui_screens", 0))
    p = _band(screens, [(1, 1), (3, 2)])
    if p:
        parts.append(f"ui_screens={screens}:+{p}")
    total += p
    for key, pts in (("data_migration", 2), ("security_sensitive", 1), ("no_existing_tests", 1)):
        if factors.get(key):
            parts.append(f"{key}:+{pts}")
            total += pts
    deps = len(task.get("depends_on", []))
    if deps >= 3:
        parts.append(f"depends_on={deps}:+1")
        total += 1
    return max(1, min(10, total)), parts or ["baseline"], True


def threshold_from_state(backlog_path: Path) -> Optional[int]:
    state = backlog_path.parent / "state.json"
    if state.is_file():
        try:
            return int(load_json(state)["settings"]["complexity_threshold"])
        except (KeyError, ValueError, TypeError):
            return None
    return None


def analyze(backlog: dict, threshold: int) -> List[dict]:
    tasks = backlog.get("tasks", [])
    children = {t.get("parent") for t in tasks if t.get("parent")}
    rows = []
    for task in tasks:
        score, parts, computed = score_task(task)
        over = score > threshold
        rows.append({
            "id": task["id"], "title": task.get("title", ""), "score": score, "computed": computed,
            "rationale": ", ".join(parts), "above_threshold": over,
            "split": "done" if task["id"] in children else ("recommended" if over else "no"),
        })
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("backlog", type=Path)
    ap.add_argument("--threshold", type=int)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    if not args.backlog.is_file():
        die(f"backlog not found: {args.backlog}")
    threshold = args.threshold or threshold_from_state(args.backlog) or DEFAULT_THRESHOLD
    if not 1 <= threshold <= 10:
        die("threshold must be between 1 and 10")
    backlog = load_json(args.backlog)
    rows = analyze(backlog, threshold)
    if args.write:
        by_id = {r["id"]: r for r in rows}
        for task in backlog.get("tasks", []):
            row = by_id[task["id"]]
            if row["computed"]:
                task["complexity"]["score"] = row["score"]
                task["complexity"]["rationale"] = row["rationale"]
        save_json(args.backlog, backlog)
    pending_split = [r for r in rows if r["split"] == "recommended"]
    if args.json:
        print(json.dumps({"threshold": threshold, "tasks": rows}, indent=2, ensure_ascii=False))
    else:
        print(f"complexity threshold: {threshold}")
        for r in rows:
            flag = {"recommended": "  <- split recommended", "done": "  (split done)"}.get(r["split"], "")
            print(f"{r['id']:<9} {r['score']:>2}  {r['title'][:48]:<48} [{r['rationale']}]{flag}")
        print(f"{len(pending_split)} task(s) above threshold without subtasks")
    return 1 if (args.strict and pending_split) else 0


if __name__ == "__main__":
    sys.exit(main())
