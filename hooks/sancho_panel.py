"""Collects what the Sancho panel shows, as one JSON object on stdout.

Reads only (except --mark-seen, which moves the personal 'last seen' marker of
`state.py since`, kept in the git folder). Runs the bundled skill's `state.py status --json` in the current
directory (the session's folder). In a repository checkout (tools/build.py and
dist/ present, or SANCHO_REPO set) it also compares dist/sancho.zip with
skills/sancho; in the plugin as installed the ZIP state is "none".
"""
import hashlib, json, os, subprocess, sys, zipfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
STATE = PLUGIN / "skills" / "sancho" / "scripts" / "state.py"
REPO = Path(os.environ["SANCHO_REPO"]) if os.environ.get("SANCHO_REPO") else PLUGIN
SKILL = REPO / "skills" / "sancho"
ZIP = REPO / "dist" / "sancho.zip"
SKIP_DIRS = {"__pycache__", ".pytest_cache"}  # same rules as tools/build.py


def status():
    script = STATE
    if not script.exists():
        return None, f"state.py non trovato in {script}"
    p = subprocess.run([sys.executable, "-I", str(script), "status", "--json"],
                       capture_output=True, text=True, encoding="utf-8", timeout=20)
    if p.returncode != 0:
        msg = (p.stderr or p.stdout).strip()
        if "no .sancho/" in msg:
            return None, None
        return None, msg[-400:] or f"state.py exit {p.returncode}"
    return json.loads(p.stdout), None


def zip_check():
    if not os.environ.get("SANCHO_REPO") and not ((REPO / "tools" / "build.py").exists() and ZIP.parent.is_dir()):
        return {"state": "none", "detail": ""}
    if not ZIP.exists():
        return {"state": "missing", "detail": f"{ZIP} non esiste"}
    try:
        z = zipfile.ZipFile(ZIP)
        packed = {n[len("sancho/"):]: hashlib.sha256(z.read(n)).hexdigest()
                  for n in z.namelist() if n.startswith("sancho/") and not n.endswith("/")
                  and not any(part in SKIP_DIRS for part in n.split("/"))}
    except Exception as exc:
        return {"state": "unknown", "detail": f"zip illeggibile: {exc}"}
    local = {}
    for f in SKILL.rglob("*"):
        if f.is_file() and not any(part in SKIP_DIRS for part in f.relative_to(SKILL).parts) and f.suffix not in (".pyc", ".tmp"):
            local[f.relative_to(SKILL).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
    for extra in ("LICENSE", "NOTICE"):  # build.py adds these from the repo root
        if (REPO / extra).exists():
            local[extra] = hashlib.sha256((REPO / extra).read_bytes()).hexdigest()
    changed = sorted(k for k in local if k in packed and local[k] != packed[k])
    added = sorted(k for k in local if k not in packed)
    removed = sorted(k for k in packed if k not in local)
    if not (changed or added or removed):
        return {"state": "ok", "detail": f"dist/sancho.zip = skills/sancho ({len(local)} file)"}
    parts = []
    if changed: parts.append(f"{len(changed)} modificati ({', '.join(changed[:3])})")
    if added: parts.append(f"{len(added)} nuovi ({', '.join(added[:3])})")
    if removed: parts.append(f"{len(removed)} tolti ({', '.join(removed[:3])})")
    return {"state": "stale", "detail": "; ".join(parts)}


def since(mark_seen):
    """Team mode: what the others did since this member last looked (state.py since --json)."""
    args = [sys.executable, "-I", str(STATE), "since", "--json"]
    if mark_seen:  # move the marker first, then read: nothing left to show
        subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=20)
    p = subprocess.run(args + ["--peek"], capture_output=True, text=True, encoding="utf-8", timeout=20)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except ValueError:
        return None


def main():
    out = {"cwd": os.getcwd()}
    try:
        out["status"], out["error"] = status()
    except Exception as exc:
        out["status"], out["error"] = None, str(exc)
    out["since"] = None
    if out["status"] and "team" in out["status"]:
        try:
            out["since"] = since("--mark-seen" in sys.argv[1:])
        except Exception:
            out["since"] = None
    out["zip"] = zip_check()
    print(json.dumps(out))


main()
