#!/usr/bin/env python3
"""Validate architecture SVG files for GitHub/Markdown compatibility."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SVG_DIR = REPO_ROOT / "docs" / "architecture"

SVG_FILES = [
    "system-architecture.svg",
    "agent-lifecycle.svg",
    "provider-architecture.svg",
    "grounding-pipeline.svg",
]

FORBIDDEN_PATTERNS = [
    (r"<foreignObject\b", "foreignObject"),
    (r"<script\b", "script"),
    (r"https?://", "external URL"),
    (r"url\(\s*['\"]?(?!#)", "external url() reference"),
    (r"<style\b", "style block (stripped by GitHub)"),
    (r"@import\b", "CSS @import"),
    (r"<link\b", "external stylesheet link"),
    (r"xlink:href\s*=\s*['\"]http", "external xlink:href"),
]

SVG_NS = "http://www.w3.org/2000/svg"


def validate_svg(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")

    # Strip xmlns (required SVG namespace is not an external dependency)
    stripped = re.sub(r'xmlns="http://www\.w3\.org/2000/svg"', "", text)
    for pattern, label in FORBIDDEN_PATTERNS:
        if re.search(pattern, stripped, re.IGNORECASE):
            errors.append(f"forbidden: {label}")

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        errors.append(f"XML parse error: {exc}")
        return errors

    if root.tag != f"{{{SVG_NS}}}svg":
        errors.append(f"root element is {root.tag!r}, expected svg")

    view_box = root.attrib.get("viewBox")
    if not view_box:
        errors.append("missing viewBox attribute")
    else:
        parts = view_box.split()
        if len(parts) != 4:
            errors.append(f"invalid viewBox: {view_box!r}")
        else:
            try:
                w, h = float(parts[2]), float(parts[3])
                if w <= 0 or h <= 0:
                    errors.append(f"non-positive viewBox dimensions: {view_box}")
            except ValueError:
                errors.append(f"non-numeric viewBox: {view_box!r}")

    # Check referenced gradient/marker IDs if any url(#id) present
    ids = {el.attrib["id"] for el in root.iter() if "id" in el.attrib}
    for match in re.finditer(r"url\(#([^)]+)\)", text):
        ref_id = match.group(1)
        if ref_id not in ids:
            errors.append(f"referenced id #{ref_id} not defined")

    # Warn if class= is used without inline fill on text (GitHub strips styles)
    if 'class="' in text:
        errors.append("uses class attribute (styles may not apply on GitHub)")

    return errors


def main() -> int:
    failures = 0
    for name in SVG_FILES:
        path = SVG_DIR / name
        if not path.exists():
            print(f"FAIL {name}: file not found")
            failures += 1
            continue
        errors = validate_svg(path)
        if errors:
            print(f"FAIL {name}:")
            for err in errors:
                print(f"  - {err}")
            failures += 1
        else:
            print(f"OK   {name}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
