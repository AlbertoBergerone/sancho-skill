#!/usr/bin/env python3
"""Build helper for the Sancho repository (standard library only).

  python tools/build.py           regenerate agents/ from skills/sancho/roles/ and build dist/sancho.zip
  python tools/build.py --check   fail if agents/ is out of date (used by tests and CI)
  python tools/build.py --agents  only regenerate agents/
  python tools/build.py --zip     only build dist/sancho.zip

skills/sancho/roles/*.md is the single source for the seven roles. In the Claude Code
plugin they become subagents (agents/*.md, invoked as sancho:<role>); in the ZIP for the
Claude apps the main conversation reads them directly.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "sancho"
ROLES = SKILL / "roles"
AGENTS = ROOT / "agents"
DIST = ROOT / "dist"

PREAMBLE = """<!-- Generated from skills/sancho/roles/{name}.md by tools/build.py. Edit the source, then run the build. -->

> You are running as a Sancho subagent. Paths such as `references/...`, `scripts/...`, `schemas/...`,
> `templates/...` and `roles/...` are relative to the Sancho skill directory, whose absolute path the
> orchestrator gives you in the brief (it is `skills/sancho` inside the plugin). Project files such as
> `.sancho/...`, `docs/...` and `design/...` are relative to the project root. You cannot talk to the
> user: if a decision belongs to the user, stop and return it as an open question in your handoff.
"""


def render(role_file: Path) -> str:
    text = role_file.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise SystemExit(f"{role_file}: missing frontmatter")
    end = text.index("\n---\n", 4) + len("\n---\n")
    return text[:end] + "\n" + PREAMBLE.format(name=role_file.stem) + text[end:]


def expected_agents() -> dict:
    return {f"{p.stem}.md": render(p) for p in sorted(ROLES.glob("*.md"))}


def write_agents() -> None:
    AGENTS.mkdir(exist_ok=True)
    wanted = expected_agents()
    for stale in AGENTS.glob("*.md"):
        if stale.name not in wanted:
            stale.unlink()
    for name, content in wanted.items():
        with open(AGENTS / name, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
    print(f"agents/: {len(wanted)} subagents generated")


def check_agents() -> int:
    wanted = expected_agents()
    present = {p.name: p.read_text(encoding="utf-8") for p in AGENTS.glob("*.md")} if AGENTS.is_dir() else {}
    problems = [n for n in wanted if present.get(n) != wanted[n]] + [n for n in present if n not in wanted]
    if problems:
        print("agents/ out of date: " + ", ".join(sorted(problems)) + " (run: python tools/build.py --agents)")
        return 1
    print("agents/ in sync with roles/")
    return 0


def build_zip() -> Path:
    DIST.mkdir(exist_ok=True)
    out = DIST / "sancho.zip"
    skip_dirs = {"__pycache__", ".pytest_cache"}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(SKILL.rglob("*")):
            if path.is_dir() or any(part in skip_dirs for part in path.parts) or path.suffix in (".pyc", ".tmp"):
                continue
            zf.write(path, Path("sancho") / path.relative_to(SKILL))
        for extra in ("LICENSE", "NOTICE"):
            zf.write(ROOT / extra, Path("sancho") / extra)
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert "sancho/SKILL.md" in names, "SKILL.md must be at sancho/SKILL.md inside the ZIP"
    print(f"dist/sancho.zip: {len(names)} files")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--agents", action="store_true")
    ap.add_argument("--zip", action="store_true")
    a = ap.parse_args()
    if a.check:
        return check_agents()
    if a.agents or not a.zip:
        write_agents()
    if a.zip or not a.agents:
        build_zip()
    return 0


if __name__ == "__main__":
    sys.exit(main())
