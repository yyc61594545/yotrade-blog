---
title: RAG 系统评测框架搭建实战
description: 讲解如何为 RAG 系统搭建一套完整评测框架，涵盖检索指标、生成质量指标、黄金测试集构建与 CI 集成方法。
keywords:
  - RAG 评测框架
  - RAG 系统评估指标
  - 检索质量评估
  - LLM as judge 评测
  - RAG 黄金测试集
pubDate: '2026-07-05'
updatedDate: '2026-07-05'
canonical: https://blog.yotradeapi.com/blog/ai-rag-evaluation-framework/
tags:
  - RAG
  - 应用工程
  - 评测框架
  - 工程实践
category: 应用工程
heroImage: ../../assets/blog-placeholder-5.jpg
---

一个基础的关键词匹配测试（参考下方相关阅读里的 RAG 最佳实践）能帮你发现"答案完全跑偏"这种明显问题，但没法回答更细粒度的问题：**是检索环节没找到对的片段，还是找到了但生成阶段没用好？** 要回答这个问题，需要一套把检索和生成拆开分别打分的评测框架。本文讲清楚这套框架具体怎么搭。

## 一、为什么要把检索和生成拆开评测

RAG 系统的问题通常出在两个环节之一，混在一起评估会导致你迭代错方向：

- **检索环节的锅**：向量库里根本没检索到包含答案的片段——这时候不管生成 prompt 写得多好都没用，得去调 chunk 策略、embedding 模型或加 rerank
- **生成环节的锅**：检索到的片段里明明有答案，但模型没用上、编造了内容，或者答非所问——这时候该调的是 prompt 和上下文拼装方式，跟检索无关

只有把两个环节的指标分开算，才能准确判断该往哪个方向优化。

## 二、检索质量指标

| 指标 | 含义 | 计算方式 |
|---|---|---|
| Context Recall | 相关片段有多少比例被召回 | 命中的相关片段数 / 全部相关片段数 |
| Context Precision | 召回的片段里有多少是真正相关的 | 相关片段数 / 召回片段总数 |
| MRR（平均倒数排名） | 第一个相关片段排在第几位 | 对每个查询取 1/首个命中位置，取平均 |
| Hit Rate@K | Top-K 结果里是否至少命中一个相关片段 | 命中查询数 / 总查询数 |

```python
def context_recall(retrieved_chunks, relevant_chunk_ids):
    retrieved_ids = {c["id"] for c in retrieved_chunks}
    hit = retrieved_ids & set(relevant_chunk_ids)
    return len(hit) / len(relevant_chunk_ids) if relevant_chunk_ids else 0

def mrr(retrieved_chunks, relevant_chunk_ids):
    for rank, chunk in enumerate(retrieved_chunks, start=1):
        if chunk["id"] in relevant_chunk_ids:
            return 1 / rank
    return 0
```

## 三、生成质量指标

检索没问题之后，还要评估模型基于检索结果生成的答案质量：

- **Faithfulness（忠实度）**：答案里的每个论断是否都能在检索到的片段里找到依据，衡量模型有没有"编造"内容
- **Answer Relevancy（答案相关性）**：答案是否切题回答了问题本身，而不是绕开问题说一堆检索片段里的相关信息
- **Answer Correctness（答案正确性）**：和标准答案对比，语义是否一致（不要求逐字匹配）

这三个指标很难用简单的字符串匹配算出来，业界通用做法是用**另一个 LLM 当裁判**（LLM-as-judge）：

```python
JUDGE_PROMPT = """
你是评测员。基于以下检索片段和生成的答案，判断答案中的每一句话是否都能在片段中找到依据。
检索片段：
{context}

生成答案：
{answer}

请输出 JSON：{{"faithfulness_score": 0-1 之间的小数, "unsupported_claims": ["无依据的论断列表"]}}
"""

def judge_faithfulness(llm_call, context, answer):
    result = llm_call(JUDGE_PROMPT.format(context=context, answer=answer))
    return json.loads(result)
```

**注意**：裁判模型最好选择和被测系统不同的模型，避免"自己评自己"引入偏差；裁判 prompt 里一定要要求给出理由（`unsupported_claims`），只输出一个分数无法排查问题出在哪句话。

## 四、黄金测试集怎么构建

评测框架的效果上限取决于测试集质量，构建时建议：

1. **从真实用户查询日志里抽样**，而不是自己拍脑袋编问题——真实查询往往有拼写错误、口语化表达、模糊指代，比工整的书面语更能暴露问题
2. **每条测试用例标注"标准答案"和"应该被检索到的片段 ID"**，这样才能同时算检索指标和生成指标
3. **覆盖边界情况**：库里没有答案时模型是否会诚实说"不知道"而不是编造；同一个问题换个问法是否还能拿到一致的答案；涉及多个文档综合信息的复杂问题
4. **测试集规模不需要很大**，50–200 条覆盖典型场景的用例，比几千条低质量自动生成的用例更有信号价值
5. **定期补充新用例**：每次线上发现一个 badcase，把它加进测试集，防止同样的问题回归

## 五、CI 集成：让回归自动被发现

把评测框架接入 CI，在每次调整 chunk 策略、换 embedding 模型或改 prompt 之后自动跑一遍：

```yaml
# .github/workflows/rag-eval.yml
name: RAG Evaluation
on: [pull_request]
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python scripts/run_rag_eval.py --golden-set eval/golden.jsonl --threshold 0.8
```

设定一个及格线（比如 Faithfulness 平均分不低于 0.8，Context Recall 不低于 0.75），低于阈值就让 CI 失败，防止不小心引入的改动悄悄拉低整体质量却没人发现。

## 六、把结果可视化，方便定位问题

单纯输出一个总分意义不大，建议按类别拆分展示：

| 问题类别 | Context Recall | Faithfulness | 样本数 |
|---|---|---|---|
| 单文档事实问答 | 0.92 | 0.95 | 40 |
| 跨文档综合问答 | 0.68 | 0.81 | 25 |
| 表格数据问答 | 0.55 | 0.77 | 15 |
| 模糊/口语化提问 | 0.74 | 0.88 | 20 |

这种分类视图能直接告诉你下一步该优化哪类场景——上表里"表格数据问答"明显是短板，对应的优化方向就是加专门的表格解析而不是调整通用 chunk 策略。

## 七、相关阅读

- [RAG 中文最佳实践指南](/blog/rag-cn-best-practices/)
- [LlamaIndex 中文 RAG 教程](/blog/llamaindex-cn-rag-tutorial/)
- [LLM 输出验证：如何保证结构化输出可靠](/blog/llm-output-validation/)
- [Claude vs Gemini 文档 RAG 对比](/blog/claude-vs-gemini-document-rag/)

搭建评测框架过程中经常需要用不同模型分别做生成和裁判，避免自评偏差，通过 [YoTradeApi](https://yotradeapi.com) 一个接口即可切换调用多家模型，方便快速搭建这类交叉评测流程。
