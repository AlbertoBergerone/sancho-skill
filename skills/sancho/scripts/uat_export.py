#!/usr/bin/env python3
"""Export the UAT checklist to Markdown and CSV, and import results back from CSV.

Export:
  python uat_export.py .sancho/uat.json --md docs/uat/UAT.md --csv docs/uat/uat.csv
                       [--lang it|en|es] [--delimiter ";"]
Import (after the tester filled the spreadsheet):
  python uat_export.py .sancho/uat.json --import-csv docs/uat/uat.csv [--tester "Name"]

--lang defaults to settings.language in .sancho/state.json, else en.
CSV is written as UTF-8 with BOM so spreadsheet apps detect the encoding; use
--delimiter ";" for spreadsheet apps configured for Italian/Spanish locales.
On import, a failed case without defects gets a new open defect (severity major)
that the QA role must triage; the script prints what it created.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import configure_stdout, die, load_json, now_iso, save_json, write_text  # noqa: E402
from _schema import validate  # noqa: E402

LABELS: Dict[str, Dict[str, str]] = {
    "en": {
        "title": "User Acceptance Test checklist", "build": "Build under test", "summary": "Summary",
        "story": "Story", "criteria": "Criteria", "platform": "Platform", "pre": "Preconditions",
        "data": "Test data", "steps": "Steps", "expected": "Expected result", "result": "Result",
        "by": "Executed by", "at": "Executed at", "notes": "Notes", "defects": "Defects", "id": "ID",
        "case": "Title", "how": "How to record the result: tick one box, add notes, and report every failure.",
        "pass": "pass", "fail": "fail", "blocked": "blocked", "not_tested": "not tested",
        "defect_list": "Defects", "total": "total", "severity": "Severity", "status": "Status", "description": "Description",
    },
    "it": {
        "title": "Checklist di collaudo utente (UAT)", "build": "Versione in prova", "summary": "Riepilogo",
        "story": "Story", "criteria": "Criteri", "platform": "Piattaforma", "pre": "Precondizioni",
        "data": "Dati di test", "steps": "Passi", "expected": "Risultato atteso", "result": "Esito",
        "by": "Eseguito da", "at": "Eseguito il", "notes": "Note", "defects": "Difetti", "id": "ID",
        "case": "Titolo", "how": "Come registrare l'esito: spunta una casella, aggiungi note e segnala ogni errore.",
        "pass": "superato", "fail": "fallito", "blocked": "bloccato", "not_tested": "non eseguito",
        "defect_list": "Difetti", "total": "totale", "severity": "Gravità", "status": "Stato", "description": "Descrizione",
    },
    "es": {
        "title": "Lista de pruebas de aceptación de usuario (UAT)", "build": "Versión en prueba", "summary": "Resumen",
        "story": "Historia", "criteria": "Criterios", "platform": "Plataforma", "pre": "Precondiciones",
        "data": "Datos de prueba", "steps": "Pasos", "expected": "Resultado esperado", "result": "Resultado",
        "by": "Ejecutado por", "at": "Ejecutado el", "notes": "Notas", "defects": "Defectos", "id": "ID",
        "case": "Título", "how": "Cómo registrar el resultado: marca una casilla, añade notas e informa de cada fallo.",
        "pass": "superado", "fail": "fallido", "blocked": "bloqueado", "not_tested": "no ejecutado",
        "defect_list": "Defectos", "total": "total", "severity": "Gravedad", "status": "Estado", "description": "Descripción",
    },
}
RESULTS = ["pass", "fail", "blocked", "not_tested"]
CSV_FIELDS = ["id", "story", "criteria", "case", "platform", "pre", "data", "steps", "expected", "result", "by", "at", "notes", "defects"]


def pick_lang(uat_path: Path, lang: Optional[str]) -> str:
    if lang:
        return lang if lang in LABELS else "en"
    state = uat_path.parent / "state.json"
    if state.is_file():
        code = str(load_json(state).get("settings", {}).get("language", "en"))[:2].lower()
        return code if code in LABELS else "en"
    return "en"


def steps_text(case: dict, sep: str = "\n") -> str:
    lines = []
    for s in case["steps"]:
        line = f"{s['n']}. {s['action']}"
        if s.get("expected"):
            line += f" -> {s['expected']}"
        lines.append(line)
    return sep.join(lines)


def to_markdown(uat: dict, lang: str) -> str:
    L = LABELS[lang]
    cases = uat.get("cases", [])
    counts = {r: sum(1 for c in cases if c.get("result") == r) for r in RESULTS}
    out = [f"# {L['title']}", ""]
    if uat.get("build"):
        out += [f"**{L['build']}:** {uat['build']}", ""]
    out += [f"**{L['summary']}:** " + " · ".join(f"{L[r]} {counts[r]}" for r in RESULTS) + f" · {L['total']} {len(cases)}", "",
            f"_{L['how']}_", ""]
    for c in cases:
        out += [f"## {c['id']} · {c['title']}", "",
                f"- **{L['story']}:** {c['story']} · **{L['criteria']}:** {', '.join(c['criteria'])}",
                f"- **{L['platform']}:** {c['platform']}", ""]
        if c.get("preconditions"):
            out += [f"**{L['pre']}**", ""] + [f"- {p}" for p in c["preconditions"]] + [""]
        if c.get("test_data"):
            out += [f"**{L['data']}**", ""] + [f"- `{d}`" for d in c["test_data"]] + [""]
        out += [f"**{L['steps']}**", ""]
        for s in c["steps"]:
            out.append(f"{s['n']}. {s['action']}" + (f"  \n   ↳ {s['expected']}" if s.get("expected") else ""))
        out += ["", f"**{L['expected']}:** {c['expected_result']}", ""]
        boxes = " ".join(("[x]" if c.get("result") == r else "[ ]") + f" {L[r]}" for r in RESULTS)
        out += [f"**{L['result']}:** {boxes}", ""]
        meta = []
        if c.get("executed_by"):
            meta.append(f"{L['by']}: {c['executed_by']}")
        if c.get("executed_at"):
            meta.append(f"{L['at']}: {c['executed_at']}")
        if c.get("defects"):
            meta.append(f"{L['defects']}: {', '.join(c['defects'])}")
        if meta:
            out += [" · ".join(meta), ""]
        out += [f"**{L['notes']}:** {c.get('notes', '')}", "", "---", ""]
    defects = uat.get("defects", [])
    if defects:
        out += [f"## {L['defect_list']}", "",
                f"| ID | UAT | {L['severity']} | {L['status']} | {L['description']} |", "|---|---|---|---|---|"]
        for d in defects:
            out.append(f"| {d['id']} | {d['uat']} | {d['severity']} | {d['status']} | {d['description']} |")
        out.append("")
    return "\n".join(out)


def to_csv(uat: dict, lang: str, delimiter: str) -> str:
    L = LABELS[lang]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimiter, lineterminator="\n")
    w.writerow([L[f] for f in CSV_FIELDS])
    for c in uat.get("cases", []):
        w.writerow([
            c["id"], c["story"], ", ".join(c["criteria"]), c["title"], c["platform"],
            "\n".join(c.get("preconditions", [])), "\n".join(c.get("test_data", [])), steps_text(c),
            c["expected_result"], L[c.get("result", "not_tested")], c.get("executed_by", ""),
            c.get("executed_at", ""), c.get("notes", ""), ", ".join(c.get("defects", [])),
        ])
    return buf.getvalue()


def _normalize_result(value: str) -> Optional[str]:
    v = value.strip().lower().replace("_", " ")
    for lang in LABELS.values():
        for key in RESULTS:
            if v in (key.replace("_", " "), lang[key].lower()):
                return key
    return None


def _read_any(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252"):  # spreadsheet apps on Windows often re-save as cp1252
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def _normalize_datetime(value: str) -> Optional[str]:
    """Accept ISO 8601 or day-first dates typed by testers (28/10/2026, 28-10-2026 14:30, 28.10.2026)."""
    v = value.strip()
    if not v:
        return None
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v
    except ValueError:
        pass
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:[ T](\d{1,2})[:.](\d{2}))?$", v)
    if m:
        d, mo, y, hh, mm = m.groups()
        try:
            dt = datetime(int(y), int(mo), int(d), int(hh or 12), int(mm or 0))
        except ValueError:
            return None
        return dt.astimezone().replace(microsecond=0).isoformat()
    return None


def import_csv(uat: dict, csv_path: Path, tester: Optional[str]) -> List[str]:
    text = _read_any(csv_path)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        die(f"{csv_path} is empty")
    try:
        dialect = csv.Sniffer().sniff(lines[0], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    header = [h.strip() for h in rows[0]]
    # map localized header -> field key
    col: Dict[str, int] = {}
    for idx, h in enumerate(header):
        for lang in LABELS.values():
            for key in CSV_FIELDS:
                if h.lower() == lang[key].lower():
                    col.setdefault(key, idx)
    for needed in ("id", "result"):
        if needed not in col:
            die(f"CSV has no '{needed}' column")
    cases = {c["id"]: c for c in uat.get("cases", [])}
    defects = uat.setdefault("defects", [])
    next_def = 1 + max([int(d["id"].split("-")[1]) for d in defects] or [0])
    log: List[str] = []
    for row in rows[1:]:
        if not row or col["id"] >= len(row) or not row[col["id"]].strip():
            continue
        cid = row[col["id"]].strip()
        if cid not in cases:
            log.append(f"skip {cid}: unknown case")
            continue
        raw_result = row[col["result"]].strip() if col["result"] < len(row) else ""
        result = _normalize_result(raw_result) if raw_result else "not_tested"
        if result is None:
            log.append(f"skip {cid}: unrecognized result '{raw_result}'")
            continue
        case = cases[cid]
        case["result"] = result

        def cell(key: str) -> str:
            return row[col[key]].strip() if key in col and col[key] < len(row) else ""

        if cell("notes"):
            case["notes"] = cell("notes")
        if result == "not_tested":
            for k in ("executed_at", "executed_by"):
                case.pop(k, None)
            continue
        case["executed_by"] = cell("by") or case.get("executed_by") or tester or "tester"
        typed = cell("at")
        when = _normalize_datetime(typed) if typed else None
        if typed and when is None:
            case["notes"] = (case.get("notes", "") + f" [date as typed: {typed}]").strip()
            log.append(f"{cid}: unreadable date '{typed}', recorded the import time instead")
        case["executed_at"] = when or case.get("executed_at") or now_iso()
        if result == "blocked" and not case.get("notes"):
            case["notes"] = "blocked (reason not given)"
        if result == "fail" and not case.get("defects"):
            did = f"DEF-{next_def:03d}"
            next_def += 1
            defects.append({"id": did, "uat": cid, "severity": "major",
                            "description": case.get("notes") or f"{cid} failed: {case['title']}", "status": "open"})
            case["defects"] = [did]
            log.append(f"{cid}: fail -> created {did} (severity major, triage required)")
        else:
            log.append(f"{cid}: {result}")
    return log


def main(argv: Optional[List[str]] = None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("uat", type=Path)
    ap.add_argument("--md", type=Path)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--lang")
    ap.add_argument("--delimiter", default=",")
    ap.add_argument("--import-csv", type=Path, dest="import_csv")
    ap.add_argument("--tester")
    args = ap.parse_args(argv)
    if not args.uat.is_file():
        die(f"UAT file not found: {args.uat}")
    uat = load_json(args.uat)
    lang = pick_lang(args.uat, args.lang)
    if args.import_csv:
        for line in import_csv(uat, args.import_csv, args.tester):
            print(line)
        errors = validate(uat, "uat")
        if errors:
            die("import would make the UAT file invalid, nothing saved:\n  " + "\n  ".join(errors[:10]))
        save_json(args.uat, uat)
        print(f"updated {args.uat}")
    if not (args.md or args.csv or args.import_csv):
        die("nothing to do: pass --md, --csv or --import-csv")
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        write_text(args.md, to_markdown(uat, lang), encoding="utf-8", newline="\n")
        print(f"wrote {args.md}")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        write_text(args.csv, to_csv(uat, lang, args.delimiter), encoding="utf-8-sig", newline="")
        print(f"wrote {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
