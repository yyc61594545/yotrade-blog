---
title: AI API 中转稳定性测试方法
description: 可复现的 AI API 中转稳定性评估方案，覆盖首 token 延迟、断流率、长上下文、并发与失败重试，附 Python 测试脚本。
keywords:
- ai api 中转 稳定性
- api 中转 测试
- llm api 稳定性
- 中转 断流率
- 中转 首 token 延迟
pubDate: '2026-05-18'
updatedDate: '2026-05-18'
canonical: https://blog.yotradeapi.com/blog/ai-api-relay-stability-test/
tags:
- 稳定性测试
- API 中转
- 性能评测
- Python
category: 测试评测
featured: true
heroImage: ../../assets/blog-placeholder-4.jpg
---

中转服务"看起来能用"和"真的能用"中间隔着一条不小的鸿沟。一个 Cursor 任务跑 30 分钟，中间断一次流就要从头来过。本文给一套可以复制粘贴跑起来的测试方案，把"稳定性"拆成可测的几个数字，让换中转这件事从感觉判断变成数据判断。

## 一、把"稳定性"拆开

直接说"稳不稳"没法判断。我们把它拆成 6 个指标：

| 指标 | 定义 | 实用阈值（编程代理场景） |
| --- | --- | --- |
| TTFB（time to first byte） | 从发请求到收到第一个 token 的时间 | p50 < 2s, p95 < 5s |
| 总时延 | 整个请求耗时 | p95 < 30s（短任务） |
| 输出速率 | tokens / 秒 | > 30 tokens/s |
| 断流率 | 流式响应中途断开比例 | < 1% |
| 错误率 | 非 2xx 状态码比例 | < 0.5% |
| 长上下文成功率 | 128k 输入完整返回比例 | > 99% |

这 6 个数字一旦拉到日表上，"中转好不好"就有了客观结论。

## 二、测试矩阵设计

不要只跑一种 prompt。设计一个矩阵覆盖典型 workload：

| 场景 | 输入长度 | 输出预期 | 测试目的 |
| --- | --- | --- | --- |
| short_qa | ~200 tokens | ~100 | TTFB、协议握手 |
| code_gen | ~2k | ~1k | 编程代理日常 |
| long_context | ~64k | ~2k | 大上下文吞吐 |
| concurrent | 100 并发 short_qa | -- | 限流策略 |
| tool_call | 含 tools | function call | 协议兼容 |
| vision | 含 image | 文字描述 | 多模态 |

## 三、最小测试脚本：stability_probe.py

```python
"""
用法：
  python stability_probe.py --base-url https://yotradeapi.com/v1 \
      --api-key sk-xxx --model claude-sonnet-4-6 --runs 30
输出：
  CSV：ts, scenario, ttfb, total, tokens, status, error
"""
import argparse, csv, json, statistics, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI, APIError, APIConnectionError, RateLimitError

SCENARIOS = {
    "short_qa": [
        {"role": "user", "content": "用 1 句话解释什么是 LRU 缓存。"}
    ],
    "code_gen": [
        {"role": "system", "content": "你是严谨的 TypeScript 工程师。"},
        {"role": "user", "content": (
            "写一个 fetch 包装器，支持超时、指数退避重试、自动 JSON 解析，"
            "包含完整 TypeScript 类型签名与单元测试。"
        )}
    ],
    "long_context": [
        {"role": "user", "content": "请总结下面这段代码：\n" + ("// noop line\n" * 8000)}
    ],
}

def run_one(client, model, scenario, messages):
    t0 = time.time()
    first_t = None
    out_tokens = 0
    status = "ok"
    error = ""
    try:
        stream = client.chat.completions.create(
            model=model, messages=messages, stream=True, timeout=120
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                if first_t is None:
                    first_t = time.time() - t0
                out_tokens += 1
    except RateLimitError as e:
        status, error = "429", str(e)[:200]
    except APIConnectionError as e:
        status, error = "conn", str(e)[:200]
    except APIError as e:
        status, error = f"api_{e.status_code}", str(e)[:200]
    except Exception as e:
        status, error = "exc", repr(e)[:200]
    return {
        "ts": int(time.time()),
        "scenario": scenario,
        "ttfb": round(first_t or 0, 3),
        "total": round(time.time() - t0, 3),
        "tokens": out_tokens,
        "status": status,
        "error": error,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--concurrent", type=int, default=1)
    ap.add_argument("--scenarios", default="short_qa,code_gen")
    ap.add_argument("--out", default="stability.csv")
    args = ap.parse_args()

    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    rows = []
    scenarios = args.scenarios.split(",")

    with ThreadPoolExecutor(max_workers=args.concurrent) as ex:
        futures = []
        for _ in range(args.runs):
            for s in scenarios:
                futures.append(ex.submit(run_one, client, args.model, s, SCENARIOS[s]))
        for f in as_completed(futures):
            row = f.result()
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False))

    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    by_scenario = {}
    for r in rows:
        by_scenario.setdefault(r["scenario"], []).append(r)
    for s, items in by_scenario.items():
        ok = [r for r in items if r["status"] == "ok"]
        if not ok:
            print(f"{s}: ALL FAIL"); continue
        ttfb = [r["ttfb"] for r in ok if r["ttfb"]]
        total = [r["total"] for r in ok]
        err = [r for r in items if r["status"] != "ok"]
        print(f"{s}: n={len(items)} ok={len(ok)} "
              f"ttfb_p50={statistics.median(ttfb):.2f}s "
              f"ttfb_p95={sorted(ttfb)[int(len(ttfb)*0.95)-1]:.2f}s "
              f"total_p50={statistics.median(total):.2f}s "
              f"err_rate={len(err)/len(items):.2%}")

if __name__ == "__main__":
    main()
```

跑法（建议至少 30 次）：

```bash
python stability_probe.py \
  --base-url https://yotradeapi.com/v1 \
  --api-key $YOTRADE_API_KEY \
  --model claude-sonnet-4-6 \
  --runs 30 --concurrent 4 \
  --scenarios short_qa,code_gen
```

## 四、长上下文专项测试

`long_context` 这个场景容易把网关打出问题。建议单独跑：

```bash
python stability_probe.py --runs 5 --concurrent 1 --scenarios long_context ...
```

观察点：

- 是否真的接受 64k 以上输入（部分网关有隐性截断）
- 输出是否在 800 tokens 后断流（流式 keep-alive 配置）
- 总时延是否超过 90s

## 五、并发与限流测试

把 `--concurrent` 拉到 20、50、100，看错误码分布：

| 错误码 | 含义 | 怎么应对 |
| --- | --- | --- |
| 429 + Retry-After 头 | 网关合理限流 | 客户端按头部退避 |
| 429 无 Retry-After | 限流但不友好 | 客户端固定 5s 退避，记录 |
| 502/504 | 上游断流 | 中转可能用同一节点扛不住 |
| connection reset | TCP 层断 | 网络绕路问题 |

429 本身不是坏事——明确告诉你"该退避了"。比 502 + 不告诉你原因强得多。

## 六、跨中转对比

把脚本同时跑多家中转，把 CSV 合并：

```bash
for base in \
  "https://yotradeapi.com/v1|sk-yo-xx" \
  "https://other-relay.example.com/v1|sk-ot-xx"; do
  url="${base%|*}"; key="${base#*|}"
  python stability_probe.py --base-url "$url" --api-key "$key" \
      --model claude-sonnet-4-6 --runs 30 \
      --out "$(echo $url | sed 's|[/:]|_|g').csv"
done
```

然后用 pandas/Excel 出一张总览表。**关键纪律**：对比时模型名要一致、prompt 要一致、运行时段要接近，否则数据没意义。

## 七、CI 接入

把脚本放进 GitHub Actions 每 6 小时跑一次：

```yaml
name: relay-stability
on:
  schedule: [{ cron: "0 */6 * * *" }]
  workflow_dispatch:
jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install openai
      - env:
          KEY: ${{ secrets.YOTRADE_API_KEY }}
        run: |
          python stability_probe.py \
            --base-url https://yotradeapi.com/v1 \
            --api-key "$KEY" --model claude-sonnet-4-6 \
            --runs 20 --concurrent 2 --out today.csv
      - uses: actions/upload-artifact@v4
        with: { name: stability, path: today.csv }
```

跑一周之后，谁稳谁不稳就有答案了。

## 八、判断标准建议

最终怎么用这些数据下决策？我个人的阈值是：

- **可以接入生产**：err_rate < 0.5%，TTFB p95 < 5s，长上下文成功率 > 99%
- **可以做小流量**：err_rate < 2%，TTFB p95 < 8s
- **只能玩玩**：err_rate > 5% 或长上下文经常失败

数字到不了第一条不要接入正式工作流，**断流一次的恢复成本远高于换网关的成本**。

## 九、相关阅读

- [Cursor API 中转怎么选：2026 实用清单](/blog/2026-05-15-cursor-api-relay-recommendation-2026/)
- [Claude Code 镜像国内配置完整指南](/blog/claude-code-mirror-cn-setup/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [AI API 中转常见错误码排查手册](/blog/ai-api-relay-error-codes/)

如果你需要一个稳定的基线来对比其它中转，[YoTradeApi](https://yotradeapi.com) 提供独立 API Key 与用量日志，方便直接接入上面这套脚本做基线测试。
