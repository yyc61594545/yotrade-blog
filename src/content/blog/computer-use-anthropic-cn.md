---
title: Claude Computer Use 实战：让 AI 操作你的电脑
description: Anthropic Computer Use 在国内通过中转接入的可行性、Docker 沙箱、用例与风险，含完整 Python 接入代码与边界提醒。
keywords:
- claude computer use
- anthropic computer use
- ai 操作 电脑
- claude 桌面 自动化
- computer use 国内
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/computer-use-anthropic-cn/
tags:
- Computer Use
- Anthropic
- Agent
- 桌面自动化
- 进阶
category: 工程实战
heroImage: ../../assets/blog-placeholder-3.jpg
---

# Claude Computer Use 实战：让 AI 操作你的电脑

Anthropic 在 2024 年发布了 Computer Use——让 Claude 控制鼠标、键盘、看截图、操作浏览器。这是 LLM 走向"真正 agent"的关键一步。本文给国内接入与使用的实战指南，附完整边界提醒。

## 一、Computer Use 是什么

简单理解：

```
你 → "帮我去 Twitter 发一条说 hello"
  ↓
Claude → 截屏 → 看到桌面 → 决定点哪里 → 调用 click()/type() → 截屏 → ...
  ↓
完成任务
```

技术上 Claude 调用三类工具：

- `computer`：截屏、鼠标、键盘
- `bash`：跑 shell 命令
- `text_editor`：编辑文本文件

## 二、风险与边界

**先讲风险**，再讲怎么用。

| 风险 | 严重度 |
| --- | --- |
| 误操作误删文件 | 高 |
| 输入密码 / 验证码风险 | 高 |
| 网页跳转后被钓鱼 | 中 |
| 跨网站身份混淆 | 中 |
| 时长任务失控 | 中 |
| 隐私（截屏给云端） | 中 |

**官方推荐**：在虚拟机或 Docker 容器里跑，**不要在主机直接跑**。

## 三、最小 Docker 部署

Anthropic 提供官方 demo 容器：

```bash
# 拉取镜像
docker pull ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest

# 跑（含 noVNC）
docker run \
    -e ANTHROPIC_API_KEY=sk-yo-... \
    -e ANTHROPIC_BASE_URL=https://yotradeapi.com \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest
```

浏览器打开 `http://localhost:8080`，看到一个 Linux 桌面（Xfce）+ 右侧 Streamlit 对话框。

输入任务："打开 Firefox，搜索 weather Beijing"，按 Send。Claude 开始操作。

## 四、走中转

`ANTHROPIC_BASE_URL=https://yotradeapi.com` 即可。中转需要支持：

- `/v1/messages` 端点
- `computer-use-*` beta 头透传
- 大尺寸图片（截屏，每张约 100k tokens）

测试：

```bash
curl https://yotradeapi.com/v1/messages \
  -H "x-api-key: $KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: computer-use-2024-10-22" \
  -d '{
    "model": "claude-sonnet-4-6",
    "max_tokens": 1024,
    "tools": [{"type": "computer_20241022", "name": "computer", "display_width_px": 1024, "display_height_px": 768, "display_number": 1}],
    "messages": [{"role": "user", "content": "截图当前桌面"}]
  }'
```

返回里看到 `tool_use` block + computer tool call 即正常。

## 五、Python 自实现（不用 Streamlit demo）

```python
import anthropic
from anthropic.types.beta import BetaToolComputerUse20241022Param
import base64, subprocess

client = anthropic.Anthropic(
    base_url="https://yotradeapi.com",
    api_key="sk-yo-...",
)

def screenshot():
    """截屏并返回 base64"""
    subprocess.run(["scrot", "/tmp/sc.png"])
    return base64.b64encode(open("/tmp/sc.png", "rb").read()).decode()

def execute_tool(tool_use):
    if tool_use.name == "computer":
        action = tool_use.input["action"]
        if action == "screenshot":
            return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot()}}
        elif action == "left_click":
            x, y = tool_use.input["coordinate"]
            subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "1"])
            return "clicked"
        elif action == "type":
            text = tool_use.input["text"]
            subprocess.run(["xdotool", "type", text])
            return "typed"
        # 其它 action: key, mouse_move, scroll, etc.

messages = [{"role": "user", "content": "打开 Firefox 浏览器"}]

while True:
    resp = client.beta.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        tools=[{
            "type": "computer_20241022",
            "name": "computer",
            "display_width_px": 1024,
            "display_height_px": 768,
        }],
        messages=messages,
        betas=["computer-use-2024-10-22"],
    )

    messages.append({"role": "assistant", "content": resp.content})

    if resp.stop_reason == "end_turn":
        break

    tool_results = []
    for block in resp.content:
        if block.type == "tool_use":
            result = execute_tool(block)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": [result] if isinstance(result, dict) else result,
            })

    messages.append({"role": "user", "content": tool_results})
```

每个回合 Claude 看截图、决定动作、客户端执行、回传结果。

## 六、典型场景

### 场景 1：自动化 QA

让 Claude 跑一遍你的 web app：

```
> 任务：注册新用户、登录、上传一个文件、修改设置、退出登录。
> 期间出现任何错误立刻报告。
> 用 admin@test.com / password 注册。
```

比 Playwright 灵活，能处理"页面变化"的情况。

### 场景 2：跨应用工作流

```
> 任务：从邮件里找到最新 invoice，把数字填到这个 Excel 表，发邮件回复确认。
```

跨多个应用，传统脚本不容易写。

### 场景 3：抓数据

```
> 任务：去 example.com 把所有产品价格抓出来存 CSV。
```

比 Selenium 适应性强。但**爬虫场景看清楚目标网站 ToS**。

## 七、性能与成本

| 指标 | 实测值 |
| --- | --- |
| 单次截图 token | ~1500–2000 |
| 一个 5 分钟任务 | 100k–300k tokens |
| 单次任务成本 | $1–5 |
| 任务成功率 | 60–85%（看场景） |

**Computer use 是当前最贵的 Claude 用法**。简单任务别用——Playwright 脚本更便宜更稳。

## 八、对比 Playwright / Puppeteer

| 维度 | Computer Use | Playwright |
| --- | --- | --- |
| 学习成本 | 低 | 中 |
| 跨应用 | ✓ | ✗ |
| 适应 UI 变化 | 强 | 弱 |
| 速度 | 慢 | 快 |
| 成本 | 高 | 几乎 0 |
| 调试 | 难 | 容易 |
| 稳定性 | 中 | 高 |

**结论**：

- 重复性高的流程 → Playwright
- 一次性 / 探索性 / 跨应用 → Computer Use

## 九、安全清单

启用 Computer Use 之前**逐条确认**：

- [ ] 跑在 Docker / VM，不在主机
- [ ] 容器内文件系统隔离
- [ ] 不暴露 production secrets
- [ ] 不让 agent 访问你的银行 / 邮件
- [ ] 任务有时限上限（超时强制停）
- [ ] 截屏不包含敏感信息（事先 mask）
- [ ] 中转后台预算上限
- [ ] 操作日志保留（审计）

## 十、Computer Use 2025 现状

| 维度 | 现状 |
| --- | --- |
| 模型 | Claude Sonnet 4.6 / Opus 4.7 |
| 协议 | beta（可能变化） |
| OS 支持 | Linux + macOS（社区方案） |
| 中转支持 | 看具体中转 |
| 浏览器 / 桌面 | 都行 |

**仍是 beta 特性**，生产慎用。当前主要用于：

- 内部 QA 自动化
- 演示 / 探索
- 一次性数据采集

## 十一、相关阅读

- [Claude Code Subagent 实战](/blog/claude-code-subagent-practice/)
- [Claude Extended Thinking 完整指南](/blog/claude-extended-thinking-guide/)
- [Claude 并行 Tool Use 实战](/blog/parallel-tool-use-claude/)
- [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)
- [API Key 泄露应急响应](/blog/api-key-leak-emergency-response/)

需要透传 computer-use beta 头的中转？[YoTradeApi](https://yotradeapi.com) 完整透传 Anthropic beta headers，按上面 Docker 命令直接接入。
