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

## License

内容仅供技术评估，发布前请自行核验第三方价格与模型列表。
