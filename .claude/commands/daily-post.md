---
description: 自动产出当天一篇博客：选题 → 写稿 → 校验 → 提交 → 推送
---

# /daily-post — 每日一篇

按下面流程**完整执行**，每一步做完直接进下一步，不要中途询问用户（这是定时任务）。

## 1. 选题

跑 `python3 scripts/pick-next-topic.py`，得到 JSON：

```json
{ "slug": "...", "title": "...", "category": "...", "remaining": N }
```

**记住 slug / title / category。** 三个字段决定文件名、首屏标题、frontmatter `category`。

如果脚本以非 0 退出（池子空 / 解析失败）：
- 不要 fallback 自己编 slug
- 直接 commit 一个空 marker 文件 `scripts/.pool-exhausted-YYYY-MM-DD`（提示用户补池），然后退出
- 退出前在终端打印 "⚠️  topic pool exhausted，请编辑 scripts/topic-pool.md 追加候选"

## 2. 写稿

在 `src/content/blog/<slug>.md` 创建文章。**严格遵循 frontmatter schema**（见 `src/content.config.ts`）：

```yaml
---
title: <选题 title，≤80 字符>
description: <120–180 字符，含核心关键词，不堆砌>
keywords:
  - <长尾词 1>
  - <长尾词 2>
  - <长尾词 3>
  - <长尾词 4>
  - <长尾词 5>
pubDate: '<今天日期 YYYY-MM-DD>'
updatedDate: '<同上>'
canonical: https://blog.yotradeapi.com/blog/<slug>/
tags:
  - <tag1>
  - <tag2>
  - <tag3>
  - <tag4>
category: <picker 给的 category>
heroImage: ../../assets/blog-placeholder-<1-5 随机>.jpg
---
```

**Frontmatter 红线**：

- `title` ≤ 80 字符
- `description` ≤ 180 字符
- `canonical` 必须以 `/` 结尾
- `tags` 元素必须是字符串。**含纯数字（如年份）的 tag 一律加单引号**：`- '2026'`
- `keywords` 至少 5 个，覆盖主词 + 长尾
- `category` 用 picker 给的，不要自创新分类

**正文要求**：

- 1800–3500 字，分 5–9 个二级标题（`## 一、`/`## 二、` 中文序号或意译标题）
- 至少 1 个表格 或 1 个代码块（看选题适配）
- 中文为主，技术术语保留英文（如 Claude Code、MCP、SSE）
- 避免空话套话；每一节给"可操作的结论"或"可复用的判断"
- **若选题是"行业观察 / 趋势 / 新闻"**：
  - 不要编造具体时间线、融资数字、未公开事件
  - 用"行业普遍观察 / 公开信息整理 / 个人判断"的口吻
  - 任何具体数字标注为"近似 / 估算 / 仅作参考"

**结尾必须**有这两段：

```markdown
## N、相关阅读

- [<相关文章标题 1>](/blog/<existing-slug-1>/)
- [<相关文章标题 2>](/blog/<existing-slug-2>/)
- [<相关文章标题 3>](/blog/<existing-slug-3>/)
- [<相关文章标题 4>](/blog/<existing-slug-4>/)

<一句导流话术>，[YoTradeApi](https://yotradeapi.com) <相关好处一句>。
```

**相关阅读必须 3–5 条，全部链到已存在的文章**（`ls src/content/blog/*.md` 拿 slug 列表，挑相关性最高的）。链接结尾要带 `/`。

**CTA 链接固定为** `https://yotradeapi.com`（**不**带 `/register` 或其他路径）。

## 3. 校验

跑 `python3 scripts/validate-blog.py`。

- 通过：继续下一步
- 失败：根据报错修正（最常见：title/description 超长、tag 是数字、canonical 缺 `/`、内链 slug 不存在）→ 再跑一次 → 必须通过才能进下一步

## 4. 提交并推送

```bash
git add src/content/blog/<slug>.md
git commit -m "content: <category> | <title>"
git push origin main
```

提交信息固定格式 `content: <category> | <title>`，方便后续 git log 检索。

## 5. 选题池余量提醒

picker 输出的 `remaining < 20` 时，在最后回复里加一句：

> ⚠️ 选题池仅剩 N 个，建议补充 `scripts/topic-pool.md`

## 6. 结束语

回复用户**一段话内**说清楚：

1. 今天发布的文章标题 + 链接 `https://blog.yotradeapi.com/blog/<slug>/`
2. 选题池剩余数量
3. commit SHA（`git log -1 --format=%h`）

**不要**：
- 在结尾贴整段文章
- 询问用户是否需要其他操作
- 解释你的选题理由

任务完成后即可结束。
