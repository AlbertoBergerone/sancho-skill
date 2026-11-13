#!/usr/bin/env python3
"""Sancho repository self-test. Standard library only; runs offline.

  python -I tests/validate.py            run everything
  python -I tests/validate.py -k cve     run checks whose name contains "cve"

Checks: skill frontmatter and size, plugin manifests, agents/roles sync, commands,
schema sanity, schema fixtures (valid accepted, invalid rejected), every script
against its fixtures, the FieldLog example, evals coverage, and that every file
SKILL.md points to exists. Exit code 0 when all checks pass.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Callable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "sancho"
SCRIPTS = SKILL / "scripts"
FIX = ROOT / "tests" / "fixtures"
EXAMPLE = ROOT / "examples" / "fieldlog"
sys.path.insert(0, str(SCRIPTS))

from _schema import Validator, check_schema, load_schema, validate  # noqa: E402

CHECKS: List[Tuple[str, Callable[[], None]]] = []


def check(fn: Callable[[], None]) -> Callable[[], None]:
    CHECKS.append((fn.__name__, fn))
    return fn


def run(script: str, *args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *args], cwd=str(cwd),
                          capture_output=True, text=True, encoding="utf-8")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter(path: Path) -> Tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, f"{path}: missing YAML frontmatter"
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            meta[key.strip()] = value
    return meta, m.group(2)


# ---------------------------------------------------------------- skill & plugin

@check
def skill_frontmatter() -> None:
    meta, body = frontmatter(SKILL / "SKILL.md")
    name, desc = meta.get("name", ""), meta.get("description", "")
    assert name == "sancho", f"name is {name!r}"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64
    assert "claude" not in name and "anthropic" not in name
    assert 0 < len(desc) <= 1024, f"description length {len(desc)}"
    assert "<" not in desc and ">" not in desc, "angle brackets in description"
    lines = (SKILL / "SKILL.md").read_text(encoding="utf-8").count("\n")
    assert lines < 500, f"SKILL.md has {lines} lines (limit 500)"


@check
def skill_references_exist() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    refs = set(re.findall(r"`((?:references|roles|scripts|schemas|templates)/[A-Za-z0-9_./-]+)`", text))
    assert refs, "SKILL.md references no files"
    missing = sorted(r for r in refs if not (SKILL / r).exists())
    assert not missing, f"missing: {missing}"
    for md in (SKILL / "references").rglob("*.md"):
        for r in re.findall(r"`((?:references|roles|scripts|schemas|templates)/[A-Za-z0-9_./-]+)`", md.read_text(encoding="utf-8")):
            assert (SKILL / r).exists(), f"{md.relative_to(ROOT)} points to missing {r}"


@check
def plugin_manifests() -> None:
    plugin = load(ROOT / ".claude-plugin" / "plugin.json")
    assert plugin["name"] == "sancho"
    assert re.fullmatch(r"\d+\.\d+\.\d+", plugin["version"])
    market = load(ROOT / ".claude-plugin" / "marketplace.json")
    assert market["plugins"][0]["name"] == "sancho" and market["plugins"][0]["source"] == "./"
    assert market["owner"]["name"]
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"[{plugin['version']}]" in changelog, "plugin version missing from CHANGELOG"


@check
def agents_in_sync_with_roles() -> None:
    res = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "build.py"), "--check"],
                         cwd=str(ROOT), capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    roles = sorted(p.stem for p in (SKILL / "roles").glob("*.md"))
    assert len(roles) == 7, roles
    for role in roles:
        meta, body = frontmatter(SKILL / "roles" / f"{role}.md")
        assert meta.get("name") == role and meta.get("description"), role
        assert "MUST NOT" in body, f"{role}: no prohibitions section"


@check
def commands_present() -> None:
    expected = {"help", "status", "next", "checkpoint", "discover", "specify", "plan", "tasks",
                "implement", "verify", "release", "evolve"}
    found = {p.stem for p in (ROOT / "commands").glob("*.md")}
    assert expected <= found, f"missing commands: {sorted(expected - found)}"
    for p in (ROOT / "commands").glob("*.md"):
        meta, body = frontmatter(p)
        assert meta.get("description"), f"{p.name}: no description"
        assert "sancho" in body, f"{p.name}: does not route to the skill"


# ------------------------------------------------------------------------ schemas

@check
def schemas_are_sane() -> None:
    for p in sorted((SKILL / "schemas").glob("*.schema.json")):
        problems = check_schema(load(p))
        assert not problems, f"{p.name}: {problems}"


@check
def schema_fixtures() -> None:
    for d in sorted((FIX / "schemas").iterdir()):
        v = Validator(load_schema(d.name))
        valid = sorted(d.glob("valid*.json"))
        invalid = sorted(d.glob("invalid-*.json"))
        assert valid and len(invalid) >= 2, f"{d.name}: need 1 valid and 2 invalid fixtures"
        for f in valid:
            assert not v.errors(load(f)), f"{d.name}/{f.name} rejected: {v.errors(load(f))[:3]}"
        for f in invalid:
            assert v.errors(load(f)), f"{d.name}/{f.name} was accepted"


# ------------------------------------------------------------------------ scripts

@check
def coherence_script() -> None:
    good = run("coherence_check.py", str(FIX / "coherence/backlog-good.json"), "--uat", str(FIX / "coherence/uat-good.json"))
    assert good.returncode == 0, good.stdout
    bad = run("coherence_check.py", str(FIX / "coherence/backlog-bad.json"), "--json")
    assert bad.returncode == 1
    issues = json.loads(bad.stdout)["issues"]
    expected = load(FIX / "coherence/expected-bad.json")["codes"]
    for code, refs in expected.items():
        got = sorted(i["ref"] for i in issues if i["code"] == code)
        assert got == sorted(refs), f"{code}: expected {refs}, got {got}"
    spec = run("coherence_check.py", str(FIX / "coherence/backlog-good.json"), "--stage", "spec")
    assert spec.returncode == 0, "spec stage must not require tasks or UAT"


@check
def complexity_script() -> None:
    exp = load(FIX / "complexity/expected.json")
    res = run("complexity.py", str(FIX / "complexity/backlog.json"), "--threshold", str(exp["threshold"]), "--json")
    assert res.returncode == 0, res.stderr
    rows = {r["id"]: r for r in json.loads(res.stdout)["tasks"]}
    for tid, score in exp["scores"].items():
        assert rows[tid]["score"] == score, f"{tid}: {rows[tid]['score']} != {score}"
        assert rows[tid]["split"] == exp["split"][tid], f"{tid}: split {rows[tid]['split']}"
    again = run("complexity.py", str(FIX / "complexity/backlog.json"), "--threshold", "7", "--json")
    assert again.stdout == res.stdout, "output is not deterministic"
    strict = run("complexity.py", str(FIX / "complexity/backlog.json"), "--threshold", "7", "--strict")
    assert strict.returncode == 1


@check
def contrast_script() -> None:
    ok = run("contrast_check.py", str(FIX / "contrast/tokens-pass.json"), "--json")
    assert ok.returncode == 0, ok.stdout
    bad = run("contrast_check.py", str(FIX / "contrast/tokens-fail.json"), "--json")
    assert bad.returncode == 1
    pairs = json.loads(bad.stdout)["pairs"]
    assert all(not p["pass"] for p in pairs)
    black_white = json.loads(ok.stdout)["pairs"][0]["ratio"]
    assert 17.5 < black_white < 18.0, black_white
    import contrast_check as cc
    assert round(cc.ratio("#000000", "#ffffff"), 2) == 21.0
    assert round(cc.ratio("#767676", "#ffffff"), 2) == 4.54  # well-known AA boundary grey


@check
def uat_script() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        shutil.copy(FIX / "uat/uat.json", t / "uat.json")
        res = run("uat_export.py", str(t / "uat.json"), "--import-csv", str(FIX / "uat/results-it.csv"),
                  "--md", str(t / "UAT.md"), "--csv", str(t / "uat.csv"), "--lang", "it", "--delimiter", ";")
        assert res.returncode == 0, res.stderr
        doc = load(t / "uat.json")
        assert not validate(doc, "uat"), validate(doc, "uat")
        cases = {c["id"]: c for c in doc["cases"]}
        assert cases["UAT-001"]["result"] == "fail" and cases["UAT-001"]["defects"] == ["DEF-001"]
        assert cases["UAT-002"]["result"] == "pass" and cases["UAT-002"]["executed_by"] == "Danilo"
        md = (t / "UAT.md").read_text(encoding="utf-8")
        assert "[x] fallito" in md and "DEF-001" in md and "Precondizioni" in md
        rows = list(csv.reader((t / "uat.csv").read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
        assert rows[0][0] == "ID" and rows[0][9] == "Esito"
        # round trip: re-import the exported CSV keeps the results
        res2 = run("uat_export.py", str(t / "uat.json"), "--import-csv", str(t / "uat.csv"))
        assert res2.returncode == 0, res2.stderr
        assert load(t / "uat.json")["cases"][0]["result"] == "fail"


@check
def cve_enrich_replay() -> None:
    ins = [str(FIX / "cve/inputs" / n) for n in ("package-lock.json", "requirements.txt", "sbom.cdx.json")]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.json"
        res = run("cve_enrich.py", *ins, "--replay", str(FIX / "cve/responses"), "--out", str(out), "--md", str(Path(tmp) / "sca.md"))
        assert res.returncode == 0, res.stderr
        rep = load(out)
        assert not validate(rep, "security-report"), validate(rep, "security-report")
        assert rep["enrichment"] == {"osv": "run", "nvd": "run", "kev": "run", "epss": "run"}
        sev = {f["component"]["name"]: (f["severity"], f.get("cvss", {}).get("base_score")) for f in rep["findings"]}
        assert sev["org.apache.logging.log4j:log4j-core"] == ("blocker", 10.0), sev
        assert sev["lodash"] == ("major", 7.4), sev
        assert sev["requests"] == ("major", 7.5), sev
        assert "left-pad" not in sev
        assert any("flask" in x for x in rep["summary"]["not_run"]), "unpinned requirement not reported"
        assert rep["findings"][0]["kev"] is True


@check
def cve_enrich_offline() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.json"
        res = run("cve_enrich.py", str(FIX / "cve/inputs/package-lock.json"), "--offline", "--out", str(out), "--md", str(Path(tmp) / "sca.md"))
        assert res.returncode == 0, "offline must not be fatal"
        rep = load(out)
        assert not validate(rep, "security-report")
        assert rep["enrichment"]["osv"] == "not_run" and rep["findings"] == []
        assert any("NOT checked" in x for x in rep["summary"]["not_run"])
        assert "Unknown" in (Path(tmp) / "sca.md").read_text(encoding="utf-8")


@check
def cvss_calculator() -> None:
    import cve_enrich as ce
    cases = {
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H": 9.8,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H": 10.0,
        "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:H/A:H": 7.4,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N": 6.1,
        "CVSS:3.0/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N": 5.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N": 0.0,
    }
    for vec, score in cases.items():
        assert ce.cvss3_base_score(vec) == score, f"{vec}: {ce.cvss3_base_score(vec)} != {score}"
    assert ce.cvss3_base_score("CVSS:4.0/AV:N") is None
    assert ce.classify(5.0, 0.6, False, None)[0] == "blocker"
    assert ce.classify(None, None, False, "MODERATE")[0] == "minor"
    assert ce.classify(None, None, False, None)[0] == "minor"


@check
def state_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        assert "No Sancho project" in run("state.py", "next", cwd=t).stdout
        assert run("state.py", "init", "--name", "T", "--level", "L1", "--platforms", "web", "--language", "it", cwd=t).returncode == 0
        st = load(t / ".sancho/state.json")
        assert st["phases"]["plan"]["status"] == "skipped" and st["phases"]["plan"]["skip_reason"] == "level-default"
        assert run("state.py", "start", "specify", cwd=t).returncode == 1, "must not skip an open gate"
        items = [line.split(":")[0] for line in run("state.py", "checklist", "discover", cwd=t).stdout.splitlines()]
        assert run("state.py", "submit", "discover", "--results", items[0] + "=pass", "--coherence", "n/a", cwd=t).returncode == 1
        results = ",".join(f"{i}=pass" for i in items[:-1]) + f",{items[-1]}=fail"
        assert run("state.py", "submit", "discover", "--results", results, "--coherence", "n/a", cwd=t).returncode == 0
        assert run("state.py", "approve", "discover", cwd=t).returncode == 1, "approve with failures must be refused"
        assert run("state.py", "approve", "discover", "--override", "user accepts DIS-9 open", cwd=t).returncode == 0
        nxt = json.loads(run("state.py", "next", "--json", cwd=t).stdout)
        assert nxt["phase"] == "specify", nxt
        assert run("state.py", "skip", "verify", "--reason", "demo", "--adr", "docs/adr/0001.md", cwd=t).returncode == 1
        (t / "docs/adr").mkdir(parents=True)
        (t / "docs/adr/0001.md").write_text("# ADR\n", encoding="utf-8")
        assert run("state.py", "skip", "verify", "--reason", "demo", "--adr", "docs/adr/0001.md", cwd=t).returncode == 0
        assert run("state.py", "validate", cwd=t).returncode == 0
        status = run("state.py", "status", cwd=t).stdout
        assert "NEXT" in status and "level L1" in status


# ------------------------------------------------- regressions from the first review

@check
def cve_unknown_is_never_clean() -> None:
    """An SBOM whose components lack purls must not produce a 'no vulnerabilities' report."""
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "bom.json").write_text(json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.5", "components": [
            {"group": "org.apache.logging.log4j", "name": "log4j-core", "version": "2.14.1"}]}), encoding="utf-8")
        res = run("cve_enrich.py", str(t / "bom.json"), "--replay", str(FIX / "cve/responses"), "--out", str(t / "r.json"), "--md", str(t / "r.md"))
        assert res.returncode == 0, res.stderr
        rep = load(t / "r.json")
        assert rep["enrichment"]["osv"] == "not_run", rep["enrichment"]
        assert any("no purl" in x for x in rep["summary"]["not_run"])
        md = (t / "r.md").read_text(encoding="utf-8")
        assert "Unknown" in md and "No known vulnerabilities" not in md


@check
def cve_requirements_formats() -> None:
    import cve_enrich as ce
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "requirements.txt").write_text("requests==2.19.1 \\\n    --hash=sha256:aaa \\\n    --hash=sha256:bbb\n# c\nflask==2.0.1  # web\n", encoding="utf-8")
        pkgs, skipped = ce.read_requirements(t / "requirements.txt")
        assert [p["name"] for p in pkgs] == ["requests", "flask"] and not skipped, (pkgs, skipped)
        (t / "requirements-ps.txt").write_text("requests==2.19.1\r\n", encoding="utf-16")  # PowerShell 5.1 pip freeze
        pkgs, _ = ce.read_requirements(t / "requirements-ps.txt")
        assert pkgs and pkgs[0]["version"] == "2.19.1"


@check
def state_gate_rules() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        run("state.py", "init", "--name", "T", "--level", "L2", "--platforms", "Web,Android", cwd=t)
        assert load(t / ".sancho/state.json")["project"]["platforms"] == ["web", "android"]

        def close(phase: str, coherence: str, *extra: str) -> subprocess.CompletedProcess:
            items = [line.split(":")[0] for line in run("state.py", "checklist", phase, cwd=t).stdout.splitlines()]
            results = ",".join(f"{i}=pass" for i in items)
            run("state.py", "submit", phase, "--results", results, "--coherence", coherence, cwd=t)
            return run("state.py", "approve", phase, *extra, cwd=t)

        # n/a needs a note; notes may contain commas
        items = [line.split(":")[0] for line in run("state.py", "checklist", "discover", cwd=t).stdout.splitlines()]
        bad = ",".join(f"{i}=pass" for i in items[:-1]) + f",{items[-1]}=n/a"
        assert run("state.py", "submit", "discover", "--results", bad, "--coherence", "n/a", cwd=t).returncode != 0
        good = ",".join(f"{i}=pass" for i in items[:-1]) + f",{items[-1]}=n/a:no budget, no deadline"
        assert run("state.py", "submit", "discover", "--results", good, "--coherence", "n/a", cwd=t).returncode == 0
        assert run("state.py", "approve", "discover", cwd=t).returncode == 0
        # coherence not_run cannot pass a SPECIFY gate without override
        run("state.py", "start", "specify", cwd=t)
        assert close("specify", "not_run").returncode == 1
        assert run("state.py", "approve", "specify", "--override", "user accepts", cwd=t).returncode == 0
        # --reopen keeps phase order
        assert run("state.py", "start", "release", "--reopen", cwd=t).returncode == 1
        # level change applies level-default skips both ways
        assert run("state.py", "set-level", "L1", cwd=t).returncode == 0
        st = load(t / ".sancho/state.json")
        assert st["phases"]["plan"]["status"] == "skipped" and st["phases"]["plan"]["skip_reason"] == "level-default"
        assert json.loads(run("state.py", "next", "--json", cwd=t).stdout)["phase"] == "tasks"
        assert run("state.py", "set-level", "L2", cwd=t).returncode == 0
        assert load(t / ".sancho/state.json")["phases"]["plan"]["status"] == "not_started"
        # second iteration: close everything, then new-iteration reopens SPECIFY..EVOLVE
        assert run("state.py", "new-iteration", cwd=t).returncode == 1, "must refuse with open phases"
        for ph in ("plan", "tasks", "implement", "verify", "release", "evolve"):
            assert run("state.py", "start", ph, cwd=t).returncode == 0, ph
            assert close(ph, "pass" if ph != "evolve" else "n/a").returncode == 0, ph
        assert "All phases are closed" in run("state.py", "next", cwd=t).stdout
        assert run("state.py", "new-iteration", cwd=t).returncode == 0
        st = load(t / ".sancho/state.json")
        assert st["iteration"] == 2 and st["phases"]["discover"]["status"] == "approved"
        assert st["phases"]["specify"]["status"] == "not_started" and st["current_phase"] == "specify"
        # reopening an approved phase mid-project returns current_phase to the first open phase afterwards
        assert run("state.py", "start", "specify", cwd=t).returncode == 0
        out = close("specify", "pass").stdout
        assert "next phase is PLAN" in out, out


@check
def uat_import_robustness() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        shutil.copy(FIX / "uat/uat.json", t / "uat.json")
        csv_text = "ID;Esito;Eseguito da;Eseguito il;Note\nUAT-001;fallito;Danilo;28/10/2026;la pagina è bianca\nUAT-002;superato;Danilo;ieri;\n"
        (t / "res.csv").write_bytes(csv_text.encode("cp1252"))
        res = run("uat_export.py", str(t / "uat.json"), "--import-csv", str(t / "res.csv"))
        assert res.returncode == 0, res.stderr
        doc = load(t / "uat.json")
        assert not validate(doc, "uat"), validate(doc, "uat")
        cases = {c["id"]: c for c in doc["cases"]}
        assert cases["UAT-001"]["executed_at"].startswith("2026-10-28")
        assert "ieri" in cases["UAT-002"]["notes"]
        (t / "empty.csv").write_text("", encoding="utf-8")
        res = run("uat_export.py", str(t / "uat.json"), "--import-csv", str(t / "empty.csv"))
        assert res.returncode == 2 and "empty" in res.stderr


@check
def contrast_no_rounding_and_duplicates() -> None:
    import coherence_check as cc
    import contrast_check as ct
    doc = {"color": {"fg": "#008676", "bg": "#ffffff"}, "contrast_pairs": [{"fg": "color.fg", "bg": "color.bg", "usage": "text"}]}
    row = ct.check(doc)[0]
    assert row["ratio"] == 4.5 and row["pass"] is False, row  # 4.495:1 must fail even though it displays as 4.50
    backlog = load(FIX / "coherence/backlog-good.json")
    backlog["tasks"].append(dict(backlog["tasks"][0]))
    codes = [(i["code"], i["ref"]) for i in cc.check(backlog, load(FIX / "coherence/uat-good.json"))]
    assert ("C0", "T-001") in codes, codes


# ------------------------------------------------------------------------ example

@check
def example_fieldlog() -> None:
    sd = EXAMPLE / ".sancho"
    for name, path in (("state", sd / "state.json"), ("backlog", sd / "backlog.json"), ("uat", sd / "uat.json"),
                       ("security-report", EXAMPLE / "docs/security/security-report.json")):
        errors = validate(load(path), name)
        assert not errors, f"{path.relative_to(ROOT)}: {errors[:3]}"
    handoffs = sorted((sd / "handoffs").glob("*.json"))
    assert handoffs, "example has no handoff"
    for h in handoffs:
        assert not validate(load(h), "handoff"), f"{h.name}: {validate(load(h), 'handoff')[:3]}"
    res = run("coherence_check.py", str(sd / "backlog.json"), "--uat", str(sd / "uat.json"))
    assert res.returncode == 0, res.stdout
    res = run("contrast_check.py", str(EXAMPLE / "design/tokens.json"))
    assert res.returncode == 0, res.stdout
    adrs = sorted((EXAMPLE / "docs/adr").glob("*.md"))
    assert len(adrs) >= 2, adrs
    for f in ("Dockerfile", "docker-compose.yml", "docs/constitution.md", "docs/spec.md", "docs/plan.md",
              "docs/uat/UAT.md", "docs/uat/uat.csv", "docs/security/SECURITY-REPORT.md", "design/logo.svg"):
        assert (EXAMPLE / f).is_file(), f"missing example file {f}"
    docker = (EXAMPLE / "Dockerfile").read_text(encoding="utf-8")
    assert "USER " in docker and "HEALTHCHECK" in docker and "@sha256:" in docker, "Dockerfile misses hardening"


# ------------------------------------------------- regressions from user testing

@check
def status_counts_only_open_security_findings() -> None:
    # status must count unresolved findings (open, not_verified), not the report summary,
    # which also counts fixed / accepted / false-positive findings.
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp) / "fieldlog"
        shutil.copytree(EXAMPLE, t)
        data = json.loads(run("state.py", "status", "--json", cwd=t).stdout)
        sec = data["security"]
        assert (sec["blocker"], sec["major"], sec["minor"], sec["nit"]) == (0, 1, 1, 0), sec
        assert sec["closed"] == {"fixed": 1}, sec
        assert len(sec["not_run"]) == 1, sec
        text = run("state.py", "status", cwd=t).stdout
        assert "security (open): blocker 0, major 1, minor 1, nit 0" in text, text
        assert "closed: fixed 1" in text and "NOT RUN: 1" in text, text
        rp = t / "docs/security/security-report.json"
        rep = load(rp)
        for f in rep["findings"]:
            if f["id"] == "F-003":
                f["status"], f["accepted_by"] = "accepted_risk", "user"
            if f["id"] == "F-001":
                f["status"] = "not_verified"
        rp.write_text(json.dumps(rep, indent=2), encoding="utf-8")
        assert run("state.py", "validate", cwd=t).returncode == 0
        sec = json.loads(run("state.py", "status", "--json", cwd=t).stdout)["security"]
        assert (sec["major"], sec["minor"]) == (1, 0), sec
        assert sec["closed"] == {"accepted_risk": 1, "fixed": 1}, sec


@check
def status_lists_unverified_security_blockers() -> None:
    # a blocker finding still not_verified is unresolved: it must appear among the BLOCKER lines.
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp) / "fieldlog"
        shutil.copytree(EXAMPLE, t)
        rp = t / "docs/security/security-report.json"
        rep = load(rp)
        for f in rep["findings"]:
            if f["id"] == "F-001":
                f["severity"], f["status"] = "blocker", "not_verified"
        rp.write_text(json.dumps(rep, indent=2), encoding="utf-8")
        data = json.loads(run("state.py", "status", "--json", cwd=t).stdout)
        assert any(b.startswith("security F-001") for b in data["blockers"]), data["blockers"]
        assert "BLOCKER: security F-001" in run("state.py", "status", cwd=t).stdout


@check
def status_reports_invalid_files() -> None:
    # an invalid project file must never look like a complete status: name it, omit its counts, exit 1.
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp) / "fieldlog"
        shutil.copytree(EXAMPLE, t)
        clean = run("state.py", "status", cwd=t)
        assert clean.returncode == 0 and "INVALID" not in clean.stdout, clean.stdout
        assert json.loads(run("state.py", "status", "--json", cwd=t).stdout)["invalid_files"] == []
        up = t / ".sancho/uat.json"
        original = up.read_text(encoding="utf-8")

        rep = json.loads(original)
        del rep["cases"]
        up.write_text(json.dumps(rep), encoding="utf-8")
        r = run("state.py", "status", cwd=t)
        assert r.returncode == 1, r.returncode
        assert "INVALID" in r.stdout and "uat.json" in r.stdout and "missing required 'cases'" in r.stdout, r.stdout
        assert "UAT:" not in r.stdout and "open defects" not in r.stdout, r.stdout
        assert "Fix DEF-001" not in r.stdout and "state.py validate" in r.stdout, r.stdout
        r = run("state.py", "status", "--json", cwd=t)
        assert r.returncode == 1, r.returncode
        data = json.loads(r.stdout)
        assert [f["name"] for f in data["invalid_files"]] == ["uat"], data["invalid_files"]
        assert "uat.json" in run("state.py", "next", cwd=t).stdout

        # a shape the counters would trip on, and a file that is not JSON at all: no traceback
        rep = json.loads(original)
        del rep["cases"][0]["result"]
        up.write_text(json.dumps(rep), encoding="utf-8")
        r = run("state.py", "status", cwd=t)
        assert r.returncode == 1 and "Traceback" not in r.stderr and "INVALID" in r.stdout, r.stderr
        up.write_text("{ not json", encoding="utf-8")
        r = run("state.py", "status", cwd=t)
        assert r.returncode == 1 and "Traceback" not in r.stderr and "INVALID" in r.stdout, r.stderr
        r = run("state.py", "validate", cwd=t)
        assert r.returncode == 1 and "Traceback" not in r.stderr and "FAIL uat" in r.stdout, r.stderr
        up.write_text(original, encoding="utf-8")

        (t / ".sancho/state.json").write_text("{ not json", encoding="utf-8")
        r = run("state.py", "status", cwd=t)
        assert r.returncode != 0 and "Traceback" not in r.stderr and "state.json" in r.stderr, r.stderr
    cmds = (SKILL / "references/commands.md").read_text(encoding="utf-8")
    assert "INVALID" in cmds, "commands.md does not say how to relay an INVALID line"


@check
def cve_aliases_are_one_finding() -> None:
    # OSV lists one issue under several ids (GHSA, PYSEC): one finding per package and issue, not one per advisory.
    import cve_enrich as ce
    cvss = [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"}]
    vulns = {
        "GHSA-aaaa": {"summary": "A", "aliases": ["CVE-2018-18074", "PYSEC-1"], "severity": cvss},
        "PYSEC-1": {"summary": "A again", "aliases": ["CVE-2018-18074", "GHSA-aaaa"]},
        "GHSA-bbbb": {"summary": "B", "aliases": ["CVE-2023-32681"]},
        "GHSA-cccc": {"summary": "C", "aliases": ["PYSEC-2"]},
        "PYSEC-2": {"summary": "C again"},
    }

    class Stub:
        mode = "replay"

        def get_json(self, kind, ident, url, body=None, headers=None):
            if kind == "osv-batch":
                return {"results": [{"vulns": [{"id": "GHSA-aaaa"}]},
                                    {"vulns": [{"id": v} for v in vulns]}]}
            if kind == "osv-vuln":
                return vulns[ident]
            return {"vulnerabilities": []} if kind == "kev" else {"data": []}

    with tempfile.TemporaryDirectory() as tmp:
        req = Path(tmp) / "requirements.txt"
        req.write_text("flask==1.0\nrequests==2.19.0\n", encoding="utf-8")
        rep = ce.enrich([req], Stub(), use_nvd=False)
    assert not validate(rep, "security-report"), validate(rep, "security-report")
    found = sorted((f["component"]["name"], f["advisory"]) for f in rep["findings"])
    assert found == [("flask", "GHSA-aaaa"), ("requests", "GHSA-aaaa"), ("requests", "GHSA-bbbb"), ("requests", "GHSA-cccc")], found
    merged = next(f for f in rep["findings"] if f["component"]["name"] == "requests" and f["advisory"] == "GHSA-aaaa")
    assert "cvss" in merged and "PYSEC-1" in merged["severity_rationale"], merged
    assert sum(rep["summary"][k] for k in ("blocker", "major", "minor", "nit")) == 4, rep["summary"]


@check
def cve_missing_input_is_reported() -> None:
    # a project with no lockfile must get a report that says so, not just an error and no file.
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        res = run("cve_enrich.py", str(t / "requirements.txt"), "--offline", "--out", str(t / "r.json"), "--md", str(t / "r.md"))
        assert res.returncode == 2, "a missing input must still be flagged by the exit code"
        rep = load(t / "r.json")
        assert not validate(rep, "security-report")
        assert rep["enrichment"]["osv"] == "not_run" and rep["findings"] == [], rep
        assert any("requirements.txt" in x and "not found" in x for x in rep["summary"]["not_run"]), rep["summary"]
        assert "Unknown" in (t / "r.md").read_text(encoding="utf-8")


@check
def start_keeps_the_original_start_date() -> None:
    # every phase command runs `start`: on a phase already in progress it must not move started_at.
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp) / "fieldlog"
        shutil.copytree(EXAMPLE, t)
        before = load(t / ".sancho/state.json")["phases"]["verify"]["started_at"]
        assert run("state.py", "start", "verify", cwd=t).returncode == 0
        assert load(t / ".sancho/state.json")["phases"]["verify"]["started_at"] == before


@check
def next_after_reject_names_the_concrete_step() -> None:
    # a rejected gate keeps the concrete work: "rework" alone does not tell anyone what to do.
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp) / "fieldlog"
        shutil.copytree(EXAMPLE, t)
        items = [i["id"] for i in load(SCRIPTS / "gates.json")["phases"]["verify"]]
        res = run("state.py", "submit", "verify", "--results", ",".join(f"{i}=fail:open" for i in items),
                  "--coherence", "pass", cwd=t)
        assert res.returncode == 0, res.stderr
        assert run("state.py", "reject", "verify", "--reason", "UAT-004 not run", cwd=t).returncode == 0
        nxt = json.loads(run("state.py", "next", "--json", cwd=t).stdout)
        assert nxt["who"] == "developer" and "UAT-004 not run" in nxt["action"], nxt
        assert "Fix DEF-001" in nxt["action"] and "resubmit" in nxt["action"], nxt


@check
def references_cover_eval_gaps() -> None:
    # gaps found by running tests/evals.json; each rule lives in a reference, not in a script.
    uat = (SKILL / "references/uat.md").read_text(encoding="utf-8")
    tester = uat[uat.index("## For the tester"):]
    assert "spreadsheet" in tester and "chat" in tester, "help uat must name both ways of running UAT"
    discover = (SKILL / "references/phases/00-discover.md").read_text(encoding="utf-8")
    assert "at most three questions" in discover, "00-discover.md must cap L0 at three questions"
    cmds = (SKILL / "references/commands.md").read_text(encoding="utf-8")
    assert "both where things stand and what to do" in cmds, "commands.md misses the combined question rule"
    assert "core files" in cmds, "commands.md must say which files status checks"
    assert "already describes a project" in cmds, "commands.md must say when the tour is not shown"
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "already describes a project" in skill, "SKILL.md must say when the tour is not shown"
    for name, text in (("SKILL.md", skill), ("commands.md", cmds)):
        assert "language of the user's latest message" in text, f"{name} must let the user's language win"
        assert "language of the conversation so far" in text, f"{name}: a bare command must not switch language"
    assert "default to the language the user writes in" not in skill, "settings.language must not beat the user"
    assert "project language" in skill, "SKILL.md must name the exception for tester-facing text"
    assert "project language (`settings.language`)" in uat, "uat.md must say which language UAT cases are written in"
    tasks = (SKILL / "references/phases/03-tasks.md").read_text(encoding="utf-8")
    assert "--lang <lang>" not in tasks and "--lang <it|en|es>" not in uat, "the UAT export must default to the project language"


@check
def status_relay_rules() -> None:
    # findings 12-14 from the user's runs on 2026-11-09: the relay drifted, the tour replaced "no project", new UAT cases copied old cases' language.
    cmds = (SKILL / "references/commands.md").read_text(encoding="utf-8")
    status = cmds[cmds.index("## status"):]
    status = status[:status.index("\n## ", 1)]
    assert "only the output of `scripts/state.py status`" in status, "status must relay the script, not read other files"
    assert "exactly one NEXT line" in status, "status must always end with one NEXT line"
    assert "same layout every time" in status, "status must keep one layout"
    assert "no Sancho project in this folder" in status, "status with no project must not show the tour"
    # finding 12 reopened: words alone did not hold in the app; status now has a template to copy.
    assert "Copy this template" in status, "status must give a template to copy"
    tpl = status[status.index("Copy this template"):]
    tpl = tpl[tpl.index("```"):tpl.index("```", tpl.index("```") + 3)]
    assert "Blockers: none" in tpl and tpl.rstrip().splitlines()[-1].startswith("Next ("), "template must end with Blockers then one Next line"
    assert "never promote" in status, "a major must not be shown as a blocker"
    assert "on the NEXT line itself" in status, "the offer to start must not add a line after NEXT"
    first = cmds[cmds.index("## First run"):cmds.index("## First run") + 600]
    assert "never for `status`" in first, "the tour must not answer status"
    uat = (SKILL / "references/uat.md").read_text(encoding="utf-8")
    assert "even when the existing cases are in another language" in uat, "new UAT cases must not copy old cases' language"


@check
def production_testing_needs_window() -> None:
    # decision of 2026-11-09: active tests on the user's own production only with a recorded approval and an agreed window.
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        assert run("state.py", "init", "--name", "T", "--level", "L2", "--platforms", "web", cwd=t).returncode == 0
        win = "2026-11-10T22:00:00+01:00/2026-11-10T23:00:00+01:00"
        r = run("state.py", "approval", "--action", "ZAP full active scan", "--scope", "https://app.example.com (production)", "--window", win, cwd=t)
        assert r.returncode == 0, r.stderr
        assert load(t / ".sancho/state.json")["approvals"][-1]["window"] == win
        assert run("state.py", "validate", cwd=t).returncode == 0
        assert run("state.py", "approval", "--action", "a", "--scope", "s", "--window", "tonight", cwd=t).returncode != 0
        backwards = "2026-11-10T23:00:00+01:00/2026-11-10T22:00:00+01:00"
        assert run("state.py", "approval", "--action", "a", "--scope", "s", "--window", backwards, cwd=t).returncode != 0
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    role = (SKILL / "roles/security.md").read_text(encoding="utf-8")
    ref = (SKILL / "references/security.md").read_text(encoding="utf-8")
    for name, text in (("SKILL.md", skill), ("roles/security.md", role), ("references/security.md", ref)):
        assert "agreed time window" in text, f"{name} must allow production only with an agreed window"
        assert "never production" not in text and "Refuse third-party and production" not in text, f"{name} still forbids production"
    assert "--window" in ref, "references/security.md must show how to record the window"


@check
def next_puts_blockers_first() -> None:
    # seen 2026-11-10: with F-001 raised to blocker, next still named DEF-001 (major).
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp) / "fieldlog"
        shutil.copytree(EXAMPLE, t)
        rep = t / "docs/security/security-report.json"
        data = load(rep)
        for f in data["findings"]:
            if f["id"] == "F-001":
                f["severity"] = "blocker"
        rep.write_text(json.dumps(data, indent=2), encoding="utf-8")
        nxt = json.loads(run("state.py", "next", "--json", cwd=t).stdout)
        assert "security F-001" in nxt["action"], f"a security blocker must come before a major defect: {nxt}"
        uat_path = t / ".sancho/uat.json"
        uat = load(uat_path)
        uat["defects"].append({"id": "DEF-099", "uat": uat["defects"][0]["uat"], "severity": "blocker",
                               "description": "App crashes on start", "steps_to_reproduce": "open the app", "status": "open"})
        uat_path.write_text(json.dumps(uat, indent=2), encoding="utf-8")
        assert run("state.py", "validate", cwd=t).returncode == 0
        nxt = json.loads(run("state.py", "next", "--json", cwd=t).stdout)
        assert "DEF-099" in nxt["action"], f"a blocker defect listed after a major must come first: {nxt}"


@check
def assess_command_wired() -> None:
    # added 2026-11-10 after two real analyses were done outside any Sancho procedure.
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "| `assess" in skill and "references/assess.md" in skill, "SKILL.md must route assess"
    ref = (SKILL / "references/assess.md").read_text(encoding="utf-8")
    for needle in ("blocker", "VERIFIED", "NOT RUN", "cve_enrich.py", "templates/assessment.md", "read-only", "secrets",
                   "--no-nvd", "working tree", "names only", "real database", "one row per package"):
        assert needle in ref, f"references/assess.md misses {needle!r}"
    tpl = (SKILL / "templates/assessment.md").read_text(encoding="utf-8")
    assert tpl.index("Act first") < tpl.index("Strengths"), "urgent findings must come before the rest"
    assert tpl.index("Act first") < tpl.index("Answer") < tpl.index("The project in brief"), "the answer must come right after Act first"
    assert "| VERIFIED" not in tpl, "the template must not pre-fill an evidence label"
    assert (ROOT / "commands/assess.md").is_file(), "plugin command missing"
    assert "assess" in (SKILL / "references/commands.md").read_text(encoding="utf-8").split("## help")[0]
    for f in ("README.md", "README.it.md", "README.es.md", "docs/guide.en.md", "docs/guide.it.md", "docs/guide.es.md"):
        assert "sancho:assess" in (ROOT / f).read_text(encoding="utf-8"), f"{f} misses assess"
    assert any("assess" in e.get("tags", []) for e in load(ROOT / "tests/evals.json")["evals"]), "no eval for assess"


@check
def invocation_forms_documented() -> None:
    # Claude Code plugin uses /sancho:<command>; the Claude apps (and skill-only installs) use /sancho <command>.
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("/sancho:<command>", "/sancho <command>", "leading colon"):
        assert needle in skill, f"SKILL.md misses {needle!r}"
    cmds = (SKILL / "references/commands.md").read_text(encoding="utf-8")
    assert "/sancho:status" in cmds and "/sancho status" in cmds, "commands.md misses one invocation form"
    for lang in ("en", "it", "es"):
        guide = (ROOT / f"docs/guide.{lang}.md").read_text(encoding="utf-8")
        assert "/sancho:status" in guide and "/sancho status" in guide, f"guide.{lang}.md misses one form"
        assert "<!-- invocation-forms -->" in guide, f"guide.{lang}.md misses the invocation note"


# ----------------------------------------------------------------------- team mode

def run_as(member: str, script: str, *args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = {**__import__("os").environ, "SANCHO_USER": member}
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *args], cwd=str(cwd),
                          capture_output=True, text=True, encoding="utf-8", env=env)


def git_in(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    p = subprocess.run(["git", "-c", "init.defaultBranch=main", "-c", "core.autocrlf=false", *args], cwd=str(cwd),
                       capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, f"git {' '.join(args)}: {p.stdout}{p.stderr}"
    return p


TEAM = [("luca", "Luca", "developer"), ("sara", "Sara", "developer"), ("danilo", "Danilo", "developer,qa")]


def team_project(t: Path, team: bool = True) -> None:
    """A project in IMPLEMENT with four tasks: T-003 depends on T-001, T-004 is planned for sara."""
    assert run("state.py", "init", "--name", "Team", "--level", "L1", "--platforms", "web", cwd=t).returncode == 0
    st = load(t / ".sancho/state.json")
    for ph in ("discover", "specify", "tasks"):
        st["phases"][ph] = {"status": "skipped", "skip_reason": "level-default"}
    st["phases"]["implement"].update({"status": "in_progress", "started_at": st["created_at"]})
    st["current_phase"] = "implement"
    (t / ".sancho/state.json").write_text(json.dumps(st, indent=2), encoding="utf-8")

    def task(tid: str, deps=(), **extra) -> dict:
        return {"id": tid, "story": "S-001", "title": f"work {tid}", "owner": "developer", "status": "pending",
                "depends_on": list(deps), "complexity": {"score": 3}, **extra}
    backlog = {"protocol": "sancho/1.0",
               "requirements": [{"id": "R-001", "kind": "functional", "statement": "x", "priority": "must", "source": "user"}],
               "stories": [{"id": "S-001", "title": "s", "as_a": "a", "i_want": "b", "so_that": "c", "requirements": ["R-001"],
                            "priority": "must", "context": "self-contained context for the team tests",
                            "acceptance_criteria": [{"id": "AC-001.1", "description": "d", "verification": {"method": "review"},
                                                     "status": "not_verified"}]}],
               "tasks": [task("T-001"), task("T-002"), task("T-003", ["T-001"]), task("T-004", assignee="sara")]}
    (t / ".sancho/backlog.json").write_text(json.dumps(backlog, indent=2), encoding="utf-8")
    if team:
        for mid, name, roles in TEAM:
            extra = ["--coordinator"] if mid == "danilo" else []
            r = run("state.py", "team", "add", "--id", mid, "--name", name, "--email", f"{mid}@example.com", "--roles", roles, *extra, cwd=t)
            assert r.returncode == 0, r.stderr
    assert run("state.py", "validate", cwd=t).returncode == 0, run("state.py", "validate", cwd=t).stdout


def tasks_of(cwd: Path, member: str = "danilo") -> dict:
    out = json.loads(run_as(member, "state.py", "status", "--json", cwd=cwd).stdout)
    return out


@check
def team_merges_without_conflicts() -> None:
    # three people, four clones (luca works from two computers), merged in turn: no conflict, same state everywhere
    assert shutil.which("git"), "git is needed for the team mode checks"
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        git_in(base, "init", "--bare", "origin.git")
        seed = base / "seed"
        seed.mkdir()
        git_in(seed, "init")
        team_project(seed)
        assert ".sancho/log/*.jsonl merge=union" in (seed / ".gitattributes").read_text(encoding="utf-8")
        git_in(seed, "add", "-A")
        git_in(seed, "-c", "user.name=seed", "-c", "user.email=seed@example.com", "commit", "-m", "seed")
        git_in(seed, "push", str(base / "origin.git"), "HEAD:main")
        clones = {}
        for name, member in (("a", "luca"), ("a2", "luca"), ("b", "sara"), ("c", "danilo")):
            git_in(base, "clone", "-b", "main", str(base / "origin.git"), name)
            git_in(base / name, "config", "user.email", f"{member}@example.com")
            git_in(base / name, "config", "user.name", member)
            clones[name] = (base / name, member)

        def act(name: str, *args: str) -> None:
            cwd, member = clones[name]
            r = run_as(member, "state.py", *args, cwd=cwd)
            assert r.returncode == 0, f"{member}: {' '.join(args)}: {r.stdout}{r.stderr}"

        def sync(name: str, msg: str) -> None:
            cwd, _ = clones[name]
            git_in(cwd, "add", "-A")
            git_in(cwd, "commit", "-m", msg)
            git_in(cwd, "pull", "--no-rebase", "--no-edit", "origin", "main")
            assert not git_in(cwd, "diff", "--name-only", "--diff-filter=U").stdout.strip(), f"conflict in {name}"
            git_in(cwd, "push", "origin", "HEAD:main")

        act("a", "claim", "T-001")
        act("a", "task", "T-001", "--status", "ready_for_review", "--evidence", "commit:abcdef1")
        act("a2", "claim", "T-004")          # same member, other computer: both append to luca.jsonl
        act("b", "claim", "T-002")
        sync("a", "luca: T-001 ready")
        sync("a2", "luca: T-004")            # union merge of luca.jsonl
        sync("b", "sara: T-002")
        git_in(clones["c"][0], "pull", "--no-rebase", "--no-edit", "origin", "main")
        act("c", "review", "T-001", "--approve", "--evidence", "test:pytest tests/test_t001.py")
        sync("c", "danilo: review T-001")
        states = []
        for name in ("a", "a2", "b", "c"):
            git_in(clones[name][0], "pull", "--no-rebase", "--no-edit", "origin", "main")
            s = tasks_of(clones[name][0])
            states.append((s["tasks"], s["team"]["claims"]))
        assert all(x == states[0] for x in states), states
        tasks, claims = states[0]
        assert tasks == {"completed": 1, "in_progress": 2, "pending": 1}, tasks
        assert {k: v["by"] for k, v in claims.items()} == {"T-002": "sara", "T-004": "luca"}, claims
        assert len((clones["a"][0] / ".sancho/log/luca.jsonl").read_text(encoding="utf-8").splitlines()) == 3
        nxt = json.loads(run_as("danilo", "state.py", "next", "--json", cwd=clones["c"][0]).stdout)
        assert "T-003" in nxt["action"] and nxt["mine"], nxt   # T-001 done, so T-003 is ready and free
        nxt = json.loads(run_as("luca", "state.py", "next", "--json", cwd=clones["a"][0]).stdout)
        assert "Continue T-004" in nxt["action"], nxt


@check
def team_contested_claim() -> None:
    import time
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        git_in(base, "init", "--bare", "origin.git")
        seed = base / "seed"
        seed.mkdir()
        git_in(seed, "init")
        team_project(seed)
        git_in(seed, "add", "-A")
        git_in(seed, "-c", "user.name=seed", "-c", "user.email=seed@example.com", "commit", "-m", "seed")
        git_in(seed, "push", str(base / "origin.git"), "HEAD:main")
        for name in ("a", "b"):
            git_in(base, "clone", "-b", "main", str(base / "origin.git"), name)
            git_in(base / name, "config", "user.email", f"{name}@example.com")
            git_in(base / name, "config", "user.name", name)
        a, b = base / "a", base / "b"
        assert run_as("luca", "state.py", "claim", "T-001", cwd=a).returncode == 0
        time.sleep(1.2)
        assert run_as("sara", "state.py", "claim", "T-001", cwd=b).returncode == 0   # not seen yet
        for cwd in (a, b):
            git_in(cwd, "add", "-A")
            git_in(cwd, "commit", "-m", "claim")
            git_in(cwd, "pull", "--no-rebase", "--no-edit", "origin", "main")
            git_in(cwd, "push", "origin", "HEAD:main")
        s = tasks_of(b, "sara")
        assert s["team"]["claims"]["T-001"]["by"] == "luca", s["team"]
        assert [(c["item"], c["lost"], c["won"]) for c in s["team"]["conflicts"]] == [("T-001", "sara", "luca")]
        nxt = json.loads(run_as("sara", "state.py", "next", "--json", cwd=b).stdout)
        assert "already claimed by luca" in nxt["action"], nxt
        assert "CONFLICT: T-001" in run_as("sara", "state.py", "next", "--team", cwd=b).stdout
        assert run_as("sara", "state.py", "claim", "T-001", cwd=b).returncode == 1, "a visible claim must be refused"
        assert run_as("sara", "state.py", "task", "T-001", "--status", "blocked", "--reason", "x", cwd=b).returncode == 1
        assert run_as("sara", "state.py", "release", "T-001", cwd=b).returncode == 0
        s = tasks_of(b, "sara")
        assert not s["team"]["conflicts"] and s["team"]["claims"]["T-001"]["by"] == "luca", s["team"]
        nxt = json.loads(run_as("sara", "state.py", "next", "--json", cwd=b).stdout)
        assert "T-004" in nxt["action"], f"the task planned for sara comes first: {nxt}"


@check
def team_four_eyes_and_review() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        team_project(t)
        assert run_as("danilo", "state.py", "claim", "T-001", cwd=t).returncode == 0
        assert run_as("danilo", "state.py", "task", "T-001", "--status", "ready_for_review", cwd=t).returncode == 2, "evidence required"
        assert run_as("danilo", "state.py", "task", "T-001", "--status", "completed", "--evidence", "commit:abcdef1", cwd=t).returncode == 1
        assert run_as("danilo", "state.py", "task", "T-001", "--status", "ready_for_review", "--evidence", "commit:abcdef1", cwd=t).returncode == 0
        r = run_as("danilo", "state.py", "review", "T-001", "--approve", "--evidence", "test:pytest", cwd=t)
        assert r.returncode == 1 and "four eyes" in r.stderr, r.stderr
        assert run_as("luca", "state.py", "review", "T-001", "--changes", "x", cwd=t).returncode == 1, "luca has no qa role"
        r = run("state.py", "team", "add", "--id", "luca", "--name", "Luca", "--email", "luca@example.com", "--roles", "developer,qa", cwd=t)
        assert r.returncode == 0
        nxt = json.loads(run_as("luca", "state.py", "next", "--json", cwd=t).stdout)
        assert nxt["action"].startswith("Review T-001"), nxt
        assert run_as("luca", "state.py", "review", "T-001", "--changes", "missing test for the error path", cwd=t).returncode == 0
        nxt = json.loads(run_as("danilo", "state.py", "next", "--json", cwd=t).stdout)
        assert "Continue T-001" in nxt["action"] and "missing test" in nxt["action"], nxt
        run_as("danilo", "state.py", "task", "T-001", "--status", "ready_for_review", "--evidence", "commit:abcdef2", cwd=t)
        assert run_as("luca", "state.py", "review", "T-001", "--approve", "--evidence", "test:pytest -k error", cwd=t).returncode == 0
        s = tasks_of(t)
        assert s["tasks"].get("completed") == 1 and "T-001" not in s["team"]["claims"], s
        assert run("state.py", "validate", cwd=t).returncode == 0
        # a log written in someone else's name is refused, and reported
        with open(t / ".sancho/log/sara.jsonl", "a", encoding="utf-8") as fh:
            fh.write('{"at":"2026-11-13T10:00:00+01:00","by":"luca","event":"release","task":"T-002"}\n')
        v = run("state.py", "validate", cwd=t)
        assert v.returncode == 1 and "each member writes only their own log" in v.stdout, v.stdout
        assert "Repair .sancho/log/sara.jsonl" in json.loads(run_as("luca", "state.py", "next", "--json", cwd=t).stdout)["action"]
        assert run("state.py", "whoami", cwd=t).returncode in (0, 1)


@check
def solo_mode_unchanged_with_task_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        team_project(t, team=False)
        assert not (t / ".sancho/team.json").exists()
        assert run("state.py", "claim", "T-001", cwd=t).returncode == 1, "claim is for team mode"
        assert run("state.py", "task", "T-001", "--status", "in_progress", cwd=t).returncode == 0
        assert run("state.py", "task", "T-001", "--status", "ready_for_review", cwd=t).returncode == 2
        assert run("state.py", "task", "T-001", "--status", "completed", "--evidence", "commit:abcdef1", cwd=t).returncode == 0
        bl = load(t / ".sancho/backlog.json")
        assert bl["tasks"][0]["status"] == "completed" and bl["tasks"][0]["evidence"] == [{"type": "commit", "commit": "abcdef1"}]
        nxt = json.loads(run("state.py", "next", "--json", cwd=t).stdout)
        assert nxt["who"] == "developer" and "T-002" in nxt["action"] and "member" not in nxt, nxt
        assert "team" not in json.loads(run("state.py", "status", "--json", cwd=t).stdout)
        # uat and defect without a team write uat.json directly, validated
        (t / ".sancho/uat.json").write_text(json.dumps(uat_cases()), encoding="utf-8")
        r = run("state.py", "uat", "UAT-001", "--result", "fail", "--new-defect", "major:error text reveals the account", "--tester", "Ana", cwd=t)
        assert r.returncode == 0, r.stderr
        ua = load(t / ".sancho/uat.json")
        assert ua["cases"][0]["defects"] == ["DEF-001"] and ua["cases"][0]["executed_by"] == "Ana", ua["cases"][0]
        assert run("state.py", "defect", "DEF-001", "--status", "fixed", "--task", "T-002", cwd=t).returncode == 0
        assert load(t / ".sancho/uat.json")["defects"][0]["status"] == "fixed"
        assert run("state.py", "validate", cwd=t).returncode == 0


def uat_cases() -> dict:
    def case(cid: str) -> dict:
        return {"id": cid, "story": "S-001", "criteria": ["AC-001.1"], "title": f"check {cid}", "platform": "web (Chrome)",
                "preconditions": [], "steps": [{"n": 1, "action": "do it"}], "expected_result": "it works", "result": "not_tested"}
    return {"protocol": "sancho/1.0", "cases": [case("UAT-001"), case("UAT-002"), case("UAT-003")], "defects": []}


def set_team(t: Path, **fields) -> None:
    team = load(t / ".sancho/team.json")
    team.update(fields)
    (t / ".sancho/team.json").write_text(json.dumps(team, indent=2), encoding="utf-8")


def to_phase(t: Path, phase: str) -> None:
    st = load(t / ".sancho/state.json")
    for ph in ("implement", "verify"):
        if ph != phase:
            st["phases"][ph] = {"status": "skipped", "skip_reason": "level-default"} if ph == "implement" else {"status": "not_started"}
    st["phases"][phase] = {"status": "in_progress", "lead": "qa" if phase == "verify" else "developer", "started_at": st["created_at"]}
    st["current_phase"] = phase
    (t / ".sancho/state.json").write_text(json.dumps(st, indent=2), encoding="utf-8")


def log_event(t: Path, ev: dict) -> None:
    with open(t / f".sancho/log/{ev['by']}.jsonl", "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(ev) + "\n")


@check
def team_gate_quorum() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        team_project(t)
        set_team(t, approvers={"default": ["danilo", "luca"]}, quorum={"implement": 2})
        items = ",".join(f"{line.split(':')[0]}=pass" for line in run("state.py", "checklist", "implement", cwd=t).stdout.splitlines())
        assert run_as("luca", "state.py", "submit", "implement", "--results", items, "--coherence", "pass", cwd=t).returncode == 1, "coordinator only"
        r = run_as("danilo", "state.py", "submit", "implement", "--results", items, "--coherence", "pass", cwd=t)
        assert r.returncode == 0 and "danilo, luca (2 needed)" in r.stdout, r.stdout
        assert run_as("sara", "state.py", "approve", "implement", cwd=t).returncode == 1, "sara is not an approver"
        r = run_as("danilo", "state.py", "approve", "implement", cwd=t)
        assert r.returncode == 0 and "1 of 2" in r.stdout, r.stdout
        assert load(t / ".sancho/state.json")["phases"]["implement"]["status"] == "awaiting_approval"
        nxt = json.loads(run_as("luca", "state.py", "next", "--json", cwd=t).stdout)
        assert nxt["mine"] and nxt["action"].startswith("Review the IMPLEMENT gate"), nxt
        nxt = json.loads(run_as("sara", "state.py", "next", "--json", cwd=t).stdout)
        assert not nxt["mine"] and "waits for luca" in nxt["action"], nxt
        assert "gate:   implement 1 of 2 approvals (danilo); waiting for luca" in run_as("sara", "state.py", "status", cwd=t).stdout
        # luca's approval arrives with a pull (written in his own clone): the coordinator closes the gate
        st = load(t / ".sancho/state.json")
        later = datetime_after(st["phases"]["implement"]["gate"]["submitted_at"])
        log_event(t, {"at": later, "by": "luca", "event": "gate_approve", "phase": "implement", "iteration": 1})
        nxt = json.loads(run_as("sara", "state.py", "next", "--json", cwd=t).stdout)
        assert "has its approvals" in nxt["action"], nxt
        r = run_as("danilo", "state.py", "approve", "implement", cwd=t)
        assert r.returncode == 0 and "approved" in r.stdout, r.stdout
        st = load(t / ".sancho/state.json")
        assert st["phases"]["implement"]["status"] == "approved" and st["phases"]["implement"]["gate"]["approved_by"] == ["danilo", "luca"]
        assert st["current_phase"] == "verify"
        # decisions and approvals carry the member's id
        assert run_as("sara", "state.py", "decision", "--summary", "use SQLite offline", "--by", "user", cwd=t).returncode == 0
        assert load(t / ".sancho/state.json")["decisions"][-1]["decided_by"] == "sara"
        assert run_as("sara", "state.py", "start", "verify", cwd=t).returncode == 1, "the coordinator opens phases"
        assert run("state.py", "validate", cwd=t).returncode == 0


def datetime_after(at: str, seconds: int = 5) -> str:
    from datetime import datetime, timedelta
    return (datetime.fromisoformat(at) + timedelta(seconds=seconds)).isoformat()


@check
def team_verify_and_compact() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        team_project(t)
        to_phase(t, "verify")
        (t / ".sancho/uat.json").write_text(json.dumps(uat_cases()), encoding="utf-8")
        assert run_as("sara", "state.py", "claim", "UAT-001", cwd=t).returncode == 0
        assert run_as("luca", "state.py", "claim", "UAT-001", cwd=t).returncode == 1
        assert run_as("luca", "state.py", "claim", "UAT-002", cwd=t).returncode == 0
        nxt = json.loads(run_as("sara", "state.py", "next", "--json", cwd=t).stdout)
        assert nxt["action"].startswith("Run UAT-001"), nxt
        # both open DEF-001 in their own clones (luca first): sara's becomes DEF-002
        assert run_as("luca", "state.py", "uat", "UAT-002", "--result", "fail", "--new-defect", "blocker:crash on save", cwd=t).returncode == 0
        st = load(t / ".sancho/state.json")
        log_event(t, {"at": datetime_after(st["created_at"], 3600 * 24 * 365), "by": "sara", "event": "defect_open", "defect": "DEF-001",
                      "uat": "UAT-001", "severity": "major", "description": "wrong error text"})
        log_event(t, {"at": datetime_after(st["created_at"], 3600 * 24 * 365 + 1), "by": "sara", "event": "uat_result", "case": "UAT-001",
                      "result": "fail", "defects": ["DEF-001"]})
        s = tasks_of(t)
        assert s["team"]["renamed"] == [{"from": "DEF-001", "to": "DEF-002", "by": "sara"}], s["team"]
        assert s["open_defects"] == {"blocker": 1, "major": 1, "minor": 0, "nit": 0}, s
        assert "RENAMED: sara's DEF-001 is DEF-002" in run_as("sara", "state.py", "status", cwd=t).stdout
        nxt = json.loads(run_as("danilo", "state.py", "next", "--json", cwd=t).stdout)
        assert nxt["action"].startswith("Claim DEF-001 (blocker)"), nxt
        assert run_as("danilo", "state.py", "claim", "DEF-001", cwd=t).returncode == 0
        assert run_as("sara", "state.py", "defect", "DEF-001", "--status", "fixed", cwd=t).returncode == 1, "not hers"
        assert run_as("danilo", "state.py", "defect", "DEF-001", "--status", "fixed", "--task", "T-002", cwd=t).returncode == 0
        r = run_as("danilo", "state.py", "defect", "DEF-001", "--status", "verified", cwd=t)
        assert r.returncode == 1 and "four eyes" in r.stderr, r.stderr
        assert run_as("luca", "state.py", "defect", "DEF-001", "--status", "verified", cwd=t).returncode == 1, "luca has no qa role"
        run("state.py", "team", "add", "--id", "luca", "--name", "Luca", "--email", "luca@example.com", "--roles", "developer,qa", cwd=t)
        nxt = json.loads(run_as("luca", "state.py", "next", "--json", cwd=t).stdout)
        assert nxt["action"].startswith("Verify DEF-001"), nxt
        assert run_as("luca", "state.py", "defect", "DEF-001", "--status", "verified", cwd=t).returncode == 0
        assert run_as("sara", "state.py", "defect", "DEF-002", "--status", "wont_fix", cwd=t).returncode == 1, "coordinator only"
        # compaction: only the coordinator; settled items move to the files, the state stays the same
        before = tasks_of(t)
        assert run_as("luca", "state.py", "compact", cwd=t).returncode == 1
        r = run_as("danilo", "state.py", "compact", cwd=t)
        assert r.returncode == 0 and "the state is unchanged" in r.stdout, r.stdout + r.stderr
        after = tasks_of(t)
        for key in ("tasks", "uat", "open_defects"):
            assert before[key] == after[key], (key, before[key], after[key])
        assert after["team"]["renamed"] == before["team"]["renamed"]
        ua = load(t / ".sancho/uat.json")
        assert [d["id"] for d in ua["defects"]] == ["DEF-001"] and ua["defects"][0]["status"] == "verified", ua["defects"]
        assert next(c for c in ua["cases"] if c["id"] == "UAT-002")["result"] == "fail"
        assert "DEF-001" not in (t / ".sancho/log/danilo.jsonl").read_text(encoding="utf-8")
        assert "DEF-001" in (t / ".sancho/log/sara.jsonl").read_text(encoding="utf-8"), "sara's open defect stays in her log"
        assert len(list((t / ".sancho/log/archive").glob("*.jsonl"))) == 1
        assert run("state.py", "validate", cwd=t).returncode == 0
        assert "nothing to compact" in run_as("danilo", "state.py", "compact", cwd=t).stdout


def team_remote(base: Path, names: Tuple[str, ...]) -> Dict[str, Path]:
    """origin.git seeded with a team project, plus one clone per name (git identity = name)."""
    git_in(base, "init", "--bare", "origin.git")
    seed = base / "seed"
    seed.mkdir()
    git_in(seed, "init")
    team_project(seed)
    git_in(seed, "add", "-A")
    git_in(seed, "-c", "user.name=seed", "-c", "user.email=seed@example.com", "commit", "-m", "seed")
    git_in(seed, "push", str(base / "origin.git"), "HEAD:main")
    out = {}
    for name in names:
        git_in(base, "clone", "-b", "main", str(base / "origin.git"), name)
        git_in(base / name, "config", "user.email", f"{name}@example.com")
        git_in(base / name, "config", "user.name", name)
        out[name] = base / name
    return out


def push(cwd: Path, msg: str) -> None:
    git_in(cwd, "add", "-A")
    git_in(cwd, "commit", "-m", msg)
    git_in(cwd, "pull", "--no-rebase", "--no-edit", "origin", "main")
    git_in(cwd, "push", "origin", "HEAD:main")


@check
def team_since_and_hook() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        c = team_remote(Path(tmp), ("luca", "danilo"))
        luca, danilo = c["luca"], c["danilo"]
        assert "first look" in run_as("luca", "state.py", "since", cwd=luca).stdout
        assert run_as("luca", "state.py", "claim", "T-001", cwd=luca).returncode == 0
        assert run_as("luca", "state.py", "task", "T-001", "--status", "ready_for_review", "--evidence", "commit:abcdef1", cwd=luca).returncode == 0
        push(luca, "luca: T-001 ready")
        assert "nothing new" in run_as("luca", "state.py", "since", cwd=luca).stdout
        git_in(danilo, "pull", "--no-rebase", "--no-edit", "origin", "main")
        assert run_as("danilo", "state.py", "review", "T-001", "--changes", "add the offline test", cwd=danilo).returncode == 0
        assert run_as("danilo", "state.py", "claim", "T-002", cwd=danilo).returncode == 0
        push(danilo, "danilo: review T-001")
        # luca installs the hook, then pulls: the hook prints what changed
        r = run_as("luca", "state.py", "hooks", "install", cwd=luca)
        assert r.returncode == 0, r.stderr
        assert "installed" in run_as("luca", "state.py", "hooks", "status", cwd=luca).stdout
        env = {**__import__("os").environ, "SANCHO_USER": "luca"}
        pull = subprocess.run(["git", "pull", "--no-rebase", "--no-edit", "origin", "main"], cwd=str(luca),
                              capture_output=True, text=True, encoding="utf-8", env=env)
        assert pull.returncode == 0, pull.stderr
        hook_out = pull.stdout + pull.stderr
        assert "FOR YOU: danilo asked for changes on T-001: add the offline test" in hook_out, hook_out
        assert "danilo: asked for changes on T-001" in hook_out and "took T-002" in hook_out, hook_out
        # the hook moved the marker: nothing new now; an explicit reference still works
        assert "nothing new" in run_as("luca", "state.py", "since", cwd=luca).stdout
        out = json.loads(run_as("luca", "state.py", "since", "HEAD~1", "--json", "--peek", cwd=luca).stdout)
        assert out["by_member"]["danilo"] == ["asked for changes on T-001: add the offline test", "took T-002"], out
        assert run_as("luca", "state.py", "hooks", "remove", cwd=luca).returncode == 0
        assert "not installed" in run_as("luca", "state.py", "hooks", "status", cwd=luca).stdout


@check
def renumber_duplicate_ids() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        team_project(t, team=False)
        bl = load(t / ".sancho/backlog.json")
        dup = dict(bl["tasks"][1], title="the other T-002, added in parallel")
        bl["tasks"].append(dup)
        bl["tasks"].append(dict(bl["tasks"][0], id="T-006", depends_on=["T-002"]))
        (t / ".sancho/backlog.json").write_text(json.dumps(bl, indent=2), encoding="utf-8")
        r = run("state.py", "renumber", cwd=t)
        assert "tasks: second T-002 -> T-007" in r.stdout and "dry run" in r.stdout, r.stdout
        assert "T-006 refers to T-002" in r.stdout, r.stdout
        assert load(t / ".sancho/backlog.json") == bl, "a dry run changes nothing"
        assert run("state.py", "renumber", "--apply", cwd=t).returncode == 0
        ids = [x["id"] for x in load(t / ".sancho/backlog.json")["tasks"]]
        assert ids == ["T-001", "T-002", "T-003", "T-004", "T-007", "T-006"], ids
        assert "no duplicate ids" in run("state.py", "renumber", cwd=t).stdout
        assert run("state.py", "validate", cwd=t).returncode == 0


@check
def panel_wired() -> None:
    # The plugin's panel (band, toasts, details pane) for the Claude app and Claude Code; not in the ZIP.
    plugin = load(ROOT / ".claude-plugin" / "plugin.json")
    assert (ROOT / plugin["types"]).is_file(), "plugin.json types file missing"
    modules = load(ROOT / "hooks" / "hooks.json")["modules"]
    assert modules and all((ROOT / "hooks" / m).is_file() for m in modules), modules
    reg = (ROOT / "hooks" / "register.tsx").read_text(encoding="utf-8")
    assert "'/sancho " not in reg, "the panel must suggest the plugin form /sancho:<command>"
    p = subprocess.run([sys.executable, "-I", str(ROOT / "hooks" / "sancho_panel.py")], cwd=str(EXAMPLE),
                       capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["error"] is None and out["status"]["project"]["name"] == "FieldLog", out
    with tempfile.TemporaryDirectory() as tmp:
        p = subprocess.run([sys.executable, "-I", str(ROOT / "hooks" / "sancho_panel.py")], cwd=tmp,
                           capture_output=True, text=True, encoding="utf-8")
        out = json.loads(p.stdout)
        assert out["status"] is None and out["error"] is None, out


# --------------------------------------------------------------------------- docs

@check
def docs_links_and_languages() -> None:
    docs = sorted([*ROOT.glob("README*.md"), *(ROOT / "docs").glob("*.md"), ROOT / "examples/fieldlog/WALKTHROUGH.md"])
    for kind in ("install", "guide"):
        for lang in ("en", "it", "es"):
            assert (ROOT / "docs" / f"{kind}.{lang}.md").is_file(), f"missing docs/{kind}.{lang}.md"
    broken = []
    for doc in docs:
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", doc.read_text(encoding="utf-8")):
            if re.match(r"^[a-z]+://", target) or target.startswith("mailto:"):
                continue
            if not (doc.parent / target).exists():
                broken.append(f"{doc.relative_to(ROOT)} -> {target}")
    assert not broken, broken
    for lang_readme, guide in (("README.md", "docs/install.en.md"), ("README.it.md", "docs/install.it.md"), ("README.es.md", "docs/install.es.md")):
        assert guide in (ROOT / lang_readme).read_text(encoding="utf-8"), f"{lang_readme} does not link {guide}"


# -------------------------------------------------------------------------- evals

@check
def evals_coverage() -> None:
    data = load(ROOT / "tests" / "evals.json")
    evals = data["evals"]
    assert data["skill_name"] == "sancho"
    assert len(evals) >= 16, len(evals)
    ids = [e["id"] for e in evals]
    assert len(ids) == len(set(ids)), "duplicate eval ids"
    tags = {t for e in evals for t in e.get("tags", [])}
    required = {"discover", "specify", "plan", "tasks", "implement", "verify", "release", "evolve", "help",
                "status", "next", "first-run", "gate-rejected", "skip-with-adr", "user-stack", "dast-refusal",
                "offline", "handoff-unverified"}
    assert required <= tags, f"evals do not cover: {sorted(required - tags)}"
    for e in evals:
        assert e["prompt"] and e["expected_output"] and e.get("assertions"), e["id"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-k", default="")
    args = ap.parse_args()
    failed = 0
    selected = [(n, f) for n, f in CHECKS if args.k in n]
    for name, fn in selected:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            detail = str(exc) or traceback.format_exc(limit=1).strip().splitlines()[-1]
            print(f"FAIL {name}: {detail}")
    print(f"\n{len(selected) - failed}/{len(selected)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
