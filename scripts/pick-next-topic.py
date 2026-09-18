#!/usr/bin/env python3
"""
Pick the next blog topic from scripts/topic-pool.md.

Rules
- Parse lines of form `- slug | title | category` from topic-pool.md.
- Skip slugs already published (file exists under src/content/blog/<slug>.md).
- Only `cn-` slugs are eligible (2026-09-18): they bring 88% of blog traffic.
- Entries under a heading containing 【优先】 go first, in pool order.
- Rotate categories: prefer a category that did NOT appear in the most
  recent 7 published posts (sorted by mtime). Tie-break by pool order.
- Output a JSON object: {"slug", "title", "category", "remaining": N}
- Exit non-zero with a clear message if pool is empty or unparsable.

Used by `/daily-post` (see .claude/commands/daily-post.md).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "scripts" / "topic-pool.md"
BLOG = ROOT / "src" / "content" / "blog"

LINE_RE = re.compile(r"^- ([a-z0-9][a-z0-9-]*)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*$")
PRIORITY_MARK = "【优先】"
SLUG_PREFIX = "cn-"


def parse_pool() -> list[tuple[str, str, str, bool]]:
    """Return (slug, title, category, is_priority) for every pool line."""
    if not POOL.exists():
        sys.exit(f"error: topic pool missing at {POOL}")
    items: list[tuple[str, str, str, bool]] = []
    priority = False
    for raw in POOL.read_text(encoding="utf-8").splitlines():
        if raw.startswith("#"):
            priority = PRIORITY_MARK in raw
            continue
        m = LINE_RE.match(raw)
        if m:
            items.append((m.group(1), m.group(2), m.group(3), priority))
    return items


def published_slugs() -> set[str]:
    return {p.stem for p in BLOG.glob("*.md")}


def recent_categories(limit: int = 7) -> list[str]:
    files = sorted(BLOG.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    cats: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^category:\s*(.+?)\s*$", text, re.MULTILINE)
        if m:
            cats.append(m.group(1).strip("'\""))
    return cats


def main() -> int:
    items = parse_pool()
    if not items:
        sys.exit("error: no parsable entries in topic-pool.md")

    published = published_slugs()
    available = [
        (s, t, c, p) for s, t, c, p in items if s.startswith(SLUG_PREFIX) and s not in published
    ]
    if not available:
        sys.exit(f"error: no unpublished {SLUG_PREFIX} topics left; extend topic-pool.md")

    priority = [x for x in available if x[3]]
    if priority:
        pick = priority[0]
    else:
        recent_set = set(recent_categories())
        # Prefer a candidate whose category is NOT in the last 7 posts; keep pool order.
        pick = next((x for x in available if x[2] not in recent_set), available[0])

    out = {
        "slug": pick[0],
        "title": pick[1],
        "category": pick[2],
        "remaining": len(available) - 1,
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
