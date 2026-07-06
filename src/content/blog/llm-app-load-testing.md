---
title: LLM 应用压测方案：从指标设计到工具实现
description: 讲清 LLM 应用压测和传统 Web 压测的本质区别，如何设计并发模型、选取核心指标，附 locust 实测脚本与常见误区。
keywords:
  - LLM 应用压测
  - 大模型接口压测
  - LLM 并发测试
  - locust llm 测试
  - LLM 性能测试方案
pubDate: '2026-07-06'
updatedDate: '2026-07-06'
canonical: https://blog.yotradeapi.com/blog/llm-app-load-testing/
tags:
  - 压测
  - 性能测试
  - 应用工程
  - LLM 工程
category: 应用工程
heroImage: ../../assets/blog-placeholder-4.jpg
---

传统 Web 接口压测的思路是"发一堆请求，看 QPS 和响应时间"，直接套用到 LLM 应用上会得出误导性结论——因为 LLM 请求的响应时间不是一个稳定值，而是和输出长度强相关，还要考虑流式输出场景下"首字延迟"和"总耗时"是两个完全不同的指标。本文讲清楚 LLM 应用压测该怎么设计，而不是简单照搬传统压测工具的默认配置。

## 一、为什么不能直接套用传统压测思路

传统接口压测假设：同样的请求，响应时间基本稳定，QPS 是核心指标。这个假设在 LLM 场景下不成立，原因有三个：

1. **响应时间受输出长度影响**：同一个接口，输出 50 token 和输出 2000 token 的耗时可能差十几倍，用平均响应时间做单一指标会掩盖真实分布
2. **流式与非流式的"完成"定义不同**：流式场景下用户体验依赖首字延迟（TTFT），而不是总耗时；非流式场景只能等全部生成完才算完成
3. **上游服务商本身有并发限制**：LLM API 大多有 RPM/TPM 限流（参考 [LLM API 限速处理完整指南](/blog/llm-rate-limit-handling/)），压测很容易先把限流打满，测出来的"瓶颈"其实是限流阈值，不是你自己系统的真实承载能力

## 二、核心指标该怎么选

| 指标 | 含义 | 为什么重要 |
| --- | --- | --- |
| TTFT（首字延迟） | 从请求发出到收到第一个 token 的时间 | 流式场景下用户感知的"响应速度"主要看这个 |
| TPOT（单 token 生成耗时） | 首字之后，平均每个 token 的生成间隔 | 反映生成阶段的吞吐稳定性 |
| 端到端总耗时 | 从请求到完整响应结束 | 非流式场景、批量任务场景的核心指标 |
| 有效并发数 | 系统能同时稳定处理的请求数，而非瞬时峰值 | 决定容量规划，比单纯的"最大 QPS"更有意义 |
| 错误率分类 | 429（限流）/ 5xx（服务错误）/ 超时，分开统计 | 三种错误对应的应对策略完全不同，混在一起没法定位问题 |

**不要只报一个"平均响应时间"**。LLM 响应时间分布通常是长尾的，p50 和 p99 可能差好几倍，压测报告至少要给 p50 / p90 / p99 三档，否则掩盖了尾部延迟问题。

## 三、并发模型设计：模拟真实流量形态

压测的价值取决于并发模型是否贴近真实场景。常见的三种并发模型：

- **恒定并发**：固定 N 个虚拟用户持续发请求，测系统在稳定负载下的表现，适合评估日常基线容量
- **阶梯递增**：并发数每隔固定时间递增一档（比如每 2 分钟 +10 并发），用于找到系统开始出现明显性能劣化的拐点
- **突发脉冲**：短时间内并发数陡增后回落，模拟营销活动、定时任务并发触发等场景，重点看系统能否平滑消化突发流量而不是直接大面积超时

三种模型对应不同的测试目的，不要只跑一种就下结论。日常容量规划用恒定并发，找系统瓶颈用阶梯递增，评估突发抗压能力用突发脉冲。

## 四、用 Locust 搭建压测脚本

以下是一个针对流式 LLM 接口的 Locust 压测脚本示例，核心是**分别记录 TTFT 和总耗时**，而不是只测总耗时：

```python
import time
import json
from locust import HttpUser, task, between, events

class LLMUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def chat_stream(self):
        payload = {
            "model": "target-model",
            "messages": [{"role": "user", "content": "写一段 200 字的产品介绍"}],
            "stream": True,
        }
        start = time.monotonic()
        first_token_time = None

        with self.client.post(
            "/v1/chat/completions",
            json=payload,
            stream=True,
            catch_response=True,
        ) as response:
            try:
                for line in response.iter_lines():
                    if not line:
                        continue
                    if first_token_time is None:
                        first_token_time = time.monotonic()
                        ttft = (first_token_time - start) * 1000
                        events.request.fire(
                            request_type="TTFT",
                            name="chat_stream_first_token",
                            response_time=ttft,
                            response_length=0,
                            exception=None,
                        )
                total_time = (time.monotonic() - start) * 1000
                response.success()
            except Exception as e:
                response.failure(str(e))
```

这个脚本的关键点在于用 `events.request.fire` 手动上报了一个自定义的 `TTFT` 指标类型，让 Locust 的统计面板里 TTFT 和总耗时分开展示，避免两个不同含义的耗时被平均到一起。

## 五、压测前必须做的三件事

1. **和上游 API 服务商确认限流阈值**：压测目标并发不能超过账号的 RPM/TPM 上限，否则测出来的失败率是限流导致的，不代表自己系统的真实瓶颈。多账号轮询分发的方案见 [LLM API 限速处理完整指南](/blog/llm-rate-limit-handling/)
2. **固定输入输出长度做基线对比**：如果每次压测用的 prompt 长度和期望输出长度不一样，不同批次的压测结果没有可比性，至少要有一组"固定长度"的基线测试
3. **区分测试环境和生产环境的模型版本**：不同版本、不同区域部署的同一模型，延迟表现可能有明显差异，压测报告要标注清楚测的是哪个具体版本

## 六、压测中容易被忽略的两个陷阱

**陷阱一：本地压测客户端本身成为瓶颈**。如果并发数开得很高，压测脚本所在的机器 CPU、网络带宽、连接数可能先于被测系统达到瓶颈，导致压测结果失真。压测时要同步监控压测客户端自身的资源占用，确认瓶颈来自被测系统而不是压测工具本身。

**陷阱二：只测单轮对话，忽略多轮上下文场景**。很多 LLM 应用是多轮对话，上下文越长，输入 token 数越大，推理耗时和成本都会上升。只用单轮短 prompt 压测，容易低估生产环境里长上下文场景的真实负载，应该按实际业务的对话轮次分布构造测试用例。

## 七、压测结果怎么用于容量规划

压测跑完不是拿到几个数字就结束，核心产出应该是回答三个问题：

- 当前架构在 SLA 要求的延迟范围内，能支撑的最大稳定并发是多少
- 超过这个并发之后，系统是优雅降级（排队、限流提示）还是直接大面积报错
- 如果要支撑 N 倍于当前的流量，需要在哪个环节扩容（自建推理节点、上游 API 配额、还是中间层缓存）

把这三个问题的答案写进容量规划文档，压测才算真正产生了工程价值，而不只是一份"跑了个测试"的记录。

## 八、相关阅读

- [LLM API 限速（Rate Limit）处理完整指南](/blog/llm-rate-limit-handling/)
- [LLM 输出验证：schema + 业务规则双层防护](/blog/llm-output-validation/)
- [LLM Agent 评估方法论](/blog/llm-agent-evaluation-methods/)
- [Claude Message Batches 成本节省实践](/blog/claude-message-batches-savings/)

压测阶段需要在多个模型间快速切换对比延迟和成本？[YoTradeApi](https://yotradeapi.com) 一个 Key 接入全系模型，方便同一套压测脚本跑不同模型的对比数据。
