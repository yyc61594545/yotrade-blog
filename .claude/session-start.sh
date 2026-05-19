#!/usr/bin/env bash
# Inject project context for every Claude Code / web session.
# Output here is appended to the model's system context.

set -u

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0

cat <<'EOF'
# YoTradeApi Blog 项目知识

## 是什么
面向中文开发者的 SEO 博客。导流到 yotradeapi.com（AI API 中转）。
站点：https://blog.yotradeapi.com

## 技术栈
- Astro 6 + MDX
- @astrojs/sitemap + @astrojs/rss
- Cloudflare Pages 部署
- Node >= 22.12

## 目录结构关键点
- src/content/blog/*.md → 文章 markdown（frontmatter schema 见 src/content.config.ts）
- src/pages/blog/[...slug].astro → 文章页路由
- src/pages/{tags,categories,tools,compare,pricing-tracker}/ → 索引页
- src/layouts/BlogPost.astro → 文章布局（含面包屑、相关文章、CTA）
- src/components/BaseHead.astro → SEO meta + JSON-LD

## 写新文章要点
1. 文件名 = slug = canonical URL 最后一段
2. 必填 frontmatter: title (≤80) / description (≤180) / keywords / pubDate /
   updatedDate / canonical / tags / category
3. 文末必须有"相关阅读"内链 + YoTradeApi 注册 CTA
4. 写完跑 `python3 scripts/validate-blog.py`

## 关键命令
- python3 scripts/validate-blog.py  → 校验所有文章
- npm run dev                       → 本地开发（如能装 node_modules）
- npm run build                     → 构建（部署用）

## 部署
push to main → GitHub Actions → Cloudflare Pages 自动部署
开发分支：claude/yotradeapi-blog-system-Jf8G5
EOF

# 校验文章（仅打印错误，不阻塞会话）
if command -v python3 >/dev/null 2>&1; then
    python3 scripts/validate-blog.py 2>&1 | tail -5 || true
fi

# 当前文章统计
n=$(ls src/content/blog/*.md 2>/dev/null | wc -l | tr -d ' ')
echo ""
echo "当前文章数：$n"
echo "最新 3 篇："
ls -t src/content/blog/*.md 2>/dev/null | head -3 | sed 's|src/content/blog/|  - |'
