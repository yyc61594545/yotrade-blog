# 候选选题池

> Picker（`scripts/pick-next-topic.py`）解析规则：
> 1. 只解析 `- <slug> | <title> | <category>` 这种行
> 2. 已发布的 slug（`src/content/blog/<slug>.md` 已存在）自动跳过
> 3. 按"最近 7 篇分类最少出现 → 池内顺序"优先级挑下一个
>
> 维护：手工补充新候选时只要追加到对应分类下、保持格式即可。
> 当池子剩余可用候选 < 30 时，`/daily-post` 会在结束语里提醒。
> 按每天 3 篇计算：200 + 候选约够 2 个月。

## 优先出稿（Bing 实证高展示量缺口）

> picker 规则是"最近 7 篇没出现过的分类优先，否则取池内第一条"，
> 所以池内位置直接决定出稿时间。这几条是有实测展示量支撑的核心业务词，
> 放在最前面，避免被排到一个月之后。新的高价值选题也应加在这一节。

- cn-claude-mirror-sites-guide | Claude 镜像站国内可用性实测与风险提示（2026） | 国内场景
- cn-chatgpt-plus-daichong-guide | ChatGPT Plus 代充完全指南：流程、价格与避坑 | 国内场景
- cn-chatgpt-account-register-full | ChatGPT 账号注册完整教程 2026（含各种验证方式） | 小白入门

## 技术深度（Anthropic / OpenAI / 各家 API 细节）

- claude-tool-use-best-practices | Claude Tool Use 最佳实践与陷阱 | 技术深度
- function-calling-vs-tool-use | Function Calling vs Tool Use 差异辨析 | 技术深度
- llm-json-mode-comparison | 各家 LLM JSON 模式横向对比 | 技术深度
- llm-response-format-cn-guide | response_format 参数完全指南 | 技术深度
- claude-system-prompt-engineering | Claude System Prompt 工程实战 | 技术深度
- anthropic-batch-api-cn-guide | Anthropic Batch API 国内使用指南 | 技术深度
- openai-batch-api-cn-guide | OpenAI Batch API 节省 50% 成本实战 | 技术深度
- llm-logprobs-applications | LLM logprobs 在生产场景的实用价值 | 技术深度
- llm-temperature-top-p-deep-dive | temperature 与 top_p 深度解析 | 技术深度
- claude-stop-sequences-guide | Claude stop_sequences 高级用法 | 技术深度
- llm-system-prompt-vs-user-prompt | 系统提示与用户提示的边界 | 技术深度
- claude-pdf-api-cn-guide | Claude PDF 输入 API 国内使用指南 | 技术深度
- llm-vision-token-cost | 多模态 LLM 图片 token 计费详解 | 技术深度
- claude-citations-api-guide | Claude Citations API 引用功能详解 | 技术深度
- openai-file-search-vs-rag | OpenAI File Search vs 自建 RAG | 技术深度
- anthropic-files-api-cn | Anthropic Files API 国内使用 | 技术深度
- llm-function-calling-parallel | LLM 并行函数调用实战 | 技术深度
- claude-message-batches-savings | Claude Message Batches 50% 折扣实战 | 技术深度
- llm-context-window-cn-guide | LLM 上下文窗口实用指南 | 技术深度
- llm-finish-reason-handling | LLM finish_reason 各家差异处理 | 技术深度
- claude-extended-thinking-token-budget | Claude Extended Thinking 的 token 预算分配 | 技术深度
- anthropic-prompt-template-tutorial | Anthropic Prompt Template 模板系统实战 | 技术深度
- openai-structured-outputs-vs-tool | OpenAI Structured Outputs vs tool_choice 选型 | 技术深度
- claude-message-id-tracking | Claude message_id 追踪与日志关联实战 | 技术深度
- llm-token-counting-libraries | 各家 LLM token 计数库对比与选型 | 技术深度
- claude-streaming-event-types | Claude 流式响应事件类型完全指南 | 技术深度
- openai-completion-vs-chat-api | OpenAI Completions 与 Chat API 选型与差异 | 技术深度
- anthropic-vision-multi-image | Anthropic Vision 多图输入的最佳实践 | 技术深度
- claude-tool-use-with-streaming | Claude 流式 + 工具调用的正确姿势 | 技术深度
- llm-429-retry-after-header | LLM 429 响应中 Retry-After 头的正确处理 | 技术深度
- claude-prompt-injection-defense | Claude 应用的 Prompt Injection 防御 | 技术深度
- openai-realtime-api-guide | OpenAI Realtime API 国内使用指南 | 技术深度
- anthropic-cache-control-tutorial | Anthropic cache_control 五分钟入门到精通 | 技术深度
- llm-temperature-by-task-type | 按任务类型设置 LLM temperature 速查 | 技术深度
- claude-skill-vs-tool-vs-mcp | Claude Skill、Tool、MCP 三者边界与协作 | 技术深度
- openai-fine-tuning-cn-guide | OpenAI Fine-Tuning 国内使用指南 | 技术深度
- anthropic-prompt-improver-cn | Anthropic Prompt Improver 实战体验 | 技术深度
- llm-context-priming-techniques | LLM 上下文预热（context priming）技巧 | 技术深度
- claude-conversation-summary | Claude 长对话压缩与摘要策略 | 技术深度
- openai-assistants-vs-responses | OpenAI Assistants API 与 Responses API 迁移 | 技术深度
- llm-prompt-injection-attack-patterns | LLM Prompt Injection 攻击模式图谱 | 技术深度
- claude-token-efficient-tool-use | Claude token-efficient tool use 实战 | 技术深度
- openai-batch-vs-streaming | OpenAI Batch 与 Streaming 的选择决策 | 技术深度
- anthropic-tier-limits-cn | Anthropic Tier 限制与升级路径 | 技术深度
- llm-stop-token-cn-guide | LLM stop token 设计完全指南 | 技术深度
- claude-multi-turn-tool-loop | Claude 多轮工具调用循环健壮性设计 | 技术深度
- openai-prompt-cache-vs-anthropic | OpenAI Prompt Cache 与 Anthropic 缓存对比 | 技术深度
- anthropic-extended-output-cn | Anthropic Extended Output 用法与限制 | 技术深度
- llm-jsonl-batch-format | LLM Batch JSONL 格式规范与陷阱 | 技术深度

## 应用工程（生产化、Agent、Eval、流水线）

- ai-chatbot-from-scratch | 从零搭建生产级 AI Chatbot | 应用工程
- ai-coding-pair-programming | AI 结对编程实战指南 | 应用工程
- llm-error-retry-strategy | LLM API 错误重试策略设计 | 应用工程
- llm-context-engineering | LLM 上下文工程方法论 | 应用工程
- ai-agent-tool-design | AI Agent 工具集合的设计原则 | 应用工程
- llm-eval-golden-set | LLM 评测 Golden Set 构建方法 | 应用工程
- ai-prompt-versioning | Prompt 版本管理实战 | 应用工程
- llm-prompt-template-engineering | Prompt 模板工程实战 | 应用工程
- ai-agent-memory-design | AI Agent 记忆系统设计 | 应用工程
- llm-streaming-backpressure | LLM 流式响应背压处理 | 应用工程
- ai-agent-fallback-design | AI Agent 降级与容错策略 | 应用工程
- llm-multi-turn-conversation | LLM 多轮对话状态管理 | 应用工程
- ai-pipeline-orchestration | AI 任务流水线编排实战 | 应用工程
- llm-async-job-queue | LLM 异步任务队列设计 | 应用工程
- ai-feature-rollout-strategy | AI 功能灰度发布策略 | 应用工程
- ai-chatbot-context-management | AI Chatbot 上下文管理与裁剪 | 应用工程
- ai-agent-error-recovery | AI Agent 错误恢复机制设计 | 应用工程
- ai-agent-cost-monitoring | AI Agent 单会话成本监控实现 | 应用工程
- llm-cache-layer-design | LLM 应用缓存层设计 | 应用工程
- ai-pipeline-error-tracing | AI 流水线的错误追踪方案 | 应用工程
- llm-fallback-multi-provider | LLM 多提供商 fallback 路由设计 | 应用工程
- ai-system-prompt-library | 团队级 System Prompt 库的组织方式 | 应用工程
- llm-output-validation | LLM 输出验证：schema + 业务规则双层 | 应用工程
- ai-agent-permission-design | AI Agent 工具权限粒度设计 | 应用工程
- ai-agent-task-decomposition | AI Agent 任务分解模式 | 应用工程
- ai-rag-evaluation-framework | RAG 系统评测框架搭建 | 应用工程
- llm-app-load-testing | LLM 应用压测方案 | 应用工程
- ai-agent-observability-design | AI Agent 可观测性设计 | 应用工程
- llm-conversation-trace-design | LLM 对话轨迹存储与查询设计 | 应用工程
- ai-agent-rollback-strategy | AI Agent 写操作回滚策略 | 应用工程
- llm-quota-management-design | LLM 用户级配额管理实现 | 应用工程
- ai-feature-ab-testing | AI 功能 A/B 测试设计 | 应用工程
- llm-prompt-regression-detection | Prompt 改动后的回归检测 | 应用工程
- ai-agent-human-in-loop | AI Agent Human-in-Loop 模式实战 | 应用工程
- ai-task-retry-queue | AI 任务重试队列设计 | 应用工程
- llm-app-deployment-checklist | LLM 应用上线 checklist | 应用工程
- ai-agent-cost-attribution | AI Agent 多租户成本归因 | 应用工程

## 国内场景（中转、付款、合规、本土工具）

- cn-llm-relay-market-overview | 国内 LLM 中转服务市场观察 | 国内场景
- cn-ai-coding-tools-overview | 国内 AI 编程工具厂商盘点 | 国内场景
- claude-code-on-cn-network | Claude Code 在国内网络的实战配置 | 国内场景
- ai-api-relay-vs-self-vpn | API 中转 vs 自建 VPN 方案对比 | 国内场景
- cn-developer-claude-billing | 国内开发者使用 Claude 的付款方案 | 国内场景
- cn-ai-tools-payment-guide | 国内开发者 AI 工具付款全攻略 | 国内场景
- cn-llm-data-compliance | 国内 LLM 应用数据合规要点 | 国内场景
- cn-trae-vs-cursor | Trae vs Cursor 国内开发者怎么选 | 国内场景
- cn-tongyi-lingma-deep-review | 通义灵码深度体验报告 | 国内场景
- cn-doubao-llm-developer-review | 豆包大模型开发者视角评测 | 国内场景
- cn-claude-code-via-bedrock | 国内用户通过 AWS Bedrock 使用 Claude Code | 国内场景
- cn-gemini-api-direct-vs-relay | Gemini API 国内直连 vs 中转选型 | 国内场景
- cn-grok-api-cn-access | Grok API 国内访问方案 | 国内场景
- cn-openai-tier-upgrade-guide | OpenAI 用量 Tier 机制与额度提升原理 | 国内场景
- cn-deepseek-coder-deep-review | DeepSeek Coder 开发者深度体验 | 国内场景
- cn-zhipu-glm-developer-review | 智谱 GLM 系列开发者视角评测 | 国内场景
- cn-moonshot-kimi-developer-review | Moonshot Kimi 开发者评测 | 国内场景
- cn-baichuan-developer-review | 百川大模型 API 开发者评测 | 国内场景
- cn-minimax-developer-review | MiniMax 海螺 API 开发者评测 | 国内场景
- cn-stepfun-developer-review | 阶跃星辰 Step API 开发者评测 | 国内场景
- cn-ai-coding-tool-vs-jb | 国内 AI 编程插件与 JetBrains 生态适配 | 国内场景
- cn-tencent-yuanbao-review | 腾讯元宝大模型 API 评测 | 国内场景
- cn-ai-relay-uptime-monitoring | 中转服务可用性自助监控方案 | 国内场景
- cn-ai-tools-corporate-procurement | 国内企业采购 AI 工具的流程 | 国内场景
- cn-yi-large-developer-review | 零一万物 Yi-Large API 评测 | 国内场景
- cn-llm-cn-vs-overseas-cost | 国产大模型 vs 海外大模型的成本对比 | 国内场景
- cn-claude-on-poe-via-cn | 国内通过 Poe 使用 Claude 的可行性 | 国内场景
- cn-cursor-business-account | Cursor 团队版国内协作与账号管理 | 国内场景

## 模型评测（横评、能力实测、Benchmark）

- claude-4-7-vs-gpt-5-1-coding | Claude 4.7 vs GPT-5.1 编程能力对比 | 模型评测
- deepseek-v3-vs-claude-sonnet | DeepSeek V3 vs Claude Sonnet 4.6 实测 | 模型评测
- qwen3-vs-claude-cn-tasks | Qwen3 vs Claude 中文任务对比 | 模型评测
- gemini-3-pro-multimodal | Gemini 3 Pro 多模态能力评测 | 模型评测
- claude-haiku-vs-gpt-mini | Claude Haiku 4.5 vs GPT-5 mini 横评 | 模型评测
- llm-leaderboard-cn-developer | 中文开发者视角的 LLM 排行榜 | 模型评测
- llm-coding-benchmark-cn | LLM 编程能力中文场景基准 | 模型评测
- llm-translation-benchmark | LLM 中英翻译能力对比 | 模型评测
- llm-summarization-quality | LLM 摘要质量横评 | 模型评测
- llm-chinese-comprehension | LLM 中文理解能力实测 | 模型评测
- claude-opus-4-7-1m-context-real-test | Claude Opus 4.7 1M 上下文实战测试 | 模型评测
- gpt-5-vs-gemini-3-coding | GPT-5 vs Gemini 3 Pro 编程能力对比 | 模型评测
- deepseek-r1-vs-claude-thinking | DeepSeek R1 vs Claude Thinking 推理能力对比 | 模型评测
- claude-vs-gpt-creative-writing | Claude vs GPT 中文创作能力对比 | 模型评测
- llm-math-reasoning-benchmark | LLM 数学推理能力横评 | 模型评测
- llm-rare-language-translation | LLM 小语种翻译能力对比 | 模型评测
- claude-vs-gemini-document-rag | Claude vs Gemini 文档问答能力对比 | 模型评测
- llm-code-completion-benchmark | LLM 代码补全质量基准 | 模型评测
- llm-meeting-minutes-summarization | LLM 会议纪要生成能力评测 | 模型评测
- llm-named-entity-cn-benchmark | LLM 中文命名实体识别基准 | 模型评测
- llm-instruction-following-benchmark | LLM 指令遵循能力横评 | 模型评测
- claude-vs-gpt-tool-use-accuracy | Claude vs GPT 工具调用准确率对比 | 模型评测
- llm-multilingual-benchmark | LLM 多语言任务横评 | 模型评测
- llm-long-context-needle | LLM 长上下文 Needle-in-a-Haystack 实测 | 模型评测
- claude-vs-gpt-empathy-rating | Claude vs GPT 共情与情感回应对比 | 模型评测

## 行业观察（趋势、商业、生态、争议）

- ai-coding-tool-vendor-lockin | AI 编程工具的厂商锁定问题 | 行业观察
- ai-startup-2026-landscape | 2026 AI 创业公司全景观察 | 行业观察
- claude-vs-openai-strategy | Anthropic vs OpenAI 战略路线对比 | 行业观察
- cursor-business-model-analysis | Cursor 商业模式分析 | 行业观察
- ai-coding-replacing-developers | AI 编程是否在取代开发者 | 行业观察
- open-source-vs-proprietary-llm | 开源 vs 闭源 LLM 现状 | 行业观察
- ai-agent-commercialization-gap | AI Agent 商业化困局观察 | 行业观察
- ai-bubble-or-real-shift | AI 泡沫论 vs 真正变革 | 行业观察
- swe-bench-leaderboard-interpretation | SWE-Bench 排行榜深度解读 | 行业观察
- ai-coding-tool-economics | AI 编程工具的经济账 | 行业观察
- ai-coding-tool-consolidation-trend | AI 编程工具的整合与收敛趋势 | 行业观察
- anthropic-claude-code-strategy | Anthropic Claude Code 战略观察 | 行业观察
- openai-codex-comeback-analysis | OpenAI Codex 回归路线分析 | 行业观察
- ai-agent-platform-war | AI Agent 平台之战格局梳理 | 行业观察
- cursor-vs-windsurf-acquisition | Cursor 与 Windsurf 并购传闻观察 | 行业观察
- ai-coding-pricing-shifts-2026 | 2026 AI 编程工具定价模型变化 | 行业观察
- llm-pricing-race-to-bottom | LLM 价格战的尽头是什么 | 行业观察
- agentic-os-future-prediction | Agentic OS 的未来形态推演 | 行业观察
- ai-developer-tools-vc-trend | AI 开发者工具赛道 VC 动向 | 行业观察
- ai-coding-tool-feature-arms-race | AI 编程工具的功能军备竞赛 | 行业观察
- mcp-protocol-adoption-trend | MCP 协议在生态中的采纳趋势 | 行业观察
- ai-startup-runway-2026 | AI 创业公司的资金跑道现状 | 行业观察
- cn-ai-coding-vendor-rise | 国内 AI 编程厂商的崛起观察 | 行业观察
- open-source-llm-self-hosting-trend | 开源 LLM 自托管的复兴 | 行业观察
- ai-coding-job-market-2026 | 2026 AI 编程对就业市场的影响 | 行业观察

## 成本优化

- llm-cost-optimization-checklist | LLM 成本优化 30 条 checklist | 成本优化
- cursor-tier-comparison | Cursor 各档位性价比对比 | 成本优化
- claude-code-vs-cursor-cost | Claude Code 与 Cursor 单任务成本对比 | 成本优化
- llm-batch-api-real-savings | Batch API 真实省钱测算 | 成本优化
- ai-api-budget-cap-design | AI API 预算上限自动化设计 | 成本优化
- llm-prompt-token-trimming-recipes | Prompt token 裁剪 12 个秘诀 | 成本优化
- claude-prompt-caching-roi-analysis | Claude Prompt Caching ROI 分析 | 成本优化
- multi-model-cost-routing | 多模型成本智能路由方案 | 成本优化
- llm-output-truncation-savings | 输出截断省钱实战 | 成本优化
- context-compression-strategies | 上下文压缩 5 种策略对比 | 成本优化
- ai-coding-roi-calculation | AI 编程工具 ROI 计算方法 | 成本优化
- llm-batch-vs-realtime-cost | Batch 与实时调用的成本临界点 | 成本优化
- embedding-model-cost-comparison | Embedding 模型成本对比 | 成本优化
- llm-team-budget-allocation | 团队 LLM 预算分配实战 | 成本优化

## 实战经验与踩坑

- claude-code-real-world-tasks | Claude Code 真实任务案例集 | 实战经验
- cursor-background-agent-cases | Cursor Background Agent 真实案例 | 实战经验
- ai-coding-debugging-stories | AI 编程调试踩坑实录 | 实战经验
- ai-refactor-legacy-monolith | AI 重构遗留单体应用实录 | 实战经验
- ai-helping-with-database-migration | 用 AI 做数据库迁移实战 | 实战经验
- ai-coding-team-adoption | 团队引入 AI 编程的踩坑 | 实战经验
- ai-test-automation-real-cases | AI 测试自动化真实案例 | 实战经验
- cursor-rules-real-projects | Cursor Rules 在真实项目中的演化 | 实战经验
- ai-pair-programming-stories | AI 结对编程一年的故事 | 实战经验
- ai-coding-monthly-cost-real | 个人开发者用 AI 月度成本实录 | 实战经验
- claude-code-1month-real-usage | Claude Code 一个月深度使用复盘 | 实战经验
- cursor-team-rollout-3months | Cursor 团队推广三个月复盘 | 实战经验
- ai-coding-onboarding-junior-dev | 用 AI 辅助新人入职的实战 | 实战经验
- ai-helping-with-microservice-extraction | AI 辅助微服务拆分实战 | 实战经验
- ai-coding-saas-zero-to-launch | AI 编程从零做 SaaS 到上线 | 实战经验
- ai-doc-platform-migration | AI 辅助文档平台迁移实战 | 实战经验
- ai-helping-codebase-onboarding | AI 辅助新代码库上手实战 | 实战经验
- ai-coding-startup-mvp-week | 用 AI 一周做完 MVP 的实战 | 实战经验
- cline-on-large-codebase | Cline 在大型代码库的实战 | 实战经验
- aider-test-driven-refactor | 用 Aider 做 TDD 重构的实战 | 实战经验
- cursor-multi-language-project | Cursor 在多语言项目里的实战 | 实战经验
- ai-coding-postmortem-bug | AI 编程引入 bug 的事后复盘 | 实战经验
- claude-code-monorepo-strategy | Claude Code 在 monorepo 里的策略 | 实战经验
- ai-coding-pr-review-replacement | AI 替代 PR 评审的实战边界 | 实战经验
- ai-coding-build-internal-tool | 用 AI 一天搭一个内部工具 | 实战经验
- cursor-rules-for-rails-project | 给 Rails 项目写 Cursor Rules | 实战经验
- ai-coding-database-schema-design | AI 辅助数据库 schema 设计实战 | 实战经验
- ai-pair-with-architect | AI 与架构师配对工作的实战 | 实战经验
- aider-on-legacy-php | Aider 重构遗留 PHP 项目实战 | 实战经验
- claude-code-on-ml-pipeline | Claude Code 在 ML 流水线的实战 | 实战经验

## 小白入门（B 类：充值/订阅代充/国内可用性/价格对比/新手教程）

> 这一类专门服务"不会翻墙、想用 ChatGPT/Claude/Cursor"的小白用户。
> 关键词全部命中百度搜索量大的长尾词（含「2026」「国内」「教程」「最新」等高权重词）。
> 文末 CTA 直接对应 YoTradeApi 订阅代充 + API 中转两条产品线。

### 充值 / 付款（10）

- cn-chatgpt-plus-payment-2026 | ChatGPT Plus 2026 最新充值方法（国内可用） | 小白入门
- cn-chatgpt-pro-200-dollar-payment | ChatGPT Pro $200 月卡国内开通教程 | 小白入门
- cn-claude-max-5x-20x-pricing | Claude Max 5x 与 20x 区别和国内代充 | 小白入门
- cn-claude-pro-plus-difference | Claude Pro 和 Plus 有什么区别 | 小白入门
- cn-gemini-advanced-cn-subscribe | Gemini Advanced 国内怎么订阅 | 小白入门
- cn-openai-api-recharge-with-rmb | OpenAI API 用人民币充值最简方法 | 小白入门
- cn-virtual-card-for-chatgpt-2026 | 2026 给 ChatGPT 充值的虚拟卡推荐 | 小白入门
- cn-chatgpt-recurring-failed-fix | ChatGPT 自动续费失败怎么办 | 小白入门
- cn-claude-api-credit-add-guide | Claude API 充值小额度教程 | 小白入门
- cn-perplexity-pro-cn-subscribe | Perplexity Pro 国内订阅完整指南 | 小白入门

### 能不能用 / 国内可用性（8）

- cn-chatgpt-cn-available-2026 | 2026 ChatGPT 国内能用吗（最新实测） | 小白入门
- cn-claude-cn-direct-access-2026 | Claude 国内直接访问最新方法 | 小白入门
- cn-cursor-cn-available-2026 | 2026 Cursor 国内能用吗 | 小白入门
- cn-gemini-cn-access-guide-2026 | Gemini 国内访问 2026 完整指南 | 小白入门
- cn-grok-cn-access-guide | Grok 国内访问与订阅指南 | 小白入门
- cn-claude-code-cn-using-2026 | Claude Code 国内能用吗（小白版） | 小白入门
- cn-openai-api-cn-relay-recommend | OpenAI API 国内中转推荐 | 小白入门
- cn-ai-tools-blocked-status-2026 | 2026 哪些 AI 工具被墙了 | 小白入门

### 价格 / 性价比（5）

- cn-chatgpt-monthly-cost-2026 | ChatGPT 一个月多少钱（含国内代充） | 小白入门
- cn-claude-vs-chatgpt-price-2026 | Claude 和 ChatGPT 价格对比（2026） | 小白入门
- cn-cursor-price-cn-2026 | Cursor 国内多少钱（含中转省钱方案） | 小白入门
- cn-ai-tool-budget-150-rmb | 月预算 ¥150 用什么 AI 工具最值 | 小白入门
- cn-claude-max-vs-pro-roi | Claude Max 和 Pro 哪个更值 | 小白入门

### 入门教程（7）

- cn-chatgpt-register-without-foreign-phone | 没有海外手机号怎么注册 ChatGPT | 小白入门
- cn-chatgpt-first-time-cn-guide | ChatGPT 国内第一次使用完整教程 | 小白入门
- cn-claude-zero-to-chat-tutorial | 从零开始用 Claude 聊天的 5 分钟教程 | 小白入门
- cn-cursor-install-cn-guide | Cursor 国内安装与第一个项目教程 | 小白入门
- cn-ai-writing-resume-cn-guide | 用 AI 写简历完整教程（中文） | 小白入门
- cn-ai-learn-english-cn-method | 用 ChatGPT/Claude 学英语的 7 个方法 | 小白入门
- cn-ai-excel-formula-cn-guide | 用 AI 写 Excel 公式速通教程 | 小白入门

## Codex 接管补充选题（2026-07）

### API 与协议

- openai-responses-api-streaming-guide | OpenAI Responses API 流式事件处理指南 | 技术深度
- openai-responses-api-tool-loop | Responses API 多轮工具调用循环实战 | 技术深度
- openai-background-mode-jobs | OpenAI Background Mode 异步任务设计 | 技术深度
- openai-webhook-signature-verification | OpenAI Webhook 签名校验与重放防护 | 技术深度
- openai-built-in-tools-selection | OpenAI 内置工具的选型与组合 | 技术深度
- openai-reasoning-effort-guide | reasoning_effort 参数的任务分级方法 | 技术深度
- openai-service-tier-latency | OpenAI service_tier 延迟与成本取舍 | 技术深度
- openai-prompt-object-versioning | OpenAI Prompt Object 版本管理实战 | 技术深度
- anthropic-message-stream-recovery | Anthropic Messages 流式中断恢复 | 技术深度
- anthropic-tool-choice-guide | Anthropic tool_choice 参数完全指南 | 技术深度
- anthropic-computer-use-safety | Computer Use 工具的安全边界设计 | 技术深度
- anthropic-citations-rag-pattern | Anthropic Citations 与 RAG 组合实战 | 技术深度
- gemini-live-api-session-design | Gemini Live API 会话状态设计 | 技术深度
- gemini-function-calling-guide | Gemini Function Calling 工程实践 | 技术深度
- gemini-context-caching-guide | Gemini Context Caching 成本优化 | 技术深度
- llm-api-idempotency-design | LLM API 写操作幂等性设计 | 技术深度
- llm-streaming-sse-parser | 跨厂商 SSE 流式解析器实现 | 技术深度
- llm-api-error-taxonomy | 多模型 API 错误码分类与统一处理 | 技术深度
- llm-tool-schema-portability | OpenAI、Anthropic、Gemini 工具 Schema 兼容层 | 技术深度
- llm-api-request-signing-proxy | AI API 网关请求签名与防重放 | 技术深度

### Agent 与生产工程

- agent-state-machine-design | AI Agent 状态机设计与落地 | 应用工程
- agent-event-sourcing | 用 Event Sourcing 记录 Agent 执行轨迹 | 应用工程
- agent-saga-compensation | Agent 多步写操作的 Saga 补偿机制 | 应用工程
- agent-tool-timeout-budget | Agent 工具调用的超时预算设计 | 应用工程
- agent-loop-termination | 防止 Agent 无限循环的终止策略 | 应用工程
- agent-human-approval-queue | Agent 人工审批队列的实现 | 应用工程
- agent-secret-isolation | Agent 工具密钥隔离与最小权限 | 应用工程
- agent-sandbox-design | AI 编程 Agent 沙箱设计 | 应用工程
- agent-replay-debugging | Agent 任务回放与确定性调试 | 应用工程
- agent-eval-trajectory-scoring | Agent 轨迹级评测方法 | 应用工程
- agent-memory-retention-policy | Agent 记忆保留与清理策略 | 应用工程
- agent-context-budget-allocation | Agent 上下文预算分配算法 | 应用工程
- agent-parallel-tool-execution | Agent 并行工具调用的并发控制 | 应用工程
- agent-multi-tenant-isolation | 多租户 Agent 的数据隔离 | 应用工程
- agent-rate-limit-coordination | 多 Agent 共享限流配额的协调 | 应用工程
- agent-output-provenance | Agent 输出来源追踪与引用设计 | 应用工程
- agent-policy-engine | 给 AI Agent 接入策略引擎 | 应用工程
- agent-dead-letter-queue | Agent 失败任务死信队列设计 | 应用工程
- agent-canary-release | Agent Prompt 与工具的金丝雀发布 | 应用工程
- agent-production-runbook | AI Agent 生产故障 Runbook | 应用工程

### RAG、检索与数据

- rag-chunking-evaluation | RAG Chunking 策略的量化评测 | 应用工程
- rag-hybrid-search-tuning | Hybrid Search 权重调优实战 | 应用工程
- rag-reranker-selection | RAG Reranker 选型与评测 | 应用工程
- rag-metadata-filter-design | RAG Metadata Filter 设计 | 应用工程
- rag-document-versioning | RAG 文档版本与索引一致性 | 应用工程
- rag-citation-verification | RAG 引用真实性自动校验 | 应用工程
- rag-access-control | 企业 RAG 的文档权限继承 | 应用工程
- rag-freshness-monitoring | RAG 知识新鲜度监控 | 应用工程
- rag-query-rewrite-eval | Query Rewrite 对 RAG 召回的影响 | 应用工程
- rag-negative-feedback-loop | 用负反馈改进 RAG 检索 | 应用工程
- embedding-dimension-tradeoff | Embedding 维度、速度与成本取舍 | 技术深度
- vector-database-migration | 向量数据库迁移与双写方案 | 应用工程
- semantic-cache-invalidation | 语义缓存失效策略 | 应用工程
- knowledge-graph-rag-boundary | Knowledge Graph 与 RAG 的使用边界 | 应用工程
- multimodal-rag-pipeline | 多模态 RAG 流水线设计 | 应用工程

### 可观测性、安全与成本

- llm-tracing-open-telemetry | 用 OpenTelemetry 追踪 LLM 调用 | 应用工程
- llm-token-cost-ledger | LLM Token 成本账本设计 | 成本优化
- llm-budget-alerting | AI API 预算告警与自动熔断 | 成本优化
- llm-cache-hit-observability | Prompt Cache 命中率监控 | 成本优化
- llm-model-routing-eval | 多模型路由器的离线评测 | 应用工程
- llm-latency-slo | LLM 应用延迟 SLO 设计 | 应用工程
- llm-stream-interruption-metrics | 流式输出中断率监控 | 应用工程
- llm-pii-redaction-gateway | AI API 网关的 PII 脱敏 | 应用工程
- llm-prompt-injection-runtime-defense | Prompt Injection 运行时防护 | 应用工程
- llm-tool-output-sanitization | Agent 工具输出净化与隔离 | 应用工程
- llm-audit-log-design | LLM 应用审计日志设计 | 应用工程
- llm-data-retention-policy | LLM 请求数据保留策略 | 应用工程
- llm-provider-outage-drill | 多模型供应商故障演练 | 实战经验
- llm-cost-anomaly-detection | LLM 成本异常检测 | 成本优化
- llm-billing-reconciliation | AI API 账单对账自动化 | 成本优化

### Codex 与开发者工作流

- codex-cli-project-instructions | Codex 项目级 AGENTS.md 编写指南 | 实战经验
- codex-code-review-workflow | 用 Codex 建立可重复的代码审查流程 | 实战经验
- codex-background-automation | Codex 后台自动化任务设计 | 实战经验
- codex-multi-agent-boundaries | Codex 多 Agent 任务拆分边界 | 实战经验
- codex-github-pr-automation | Codex 自动创建与验证 GitHub PR | 实战经验
- codex-worktree-isolation | Codex Worktree 隔离开发实战 | 实战经验
- codex-long-task-handoff | Codex 长任务状态交接方法 | 实战经验
- codex-vs-claude-code-migration | 从 Claude Code 迁移到 Codex 的实践清单 | 实战经验
- ai-coding-agent-permission-models | AI 编程代理权限模式对比 | 行业观察
- ai-coding-agent-ci-integration | AI 编程 Agent 接入 CI 的边界 | 实战经验
- ai-generated-code-provenance | AI 生成代码的来源与审计 | 行业观察
- ai-coding-agent-benchmark-design | AI 编程 Agent 内部基准设计 | 模型评测
- ai-code-review-false-positive | AI Code Review 误报治理 | 实战经验
- ai-coding-agent-security-review | AI 编程 Agent 安全评审清单 | 实战经验
- ai-coding-agent-team-governance | 团队使用 AI 编程 Agent 的治理规则 | 实战经验

## 2026-08 补充选题

### 技术深度
- llm-tokenizer-cost-difference | 各家 tokenizer 差异对中文成本的影响 | 技术深度
- llm-logprobs-confidence | 用 logprobs 做置信度判断 | 技术深度
- llm-batch-api-queue-design | 批处理 API 的排队与结果回收 | 技术深度
- llm-context-eviction-strategy | 超长会话的上下文淘汰策略 | 技术深度
- llm-tool-schema-versioning | 工具 Schema 版本演进与兼容 | 技术深度
- llm-sse-reconnect-protocol | SSE 断线重连与消息去重 | 技术深度
- llm-sampling-parameters-deep | 采样参数对输出分布的实际影响 | 技术深度
- llm-multimodal-image-token-cost | 图片输入的 token 计费机制 | 技术深度
- llm-stop-sequence-pitfalls | stop sequence 的边界与坑 | 技术深度
- llm-strict-schema-boundary | 严格模式结构化输出的能力边界 | 技术深度

### 模型评测
- llm-long-context-recall-bench | 长上下文召回能力横评 | 模型评测
- llm-chinese-instruction-bench | 中文指令遵循能力对比 | 模型评测
- llm-tool-call-reliability-bench | 工具调用可靠性实测 | 模型评测
- llm-p99-latency-comparison | 主流模型 P99 延迟对比 | 模型评测
- coding-agent-refactor-bench | 编程 Agent 重构任务横评 | 模型评测
- llm-json-stability-bench | 结构化输出稳定性横评 | 模型评测
- llm-cn-en-translation-bench | 中英互译质量实测 | 模型评测
- llm-summarization-fidelity-bench | 长文摘要忠实度实测 | 模型评测
- llm-math-reasoning-cn-bench | 中文数理推理能力对比 | 模型评测
- small-model-task-fitness | 小模型能接住哪些任务 | 模型评测

### 工程实战
- llm-gateway-routing-implementation | 自建 LLM 网关的路由实现 | 工程实战
- multi-provider-failover-practice | 多厂商故障切换落地 | 工程实战
- client-side-rate-limiter | 客户端令牌桶限速实现 | 工程实战
- llm-eval-in-ci-pipeline | 把模型评测接进 CI 流水线 | 工程实战
- agent-long-term-memory-store | Agent 长期记忆存储选型 | 工程实战
- llm-response-cache-layer | 响应缓存层设计与命中率 | 工程实战
- prompt-version-control-practice | Prompt 版本管理落地 | 工程实战
- llm-queue-backpressure | 请求队列与背压设计 | 工程实战
- agent-task-scheduler-design | Agent 任务调度器设计 | 工程实战
- llm-cold-start-warmup | 冷启动与预热策略 | 工程实战

### 成本优化
- prompt-caching-savings-guide | Prompt Caching 实战省钱指南 | 成本优化
- model-tiering-cost-strategy | 模型分级的成本策略 | 成本优化
- context-compression-savings | 上下文压缩的成本收益 | 成本优化
- batch-vs-realtime-cost | 批处理与实时调用的成本差 | 成本优化
- budget-guardrail-design | 预算护栏与超支阻断 | 成本优化
- embedding-cost-optimization | Embedding 成本优化路径 | 成本优化
- agent-loop-cost-runaway | Agent 循环的成本失控与控制 | 成本优化
- output-length-cost-control | 输出长度控制的省钱效果 | 成本优化
- cost-per-feature-accounting | 按功能核算 AI 成本 | 成本优化
- free-tier-limits-reality | 免费额度的真实边界 | 成本优化

### 小白入门
- what-is-token-for-beginners | Token 到底是什么 | 小白入门
- first-api-call-walkthrough | 第一次调用 AI API 完整走一遍 | 小白入门
- api-key-safety-for-beginners | 新手怎么安全保管 API Key | 小白入门
- temperature-top-p-for-beginners | temperature 和 top_p 怎么调 | 小白入门
- system-prompt-for-beginners | System Prompt 入门写法 | 小白入门
- streaming-or-not-for-beginners | 流式和非流式怎么选 | 小白入门
- common-error-codes-for-beginners | 常见错误码看不懂怎么办 | 小白入门
- pick-first-model-for-beginners | 新手第一个模型怎么选 | 小白入门
- context-window-for-beginners | 上下文窗口是什么意思 | 小白入门
- why-ai-gives-wrong-answer | AI 为什么会答错 | 小白入门

### 国内场景
- cn-latency-optimization-practice | 国内访问延迟优化实测 | 国内场景
- cn-payment-methods-comparison | 国内开发者付款方式对比 | 国内场景
- cn-data-boundary-compliance | 国内业务的数据出境边界 | 国内场景
- cn-team-ai-tool-rollout | 国内团队引入 AI 工具的路径 | 国内场景
- cn-invoice-reimbursement | AI API 支出的发票与报销 | 国内场景
- cn-domestic-model-integration | 国产模型接入实战 | 国内场景
- cn-mobile-app-llm-notes | 国内 App 接入 LLM 的注意事项 | 国内场景
- cn-enterprise-procurement | 国内企业采购 AI 服务的流程 | 国内场景
- cn-relay-service-selection | 中转服务选型要看哪些指标 | 国内场景
- cn-network-troubleshooting | 国内网络问题排查手册 | 国内场景

### 工具配置
- cursor-team-config-guide | Cursor 团队配置指南 | 工具配置
- claude-code-hooks-config | Claude Code Hooks 配置实战 | 工具配置
- cline-vscode-config-guide | Cline 在 VS Code 的配置 | 工具配置
- aider-workflow-config | Aider 工作流配置 | 工具配置
- open-webui-selfhost-config | Open WebUI 自托管配置 | 工具配置
- continue-dev-custom-endpoint | Continue.dev 接自定义端点 | 工具配置
- zed-ai-assistant-config | Zed AI 助手配置 | 工具配置
- jetbrains-ai-plugin-config | JetBrains 系 AI 插件配置 | 工具配置

### 行业观察
- coding-agent-landscape-2026 | 2026 编程 Agent 格局观察 | 行业观察
- llm-pricing-trend-observation | 模型定价趋势与其影响 | 行业观察
- ai-app-layer-moat | AI 应用层的护城河之争 | 行业观察
- open-weight-license-shift | 开源权重许可证的变化 | 行业观察
- agent-interop-protocol-race | Agent 互操作协议之争 | 行业观察
- inference-cost-curve-reality | 推理成本下降曲线的现实 | 行业观察
- developer-skill-shift-ai | 开发者技能结构的迁移 | 行业观察
- ai-tool-consolidation-trend | AI 开发工具的整合趋势 | 行业观察

### 实战经验
- llm-production-incident-postmortem | 一次 LLM 线上故障复盘 | 实战经验
- rag-quality-debugging-path | RAG 效果差的排查路径 | 实战经验
- prompt-regression-governance | Prompt 回归问题治理 | 实战经验
- user-feedback-to-iteration | 用户反馈回流到迭代 | 实战经验
- agent-over-permission-incident | Agent 权限过宽引发的事故 | 实战经验
- legacy-migration-with-ai | 用 AI 迁移遗留代码的真实过程 | 实战经验
- ai-doc-generation-practice | 用 AI 维护项目文档的实践 | 实战经验
- small-team-ai-workflow | 小团队的 AI 协作流程 | 实战经验

## 2026-09 卫星选题簇（围绕已验证爆款需求）

> 依据：RUM 实测数据显示 `cn-chatgpt-register-without-foreign-phone` 单篇占 blog 全站 46% 流量
> （203/439 PV/天），但"注册"这一环节此前仅此一篇覆盖，周边长尾全空白。
> 本簇用一组文章接住同一批搜索意图，并全部内链回该主文章，形成主题集群。
> 写作要求：每篇必须内链 `/blog/cn-chatgpt-register-without-foreign-phone/`，
> 且至少内链本簇其他 1 篇。

### 注册环节长尾（小白入门）
- cn-sms-verification-platform-review | ChatGPT 注册接码平台横评 2026：哪家还能用 | 小白入门
- cn-chatgpt-register-error-fix | ChatGPT 注册常见报错逐条排查 | 小白入门
- cn-chatgpt-email-choice-guide | 注册 ChatGPT 用哪种邮箱不容易被封 | 小白入门
- cn-chatgpt-account-banned-recovery | ChatGPT 账号被封的判断与申诉实操 | 小白入门
- cn-chatgpt-login-region-error | ChatGPT 登录提示地区不支持怎么解决 | 小白入门
- cn-chatgpt-2fa-security-setup | ChatGPT 账号安全设置与 2FA 全流程 | 小白入门
- cn-chatgpt-shared-account-risk | ChatGPT 共享账号的真实风险与替代方案 | 小白入门
- cn-claude-register-cn-guide | 国内注册 Claude 账号完整流程 2026 | 小白入门
- cn-gemini-register-cn-guide | 国内注册 Google Gemini 完整流程 | 小白入门
- cn-ai-account-multi-device-login | AI 账号多设备登录的限制与规避 | 小白入门

### 支付环节长尾（国内场景）
- cn-virtual-card-declined-fix | 虚拟卡支付 ChatGPT 被拒的排查清单 | 国内场景
- cn-apple-id-region-ai-subscribe | 通过 Apple ID 切区订阅 AI 服务实操 | 国内场景
- cn-alipay-wechat-ai-subscribe | 支付宝微信能付哪些 AI 服务：2026 现状 | 国内场景
- cn-ai-subscription-refund-guide | AI 订阅退款申请全流程（OpenAI/Anthropic） | 国内场景
- cn-ai-subscription-price-compare-2026 | 2026 主流 AI 订阅国内到手价横评 | 国内场景
- cn-chatgpt-team-plan-cn-guide | ChatGPT Team 版国内开通与分摊实战 | 国内场景
- cn-ai-payment-risk-control | AI 服务支付风控触发原因与规避 | 国内场景
- cn-overseas-card-application-path | 国内申请可付 AI 服务的境外卡路径对比 | 国内场景

## 2026-09 Bing 关键词实证缺口（高展示量未覆盖）

> 依据：Bing Webmaster Tools → Keyword Research 实测推荐词（3 个月窗口）。
> Bing 是本站真实流量主渠道（5.9K 点击 / 85.8K 展示，约为 Google 的 90 倍）。
> 下列三条是核对全部 62 篇 cn-* 已发布文章后确认的**真实缺口**，
> 其余高展示词（chatgpt充值 9.3K、grok订阅 612 等）已有文章正面命中，不重复立项。

