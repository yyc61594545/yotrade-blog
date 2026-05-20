# YoTradeApi Blog

面向中文开发者的 AI API 中转与开发者工具配置实测博客。
站点：https://blog.yotradeapi.com

## 内容主题

- **工具配置**：Cursor、Claude Code、Cline、Aider、Cherry Studio、Codex CLI、Continue.dev、Roo Code、Windsurf、Open WebUI
- **模型评测**：Claude (Opus/Sonnet/Haiku) / GPT-5 / Gemini / Grok / DeepSeek / Qwen 实测对比
- **工程实战**：RAG、Agent SDK、流式、可观测性、token 计算、性能优化、limit 处理
- **成本优化**：prompt caching、模型分级、预算管理
- **故障排查**：错误码、限速、流式断流、长上下文
- **安全合规**：API Key 管理、数据边界、应急响应
- **实战案例**：用 AI 写 SaaS、重构遗留项目等

## 技术栈

- Astro 6 + MDX + @astrojs/sitemap + @astrojs/rss
- Cloudflare Pages（GitHub Actions 自动部署）
- Node >= 22.12

## 项目结构

```
src/
├── content/blog/        # 90+ 篇 markdown 文章
├── content.config.ts    # frontmatter schema
├── layouts/
│   └── BlogPost.astro   # 文章布局（含面包屑、相关文章、CTA）
├── components/          # Header / Footer / BaseHead 等
├── pages/
│   ├── index.astro      # 首页
│   ├── about.astro
│   ├── tools.astro      # 工具索引
│   ├── blog/            # 文章列表 + 详情
│   ├── tags/            # 标签
│   ├── categories/      # 分类
│   ├── compare/         # 服务对比
│   ├── pricing-tracker/ # 价格追踪
│   └── 404.astro
└── styles/global.css
scripts/
├── validate-blog.py     # 文章质量校验
└── new-post.sh          # 生成符合规范的草稿
.claude/
├── settings.json        # SessionStart hook 配置
└── session-start.sh     # 注入项目知识
```

## 常用命令

| 命令 | 作用 |
| --- | --- |
| `python3 scripts/validate-blog.py` | 校验所有文章 frontmatter + 内链 |
| `bash scripts/new-post.sh <slug>` | 生成符合规范的文章草稿 |
| `npm run dev` | 本地开发服务器 |
| `npm run build` | 构建生产版本 |
| `npm run deploy` | 部署到 Cloudflare Pages |

## 写新文章规范

1. 文件名 = slug = canonical URL 最后一段（kebab-case）
2. 必填 frontmatter:
   - `title`（≤ 80 字）
   - `description`（≤ 180 字）
   - `keywords` 数组
   - `pubDate` / `updatedDate`
   - `canonical`
   - `tags` 数组
3. 推荐字段：`category`、`featured`、`heroImage`
4. 文末包含"相关阅读"内链 + YoTradeApi 注册 CTA
5. 提交前跑 `python3 scripts/validate-blog.py`

## 部署

push 到 `main` → GitHub Actions → Cloudflare Pages 自动部署。

## 每日自动发文

仓库自带一条 slash command `/daily-post`，跑一次会：

1. 默认产出 **3 篇**（可通过 `/daily-post N` 调整为 N 篇，1 ≤ N ≤ 10）
2. 每篇独立 `pick → write → validate → commit`
3. N 篇全部完成后统一推送 + 自动开 PR + squash-merge 到 main
4. 触发 Cloudflare Pages 部署

### 触发方式

在 [Claude Code on the web](https://code.claude.com/) 项目设置里加一个 **Schedule trigger**：

- **Cron**：`0 1 * * *`（UTC 01:00 ≈ 北京时间 09:00；按需调整）
- **Prompt / Command**：`/daily-post`（=3 篇）或 `/daily-post 5` 等
- **Branch**：`main`

触发后会自动开会话执行命令，跑完 PR 合并即结束。

### 维护选题池

- 候选选题写在 `scripts/topic-pool.md`，格式 `- slug | title | category`
- 已发布的 slug 自动跳过（包括本次循环里刚 commit 的），无需手动删
- picker 会按"最近 7 篇分类最少出现"挑下一个，避免连续同类
- 80 候选 ÷ 每天 3 篇 ≈ 26 天，**建议每月补一次池子**
- `/daily-post` 在剩余 < 30 时会在结束语里提醒补池

## License

内容仅供技术评估，发布前请自行核验第三方价格与模型列表。
