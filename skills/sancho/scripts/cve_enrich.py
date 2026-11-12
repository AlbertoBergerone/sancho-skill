#!/usr/bin/env python3
"""Software composition analysis + vulnerability enrichment (standard library only).

Reads dependencies from a CycloneDX SBOM, an npm package-lock.json or a pinned
requirements.txt, finds known vulnerabilities with OSV.dev, enriches CVEs with
NVD (CVSS, CWE), CISA KEV (known exploited) and FIRST EPSS (exploit probability),
and writes a report conforming to schemas/security-report.schema.json.

Usage:
  python cve_enrich.py INPUT [INPUT ...] --out docs/security/security-report.json
                       [--md docs/security/sca.md] [--no-nvd] [--offline]
                       [--replay DIR | --record DIR] [--timeout 20]

INPUT type is detected from the file name: *.cdx.json / bom.json / sbom*.json
(CycloneDX), package-lock.json, requirements*.txt. Use --type to force it.
Environment: NVD_API_KEY (optional) raises the NVD rate limit.

Severity (single Sancho scale), first matching rule wins:
  blocker  KEV listed, or CVSS >= 9.0, or EPSS >= 0.5
  major    CVSS >= 7.0, or EPSS >= 0.1
  minor    CVSS >= 4.0
  nit      CVSS < 4.0
  no CVSS  advisory severity CRITICAL/HIGH/MODERATE/LOW -> blocker/major/minor/nit,
           otherwise minor with "triage required".

Network failures never crash the run: the affected source is reported as not_run
or partial, and summary.not_run explains what is missing. Zero findings with
osv=not_run means "unknown", NOT "no vulnerabilities".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import configure_stdout, die, load_json, now_iso, save_json, write_text  # noqa: E402

OSV_BATCH = "https://api.osv.dev/v1/querybatch"
OSV_VULN = "https://api.osv.dev/v1/vulns/{id}"
NVD_CVE = "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve}"
KEV_FEED = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
EPSS_API = "https://api.first.org/data/v1/epss?cve={cves}"
USER_AGENT = "sancho-skill/1.0 (+https://github.com/AlbertoBergerone/sancho-skill)"

PURL_ECOSYSTEM = {
    "npm": "npm", "pypi": "PyPI", "maven": "Maven", "golang": "Go", "cargo": "crates.io",
    "nuget": "NuGet", "composer": "Packagist", "gem": "RubyGems", "pub": "Pub", "hex": "Hex",
    "swift": "SwiftURL", "cocoapods": "CocoaPods",
}


# --------------------------------------------------------------------------- HTTP

class Offline(Exception):
    pass


class Fetcher:
    """HTTP access with live / offline / replay / record modes (replay is used by tests)."""

    def __init__(self, mode: str = "live", directory: Optional[Path] = None, timeout: float = 20.0):
        self.mode, self.dir, self.timeout = mode, directory, timeout

    @staticmethod
    def key(kind: str, ident: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", ident)
        if len(safe) > 60:
            safe = hashlib.sha1(ident.encode()).hexdigest()[:16]
        return f"{kind}-{safe}.json"

    def get_json(self, kind: str, ident: str, url: str, body: Optional[dict] = None,
                 headers: Optional[Dict[str, str]] = None) -> Any:
        fname = self.key(kind, ident)
        if self.mode == "offline":
            raise Offline("offline mode")
        if self.mode == "replay":
            assert self.dir is not None
            path = self.dir / fname
            if not path.is_file():
                raise Offline(f"no recorded response {fname}")
            return load_json(path)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        req.add_header("User-Agent", USER_AGENT)
        req.add_header("Accept", "application/json")
        if data:
            req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise Offline(f"{kind}: {exc}") from exc
        if self.mode == "record" and self.dir is not None:
            save_json(self.dir / fname, payload)
        return payload


# ------------------------------------------------------------------- dependency input

def detect_type(path: Path) -> str:
    name = path.name.lower()
    if name == "package-lock.json" or name == "npm-shrinkwrap.json":
        return "npm-lock"
    if name.startswith("requirements") and name.endswith(".txt"):
        return "requirements"
    if name.endswith(".json"):
        try:
            doc = load_json(path)
        except ValueError:
            return "unknown"
        if isinstance(doc, dict) and doc.get("bomFormat") == "CycloneDX":
            return "cyclonedx"
    return "unknown"


def parse_purl(purl: str) -> Optional[Tuple[str, str, str]]:
    m = re.match(r"^pkg:([^/]+)/(.+?)@([^?#]+)", purl)
    if not m:
        return None
    ptype, name, version = m.group(1).lower(), urllib.parse.unquote(m.group(2)), urllib.parse.unquote(m.group(3))
    eco = PURL_ECOSYSTEM.get(ptype)
    if not eco:
        return None
    if eco == "Maven":
        name = name.replace("/", ":")
    return eco, name, version


def read_text_any(path: Path) -> str:
    """Read a text file written by any common tool: UTF-8 (with/without BOM), UTF-16 (PowerShell), cp1252."""
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def read_cyclonedx(path: Path) -> Tuple[List[dict], List[str]]:
    pkgs, skipped = [], []
    for comp in load_json(path).get("components", []) or []:
        purl = comp.get("purl", "")
        parsed = parse_purl(purl) if purl else None
        if parsed:
            pkgs.append({"ecosystem": parsed[0], "name": parsed[1], "version": parsed[2], "purl": purl})
        else:
            label = "/".join(x for x in (comp.get("group"), comp.get("name")) if x) or "?"
            skipped.append(f"{label}@{comp.get('version', '?')}" + ("" if purl else " (no purl)"))
    return pkgs, skipped


def read_npm_lock(path: Path) -> List[dict]:
    doc = load_json(path)
    pkgs = []
    if "packages" in doc:
        for key, meta in doc["packages"].items():
            if not key or "node_modules/" not in key or meta.get("link"):
                continue
            name = key.split("node_modules/")[-1]
            if meta.get("version"):
                pkgs.append({"ecosystem": "npm", "name": name, "version": meta["version"]})
    else:  # lockfileVersion 1
        def walk(deps: dict) -> None:
            for name, meta in (deps or {}).items():
                if meta.get("version"):
                    pkgs.append({"ecosystem": "npm", "name": name, "version": meta["version"]})
                walk(meta.get("dependencies", {}))
        walk(doc.get("dependencies", {}))
    return pkgs


def read_requirements(path: Path) -> Tuple[List[dict], List[str]]:
    """Pinned requirements (name==version), including pip-compile --generate-hashes output."""
    pkgs, skipped = [], []
    text = read_text_any(path)
    logical: List[str] = []
    buf = ""
    for raw in text.splitlines():
        line = raw.split(" #", 1)[0] if " #" in raw else (raw if not raw.lstrip().startswith("#") else "")
        line = line.rstrip()
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        logical.append(buf + line)
        buf = ""
    if buf:
        logical.append(buf)
    for line in logical:
        line = re.sub(r"\s--hash[= ]\S+", "", " " + line).strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9._-]+)(\[[^\]]*\])?\s*===?\s*([A-Za-z0-9.+!_-]+)\s*(;.*)?$", line)
        if m:
            pkgs.append({"ecosystem": "PyPI", "name": m.group(1), "version": m.group(3)})
        else:
            skipped.append(line)
    return pkgs, skipped


def load_packages(paths: List[Path], forced: Optional[str]) -> Tuple[List[dict], List[str]]:
    pkgs: List[dict] = []
    notes: List[str] = []
    for p in paths:
        if not p.is_file():
            notes.append(f"{p}: input not found, NOT checked")
            continue
        kind = forced or detect_type(p)
        if kind == "cyclonedx":
            found, skipped = read_cyclonedx(p)
            pkgs += found
            if skipped:
                notes.append(f"{p.name}: {len(skipped)} component(s) without a usable purl NOT checked: " + ", ".join(skipped[:5]))
        elif kind == "npm-lock":
            pkgs += read_npm_lock(p)
        elif kind == "requirements":
            found, skipped = read_requirements(p)
            pkgs += found
            if skipped:
                notes.append(f"{p.name}: {len(skipped)} unpinned requirement(s) not checked (pin with ==): " + ", ".join(skipped[:5]))
        else:
            die(f"cannot detect input type of {p}; use --type")
    seen, unique = set(), []
    for pkg in pkgs:
        k = (pkg["ecosystem"], pkg["name"].lower(), pkg["version"])
        if k not in seen:
            seen.add(k)
            unique.append(pkg)
    unique.sort(key=lambda x: (x["ecosystem"], x["name"].lower(), x["version"]))
    return unique, notes


# ------------------------------------------------------------------------ CVSS v3

_W = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
    "AC": {"L": 0.77, "H": 0.44},
    "UI": {"N": 0.85, "R": 0.62},
    "C": {"H": 0.56, "L": 0.22, "N": 0.0},
}


def _roundup(x: float) -> float:
    i = int(round(x * 100000))
    return i / 100000.0 if i % 10000 == 0 else (math.floor(i / 10000) + 1) / 10.0


def cvss3_base_score(vector: str) -> Optional[float]:
    """Base score for CVSS:3.0 / CVSS:3.1 vectors (FIRST specification). None if invalid."""
    if not vector.startswith(("CVSS:3.0/", "CVSS:3.1/")):
        return None
    try:
        m = dict(part.split(":") for part in vector.split("/")[1:])
        scope_changed = m["S"] == "C"
        pr = {"N": 0.85, "L": 0.68 if scope_changed else 0.62, "H": 0.5 if scope_changed else 0.27}[m["PR"]]
        iss = 1 - (1 - _W["C"][m["C"]]) * (1 - _W["C"][m["I"]]) * (1 - _W["C"][m["A"]])
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if scope_changed else 6.42 * iss
        expl = 8.22 * _W["AV"][m["AV"]] * _W["AC"][m["AC"]] * pr * _W["UI"][m["UI"]]
    except (KeyError, ValueError):
        return None
    if impact <= 0:
        return 0.0
    raw = 1.08 * (impact + expl) if scope_changed else impact + expl
    return _roundup(min(raw, 10))


# ------------------------------------------------------------------ severity mapping

ADVISORY_LEVEL = {"CRITICAL": "blocker", "HIGH": "major", "MODERATE": "minor", "MEDIUM": "minor", "LOW": "nit"}


def classify(cvss: Optional[float], epss: Optional[float], kev: bool, advisory: Optional[str]) -> Tuple[str, str]:
    if kev:
        return "blocker", "listed in CISA KEV (known exploited)"
    if cvss is not None and cvss >= 9.0:
        return "blocker", f"CVSS {cvss} >= 9.0"
    if epss is not None and epss >= 0.5:
        return "blocker", f"EPSS {epss:.3f} >= 0.5"
    if cvss is not None and cvss >= 7.0:
        return "major", f"CVSS {cvss} >= 7.0"
    if epss is not None and epss >= 0.1:
        return "major", f"EPSS {epss:.3f} >= 0.1"
    if cvss is not None:
        return ("minor", f"CVSS {cvss} >= 4.0") if cvss >= 4.0 else ("nit", f"CVSS {cvss} < 4.0")
    if advisory and advisory.upper() in ADVISORY_LEVEL:
        return ADVISORY_LEVEL[advisory.upper()], f"no CVSS score; advisory severity {advisory.upper()}"
    return "minor", "no CVSS score or advisory severity; triage required"


# ------------------------------------------------------------------------- pipeline

def osv_batch_body(chunk: List[dict]) -> Tuple[dict, str]:
    """Request body for OSV querybatch and its stable identifier (used for record/replay)."""
    body = {"queries": [{"package": {"name": p["name"], "ecosystem": p["ecosystem"]}, "version": p["version"]} for p in chunk]}
    return body, hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]


def osv_lookup(fetch: Fetcher, pkgs: List[dict]) -> Tuple[Dict[int, List[str]], str]:
    """Return {package index: [vuln ids]} and source status."""
    result: Dict[int, List[str]] = {}
    status = "run"
    for start in range(0, len(pkgs), 500):
        chunk = pkgs[start:start + 500]
        body, ident = osv_batch_body(chunk)
        try:
            resp = fetch.get_json("osv-batch", ident, OSV_BATCH, body=body)
        except Offline:
            return result, ("partial" if result else "not_run")
        for i, res in enumerate(resp.get("results", [])):
            ids = [v["id"] for v in (res.get("vulns") or [])]
            if res.get("next_page_token"):
                status = "partial"
            if ids:
                result[start + i] = ids
    return result, status


SEVERITY_ORDER = {"blocker": 0, "major": 1, "minor": 2, "nit": 3}


def merge_group(group: List[dict]) -> dict:
    """Fold advisories of the same issue into the most severe one, keeping what each adds."""
    group = sorted(group, key=lambda f: (SEVERITY_ORDER[f["severity"]], "cvss" not in f, f["advisory"]))
    best, others = dict(group[0]), group[1:]
    if not others:
        return best
    best["cve"] = sorted({c for f in group for c in f["cve"]})
    best["cwe"] = sorted({c for f in group for c in f["cwe"]})
    best["kev"] = any(f["kev"] for f in group)
    best["fixed_versions"] = sorted({v for f in group for v in f["fixed_versions"]})
    if any(f["status"] == "open" for f in group):
        best["status"] = "open"
    for key in ("cvss", "epss"):
        if key not in best:
            source = next((f for f in others if key in f), None)
            if source:
                best[key] = source[key]
    best["severity_rationale"] += "; also published as " + ", ".join(f["advisory"] for f in others)
    return best


def merge_aliases(rows: List[Tuple[dict, set]]) -> List[dict]:
    """One finding per package and issue: OSV lists the same issue under several ids (GHSA, PYSEC...)."""
    groups: List[dict] = []
    for finding, ids in rows:
        c = finding["component"]
        key = (c.get("ecosystem"), c["name"].lower(), c.get("version"))
        merged = {"key": key, "ids": set(ids), "findings": [finding]}
        for g in [g for g in groups if g["key"] == key and g["ids"] & ids]:
            merged["ids"] |= g["ids"]
            merged["findings"] += g["findings"]
            groups.remove(g)
        groups.append(merged)
    return [merge_group(g["findings"]) for g in groups]


def enrich(paths: List[Path], fetch: Fetcher, use_nvd: bool = True, forced: Optional[str] = None,
           nvd_delay: Optional[float] = None) -> dict:
    pkgs, notes = load_packages(paths, forced)
    enrichment = {"osv": "not_run", "nvd": "not_run", "kev": "not_run", "epss": "not_run"}
    not_run: List[str] = list(notes)
    if pkgs:
        vuln_map, enrichment["osv"] = osv_lookup(fetch, pkgs)
    else:
        vuln_map = {}
        not_run.append("No checkable packages found in the inputs: nothing was looked up, the result is UNKNOWN")
    if pkgs and enrichment["osv"] != "run":
        not_run.append("OSV.dev unreachable: dependency vulnerabilities NOT checked. Re-run with network: "
                       "python cve_enrich.py " + " ".join(str(p) for p in paths) + " --out <report>")

    details: Dict[str, dict] = {}
    detail_fail = 0
    for vid in sorted({v for ids in vuln_map.values() for v in ids}):
        try:
            details[vid] = fetch.get_json("osv-vuln", vid, OSV_VULN.format(id=urllib.parse.quote(vid)))
        except Offline:
            detail_fail += 1
    if detail_fail:
        enrichment["osv"] = "partial"
        not_run.append(f"OSV: details missing for {detail_fail} advisory(ies)")

    def cves_of(vid: str) -> List[str]:
        d = details.get(vid, {})
        ids = [vid] + list(d.get("aliases", []))
        return sorted({a for a in ids if re.match(r"^CVE-\d{4}-\d{4,}$", a)})

    all_cves = sorted({c for ids in vuln_map.values() for v in ids for c in cves_of(v)})

    kev: set = set()
    if all_cves:
        try:
            feed = fetch.get_json("kev", "catalog", KEV_FEED)
            kev = {v.get("cveID") for v in feed.get("vulnerabilities", [])}
            enrichment["kev"] = "run"
        except Offline:
            not_run.append("CISA KEV feed unreachable: exploited-in-the-wild status unknown")
    else:
        enrichment["kev"] = "run" if enrichment["osv"] == "run" else "not_run"

    epss: Dict[str, dict] = {}
    if all_cves:
        ok = True
        for start in range(0, len(all_cves), 100):
            chunk = all_cves[start:start + 100]
            try:
                resp = fetch.get_json("epss", ",".join(chunk), EPSS_API.format(cves=",".join(chunk)))
                for row in resp.get("data", []):
                    epss[row["cve"]] = {"score": float(row["epss"]), "percentile": float(row["percentile"]), "date": row.get("date", "")}
            except (Offline, KeyError, ValueError):
                ok = False
        enrichment["epss"] = "run" if ok else ("partial" if epss else "not_run")
        if not ok:
            not_run.append("FIRST EPSS unreachable for some CVEs: exploit probability unknown")
    else:
        enrichment["epss"] = "run" if enrichment["osv"] == "run" else "not_run"

    nvd: Dict[str, dict] = {}
    if use_nvd and all_cves:
        key = os.environ.get("NVD_API_KEY", "")
        delay = nvd_delay if nvd_delay is not None else (0.7 if key else 6.5)
        headers = {"apiKey": key} if key else {}
        failures = 0
        for i, cve in enumerate(all_cves):
            if i and fetch.mode in ("live", "record"):
                time.sleep(delay)
            try:
                resp = fetch.get_json("nvd", cve, NVD_CVE.format(cve=cve), headers=headers)
                items = resp.get("vulnerabilities", [])
                if items:
                    nvd[cve] = items[0].get("cve", {})
            except Offline:
                failures += 1
        enrichment["nvd"] = "run" if not failures else ("partial" if nvd else "not_run")
        if failures:
            not_run.append(f"NVD unreachable for {failures} CVE(s); set NVD_API_KEY or retry later")
    elif not use_nvd:
        not_run.append("NVD enrichment disabled (--no-nvd)")
    else:
        enrichment["nvd"] = "run" if enrichment["osv"] == "run" else "not_run"

    rows: List[Tuple[dict, set]] = []
    n = 0
    for idx in sorted(vuln_map):
        pkg = pkgs[idx]
        for vid in vuln_map[idx]:
            d = details.get(vid, {})
            if d.get("withdrawn"):
                continue
            cves = cves_of(vid)
            cvss_obj = None
            score = None
            for sev in d.get("severity", []):
                if sev.get("type") == "CVSS_V3":
                    vec = sev.get("score", "")
                    score = cvss3_base_score(vec)
                    cvss_obj = {"version": vec[5:8], "vector": vec, "source": "osv"}
                    if score is not None:
                        cvss_obj["base_score"] = score
                    break
            cwe: List[str] = list((d.get("database_specific") or {}).get("cwe_ids", []) or [])
            for cve in cves:
                rec = nvd.get(cve)
                if not rec:
                    continue
                metrics = rec.get("metrics", {})
                for mkey in ("cvssMetricV31", "cvssMetricV30"):
                    if metrics.get(mkey) and (score is None or cvss_obj is None):
                        data = metrics[mkey][0]["cvssData"]
                        score = float(data["baseScore"])
                        cvss_obj = {"version": data.get("version", mkey[-2] + "." + mkey[-1]), "vector": data["vectorString"],
                                    "base_score": score, "source": "nvd"}
                        break
                for w in rec.get("weaknesses", []):
                    for desc in w.get("description", []):
                        if re.match(r"^CWE-\d+$", desc.get("value", "")):
                            cwe.append(desc["value"])
            best_epss = max((epss[c] for c in cves if c in epss), key=lambda e: e["score"], default=None)
            in_kev = any(c in kev for c in cves)
            advisory = (d.get("database_specific") or {}).get("severity")
            severity, why = classify(score, best_epss["score"] if best_epss else None, in_kev, advisory)
            if enrichment["kev"] != "run":
                why += "; KEV not checked"
            fixed = sorted({ev["fixed"] for aff in d.get("affected", []) for rng in aff.get("ranges", [])
                            for ev in rng.get("events", []) if "fixed" in ev})
            n += 1
            finding = {
                "id": f"F-{n:03d}",
                "title": (d.get("summary") or d.get("details", "")[:120] or vid).strip(),
                "category": "sca",
                "component": {k: v for k, v in pkg.items() if k in ("name", "version", "ecosystem", "purl")},
                "advisory": vid,
                "cve": cves,
                "cwe": sorted(set(cwe)),
                "kev": in_kev,
                "fixed_versions": fixed,
                "severity": severity,
                "severity_rationale": why,
                "remediation": (f"Upgrade {pkg['name']} to {fixed[0]} or later" if fixed else "No fixed version published: assess workaround, replacement or accepted risk"),
                "status": "open",
            }
            if cvss_obj:
                finding["cvss"] = cvss_obj
            if best_epss:
                finding["epss"] = {k: v for k, v in best_epss.items() if v != ""}
            if not details.get(vid):
                finding["status"] = "not_verified"
                finding["severity_rationale"] += "; advisory details unavailable"
            rows.append((finding, {vid, *d.get("aliases", [])}))

    findings = merge_aliases(rows)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["component"]["name"].lower(), f["advisory"]))
    for i, f in enumerate(findings, 1):
        f["id"] = f"F-{i:03d}"
    summary = {k: sum(1 for f in findings if f["severity"] == k) for k in SEVERITY_ORDER}
    summary["not_run"] = not_run
    return {
        "protocol": "sancho/1.0",
        "generated_at": now_iso(),
        "scope": {"targets": [str(p) for p in paths], "environment": "source-only", "active_testing": False},
        "tools": [{"name": "sancho cve_enrich", "status": "run",
                   "command": "python cve_enrich.py " + " ".join(str(p) for p in paths),
                   "note": f"{len(pkgs)} package(s) checked"}],
        "enrichment": enrichment,
        "findings": findings,
        "summary": summary,
    }


def to_markdown(report: dict) -> str:
    s = report["summary"]
    out = ["# Dependency vulnerabilities (SCA)", "",
           f"Generated: {report['generated_at']} · sources: " + ", ".join(f"{k} {v}" for k, v in report["enrichment"].items()), "",
           f"**blocker {s['blocker']} · major {s['major']} · minor {s['minor']} · nit {s['nit']}**", ""]
    if s.get("not_run"):
        out += ["> **Not run / incomplete**", ">"] + [f"> - {x}" for x in s["not_run"]] + [""]
    if report["findings"]:
        out += ["| ID | Severity | Package | Advisory | CVE | CVSS | EPSS | KEV | Fix |", "|---|---|---|---|---|---|---|---|---|"]
        for f in report["findings"]:
            c = f["component"]
            out.append("| {id} | {sev} | {pkg}@{ver} | {adv} | {cve} | {cvss} | {epss} | {kev} | {fix} |".format(
                id=f["id"], sev=f["severity"], pkg=c["name"], ver=c.get("version", ""), adv=f.get("advisory", ""),
                cve=", ".join(f.get("cve", [])) or "-", cvss=f.get("cvss", {}).get("base_score", "-"),
                epss=(f"{f['epss']['score']:.3f}" if f.get("epss") else "-"), kev="yes" if f.get("kev") else "no",
                fix=", ".join(f.get("fixed_versions", [])[:2]) or "none"))
    elif report["enrichment"]["osv"] == "run":
        checked = report["tools"][0].get("note", "")
        out.append(f"No known vulnerabilities found by OSV.dev in the checked packages ({checked})."
                   + (" Items in the NOT RUN list above were not checked." if s.get("not_run") else ""))
    else:
        out.append("**Unknown**: no package was checked against OSV.dev, so no conclusion can be drawn.")
    return "\n".join(out) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--type", choices=["cyclonedx", "npm-lock", "requirements"])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--md", type=Path)
    ap.add_argument("--no-nvd", action="store_true")
    ap.add_argument("--offline", action="store_true")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--replay", type=Path, help="read recorded API responses from DIR (tests)")
    mode.add_argument("--record", type=Path, help="save live API responses to DIR")
    ap.add_argument("--timeout", type=float, default=20.0)
    args = ap.parse_args(argv)
    if args.offline:
        fetch = Fetcher("offline")
    elif args.replay:
        fetch = Fetcher("replay", args.replay)
    elif args.record:
        fetch = Fetcher("record", args.record, args.timeout)
    else:
        fetch = Fetcher("live", None, args.timeout)
    report = enrich(args.inputs, fetch, use_nvd=not args.no_nvd, forced=args.type)
    save_json(args.out, report)
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        write_text(args.md, to_markdown(report), encoding="utf-8", newline="\n")
    s = report["summary"]
    print(f"findings: blocker {s['blocker']}, major {s['major']}, minor {s['minor']}, nit {s['nit']}")
    print("sources: " + ", ".join(f"{k}={v}" for k, v in report["enrichment"].items()))
    for line in s["not_run"]:
        print(f"NOT RUN: {line}")
    print(f"wrote {args.out}")
    return 2 if any(not p.is_file() for p in args.inputs) else 0


if __name__ == "__main__":
    sys.exit(main())
