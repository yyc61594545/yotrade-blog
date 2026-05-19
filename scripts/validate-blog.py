#!/usr/bin/env python3
"""
Validate blog frontmatter and detect basic issues.

Run:
  python scripts/validate-blog.py

Exits non-zero if any blog post has issues. Useful in CI / SessionStart.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOG_DIR = ROOT / "src" / "content" / "blog"

REQUIRED_FRONTMATTER = ["title", "description", "keywords", "pubDate", "updatedDate", "canonical", "tags"]

errors: list[str] = []
warnings: list[str] = []
seen_canonicals: dict[str, str] = {}


def parse_frontmatter(text: str) -> dict[str, str] | None:
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", "", text)
    return text


def check_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if not fm:
        errors.append(f"{path.name}: no frontmatter")
        return

    for key in REQUIRED_FRONTMATTER:
        if key not in fm:
            errors.append(f"{path.name}: missing frontmatter `{key}`")

    title = fm.get("title", "").strip("'\"")
    if title and len(title) > 80:
        errors.append(f"{path.name}: title too long ({len(title)} > 80)")

    desc = fm.get("description", "").strip("'\"")
    if desc and len(desc) > 180:
        errors.append(f"{path.name}: description too long ({len(desc)} > 180)")

    canonical = fm.get("canonical", "").strip("'\"")
    if canonical:
        if not canonical.startswith("https://blog.yotradeapi.com/blog/"):
            warnings.append(f"{path.name}: canonical not under /blog/: {canonical}")
        if not canonical.endswith("/"):
            errors.append(f"{path.name}: canonical missing trailing slash")
        if canonical in seen_canonicals:
            errors.append(
                f"{path.name}: duplicate canonical with {seen_canonicals[canonical]}: {canonical}"
            )
        else:
            seen_canonicals[canonical] = path.name

    if "draft: true" in text[: m.end() if (m := re.match(r"^---\n.*?\n---", text, re.DOTALL)) else 0]:
        warnings.append(f"{path.name}: draft (won't be published)")

    fm_block = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if fm_block:
        for key in ("tags", "keywords"):
            block = re.search(rf"^{key}:\n((?:- .*\n)+)", fm_block.group(1), re.MULTILINE)
            if not block:
                continue
            for item in re.findall(r"^- (.*)$", block.group(1), re.MULTILINE):
                if re.fullmatch(r"-?\d+(\.\d+)?", item.strip()):
                    errors.append(
                        f"{path.name}: `{key}` contains numeric value `{item}` "
                        f"(YAML parses as number — quote it as '{item}')"
                    )

    body = text[text.find("---", 3) + 3 :] if text.startswith("---") else text
    if len(body.strip()) < 800:
        warnings.append(f"{path.name}: body short ({len(body)} chars)")

    body_no_code = strip_code(body)
    for m2 in re.finditer(r"\]\((/blog/[^)]+)\)", body_no_code):
        link = m2.group(1)
        if not link.endswith("/"):
            warnings.append(f"{path.name}: internal link without trailing slash: {link}")


def check_internal_links() -> None:
    slugs = {p.stem for p in BLOG_DIR.glob("*.md")}
    for path in sorted(BLOG_DIR.glob("*.md")):
        text = strip_code(path.read_text(encoding="utf-8"))
        for m in re.finditer(r"\]\(/blog/([^/)#]+)/?\)", text):
            target = m.group(1)
            if target not in slugs:
                warnings.append(f"{path.name}: link to nonexistent /blog/{target}/")


def main() -> int:
    for path in sorted(BLOG_DIR.glob("*.md")):
        check_file(path)
    check_internal_links()

    total = len(list(BLOG_DIR.glob("*.md")))
    print(f"checked {total} blog posts")

    if warnings:
        print(f"\n{len(warnings)} warnings:")
        for w in warnings:
            print(f"  warn: {w}")
    if errors:
        print(f"\n{len(errors)} errors:")
        for e in errors:
            print(f"  err: {e}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
