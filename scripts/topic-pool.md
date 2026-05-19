# 候选选题池

> Picker（`scripts/pick-next-topic.py`）解析规则：
> 1. 只解析 `- <slug> | <title> | <category>` 这种行
> 2. 已发布的 slug（`src/content/blog/<slug>.md` 已存在）自动跳过
> 3. 按"最近 7 篇分类最少出现 → 池内顺序"优先级挑下一个
>
> 维护：手工补充新候选时只要追加到对应分类下、保持格式即可。
> 当池子剩余可用候选 < 20 时，`/daily-post` 会提示自动续写候选。

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

## 成本与省钱

- llm-cost-optimization-checklist | LLM 成本优化 30 条 checklist | 成本优化
- cursor-tier-comparison | Cursor 各档位性价比对比 | 成本优化
- claude-code-vs-cursor-cost | Claude Code 与 Cursor 单任务成本对比 | 成本优化
- llm-batch-api-real-savings | Batch API 真实省钱测算 | 成本优化
- ai-api-budget-cap-design | AI API 预算上限自动化设计 | 成本优化

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
