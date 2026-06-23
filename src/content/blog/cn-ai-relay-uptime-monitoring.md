---
title: 中转服务可用性自助监控方案
description: 国内开发者必备：用 Python + 免费工具自建 AI API 中转服务可用性监控，实时告警、历史记录、多节点探测一步到位。
keywords:
  - ai api 中转 可用性监控
  - 中转服务 uptime 监控
  - llm api 中转 告警
  - 国内 ai api 监控方案
  - python api 健康检查
pubDate: '2026-06-23'
updatedDate: '2026-06-23'
canonical: https://blog.yotradeapi.com/blog/cn-ai-relay-uptime-monitoring/
tags:
  - 中转服务
  - 监控
  - 国内场景
  - Python
  - 运维
category: 国内场景
heroImage: ../../assets/blog-placeholder-3.jpg
---

做国内 AI 开发，最怕的不是 API 贵，而是"不知道挂了"——项目凌晨跑 batch 任务，中转服务断了三小时，早上才发现数据全空。本文给出一套**可直接落地**的自助监控方案，从轻量脚本到可视化 Dashboard 逐级递进，按需取用。

## 一、为什么需要自建监控

中转服务不同于直连官方 API，中间多了一跳（甚至多跳），任何一个环节出问题都会影响可用性：

| 故障点 | 典型现象 | 官方 API 是否同样出现 |
|--------|---------|----------------------|
| 中转节点网络抖动 | 超时 / 高延迟 | 否 |
| 中转服务本身宕机 | Connection refused / 502 | 否 |
| 上游模型降级 | 响应异常或被截断 | 是 |
| 中转计费池耗尽 | 429 / 余额不足错误 | 否（Key 问题） |
| 中转 IP 被阻断 | 特定时段失败率骤升 | 否 |

中转方虽然通常有自己的状态页，但：

1. 状态页更新不一定及时
2. 状态页描述的是"整体"，你的账户 / 特定模型可能有局部问题
3. 自己的业务场景（特定 Endpoint + 模型 + token 大小）才是最真实的探针

结论：**自建业务层监控是必要的**，不要完全依赖中转方的状态页。

## 二、最小可行方案：一个 Python 脚本

先跑起来，再考虑扩展。下面的脚本每分钟探测一次中转 Endpoint，失败时发送 bark / 企业微信告警。

```python
#!/usr/bin/env python3
"""minimal_monitor.py — 单文件 AI 中转可用性探针"""
import os, time, json, logging, requests
from datetime import datetime, timezone

RELAY_BASE   = os.environ["RELAY_BASE_URL"]   # 例如 https://api.yotradeapi.com/v1
RELAY_KEY    = os.environ["RELAY_API_KEY"]
MODEL        = os.environ.get("PROBE_MODEL", "gpt-4o-mini")
BARK_URL     = os.environ.get("BARK_URL", "")         # iOS Bark push
WXWORK_KEY   = os.environ.get("WXWORK_KEY", "")       # 企业微信 Webhook

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

def probe() -> dict:
    """发送最轻量探针请求，返回结构化结果。"""
    t0 = time.monotonic()
    try:
        resp = requests.post(
            f"{RELAY_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {RELAY_KEY}",
                     "Content-Type": "application/json"},
            json={"model": MODEL,
                  "messages": [{"role": "user", "content": "Reply OK"}],
                  "max_tokens": 5},
            timeout=30,
        )
        latency = time.monotonic() - t0
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"].strip()
        return {"ok": True, "latency": round(latency, 2),
                "status": resp.status_code, "reply": reply}
    except Exception as e:
        latency = time.monotonic() - t0
        return {"ok": False, "latency": round(latency, 2),
                "error": str(e)}

def notify(msg: str):
    """并行发送 Bark + 企业微信，任一失败不影响另一个。"""
    if BARK_URL:
        try:
            requests.get(f"{BARK_URL}/{requests.utils.quote(msg)}", timeout=10)
        except Exception as e:
            logging.warning("Bark push failed: %s", e)
    if WXWORK_KEY:
        try:
            requests.post(
                f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WXWORK_KEY}",
                json={"msgtype": "text", "text": {"content": msg}},
                timeout=10,
            )
        except Exception as e:
            logging.warning("WxWork push failed: %s", e)

def main():
    consecutive_failures = 0
    while True:
        result = probe()
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        if result["ok"]:
            logging.info("✅ OK  latency=%.2fs", result["latency"])
            if consecutive_failures >= 3:
                notify(f"✅ 中转恢复正常 ({MODEL}) @ {ts}")
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            logging.warning("❌ FAIL #%d  %s", consecutive_failures, result["error"])
            if consecutive_failures == 3:
                notify(f"⚠️ 中转连续 3 次失败 ({MODEL})\n{result['error']}\n@ {ts}")
        time.sleep(60)

if __name__ == "__main__":
    main()
```

**运行方式**：

```bash
export RELAY_BASE_URL="https://api.yotradeapi.com/v1"
export RELAY_API_KEY="sk-xxx"
export BARK_URL="https://api.day.app/your-device-key"
python3 minimal_monitor.py
```

这个脚本已经能覆盖大多数个人项目的需求。接下来看更完善的方案。

## 三、多节点 + 多模型矩阵探测

当你同时用多个中转服务或多个模型时，需要矩阵式探测：

```python
PROBES = [
    {"label": "YoTrade-GPT4o",     "base": "https://api.yotradeapi.com/v1",  "model": "gpt-4o"},
    {"label": "YoTrade-Claude",    "base": "https://api.yotradeapi.com/v1",  "model": "claude-3-5-sonnet-20241022"},
    {"label": "YoTrade-Gemini",    "base": "https://api.yotradeapi.com/v1",  "model": "gemini-2.0-flash"},
]
```

用 `concurrent.futures.ThreadPoolExecutor` 并行探测，总耗时等于最慢的那个，而非所有探测之和：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def probe_all(probes: list, key: str) -> list:
    results = []
    with ThreadPoolExecutor(max_workers=len(probes)) as executor:
        futures = {executor.submit(probe_one, p, key): p for p in probes}
        for future in as_completed(futures):
            label = futures[future]["label"]
            r = future.result()
            r["label"] = label
            results.append(r)
    return results
```

这样每轮探测耗时约等于单次 API 调用，不会因为探测数量线性增长。

## 四、接入免费 Uptime 工具做历史记录

光有告警还不够，历史趋势同样重要——某个中转在每天凌晨 2–4 点稳定抖动？这种规律只有历史数据才能发现。

### 方案 A：UptimeRobot（免费层足够）

1. 注册 [UptimeRobot](https://uptimerobot.com)，新建 **HTTP(s) monitor**
2. URL 填中转的 Healthcheck Endpoint（很多中转服务提供 `/health`）
3. 如果中转没有公开 `/health`，可以在自己的 VPS 跑上面的脚本，通过 **Push monitor** 方式上报

Push monitor 模式：UptimeRobot 给你一个心跳 URL，脚本每次探测成功就 GET 这个 URL；如果一定时间没有心跳，触发 Down 告警。

```python
HEARTBEAT_URL = os.environ.get("UPTIMEROBOT_HEARTBEAT_URL", "")

if result["ok"] and HEARTBEAT_URL:
    requests.get(HEARTBEAT_URL, timeout=5)
```

### 方案 B：Grafana Cloud（有免费额度）

适合已经熟悉 Grafana 的团队。把探测结果写入 Prometheus 格式，通过 Remote Write 推到 Grafana Cloud：

```python
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

registry = CollectorRegistry()
g_latency = Gauge("relay_latency_seconds", "API relay probe latency",
                  ["label"], registry=registry)
g_up = Gauge("relay_up", "1 = up, 0 = down", ["label"], registry=registry)

# 每次探测后
g_latency.labels(label=label).set(result["latency"])
g_up.labels(label=label).set(1 if result["ok"] else 0)
push_to_gateway("https://prometheus-prod-xx.grafana.net/api/prom/push",
                job="relay_probe", registry=registry,
                handler=...)
```

然后在 Grafana 用 `relay_up` 画可用率曲线，`relay_latency_seconds` 画 P95 延迟趋势。

## 五、告警降噪：不要在凌晨被误报吵醒

监控告警最烦的不是"没告警"，而是"假告警太多"。几个实用策略：

### 5.1 连续失败 N 次才告警

上面脚本已经实现了 `consecutive_failures >= 3` 才告警，避免单次偶发超时误报。

### 5.2 时段静默

如果你的业务在某时段本来就不跑任务，可以设置静默窗口：

```python
from datetime import datetime

def is_silence_window() -> bool:
    hour = datetime.now().hour
    return 3 <= hour < 6  # 凌晨 3–6 点静默，按需调整

if not is_silence_window():
    notify(msg)
```

### 5.3 告警合并

连续告警时，不要每次都推送，改为"首次告警 + 恢复告警"：

```python
# 只在状态变化时通知
if consecutive_failures == 3:   # 刚刚进入 DOWN 状态
    notify(f"⚠️ DOWN: {label}")
elif consecutive_failures == 0 and prev_failures >= 3:  # 刚刚恢复
    notify(f"✅ UP: {label}")
```

## 六、在 GitHub Actions / 云函数上部署（不需要常驻服务器）

不想自己维护服务器？用 GitHub Actions 每 5 分钟触发一次探测：

```yaml
# .github/workflows/relay-probe.yml
name: Relay Uptime Probe
on:
  schedule:
    - cron: "*/5 * * * *"   # 每 5 分钟
  workflow_dispatch:

jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run probe
        env:
          RELAY_BASE_URL: ${{ secrets.RELAY_BASE_URL }}
          RELAY_API_KEY:  ${{ secrets.RELAY_API_KEY }}
          BARK_URL:       ${{ secrets.BARK_URL }}
        run: python3 scripts/minimal_monitor_once.py
        # 单次探测版，不含 while True 循环
```

GitHub Actions 免费层有 2000 分钟/月，每 5 分钟跑一次约消耗 288 分钟/天，免费额度完全够用于个人项目监控。

**注意**：GitHub Actions 最小调度粒度是 `*/5 * * * *`（5 分钟），不支持 1 分钟。如果需要更高频率，需要用 Fly.io / Railway 等平台部署常驻进程。

## 七、关键指标参考值

根据国内开发者使用 AI API 中转的普遍经验，以下是大致参考（仅作估算，以实测为准）：

| 指标 | 良好 | 可接受 | 需要关注 |
|------|------|--------|---------|
| 首 token 延迟（P50） | < 1.5s | 1.5–3s | > 3s |
| 首 token 延迟（P95） | < 5s | 5–10s | > 10s |
| 每小时失败率 | < 0.5% | 0.5–2% | > 2% |
| 连续失败次数 | 0–1 | 2 | ≥ 3 触发告警 |

中转服务与直连官方 API 相比，延迟通常会多 100–500ms（网络转发开销），属于正常范围。若延迟显著高于这个值，可能是节点拥塞或路由问题。

关于稳定性测试方法论，可参考已有文章 [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)，两篇侧重点不同：那篇侧重一次性基准测试，本文侧重持续生产监控。

## 八、相关阅读

- [AI API 中转稳定性测试方法](/blog/ai-api-relay-stability-test/)
- [AI API 中转服务对比：直连 vs 代理 vs 自建 VPN](/blog/ai-api-relay-vs-self-vpn/)
- [AI API 中转常见错误码排查手册](/blog/ai-api-relay-error-codes/)
- [AI Agent 成本监控实战：从 Token 到账单的全链路追踪](/blog/ai-agent-cost-monitoring/)
- [AI API 预算上限设计：防止账单爆炸的实用方案](/blog/ai-api-budget-cap-design/)

需要稳定、低延迟的国内 AI API 中转服务，[YoTradeApi](https://yotradeapi.com) 支持 GPT、Claude、Gemini 全系模型，按量计费无最低消费。
