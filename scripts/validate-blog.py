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
import subprocess
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
    # Bing 的 URL Inspection 把超过 160 字符的 description 报成 SEO error
    # （2026-09-22 pay-for-jimeng 那篇 176 字符被报过）。这里只警告不报错，
    # schema 仍是 180，免得日更 agent 写长一点就卡住上线。
    elif desc and len(desc) > 160:
        warnings.append(f"{path.name}: description over Bing's 160-char limit ({len(desc)})")

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


# 改旧文时最容易悄悄丢掉的元素（2026-10-10 起）：AI 改写会删表格、图片、导流链接，
# 不报错也没提示。这里拿工作区版本和 HEAD 比，数量变少就警告，由 daily-post 写进 commit 信息。
LOSS_PATTERNS = {
    "表格": r"^\|[\s:|-]*-[\s:|-]*\|?\s*$",
    "图片": r"!\[[^\]]*\]\(",
    "代码块": r"^```",
    "站内链接": r"\]\(/blog/",
    "导流链接": r"\]\(https://yotradeapi\.com",
    "外部链接": r"\]\(https?://(?!yotradeapi\.com)",
    "H2": r"^## ",
    "H3": r"^### ",
}


def count_elements(text: str) -> dict[str, int]:
    return {k: len(re.findall(p, text, re.MULTILINE)) for k, p in LOSS_PATTERNS.items()}


def check_losses() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=M", "HEAD", "--", str(BLOG_DIR)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    losses: list[str] = []
    for rel in out.split():
        path = ROOT / rel
        old = subprocess.run(
            ["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, text=True
        ).stdout
        before, after = count_elements(old), count_elements(path.read_text(encoding="utf-8"))
        lost = [f"{k} {before[k]}→{after[k]}" for k in LOSS_PATTERNS if after[k] < before[k]]
        if lost:
            losses.append(f"{path.name}: " + "，".join(lost))
    return losses


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
    losses = check_losses()
    if losses:
        print(f"\nLOSS: {len(losses)} 篇改动后元素变少（和 HEAD 比），确认是有意删的：")
        for item in losses:
            print(f"  loss: {item}")
    if errors:
        print(f"\n{len(errors)} errors:")
        for e in errors:
            print(f"  err: {e}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
