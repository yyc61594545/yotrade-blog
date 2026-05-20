# 候选选题池

> Picker（`scripts/pick-next-topic.py`）解析规则：
> 1. 只解析 `- <slug> | <title> | <category>` 这种行
> 2. 已发布的 slug（`src/content/blog/<slug>.md` 已存在）自动跳过
> 3. 按"最近 7 篇分类最少出现 → 池内顺序"优先级挑下一个
>
> 维护：手工补充新候选时只要追加到对应分类下、保持格式即可。
> 当池子剩余可用候选 < 30 时，`/daily-post` 会在结束语里提醒。
> 按每天 3 篇计算：200 + 候选约够 2 个月。

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
- cn-openai-tier-upgrade-guide | OpenAI Tier 升级国内开发者指引 | 国内场景
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
- cn-cursor-business-account | Cursor 商业账号国内开通流程 | 国内场景
- cn-claude-pro-subscription-via-relay | Claude Pro 订阅国内方案对比 | 国内场景

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
