"""Minimal JSON Schema (draft 2020-12 subset) validator, standard library only.

Supported keywords: type, enum, const, required, properties, additionalProperties,
items, minItems, maxItems, uniqueItems, minLength, maxLength, pattern, minimum,
maximum, exclusiveMinimum, exclusiveMaximum, allOf, anyOf, oneOf, not, if/then/else,
$ref (local "#/$defs/..." only), format (date and date-time only, others ignored).

Unsupported keywords are rejected by `check_schema` so that schemas never rely on
something this validator silently ignores.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, List

SUPPORTED = {
    "$schema", "$id", "$defs", "$ref", "$comment", "title", "description", "default",
    "examples", "type", "enum", "const", "required", "properties",
    "additionalProperties", "items", "minItems", "maxItems", "uniqueItems", "minLength",
    "maxLength", "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "allOf", "anyOf", "oneOf", "not", "if", "then", "else", "format",
}
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _fmt_ok(fmt: str, value: str) -> bool:
    try:
        if fmt == "date":
            date.fromisoformat(value)
        elif fmt == "date-time":
            datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


class Validator:
    def __init__(self, schema: dict):
        self.root = schema

    def _resolve(self, ref: str) -> dict:
        if not ref.startswith("#/"):
            raise ValueError(f"only local refs are supported: {ref}")
        node: Any = self.root
        for part in ref[2:].split("/"):
            node = node[part]
        return node

    def errors(self, value: Any, schema: Any = None, path: str = "$") -> List[str]:
        if schema is None:
            schema = self.root
        if schema is True or schema == {}:
            return []
        if schema is False:
            return [f"{path}: not allowed"]
        errs: List[str] = []
        if "$ref" in schema:
            errs += self.errors(value, self._resolve(schema["$ref"]), path)
        t = schema.get("type")
        if t is not None:
            types = t if isinstance(t, list) else [t]
            if not any(_TYPES[x](value) for x in types):
                return errs + [f"{path}: expected {'/'.join(types)}, got {type(value).__name__}"]
        if "enum" in schema and value not in schema["enum"]:
            errs.append(f"{path}: {value!r} not in {schema['enum']}")
        if "const" in schema and value != schema["const"]:
            errs.append(f"{path}: must be {schema['const']!r}")
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                errs.append(f"{path}: shorter than {schema['minLength']}")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                errs.append(f"{path}: longer than {schema['maxLength']}")
            if "pattern" in schema and not re.search(schema["pattern"], value):
                errs.append(f"{path}: {value!r} does not match {schema['pattern']}")
            if "format" in schema and not _fmt_ok(schema["format"], value):
                errs.append(f"{path}: not a valid {schema['format']}")
        if _TYPES["number"](value):
            if "minimum" in schema and value < schema["minimum"]:
                errs.append(f"{path}: below minimum {schema['minimum']}")
            if "maximum" in schema and value > schema["maximum"]:
                errs.append(f"{path}: above maximum {schema['maximum']}")
            if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
                errs.append(f"{path}: must be > {schema['exclusiveMinimum']}")
            if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
                errs.append(f"{path}: must be < {schema['exclusiveMaximum']}")
        if isinstance(value, dict):
            for key in schema.get("required", []):
                if key not in value:
                    errs.append(f"{path}: missing required '{key}'")
            props = schema.get("properties", {})
            for key, sub in props.items():
                if key in value:
                    errs += self.errors(value[key], sub, f"{path}.{key}")
            extra = schema.get("additionalProperties", True)
            for key in value:
                if key in props:
                    continue
                if extra is False:
                    errs.append(f"{path}: unexpected property '{key}'")
                elif isinstance(extra, dict):
                    errs += self.errors(value[key], extra, f"{path}.{key}")
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                errs.append(f"{path}: fewer than {schema['minItems']} items")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                errs.append(f"{path}: more than {schema['maxItems']} items")
            if schema.get("uniqueItems"):
                seen = [json.dumps(v, sort_keys=True) for v in value]
                if len(seen) != len(set(seen)):
                    errs.append(f"{path}: items are not unique")
            if "items" in schema:
                for i, item in enumerate(value):
                    errs += self.errors(item, schema["items"], f"{path}[{i}]")
        for sub in schema.get("allOf", []):
            errs += self.errors(value, sub, path)
        if "anyOf" in schema and not any(not self.errors(value, s, path) for s in schema["anyOf"]):
            errs.append(f"{path}: does not match any of anyOf")
        if "oneOf" in schema:
            n = sum(1 for s in schema["oneOf"] if not self.errors(value, s, path))
            if n != 1:
                errs.append(f"{path}: matches {n} of oneOf (expected exactly 1)")
        if "not" in schema and not self.errors(value, schema["not"], path):
            errs.append(f"{path}: must not match 'not' schema")
        if "if" in schema:
            if not self.errors(value, schema["if"], path):
                if "then" in schema:
                    errs += self.errors(value, schema["then"], path)
            elif "else" in schema:
                errs += self.errors(value, schema["else"], path)
        return errs


def check_schema(schema: dict) -> List[str]:
    """Structural sanity check of a schema document (not a full meta-validation)."""
    problems: List[str] = []
    if schema.get("$schema") != SCHEMA_DIALECT:
        problems.append(f"$schema must be {SCHEMA_DIALECT}")

    def walk(node: Any, path: str) -> None:
        if isinstance(node, bool):
            return
        if not isinstance(node, dict):
            problems.append(f"{path}: schema must be an object or boolean")
            return
        for key in node:
            if key not in SUPPORTED:
                problems.append(f"{path}: unsupported keyword '{key}'")
        if "type" in node:
            types = node["type"] if isinstance(node["type"], list) else [node["type"]]
            for t in types:
                if t not in _TYPES:
                    problems.append(f"{path}: unknown type '{t}'")
        if "pattern" in node:
            try:
                re.compile(node["pattern"])
            except re.error as exc:
                problems.append(f"{path}: bad pattern ({exc})")
        if "$ref" in node:
            try:
                Validator(schema)._resolve(node["$ref"])
            except (KeyError, ValueError):
                problems.append(f"{path}: unresolvable $ref {node['$ref']}")
        for key in ("properties", "$defs"):
            for name, sub in node.get(key, {}).items():
                walk(sub, f"{path}.{key}.{name}")
        for key in ("items", "additionalProperties", "not", "if", "then", "else"):
            if isinstance(node.get(key), dict):
                walk(node[key], f"{path}.{key}")
        for key in ("allOf", "anyOf", "oneOf"):
            for i, sub in enumerate(node.get(key, [])):
                walk(sub, f"{path}.{key}[{i}]")

    walk(schema, "#")
    return problems


SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def load_schema(name: str) -> dict:
    """Load a bundled schema by short name, e.g. 'state' -> schemas/state.schema.json."""
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def validate(value: Any, name: str) -> List[str]:
    return Validator(load_schema(name)).errors(value)
