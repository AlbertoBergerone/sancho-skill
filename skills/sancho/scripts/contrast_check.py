#!/usr/bin/env python3
"""WCAG 2.x contrast check for design tokens.

tokens.json format (subset of the W3C design-tokens format):
{
  "color": {
    "neutral": { "0": { "$value": "#ffffff" }, "900": { "$value": "#111827" } },
    "brand":   { "primary": { "$value": "#1d4ed8" } },
    "text":    { "default": { "$value": "{color.neutral.900}" } }
  },
  "contrast_pairs": [
    { "fg": "color.text.default", "bg": "color.neutral.0", "usage": "text" },
    { "fg": "color.brand.primary", "bg": "color.neutral.0", "usage": "ui" }
  ]
}
Values may be plain strings or {"$value": ...}; references use {path.to.token}.
Colors: #rgb, #rrggbb, #rrggbbaa (alpha is composited over the background).

Minimum ratios (WCAG 2.2 AA): text 4.5, large-text 3.0, ui 3.0 (non-text, SC 1.4.11).
With --level AAA: text 7.0, large-text 4.5, ui 3.0.

Usage: python contrast_check.py design/tokens.json [--level AA|AAA] [--json]
Exit code 0 all pairs pass, 1 at least one pair fails, 2 input error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import configure_stdout, die, load_json  # noqa: E402

MIN = {
    "AA": {"text": 4.5, "large-text": 3.0, "ui": 3.0},
    "AAA": {"text": 7.0, "large-text": 4.5, "ui": 3.0},
}
HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
REF = re.compile(r"^\{([^}]+)\}$")
RGBA = Tuple[float, float, float, float]


def flatten(node: object, prefix: str = "") -> Dict[str, str]:
    out: Dict[str, str] = {}
    if isinstance(node, dict):
        if "$value" in node:
            out[prefix] = str(node["$value"])
            return out
        for key, value in node.items():
            if key.startswith("$") or key == "contrast_pairs":
                continue
            out.update(flatten(value, f"{prefix}.{key}" if prefix else key))
    elif isinstance(node, str):
        out[prefix] = node
    return out


def resolve(tokens: Dict[str, str], path: str, seen: Optional[set] = None) -> str:
    seen = seen or set()
    if path in seen:
        raise ValueError(f"circular reference at {path}")
    if path not in tokens:
        raise ValueError(f"unknown token {path}")
    value = tokens[path].strip()
    m = REF.match(value)
    return resolve(tokens, m.group(1), seen | {path}) if m else value


def parse_hex(value: str) -> RGBA:
    if not HEX.match(value):
        raise ValueError(f"not a hex color: {value}")
    h = value[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return r, g, b, a


def composite(fg: RGBA, bg: RGBA) -> RGBA:
    a = fg[3]
    return (fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a), 1.0)


def luminance(c: RGBA) -> float:
    def lin(v: float) -> float:
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def ratio(fg_hex: str, bg_hex: str) -> float:
    bg = parse_hex(bg_hex)
    if bg[3] < 1:
        bg = composite(bg, (1.0, 1.0, 1.0, 1.0))  # assume white page under a translucent background
    fg = composite(parse_hex(fg_hex), bg)
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def check(doc: dict, level: str = "AA") -> List[dict]:
    tokens = flatten(doc)
    pairs = doc.get("contrast_pairs") or []
    if not pairs:
        raise ValueError("no contrast_pairs defined in tokens file")
    rows = []
    for p in pairs:
        usage = p.get("usage", "text")
        if usage not in MIN[level]:
            raise ValueError(f"unknown usage '{usage}' (use text, large-text or ui)")
        fg, bg = resolve(tokens, p["fg"]), resolve(tokens, p["bg"])
        exact = ratio(fg, bg)
        need = MIN[level][usage]
        # WCAG thresholds are not rounded: compare the exact ratio, round only for display.
        rows.append({"fg": p["fg"], "bg": p["bg"], "fg_value": fg, "bg_value": bg, "usage": usage,
                     "ratio": round(exact, 2), "required": need, "pass": exact >= need})
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tokens", type=Path)
    ap.add_argument("--level", choices=["AA", "AAA"], default="AA")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not args.tokens.is_file():
        die(f"tokens file not found: {args.tokens}")
    try:
        rows = check(load_json(args.tokens), args.level)
    except (ValueError, KeyError) as exc:
        die(str(exc))
    failed = [r for r in rows if not r["pass"]]
    if args.json:
        print(json.dumps({"level": args.level, "pairs": rows, "failed": len(failed)}, indent=2))
    else:
        for r in rows:
            mark = "PASS" if r["pass"] else "FAIL"
            print(f"{mark} {r['ratio']:>5.2f}:1 (min {r['required']}) {r['usage']:<10} {r['fg']} {r['fg_value']} on {r['bg']} {r['bg_value']}")
        print(f"WCAG {args.level}: {len(rows) - len(failed)}/{len(rows)} pairs pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
