---
title: 国内用户通过 AWS Bedrock 使用 Claude Code 完整配置
description: 详解国内开发者借助 AWS Bedrock 在 Claude Code 中使用 Claude 模型的完整配置流程，含账号、IAM、环境变量与常见错误排查。
keywords:
  - AWS Bedrock Claude Code
  - 国内使用 Claude Code
  - Bedrock Claude 配置
  - Claude Code 企业方案
  - AWS Bedrock 中国开发者
pubDate: '2026-06-05'
updatedDate: '2026-06-05'
canonical: https://blog.yotradeapi.com/blog/cn-claude-code-via-bedrock/
tags:
  - Claude Code
  - AWS Bedrock
  - 国内场景
  - 配置教程
category: 国内场景
heroImage: ../../assets/blog-placeholder-2.jpg
---

对于在国内工作的开发者，使用 Claude Code 有两条主要路径：**API 中转**和 **AWS Bedrock**。前者配置最简单，适合个人开发者；后者走 AWS 官方基础设施，适合对数据合规有要求、公司已有 AWS 采购合同的团队。

本文专注讲 Bedrock 这条路的完整配置流程。如果只是想快速上手 Claude Code，可以先看 [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)。Bedrock 与直连 Anthropic 的选型对比，见 [走 Anthropic Direct vs Bedrock vs 中转：怎么选](/blog/anthropic-bedrock-vs-direct/)。

## 一、Bedrock 路径的前提条件

通过 Bedrock 使用 Claude Code，你需要：

1. **AWS 账号**（国际区，非 AWS 中国区——中国区的 Bedrock 不支持 Claude）
2. **申请 Claude 模型访问权限**：Bedrock 默认不开放 Claude，需要在控制台手动申请
3. **IAM 用户或角色**：带 `bedrock:InvokeModel` 和 `bedrock:InvokeModelWithResponseStream` 权限
4. **AWS CLI**（可选但推荐）：用于本地凭证管理

以下步骤以 `us-east-1`（弗吉尼亚）区域为例，该区域 Claude 模型齐全、延迟相对较低。

## 二、申请 Claude 模型访问权限

Bedrock 的模型访问是按区域、按模型申请的。

1. 登录 AWS 控制台，切换到 `us-east-1`
2. 进入 **Amazon Bedrock → Model access**
3. 点击 **Modify model access**
4. 勾选 `Claude` 系列（建议全选：Claude 3.5 Sonnet、Claude 3.5 Haiku、Claude Opus 4、Claude Sonnet 4）
5. 提交申请

Anthropic 的模型通常需要填写使用目的，审核在几分钟到几小时内完成。申请通过后，对应模型状态变为 **Access granted**。

> **注意**：不同区域的可用模型不同。`us-east-1` 和 `us-west-2` 目前（2026 年）模型最全，建议选这两个区域之一。

## 三、配置 IAM 权限

### 3.1 最小权限策略

为 Claude Code 创建一个专用的 IAM 用户（或使用角色），附加以下内联策略：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockClaudeCodeAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-opus-4-*",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-*",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-*",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-*"
      ]
    }
  ]
}
```

### 3.2 创建 Access Key

在 IAM 控制台为该用户创建 Access Key（选择 **Local code** 用途），保存 `AWS_ACCESS_KEY_ID` 和 `AWS_SECRET_ACCESS_KEY`。

### 3.3 配置本地凭证

推荐通过 AWS CLI 配置（安全，避免在 shell 配置文件中明文写密钥）：

```bash
aws configure --profile claude-code
# 依次输入：
# AWS Access Key ID: <你的 key>
# AWS Secret Access Key: <你的 secret>
# Default region name: us-east-1
# Default output format: json
```

或者直接设置环境变量（CI/CD 场景常用）：

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"
```

## 四、配置 Claude Code 使用 Bedrock

Claude Code 通过环境变量切换到 Bedrock 模式：

```bash
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-east-1
```

如果使用了命名 profile，还需要：

```bash
export AWS_PROFILE=claude-code
```

然后正常启动 Claude Code：

```bash
claude
```

启动后，Claude Code 会自动使用 Bedrock 端点调用 Claude，而不是 Anthropic 直连端点。

### 4.1 持久化配置

将环境变量写入 shell 配置文件（以 zsh 为例）：

```bash
# ~/.zshrc
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-east-1
export AWS_PROFILE=claude-code
```

或者使用 Claude Code 的项目级配置（`.claude/settings.json`）：

```json
{
  "env": {
    "CLAUDE_CODE_USE_BEDROCK": "1",
    "AWS_REGION": "us-east-1"
  }
}
```

## 五、可用的模型 ID 对照表

Bedrock 的模型 ID 格式与 Anthropic 直连不同：

| Claude Code 场景 | Anthropic 直连 ID | Bedrock 模型 ID |
|-----------------|-------------------|-----------------|
| 主力推理（大任务） | claude-opus-4-8 | anthropic.claude-opus-4-20250514-v1:0 |
| 日常编码 | claude-sonnet-4-6 | anthropic.claude-sonnet-4-20250514-v1:0 |
| 快速交互 | claude-haiku-4-5 | anthropic.claude-haiku-4-20250307-v1:0 |
| 长上下文 | claude-3-5-sonnet | anthropic.claude-3-5-sonnet-20241022-v2:0 |

Claude Code 在 Bedrock 模式下会自动使用对应的 Bedrock 模型 ID，无需手动指定。

## 六、网络访问：国内到 AWS 的连通性

这是 Bedrock 方案在国内最关键的一步。AWS 的国际区域（us-east-1 等）在国内需要走代理才能稳定访问。

**推荐做法**：

```bash
# 方案一：HTTP 代理（最简单）
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890

# 方案二：通过公司 VPN
# 连接公司 VPN 后，AWS API 通常可以正常访问

# 方案三：在境外服务器上运行 Claude Code
# 延迟会高一些，但网络最稳定
```

**延迟参考**：
- 国内 + 代理 → us-east-1：通常 200–500ms 首 token 延迟
- 境外服务器 → us-east-1：通常 100–200ms 首 token 延迟

相比 Anthropic 中转方案，Bedrock 走 AWS SDK 的 HTTPS 请求，代理兼容性更好，不容易遇到 SSE 断连问题。

## 七、常见错误与排查

### 7.1 `UnauthorizedException`

```
Error: UnauthorizedException: You don't have access to the model with the specified model ID
```

**解决**：回到 Bedrock 控制台确认模型申请已通过（状态为 Access granted），且申请的区域与 `AWS_REGION` 一致。

### 7.2 `AccessDeniedException`

```
Error: AccessDeniedException: User: arn:aws:iam::xxx is not authorized to perform: bedrock:InvokeModelWithResponseStream
```

**解决**：检查 IAM 策略是否包含 `bedrock:InvokeModelWithResponseStream`，以及 Resource ARN 中的区域是否正确。

### 7.3 凭证未找到

```
Error: Unable to locate credentials
```

**解决**：
```bash
# 验证凭证配置
aws sts get-caller-identity --profile claude-code

# 如果使用环境变量，检查是否已 export
echo $AWS_ACCESS_KEY_ID
```

### 7.4 SSE 流式响应中断

国内网络环境下，长时间的流式响应可能在中途断开。可以尝试：

1. 检查代理的超时设置（建议 > 120 秒）
2. 使用 `--no-stream` 参数（如果 Claude Code 支持）回退到非流式模式
3. 换用延迟更低的代理节点

## 八、Bedrock 方案的费用计算

Bedrock 按实际 token 消耗计费，与 Anthropic 直连价格基本持平，但有以下区别：

- **无月费**：不需要订阅 Claude.ai Pro 或 Max，按用量付费
- **AWS Credits 可抵扣**：如果公司有 AWS 信用额度，可以直接使用
- **不支持 Claude Code 的月费套餐**：Claude Code 官方的 $20/$100 套餐只适用于 Anthropic 直连，Bedrock 不参与

具体价格建议在 AWS Bedrock 定价页面查询最新数据，因为价格会随模型版本更新而调整。

## 九、相关阅读

- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [走 Anthropic Direct vs Bedrock vs 中转：怎么选](/blog/anthropic-bedrock-vs-direct/)
- [Claude Code 真实生产任务实践：10 个场景复盘](/blog/claude-code-real-world-tasks/)
- [Claude Code Hooks 工作流：自定义自动化场景](/blog/claude-code-hooks-workflow/)
- [Claude Code 子 Agent 实践：复杂任务分解策略](/blog/claude-code-subagent-practice/)

如果 AWS 注册或付款存在障碍，[YoTradeApi](https://yotradeapi.com) 提供开箱即用的 Claude API 中转，支持国内支付，可作为快速上手 Claude Code 的替代方案。
