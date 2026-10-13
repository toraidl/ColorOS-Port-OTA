#!/usr/bin/env python3
"""Validate devices/*.json against schema/device.schema.json plus extra sanity."""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEVICES = ROOT / "devices"
SCHEMA = ROOT / "schema" / "device.schema.json"

ALLOWED_URL_HOSTS = {
    "sourceforge.net",
    "downloads.sourceforge.net",
    "master.dl.sourceforge.net",
    "github.com",
    "raw.githubusercontent.com",
    "cdn.jsdelivr.net",
}


def load_schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def minimal_check(obj: dict, schema: dict, where: str) -> list[str]:
    """Small subset of JSON Schema - enough for our flat manifest."""
    errs: list[str] = []
    required = schema.get("required", [])
    props = schema.get("properties", {})
    for key in required:
        if key not in obj:
            errs.append(f"{where}: missing required field '{key}'")
    if schema.get("additionalProperties") is False:
        for key in obj:
            if key not in props:
                errs.append(f"{where}: unknown field '{key}'")
    for key, spec in props.items():
        if key not in obj:
            continue
        val = obj[key]
        t = spec.get("type")
        if t == "string" and not isinstance(val, str):
            errs.append(f"{where}: '{key}' must be a string")
            continue
        if t == "integer" and not isinstance(val, int):
            errs.append(f"{where}: '{key}' must be an integer")
            continue
        if t == "array" and not isinstance(val, list):
            errs.append(f"{where}: '{key}' must be an array")
            continue
        if t == "string":
            if "minLength" in spec and len(val) < spec["minLength"]:
                errs.append(f"{where}: '{key}' shorter than {spec['minLength']}")
            if "pattern" in spec and not re.search(spec["pattern"], val):
                errs.append(f"{where}: '{key}' does not match {spec['pattern']}")
            if "enum" in spec and val not in spec["enum"]:
                errs.append(f"{where}: '{key}' must be one of {spec['enum']}")
        if t == "integer" and "minimum" in spec and val < spec["minimum"]:
            errs.append(f"{where}: '{key}' below minimum {spec['minimum']}")
    return errs


def check_device(path: pathlib.Path, schema: dict) -> list[str]:
    where = f"devices/{path.name}"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{where}: invalid JSON: {exc}"]
    if not isinstance(obj, dict):
        return [f"{where}: root must be an object"]

    errs = minimal_check(obj, schema, where)
    if errs:
        return errs

    if obj["device"] != path.stem:
        errs.append(f"{where}: 'device' {obj['device']} != filename {path.stem}")

    url = obj["url"]
    host = re.sub(r"^https://([^/]+).*$", r"\1", url)
    if host not in ALLOWED_URL_HOSTS:
        errs.append(f"{where}: url host '{host}' not in allow-list")

    if not obj.get("size"):
        errs.append(f"{where}: 'size' must be the real package size in bytes")

    changelog = obj.get("changelog")
    if changelog:
        log_path = ROOT / changelog
        if not log_path.is_file():
            errs.append(f"{where}: changelog '{changelog}' does not exist")
        expected_dir = f"changelogs/{obj['device']}/"
        if not changelog.startswith(expected_dir):
            errs.append(f"{where}: changelog should live under {expected_dir}")
    elif "description" not in obj and "descriptionUrl" not in obj:
        errs.append(f"{where}: needs one of changelog / description / descriptionUrl")

    return errs


def main() -> int:
    schema = load_schema()
    files = sorted(DEVICES.glob("*.json"))
    if not files:
        print("no device manifests found")
        return 1
    all_errs: list[str] = []
    warnings: list[str] = []
    for path in files:
        all_errs.extend(check_device(path, schema))
        obj = json.loads(path.read_text(encoding="utf-8"))
        if not obj.get("md5"):
            warnings.append(f"devices/{path.name}: md5 is empty (downloads still "
                            f"work, but the package is not integrity checked)")
    for err in all_errs:
        print("FAIL", err)
    for warn in warnings:
        print("WARN", warn)
    if all_errs:
        print(f"{len(all_errs)} problem(s)")
        return 1
    print(f"OK {len(files)} device manifest(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
