#!/usr/bin/env bash
# 用法：bash scripts/new-post.sh <slug>
# 创建一篇带规范 frontmatter 的新文章草稿。

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <slug>" >&2
    echo "  slug = file name without .md, also used in canonical URL" >&2
    exit 1
fi

SLUG="$1"
TARGET="src/content/blog/${SLUG}.md"
TODAY="$(date -u +%Y-%m-%d)"

if [ -e "$TARGET" ]; then
    echo "file exists: $TARGET" >&2
    exit 1
fi

cat > "$TARGET" <<EOF
---
title: TODO 标题（≤ 80 字）
description: TODO 描述（≤ 180 字）
keywords:
- TODO 关键词 1
- TODO 关键词 2
pubDate: '${TODAY}'
updatedDate: '${TODAY}'
canonical: https://blog.yotradeapi.com/blog/${SLUG}/
tags:
- TODO 标签
category: TODO 分类
draft: true
heroImage: ../../assets/blog-placeholder-1.jpg
---

# TODO 标题

引子段落：1–2 句话说清这篇文章解决什么问题。

## 一、章节标题

正文内容。具体、紧凑、不要套话。

## 二、相关阅读

- [文章标题](/blog/some-other-post/)

需要在国内稳定调用 AI API？在 [YoTradeApi 注册](https://yotradeapi.com/register) 创建独立 API Key 接入即可。
EOF

echo "created: $TARGET"
echo "remember: set draft: false when ready to publish, then run:"
echo "  python3 scripts/validate-blog.py"
