---
title: Query Rewrite 对 RAG 召回的影响：怎么量化它到底有没有用
description: 多数 RAG 系统加了 Query Rewrite 却说不清收益。本文给出可落地的评测设计：拆分四类改写策略、构造对照集、用召回率与成本一起判断是否值得保留这一步。
keywords:
  - Query Rewrite
  - RAG 召回评测
  - 查询改写效果
  - RAG 检索优化
  - 多查询改写
  - HyDE 效果评估
pubDate: '2026-09-17'
updatedDate: '2026-09-17'
canonical: https://blog.yotradeapi.com/blog/rag-query-rewrite-eval/
tags:
  - RAG
  - 检索
  - 评测
  - 应用工程
category: 应用工程
---

几乎每个做过 RAG 的团队都在检索前面加过一步 Query Rewrite：让模型把用户的原始问题改写得"更适合检索"。加完之后主观感觉变好了，于是留下。但如果问一句"它带来了多少召回提升、代价是多少延迟和 token"，多数团队答不上来。

这一步的成本并不低——它在关键路径上多了一次模型调用，延迟增加几百毫秒到一秒，还引入了一个新的失败点。值不值得保留，应该用数据说话。本文给一套能在两天内跑完的评测方法。

## 一、先把"Query Rewrite"拆成四种不同的东西

"改写"这个词覆盖了目的完全不同的四类操作，混在一起评测必然得不出结论：

| 策略 | 做什么 | 主要解决 | 典型代价 |
|---|---|---|---|
| 指代消解 | 把"它""这个方案"替换成上文实体 | 多轮对话中检索失焦 | 低（短输出） |
| 关键词扩展 | 补同义词、术语英文名、缩写全称 | 词汇不匹配（vocabulary mismatch） | 低 |
| 多查询分解 | 一个复合问题拆成 2–4 个子查询 | 单次检索覆盖不全 | 高（N 倍检索） |
| 假设文档（HyDE） | 先让模型生成一段"假答案"再用它检索 | 问题与文档表述风格差异大 | 中（长输出） |

这四类的适用条件差别很大。指代消解在单轮问答里完全没用；HyDE 在文档就是 FAQ 形式（问题-答案对）时反而会拉低效果，因为原始问题本来就和文档表述同构。

**第一条可操作结论**：不要实现"一个 rewrite 步骤"，要实现四个可独立开关的步骤，然后分别评测。多数团队最后会发现只有其中一两个在自己的数据上有用。

## 二、构造对照集：150 条就够，但要分层

评测集不需要很大，但必须覆盖失败模式。推荐的构造方式：

1. **从真实日志里抽 100 条**。优先抽检索命中率低的（可以用"用户追问了""对话轮次异常长"作为弱信号）。
2. **人工补 50 条**，按上面四类策略各自的目标场景造：15 条多轮指代、15 条术语不匹配、10 条复合问题、10 条问答风格差异大的。
3. **为每条标注 golden chunk**：哪些 chunk 包含回答该问题所需的信息。允许多个。

标注 golden chunk 是最花时间的部分，但它是整个评测的地基。如果没有它，你只能评"最终答案好不好"，而那会把检索问题和生成问题混在一起——这正是大多数 RAG 调优陷入玄学的原因。这套黄金集的通用构造方法我们在 [LLM 评测黄金集怎么建](/blog/llm-eval-golden-set/) 里写得更细。

## 三、只看三个指标

评测检索环节，指标越少越好用：

- **Recall@k**：golden chunk 有多少比例出现在 top-k 里。这是主指标，k 取你实际喂给模型的数量。
- **MRR**（平均倒数排名）：第一个 golden chunk 排在第几位的倒数平均。它捕捉"召回到了但排得太后"的情况。
- **端到端 P95 延迟 + 每查询 token 成本**：改写的代价。

不要在检索评测里看答案正确率——那是下一环节的事。把两件事分开，才知道该优化谁。

```python
def evaluate(queries, retriever, k=8):
    """queries: [{"q": str, "history": list, "golden": set[str]}]"""
    recalls, rrs = [], []
    for item in queries:
        hits = [c.id for c in retriever(item["q"], item["history"], k=k)]
        golden = item["golden"]
        recalls.append(len(golden & set(hits)) / len(golden))
        rank = next((i + 1 for i, h in enumerate(hits) if h in golden), None)
        rrs.append(1 / rank if rank else 0.0)
    return {
        "recall@k": sum(recalls) / len(recalls),
        "mrr": sum(rrs) / len(rrs),
    }

# 对照运行：baseline 与每种改写策略单独开启，跑同一批 queries
for name, r in [
    ("baseline", plain_retriever),
    ("+coref", coref_retriever),
    ("+expand", expand_retriever),
    ("+multi", multiquery_retriever),
    ("+hyde", hyde_retriever),
]:
    print(name, evaluate(EVALSET, r))
```

关键是**每种策略单独开**，而不是堆在一起对比 baseline。堆在一起只能告诉你"这堆东西加起来有用"，无法剔除其中拖后腿的那个。

## 四、真实数据里常见的四个反直觉结果

跑过几个项目下来，以下模式出现得相当频繁（数值为不同项目的大致区间，仅作参考）：

**1. 指代消解的收益集中在多轮，但幅度很大。** 单轮场景 Recall 几乎不变，多轮场景常见 15–30 个百分点的提升。如果你的产品是多轮对话形态，这一步几乎一定该留——而且它可以用小模型做，成本极低。

**2. 关键词扩展容易帮倒忙。** 模型倾向于扩展出语义相关但主题偏移的词，稀释了查询向量。在术语密集的技术文档上通常有效，在通用内容上常见小幅下降。判断依据：你的用户是否会用和文档不同的词汇体系描述同一件事。

**3. 多查询分解提升 Recall，但同时提升噪声。** Recall@k 上去了，但如果不加 reranker，塞给模型的上下文质量反而更差。它几乎必须和重排一起用，选型可参考 [RAG Reranker 怎么选](/blog/rag-reranker-selection/)。

**4. HyDE 的效果高度依赖文档形态。** 在长篇叙述性文档（手册、论文、法规）上收益明显；在 FAQ、工单、短条目上经常是负收益。上线前一定要在自己的语料上验，别看论文结论。

## 五、成本侧：把延迟算进决策

假设主检索链路原本 P95 是 400ms，加一次改写调用后变成 1100ms。这 700ms 值不值，取决于产品形态：

| 场景 | 延迟敏感度 | 建议 |
|---|---|---|
| 流式对话问答 | 高 | 用小模型做改写，或改写与首次检索并行 |
| 后台批量处理 | 低 | 放心用多查询 + HyDE |
| IDE 内联补全类 | 极高 | 别做改写，改为离线扩充索引 |

有一个经常被忽略的优化：**把改写的成本前移到索引侧**。与其在查询时扩展关键词，不如在索引时为每个 chunk 额外生成几个"这段内容能回答的问题"，一起入库。查询时零额外延迟，效果往往接近 HyDE。代价是索引构建成本和存储增加，但那是一次性的。这个思路和 [RAG 分块策略评测](/blog/rag-chunking-evaluation/) 里的预处理取舍是同一类。

另一个实务细节：改写调用应该走**短超时 + 失败回退原查询**。改写服务抖动不应该让整个问答挂掉。

```python
def rewrite_with_fallback(q, history, timeout=1.5):
    try:
        return call_model(build_rewrite_prompt(q, history), timeout=timeout)
    except (TimeoutError, APIError):
        return q          # 降级：用原查询，宁可召回差一点也不能失败
```

## 六、什么时候应该删掉这一步

评测跑完后，符合以下任一条就该删：

- Recall@k 提升 **小于 3 个百分点**，而 P95 延迟增加超过 300ms
- 提升集中在评测集里人工构造的那 50 条，真实日志抽样的 100 条没有改善（说明你在优化一个不存在的问题）
- 加了 reranker 之后提升被吃掉大半（两者解决的是同一个问题，保留成本更低的那个）

删掉一个看起来"业界都在用"的步骤需要一点决心，但 RAG 链路上每多一环，调试成本就上一个台阶。链路诊断顺序可以参考 [RAG 质量问题的排查路径](/blog/rag-quality-debugging-path/)。

## 七、一个最小落地清单

如果你现在就要开始，按这个顺序做：

1. 标 150 条评测集，含 golden chunk（最耗时，但必须先做）
2. 把现有 rewrite 拆成可独立开关的模块
3. 跑五组对照：baseline + 四种策略各自单开
4. 只保留 Recall 提升 ≥ 3pt 且延迟可接受的策略
5. 保留下来的策略加超时回退，并把评测脚本接进 CI，防止后续 prompt 改动悄悄劣化

第 5 步最容易被跳过，也最容易吃亏：改写 prompt 是所有人都会顺手改的地方，没有回归门禁的话，三个月后没人说得清当前版本比最初好还是差。

## 八、相关阅读

- [RAG 分块策略评测](/blog/rag-chunking-evaluation/)
- [RAG Reranker 选型](/blog/rag-reranker-selection/)
- [RAG 质量问题排查路径](/blog/rag-quality-debugging-path/)
- [LLM 评测黄金集建设](/blog/llm-eval-golden-set/)
- [混合检索调参实践](/blog/rag-hybrid-search-tuning/)
