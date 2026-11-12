#!/usr/bin/env python3
"""Replace the YOUR_GITHUB_USER / YOUR_NAME placeholders across the repository, once.

  python tools/set_owner.py --user my-github-user --name "My Name" [--dry-run]
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "dist", "__pycache__"}
TEXT = {".md", ".json", ".py", ".yml", ".yaml", ".txt", ""}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", a.user):
        raise SystemExit("not a valid GitHub user name")
    changed = 0
    for path in ROOT.rglob("*"):
        if path.is_dir() or any(p in SKIP for p in path.parts) or path.suffix not in TEXT or path.name == "set_owner.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text.replace("YOUR_GITHUB_USER", a.user).replace("YOUR_NAME", a.name)
        if new != text:
            changed += 1
            print(("would update " if a.dry_run else "updated ") + str(path.relative_to(ROOT)))
            if not a.dry_run:
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(new)
    print(f"{changed} file(s)")
    if not a.dry_run and changed:
        print("now run: python tools/build.py && python -I tests/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
