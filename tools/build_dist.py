#!/usr/bin/env python3
"""Build dist/<DEVICE>.json from devices/ + changelogs/.

Renders each changelog to a small HTML blob and inlines it as `description`
so the on-device updater can display it without an extra fetch.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEVICES = ROOT / "devices"
DIST = ROOT / "dist"


def md_to_html(md: str) -> str:
    out: list[str] = []
    in_list = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            if in_list:
                out.append("</ul>")
                in_list = False
            level = min(len(heading.group(1)) + 1, 6)
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            continue
        bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
        if bullet:
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(bullet.group(1))}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"<p>{inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def build_one(path: pathlib.Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    log_rel = obj.get("changelog")
    if log_rel:
        body = md_to_html((ROOT / log_rel).read_text(encoding="utf-8"))
        obj["description"] = body
        del obj["changelog"]
    return obj


def main() -> int:
    DIST.mkdir(exist_ok=True)
    index: list[dict] = []
    for path in sorted(DEVICES.glob("*.json")):
        obj = build_one(path)
        target = DIST / f"{obj['device']}.json"
        target.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        index.append({
            "device": obj["device"],
            "version": obj["version"],
            "coloros": obj.get("coloros", ""),
            "android": obj.get("android", ""),
            "manifest": target.name,
        })
        print("built", target.relative_to(ROOT))
    (DIST / "index.json").write_text(
        json.dumps({"devices": index}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print("built dist/index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
