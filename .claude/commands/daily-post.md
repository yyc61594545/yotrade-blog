---
description: 自动产出今日 N 篇博客（默认 3）：循环 N 次选题→写稿→校验→提交，最后开 PR 合并到 main
---

# /daily-post — 每日 N 篇

按下面流程**完整执行**，每一步做完直接进下一步，不要中途询问用户（这是定时任务）。

## 0. 参数

`$ARGUMENTS` = 本次要产出的文章数。

- 如果 `$ARGUMENTS` 是 1–10 之间的整数，则 `N = $ARGUMENTS`
- 否则 `N = 3`（默认）

## 1. 循环：N 次选题 + 写稿 + 校验 + 提交

**对 i 从 1 到 N，重复执行 1.1 → 1.5**。每篇文章是独立的 commit，不要把多篇合并成一个 commit。

### 1.1 选题

跑 `python3 scripts/pick-next-topic.py`，得到 JSON：

```json
{ "slug": "...", "title": "...", "category": "...", "remaining": N }
```

- picker 已自动跳过仓库里已存在的 slug，包括**本会话之前几次循环里已经 commit 的文章**（因为文件已落地）
- **记住 slug / title / category**

如果脚本以非 0 退出（池子空 / 解析失败）：

- 不要 fallback 自己编 slug
- 在终端打印 "⚠️  topic pool exhausted at i=<i>，已成功发布 <i-1> 篇"
- 跳出循环，直接进入第 2 步（处理已经写完的部分）

### 1.2 写稿

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
- **不要**在 frontmatter 之后再写一个 `# 大标题`——模板已渲染 `<h1>`，重复会有两个 H1
- 至少 1 个表格 或 1 个代码块（看选题适配）
- 中文为主，技术术语保留英文（如 Claude Code、MCP、SSE）
- 避免空话套话；每一节给"可操作的结论"或"可复用的判断"
- **避免与已发布文章大段重复**：动笔前用 `ls src/content/blog/` + 关键词判断是否已有近似主题的文章。若某个子话题（如"虚拟信用卡付款"、"API 中转配置步骤"）已被其他文章详细覆盖，本文只用一两句话带过并**内链指向那篇**，不要整节重写。聚焦本文标题独有的角度
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

**相关阅读必须 3–5 条，全部链到已存在的文章**（`ls src/content/blog/*.md` 拿 slug 列表，挑相关性最高的）。链接结尾要带 `/`。**优先内链到本次循环里前几篇文章**（它们文件已存在），有助内链密度。

**CTA 链接固定为** `https://yotradeapi.com`（**不**带 `/register` 或其他路径）。

### 1.3 校验

跑 `python3 scripts/validate-blog.py`。

- 通过：继续下一步
- 失败：根据报错修正（最常见：title/description 超长、tag 是数字、canonical 缺 `/`、内链 slug 不存在）→ 再跑一次 → 必须通过才能进 1.4

### 1.4 commit

```bash
git add src/content/blog/<slug>.md
git commit -m "content: <category> | <title>"
```

每篇一个 commit。**不要 push**——push 留到全部写完后统一做（节省 CI 抖动）。

### 1.5 进入下一次循环

i++，回到 1.1。

## 2. 推送并合并到 main

N 篇全部 commit 完成后：

```bash
CURRENT_BRANCH=$(git branch --show-current)
git push origin "$CURRENT_BRANCH"
```

- **如果 `CURRENT_BRANCH == main`**：到此结束，部署已触发
- **如果 `CURRENT_BRANCH != main`**：用 GitHub MCP 一次性合并所有 commit：
  1. `mcp__github__create_pull_request`
     - `owner`: `yyc61594545`
     - `repo`: `yotrade-blog`
     - `head`: `<CURRENT_BRANCH>`
     - `base`: `main`
     - `title`: `daily: <实际产出篇数> 篇文章（<YYYY-MM-DD>）`
     - `body`: 列出每篇的 `- <category> | <title>`
  2. `mcp__github__merge_pull_request`
     - `owner`: `yyc61594545`
     - `repo`: `yotrade-blog`
     - `pullNumber`: <上一步返回的 PR number>
     - `mergeMethod`: `SQUASH`

合并后 main 触发 Cloudflare Pages 部署。

## 3. 通知 IndexNow 实时索引

PR 合并到 main 后，立刻把本次新增的 N 篇文章 URL 推送给 IndexNow API。这能让 Bing / Yandex / Seznam / Naver 5 个搜索引擎在几分钟内索引新文章（比等爬虫快 10 倍）。

把本次循环里 commit 的所有 slug 填到 SLUGS 数组里（**不要包含已发布的 slug**），跑：

```bash
python3 <<'PYEOF'
import urllib.request as r, json

KEY = '0618cefdb7e64035a4b169a872de5a78'

# 填入本次循环产出的所有 slug（不带前缀，不带 .md）
SLUGS = [
    # "<slug-1>",
    # "<slug-2>",
    # "<slug-3>",
    # "<slug-4>",
    # "<slug-5>",
]

if not SLUGS:
    print('⚠️ SLUGS 空，跳过 IndexNow 通知')
else:
    urls = [f'https://blog.yotradeapi.com/blog/{s}/' for s in SLUGS]
    payload = {
        'host': 'blog.yotradeapi.com',
        'key': KEY,
        'keyLocation': f'https://blog.yotradeapi.com/{KEY}.txt',
        'urlList': urls,
    }
    data = json.dumps(payload).encode()
    req = r.Request('https://api.indexnow.org/indexnow', data=data,
                     headers={'Content-Type': 'application/json; charset=utf-8'},
                     method='POST')
    try:
        resp = r.urlopen(req, timeout=15)
        print(f'✅ IndexNow notified: HTTP {resp.status} for {len(urls)} URLs')
    except Exception as e:
        print(f'⚠️ IndexNow notify failed: {type(e).__name__} {e}')
        # 不阻塞 routine，下次 IndexNow 自动重试或 Bing 自己从 sitemap 抓
PYEOF
```

**关键约束**：
- 必须在 PR 合并到 main 之后跑（保证 main 上 URL 已生效）
- IndexNow 失败不阻塞 routine 完成（nice-to-have，不是 must-have）
- 如果本次 0 篇发布（池子空），跳过本步

## 4. 选题池余量提醒

最后一次 picker 输出的 `remaining < 30` 时，在结束语里加一行：

> ⚠️ 选题池仅剩 N 个（按每日 3 篇计算约够 N/3 天），建议补充 `scripts/topic-pool.md`

## 5. 结束语

回复用户**一段话内**说清楚：

1. 今天实际发布的文章数（如果池子中途空了，按实际数）
2. 每篇的标题 + URL `https://blog.yotradeapi.com/blog/<slug>/`
3. 选题池剩余数量
4. PR URL（如果走了 PR）或 commit SHA

**不要**：
- 在结尾贴整段文章正文
- 询问用户是否需要其他操作
- 解释你的选题理由

任务完成后即可结束。
