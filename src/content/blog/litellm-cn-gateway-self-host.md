---
title: LiteLLM 自部署 LLM 网关完整指南
description: 用 LiteLLM 在国内自部署一个可用于多团队/多项目的 LLM 网关，含 Docker 部署、路由、限频、用量统计、Key 管理。
keywords:
- litellm 部署
- litellm 自托管
- llm 网关 自部署
- litellm proxy
- 多团队 llm 网关
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/litellm-cn-gateway-self-host/
tags:
- LiteLLM
- 自托管
- LLM 网关
- 团队部署
- API 中转
category: 工程实战
heroImage: ../../assets/blog-placeholder-3.jpg
---

# LiteLLM 自部署 LLM 网关完整指南

如果你在公司里要给团队提供"统一的 LLM 入口"，又不想直接把第三方中转 Key 发给所有人，**LiteLLM Proxy** 是最佳的中间层。本文给完整部署指南。

## 一、LiteLLM Proxy 是什么

简单理解：

```
团队成员 → LiteLLM Proxy（你的服务器）→ 第三方中转 / 官方 → 模型
```

LiteLLM Proxy 作为内部网关，负责：

- 统一 API（团队成员看到的都是 OpenAI 兼容协议）
- 路由（按模型路由到不同上游）
- 限频（每个 Key 独立 RPM/TPM）
- 用量统计（按用户、项目、模型）
- 预算控制（日 / 月预算上限）
- 审计日志

## 二、最小 Docker 部署

```bash
mkdir litellm && cd litellm
```

创建 `config.yaml`：

```yaml
model_list:
  - model_name: claude-sonnet-4-6
    litellm_params:
      model: openai/claude-sonnet-4-6
      api_base: https://yotradeapi.com/v1
      api_key: os.environ/UPSTREAM_KEY

  - model_name: claude-opus-4-7
    litellm_params:
      model: openai/claude-opus-4-7
      api_base: https://yotradeapi.com/v1
      api_key: os.environ/UPSTREAM_KEY

  - model_name: gpt-5
    litellm_params:
      model: openai/gpt-5
      api_base: https://yotradeapi.com/v1
      api_key: os.environ/UPSTREAM_KEY

  - model_name: gemini-2.5-pro
    litellm_params:
      model: openai/gemini-2.5-pro
      api_base: https://yotradeapi.com/v1
      api_key: os.environ/UPSTREAM_KEY

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
```

跑起来：

```bash
docker run -d \
  --name litellm \
  -p 4000:4000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -e UPSTREAM_KEY=sk-yo-... \
  -e LITELLM_MASTER_KEY=sk-master-... \
  -e DATABASE_URL=postgresql://litellm:pass@host/litellm \
  ghcr.io/berriai/litellm:main-stable \
  --config /app/config.yaml --port 4000 --num_workers 4
```

需要 Postgres 数据库存 Key、用量、预算记录。

访问 `http://localhost:4000/health`，返回 healthy 即可。

## 三、给团队成员发 Key

通过 admin API 创建 Key：

```bash
curl http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{
    "models": ["claude-sonnet-4-6", "claude-haiku-4-5"],
    "max_budget": 50.0,
    "user_id": "alice",
    "duration": "30d"
  }'
```

返回：

```json
{ "key": "sk-team-alice-xxxx", "expires": "..." }
```

把这个 key 发给 alice。她在 Cursor / Claude Code 里配：

```
base_url: http://your-server:4000
api_key: sk-team-alice-xxxx
```

完事。她以后用什么模型、用多少、有没有超预算，你都能在 admin 后台看到。

## 四、按用户 / 项目预算

```bash
# 项目预算
curl http://localhost:4000/team/new \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{
    "team_alias": "research-team",
    "max_budget": 500.0,
    "models": ["claude-opus-4-7", "claude-sonnet-4-6"]
  }'

# 给团队成员发 Key 时绑定 team
curl http://localhost:4000/key/generate \
  -d '{
    "team_id": "research-team-id",
    "user_id": "bob",
    "max_budget": 100.0
  }'
```

预算继承机制：

- 团队预算 = 团队下所有用户预算之和的上限
- 用户预算单独受限
- 超额 LiteLLM 自动返回 429

## 五、路由策略

LiteLLM 支持高级路由：

```yaml
model_list:
  - model_name: best-model
    litellm_params:
      model: openai/claude-opus-4-7
      api_base: https://yotradeapi.com/v1
      api_key: os.environ/UPSTREAM_1_KEY
    model_info:
      tpm: 100000   # 这个上游的 TPM

  - model_name: best-model
    litellm_params:
      model: openai/claude-opus-4-7
      api_base: https://backup-relay.example.com/v1
      api_key: os.environ/UPSTREAM_2_KEY

router_settings:
  routing_strategy: usage-based-routing-v2
  fallbacks:
    - best-model: ["claude-sonnet-4-6"]   # 失败时降级
```

逻辑：

- 同 `model_name` 多个 entry → 自动负载均衡
- 主上游挂了 → fallback 模型
- 按 TPM 智能路由（usage-based）

这样团队不感知具体上游切换，**自动 high availability**。

## 六、用量统计与告警

LiteLLM 内置 Prometheus exporter：

```yaml
general_settings:
  enable_prometheus: true
```

```bash
curl http://localhost:4000/metrics
```

接到 Grafana 看：

- 总请求数
- 按用户 / 团队 / 模型分布
- 错误率
- p50 / p95 延迟
- token 消耗

配 alertmanager 触发钉钉 / 企微：

- 团队日预算 80% → 提醒
- 错误率 > 5% → 紧急

## 七、日志与审计

```yaml
litellm_settings:
  set_verbose: false
  json_logs: true
  log_redis_response: false
  drop_params: false
```

所有请求记录到数据库与 stdout。**敏感场景关闭 prompt body 记录**：

```yaml
litellm_settings:
  redact_user_api_key_info: true
  turn_off_message_logging: true
```

## 八、跟现有工具的对接

### Cursor

```
Custom Endpoint: http://your-litellm:4000
API Key: sk-team-xxx
Model: claude-sonnet-4-6
```

### Claude Code

LiteLLM 默认是 OpenAI 兼容协议，Claude Code 需要 Anthropic 协议。LiteLLM 支持：

```bash
export ANTHROPIC_BASE_URL="http://your-litellm:4000"
export ANTHROPIC_AUTH_TOKEN="sk-team-xxx"
```

LiteLLM 自动协议转换。

### CI/CD

CI 用一把独立的 LiteLLM Key，设较低预算：

```yaml
env:
  OPENAI_API_KEY: ${{ secrets.LITELLM_CI_KEY }}
  OPENAI_API_BASE: http://litellm.internal:4000
```

## 九、生产部署注意

1. **数据库高可用**：用 RDS / Neon 等托管 Postgres
2. **多副本**：跑 3 副本前面挂 nginx，避免单点
3. **TLS**：内部也用 HTTPS，至少 mTLS
4. **Master Key 严格保护**：写进 secrets manager，不要文件
5. **定期备份**：所有 Key 与用量数据
6. **监控延迟**：Litellm Proxy 自身延迟应 < 100ms

## 十、LiteLLM vs 直接用中转

| 维度 | 直接用中转 | LiteLLM Proxy |
| --- | --- | --- |
| 部署 | 0 | 需要服务器 + DB |
| 团队管理 | 看中转后台 | 自己控 |
| 多上游 | 不便切换 | 简单 |
| 用量审计 | 中转后台 | 完全自主 |
| 数据隐私 | 看中转 | 内部 |
| 适合规模 | 个人 / 小团队 | 中大型团队 |

简单结论：

- **个人 / 小团队**：直接用中转
- **中大型团队（10+ 人）**：LiteLLM + 中转作为上游

## 十一、典型架构

```
团队成员（开发机）
   ↓
   ├── 内部 LiteLLM Proxy (HA × 3)
   │       ↓
   │       ├── 中转 A（YoTradeApi，主）
   │       ├── 中转 B（backup）
   │       └── 官方 API（fallback）
   └── 监控（Prometheus + Grafana + 告警）
```

## 十二、相关阅读

- [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)
- [API Key 泄露应急响应手册](/blog/api-key-leak-emergency-response/)
- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)

LiteLLM 上游配 [YoTradeApi](https://yotradeapi.com)，一把 Key 给整个 LiteLLM 用，团队 Key 在 LiteLLM 后台单独发。
