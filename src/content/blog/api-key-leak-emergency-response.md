---
title: AI API Key 泄露应急响应手册
description: AI API Key 不慎泄露后的完整应急流程：吊销、追溯、止血、复盘，覆盖 OpenAI、Anthropic、中转网关三种场景。
keywords:
- api key 泄露
- openai key 泄露 应急
- ai api 安全
- key 吊销
- api 密钥 安全
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/api-key-leak-emergency-response/
tags:
- 安全
- API Key
- 应急响应
- 风险管理
category: 安全合规
heroImage: ../../assets/blog-placeholder-2.jpg
---

API Key 泄露是迟早会遇到的事——commit 进 git、screenshot 误发、第三方工具漏出。本文按"5 分钟止血 / 30 分钟追溯 / 1 天复盘"三个时间窗给完整应急清单。

## 一、确认泄露场景

第一步：搞清楚泄露的 key 是什么类型，泄露到哪里。

| 类型 | 风险点 |
| --- | --- |
| 主账号 root key | 极高，可以做任何事 |
| Project-scoped key | 中，限于项目 |
| 中转 key | 中（可吊销但已消费） |
| 子用户 key | 中 |

泄露位置：

- ✗ 公开 git repo（最严重）
- ✗ 公开 gist / pastebin
- ✗ 上传到公开存储（S3 公开桶）
- ✗ 截图发到群里 / 论坛
- ✗ 被第三方工具采集

## 二、5 分钟内：止血

### 步骤 1：立刻吊销

- **OpenAI**：dashboard → API Keys → 点击 trash 图标
- **Anthropic**：Console → API Keys → Disable
- **中转**：登录后台 → Keys → 删除或禁用

**不要犹豫，先吊销再调查**。每多 1 分钟都是钱在烧。

### 步骤 2：立即发新 key 切换

新建 key，先**不要给任何工具**，写到本地 `.env.new`。

### 步骤 3：本地替换

```bash
# 找出所有用旧 key 的地方
grep -r "sk-ant-old" ~ 2>/dev/null
grep -r "sk-old-key" ~ 2>/dev/null
```

逐一替换为新 key。

## 三、30 分钟内：追溯

### 步骤 4：拉用量日志

去网关后台拉**泄露时点之后**的请求日志：

- 来源 IP
- 调用模型
- token 消耗
- 时间分布

**异常信号**：

- 大量请求来自陌生 IP
- 调用了你没用过的模型
- 短时间内 token 暴涨
- 凌晨/非工作时段大量请求

### 步骤 5：财务损失评估

```
泄露时点到吊销时点 → 这段时间所有消费
减去 → 你自己已知的合法消费
余额 → 被滥用的损失
```

如果是几美元，自己吞下；如果是几百几千美元，考虑联系网关与官方申诉。

### 步骤 6：git 历史清理

如果泄露在 git repo：

```bash
# 安装 git-filter-repo
pip install git-filter-repo

# 清掉某个文件全历史
git filter-repo --invert-paths --path config.json --force

# 或清掉所有出现 sk-xxx 的内容
git filter-repo --replace-text <(echo "sk-ant-api03-xxx==>REMOVED")

# 然后强制推送
git push --force origin main
```

**警告**：`--force` 会改写历史，**协作者要同步重新 clone**。先沟通再推。

### 步骤 7：通知协作者

如果是团队 repo，告诉所有人：

1. Key 已吊销
2. 已发新 key（在哪里取）
3. 历史已重写（怎么 sync）
4. 之后避免哪些操作

## 四、1 天内：复盘

### 步骤 8：根因分析

问自己：

- 这个 key 当初是怎么落到容易泄露的地方的？
- 是流程问题还是工具问题？
- 还有哪些 key 在同样风险下？
- 监控为什么没第一时间报警？

### 步骤 9：制度化

防止下次再发生：

#### 1. `.gitignore` 必须包含

```
.env
.env.local
.env.*.local
*.key
secrets.json
*-credentials*
.claude/.local/
```

#### 2. 用 git-secrets / pre-commit hook

```bash
brew install git-secrets
git secrets --install
git secrets --register-aws   # 也支持自定义模式
git secrets --add 'sk-ant-api[0-9]+-[A-Za-z0-9_-]+'
git secrets --add 'sk-proj-[A-Za-z0-9_-]+'
```

每次 commit 前自动扫描，匹配到模式直接拒绝。

#### 3. 用环境变量 + 密钥管理

不要把 key 写进任何代码或配置文件。用：

- macOS: Keychain
- 1Password CLI
- AWS Secrets Manager / HashiCorp Vault
- 仅启动时 source 进环境变量

#### 4. Key 命名规则

每个 key 加 prefix 标识用途：

```
yotrade-prod-backend-***
yotrade-dev-cursor-***
yotrade-ci-deploy-***
yotrade-personal-***
```

泄露时一眼能看出影响范围，且可以单独吊销。

#### 5. 设独立预算上限

每个 key 在中转后台设日预算：

- 个人开发：$5–10
- CI：$2–5（单次跑完通常 < $1）
- 生产后端：按业务

泄露后即使没立刻吊销，最坏损失也封顶。

#### 6. 监控异常

每天看一次用量。或者写个脚本：

```python
def check():
    today = get_today_spend()
    if today > 2 * normal:
        notify_dingtalk("usage spike!")
```

钉钉 / 企微 / 邮件随便选一个。

### 步骤 10：审计相关数据

如果 key 有过权限读取 OpenAI Assistants / Files / Threads / Batches 等：

- 拉一份 list
- 删掉你不认识的内容

中转网关一般没这些，但官方账号有。

## 五、特殊场景

### 场景 A：截图带 key 发到群里

立刻：

1. 撤回消息（不一定能撤回）
2. 吊销 key
3. 群里发"这个 key 已吊销，请勿尝试使用"
4. 如果群是公开的，假设有人已截图保存了

### 场景 B：第三方工具调用泄露

某第三方插件被发现外发数据：

1. 吊销给它的 key
2. 看用量是否异常
3. 在该工具的 issue / 论坛发布警告
4. 卸载工具

### 场景 C：服务端环境变量泄露

服务器被入侵或环境变量被 `process.env` 打日志：

1. 吊销所有该机器上的 key
2. 重新生成所有 key
3. 改密码 / SSH 密钥
4. 排查入侵根因

## 六、不要做的事

- ❌ 不要"先看看用量再决定吊不吊"——直接吊销
- ❌ 不要发现泄露后继续用同一个 key 一两天
- ❌ 不要把"泄露事件"压下不通知团队
- ❌ 不要用同一个 key 给所有工具
- ❌ 不要在公开 repo 提交"已吊销的 key"——不法分子可能拿去做 abuse 报告

## 七、相关阅读

- [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)
- [AI 编程代理成本控制实战](/blog/ai-coding-agent-cost-control/)
- [Cursor API 中转怎么选](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [AI API 中转常见错误码排查手册](/blog/ai-api-relay-error-codes/)

[YoTradeApi](https://yotradeapi.com) 支持一键吊销 + 用量明细 + 日预算上限，应急响应 1 分钟内可完成止血。
