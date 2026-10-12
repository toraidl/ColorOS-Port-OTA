#!/usr/bin/env python3
"""Convert an OPPO ColorOS changelog HTML page into docs/changelog.json.

The stock updater shows the changelog from an OPPO CDN HTML page
(gauss-compotacostauto-cn.allawnfs.com/...). We snapshot that page's
`<dt>/<dd>` sections so our hosted update page can render them offline and the
content survives the CDN link going away.

Usage: python3 tools/fetch_changelog.py <url>
"""
import html
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "changelog.json"


def strip_tags(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def parse(page: str) -> dict:
    sections = []
    for title, body in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", page, re.S | re.I):
        title = strip_tags(title)
        items = [ln.strip() for ln in strip_tags(body).split("\n") if ln.strip()]
        if title or items:
            sections.append({"title": title, "items": items})
    notes = []
    for note in re.findall(r'<div class="note">(.*?)</div>\s*</div>', page, re.S | re.I):
        for h4, ul in re.findall(r"<h4>(.*?)</h4>(.*?)(?:<h4>|$)", note, re.S | re.I):
            items = [strip_tags(li) for li in re.findall(r"<li>(.*?)</li>", ul, re.S | re.I)]
            items = [i for i in items if i]
            if items:
                notes.append({"title": strip_tags(h4), "items": items})
    return {"sections": sections, "notes": notes}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    url = sys.argv[1]
    req = urllib.request.Request(url, headers={"User-Agent": "ColorOS-Port-OTA/changelog"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        page = resp.read().decode("utf-8", "replace")
    data = parse(page)
    data["source"] = url
    data["sectionCount"] = len(data["sections"])
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['sections'])} section(s), "
          f"{sum(len(s['items']) for s in data['sections'])} item(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
