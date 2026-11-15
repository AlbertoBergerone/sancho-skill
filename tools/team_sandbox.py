#!/usr/bin/env python3
"""Create a sandbox to try Sancho's team mode by hand (standard library + git).

  python tools/team_sandbox.py DIR [--names anna,bruno,carla]

DIR gets:
  origin.git/          a local "server" (bare repository)
  anna/ bruno/ carla/  three clones, each with its own git user.name and user.email,
                       so Sancho recognizes a different member in each folder

The project ("Bacheca", level L1) is in IMPLEMENT with five tasks and four UAT cases.
There is no .sancho/team.json yet: creating the team is the first UAT case
(docs/testing/team-mode-UAT.md). Open one Claude Code session per folder.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "skills" / "sancho" / "scripts" / "state.py"


def git(cwd: Path, *args: str) -> None:
    r = subprocess.run(["git", "-c", "init.defaultBranch=main", "-c", "core.autocrlf=false", *args], cwd=str(cwd),
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {r.stderr.strip()}")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def project(seed: Path) -> None:
    r = subprocess.run([sys.executable, "-I", str(STATE), "init", "--name", "Bacheca", "--level", "L1", "--platforms", "web",
                        "--language", "it", "--summary", "Bacheca condivisa di annunci per un piccolo ufficio."],
                       cwd=str(seed), capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit(r.stderr)
    now = datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()
    st = json.loads((seed / ".sancho/state.json").read_text(encoding="utf-8"))
    for ph in ("discover", "specify", "tasks"):
        st["phases"][ph] = {"status": "approved", "lead": st["phases"][ph].get("lead", "analyst-pm"), "started_at": now,
                            "completed_at": now, "gate": {"checklist": [], "coherence": "pass", "approved_at": now,
                                                          "notes": "sandbox: closed by tools/team_sandbox.py"}}
    st["phases"]["implement"] = {"status": "in_progress", "lead": "developer", "started_at": now}
    st["current_phase"] = "implement"
    write_json(seed / ".sancho/state.json", st)

    def story(sid, title, want, n_req):
        return {"id": sid, "title": title, "as_a": "impiegato", "i_want": want, "so_that": "tutti siano informati",
                "requirements": [f"R-{n_req:03d}"], "priority": "must",
                "context": f"{title}. Web app semplice (HTML + API REST), nessun login esterno; vedi docs/spec.md.",
                "acceptance_criteria": [
                    {"id": f"AC-{sid[2:]}.1", "description": f"{title}: funziona dal browser", "verification": {"method": "uat", "ref": ""},
                     "status": "not_verified"},
                    {"id": f"AC-{sid[2:]}.2", "description": f"{title}: coperto da test automatici",
                     "verification": {"method": "automated_test", "ref": "tests/"}, "status": "not_verified"}]}
    stories = [story("S-001", "Pubblicare un annuncio", "pubblicare un annuncio", 1),
               story("S-002", "Leggere gli annunci", "vedere gli annunci recenti", 2),
               story("S-003", "Archiviare un annuncio", "archiviare un annuncio scaduto", 3)]
    reqs = [{"id": f"R-{i:03d}", "kind": "functional", "statement": s["title"], "priority": "must", "source": "user"}
            for i, s in enumerate(stories, 1)]

    def task(tid, sid, title, deps=(), score=3):
        return {"id": tid, "story": sid, "title": title, "owner": "developer", "status": "pending", "depends_on": list(deps),
                "complexity": {"score": score}, "criteria": [f"AC-{sid[2:]}.1", f"AC-{sid[2:]}.2"]}
    tasks = [task("T-001", "S-001", "API: crea annuncio"), task("T-002", "S-002", "API: elenco annunci"),
             task("T-003", "S-001", "Pagina: modulo nuovo annuncio", ["T-001"]),
             task("T-004", "S-002", "Pagina: bacheca", ["T-002"]), task("T-005", "S-003", "Archiviazione annunci scaduti", score=4)]
    write_json(seed / ".sancho/backlog.json", {"protocol": "sancho/1.0", "requirements": reqs, "stories": stories, "tasks": tasks})
    for s in stories:
        s["acceptance_criteria"][0]["verification"]["ref"] = ""

    def case(cid, sid, title, steps, expected):
        return {"id": cid, "story": sid, "criteria": [f"AC-{sid[2:]}.1"], "title": title, "platform": "web (Chrome)",
                "preconditions": ["L'app è avviata in locale"], "steps": [{"n": i, "action": a} for i, a in enumerate(steps, 1)],
                "expected_result": expected, "result": "not_tested"}
    cases = [case("UAT-001", "S-001", "Pubblicare un annuncio", ["Apri la bacheca", "Premi Nuovo annuncio", "Scrivi titolo e testo, premi Pubblica"], "L'annuncio compare in cima alla bacheca"),
             case("UAT-002", "S-001", "Annuncio senza titolo", ["Premi Nuovo annuncio", "Lascia vuoto il titolo, premi Pubblica"], "Un messaggio chiede il titolo; nulla viene pubblicato"),
             case("UAT-003", "S-002", "Leggere gli annunci recenti", ["Apri la bacheca"], "Gli annunci sono in ordine dal più recente"),
             case("UAT-004", "S-003", "Archiviare un annuncio scaduto", ["Apri un annuncio scaduto", "Premi Archivia"], "L'annuncio sparisce dalla bacheca e resta nell'archivio")]
    for s in stories:
        refs = [c["id"] for c in cases if c["story"] == s["id"]]
        s["acceptance_criteria"][0]["verification"]["ref"] = refs[0]
    write_json(seed / ".sancho/backlog.json", {"protocol": "sancho/1.0", "requirements": reqs, "stories": stories, "tasks": tasks})
    write_json(seed / ".sancho/uat.json", {"protocol": "sancho/1.0", "cases": cases, "defects": []})
    (seed / "docs").mkdir(exist_ok=True)
    (seed / "docs/spec.md").write_text("# Bacheca\n\nProgetto di prova per la modalità squadra di Sancho.\n", encoding="utf-8")
    (seed / "README.md").write_text("# Bacheca (sandbox)\n\nProgetto di prova creato da tools/team_sandbox.py.\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", type=Path)
    ap.add_argument("--names", default="anna,bruno,carla")
    a = ap.parse_args()
    names = [n.strip().lower() for n in a.names.split(",") if n.strip()]
    if len(names) < 2:
        sys.exit("at least two names")
    base = a.dir.resolve()
    if base.exists() and any(base.iterdir()):
        sys.exit(f"{base} is not empty")
    base.mkdir(parents=True, exist_ok=True)
    git(base, "init", "--bare", "origin.git")
    seed = base / "_seed"
    seed.mkdir()
    git(seed, "init")
    project(seed)
    git(seed, "add", "-A")
    git(seed, "-c", f"user.name={names[0].title()}", "-c", f"user.email={names[0]}@example.com", "commit", "-m", "Bacheca: progetto di prova")
    for n in names:  # one commit each, so "sancho, prepara la squadra" can suggest everyone from git log
        note = seed / "docs" / "team" / f"{n}.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(f"# {n.title()}\n\nMembro della squadra di prova.\n", encoding="utf-8")
        git(seed, "add", "-A")
        git(seed, "-c", f"user.name={n.title()}", "-c", f"user.email={n}@example.com", "commit", "-m", f"docs: {n.title()} entra nel progetto")
    git(seed, "push", str(base / "origin.git"), "HEAD:main")
    for n in names:
        git(base, "clone", "-b", "main", str(base / "origin.git"), n)
        git(base / n, "config", "user.name", n.title())
        git(base / n, "config", "user.email", f"{n}@example.com")
    import shutil
    shutil.rmtree(seed, ignore_errors=True)
    print(f"sandbox ready in {base}")
    print(f"  server: {base / 'origin.git'}")
    for n in names:
        print(f"  {n}: {base / n}  (git email {n}@example.com)")
    print("Open one Claude Code session per member folder, then follow docs/testing/team-mode-UAT.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
