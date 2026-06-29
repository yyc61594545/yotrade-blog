---
title: AI 辅助数据库 schema 设计实战
description: 用 AI 辅助设计数据库 schema，从需求分析到建表 SQL 全流程实战，涵盖范式选择、索引规划与常见坑点规避。
keywords:
  - AI 辅助数据库设计
  - schema 设计实战
  - AI 生成 SQL
  - 数据库建表规范
  - LLM 数据库优化
pubDate: '2026-06-29'
updatedDate: '2026-06-29'
canonical: https://blog.yotradeapi.com/blog/ai-coding-database-schema-design/
tags:
  - AI编程
  - 数据库
  - schema设计
  - 实战经验
category: 实战经验
heroImage: ../../assets/blog-placeholder-3.jpg
---

数据库 schema 是系统的骨架——设计好了，后期迭代顺；设计坏了，每次需求变更都是一次"换骨手术"。AI 工具在这个领域的价值，不是让你偷懒，而是让你能在 30 分钟内把一周才能对齐的设计讨论压缩完。本文记录一套我在实际项目中跑通的 AI 辅助 schema 设计流程。

## 一、为什么数据库设计特别适合 AI 辅助

大多数开发者在数据库设计上犯的错，往往不是"不懂 SQL"，而是：

- 需求理解阶段遗漏了关键实体（后期强加字段）
- 过早优化或过晚优化索引（上线才发现慢查询）
- 对第三方表结构规范不熟悉（接手别人的库一脸懵）
- 团队之间命名规范不统一（有人用 `userId`，有人用 `user_id`）

AI 在这些场景的优势：**快速把需求语言翻译成结构化实体关系，输出可讨论的草稿**。它不是最终决策者，而是"第一个架构师"。

## 二、准备工作：给 AI 提供足够上下文

好的 schema 设计 prompt 要包含三类信息：

**1. 业务上下文**
```
这是一个多租户 SaaS 系统，面向中小企业管理内部请假审批流程。
核心角色：员工、主管、HR、系统管理员（跨企业）。
企业间数据完全隔离。
```

**2. 关键业务规则**
```
- 一个员工可以属于多个部门（兼职）
- 请假类型由企业自定义，不同类型有不同扣款规则
- 审批流程最多 5 级，每级支持多人会签
- 历史记录必须保留 3 年，不允许物理删除
```

**3. 非功能性约束**
```
- 数据库：PostgreSQL 15
- 单企业员工数量预估 < 10000
- 需要支持按月汇总的报表查询
- 优先一致性，可以牺牲一定写入性能
```

把这三类信息整理好，一次性交给 AI，得到的草稿质量会比"帮我设计一个请假系统"高出一个数量级。

## 三、第一轮：实体识别与 ER 草图

**Prompt 模板**：

```
基于上面的业务描述，请识别出所有核心实体（Entity）和它们之间的关系（Relationship）。
输出格式：
1. 实体列表，每个实体注明：名称、主要属性、与其他实体的关系类型（1:1, 1:N, N:M）
2. 用文字描述 ER 图（不用真的画图）
3. 指出最复杂的 3 个关系，并说明你的初步处理思路

不要输出建表 SQL，只做实体分析。
```

**为什么先做实体分析而不直接要 SQL**：直接要 SQL，AI 会基于它最常见的模式输出，大概率遗漏你业务里的特殊规则。先做实体分析，强迫 AI（和你自己）把业务模型梳理清楚。

## 四、第二轮：逐表细化

实体确认后，按模块逐个细化，避免一次性处理太多导致 AI "失忆"。

```
现在我们来设计"请假申请"相关的表。
已确认的上下文：
- 企业 ID 字段叫 org_id（所有业务表都有）
- 主键统一用 UUID
- 时间字段统一用 timestamptz

请为以下实体输出建表 SQL（PostgreSQL 语法）：
1. leave_type（请假类型）
2. leave_application（请假申请主表）
3. leave_application_log（申请操作日志）

每张表需要：
- 完整字段定义（含注释）
- 主键和外键约束
- 你认为必要的普通索引（列出原因）
- 建表顺序（考虑外键依赖）
```

**分模块的好处**：每次对话只聚焦 3-5 张有关联的表，可以把更多 context token 用在业务规则细节上，而不是浪费在其他无关的表。

## 五、典型输出示例与审查点

AI 输出的建表 SQL 示例（节选）：

```sql
-- 请假类型
CREATE TABLE leave_type (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID        NOT NULL REFERENCES organizations(id),
    name        VARCHAR(64) NOT NULL,
    code        VARCHAR(32) NOT NULL,  -- 系统内部代码
    deduct_rule JSONB       NOT NULL DEFAULT '{}', -- 扣款规则（灵活存储）
    is_active   BOOLEAN     NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ,           -- 软删除
    UNIQUE (org_id, code)
);

-- 请假申请主表
CREATE TABLE leave_application (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID        NOT NULL REFERENCES organizations(id),
    applicant_id    UUID        NOT NULL REFERENCES employees(id),
    leave_type_id   UUID        NOT NULL REFERENCES leave_type(id),
    start_date      DATE        NOT NULL,
    end_date        DATE        NOT NULL,
    actual_days     NUMERIC(5,1) NOT NULL, -- 实际扣除天数（非自然天）
    reason          TEXT,
    status          VARCHAR(32)  NOT NULL DEFAULT 'draft',
    -- draft / pending / approved / rejected / cancelled
    current_step    SMALLINT    NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_date CHECK (end_date >= start_date)
);

CREATE INDEX idx_leave_app_org_applicant ON leave_application (org_id, applicant_id);
CREATE INDEX idx_leave_app_org_status    ON leave_application (org_id, status);
CREATE INDEX idx_leave_app_start_date    ON leave_application (start_date);
```

**必须人工审查的点**：

| 检查项 | 说明 |
|--------|------|
| JSONB 字段用法 | AI 喜欢用 JSONB 解决"灵活性"问题，但 JSONB 列无法走普通索引，若需要按规则字段查询，必须改为单独字段 |
| status 枚举 | VARCHAR + CHECK 约束 vs PostgreSQL ENUM 类型，前者更灵活但约束弱 |
| 索引是否过多 | AI 倾向于为每个"可能查询"都加索引，实际上写多读少的场景会拖累性能 |
| 缺少的索引 | 报表类查询（按月汇总）需要复合索引，AI 经常漏掉 |
| 租户隔离 | 每个 WHERE 是否都带 org_id 过滤，RLS（Row Level Security）是否需要配置 |

## 六、第三轮：索引规划专项对话

索引是 schema 设计里最容易被敷衍的环节。单独开一轮对话来处理：

```
基于以下查询模式，帮我规划 leave_application 表的索引策略：

高频查询（每日百万次级别）：
Q1: 按 org_id + applicant_id 查询员工的申请列表（支持 status 过滤）
Q2: 按 org_id + status + current_step 查询待审批列表（主管视角）

中频查询（每日万次级别）：
Q3: 按 org_id + start_date 范围查询（月报统计）
Q4: 按 id 查询单条记录

低频查询（每日百次级别）：
Q5: 跨 org 的全局统计（管理员用）

当前表预计单 org 最大行数：50 万行，全局 1000 个 org

请输出：
1. 推荐的索引列表（含创建语句）
2. 每个索引对应覆盖哪些查询
3. 你不建议加的索引（及原因）
```

把查询模式量化（频率、数据量）给到 AI，它的索引建议会实用得多。

## 七、常见坑与 AI 的局限

**坑 1：AI 不知道你的数据量**

AI 给出的索引建议，默认是"通用最佳实践"，不了解你的数据分布。比如 status 字段的索引——如果 90% 的数据都是 `approved`，这个索引的选择性极低，几乎没用。要把数据分布特征明确告诉 AI。

**坑 2：命名规范被忽视**

每次 prompt 都要在开头重申命名约定（蛇形命名、表名复数/单数、主键命名等），否则 AI 会在不同表之间混用。把命名规范写成固定 system prompt 的一部分，可以节省大量校正时间。

**坑 3：AI 生成的 SQL 语法未必适配你的版本**

PostgreSQL 15 和 13 在某些函数上有差异。输出后一定要用目标版本实际执行验证，不能只看"看起来对"。

**坑 4：外键约束的性能代价**

AI 默认会加外键约束，但高并发写入场景下，外键的检查开销不可忽视。需要明确告知："这张表是高并发写入表，不加外键约束，在应用层保证引用完整性。"

## 八、迁移脚本的 AI 辅助

Schema 设计完成后，通常还需要写迁移脚本（migration）。给 AI 的 prompt：

```
现在 production 数据库里已有以下表结构（附上 DDL）。
新需求需要做如下变更：
1. leave_application 表新增 priority 字段（SMALLINT，默认 0，不为空）
2. leave_type 表的 code 字段长度从 32 改为 64
3. 新增 leave_quota 表（附上 ERD）

请输出 PostgreSQL 的 migration SQL，要求：
- 每个变更独立事务
- 考虑大表的在线 DDL（使用 NOT VALID 延迟约束检查）
- 包含回滚脚本
```

在线 DDL、回滚脚本这类"防御性"需求，要明确在 prompt 里提，否则 AI 只会给你最简单的 ALTER TABLE。

## 九、把 AI 输出纳入 Review 流程

最后一步：把 AI 生成的 schema 草稿纳入正式 code review。

推荐做法：
1. 在 PR 描述里注明"初稿由 AI 生成，已人工 review 以下要点：..."
2. 设置 review checklist（索引合理性、命名一致性、租户隔离、软删除一致性）
3. 关键表的 explain analyze 结果附在 PR 里（用测试数据跑）

AI 辅助数据库设计的价值在于**把 schema 草稿的质量上限拉高**，减少"想了两小时才发现遗漏了一张关联表"的情况——但最终的决策还是要靠你对业务和系统的深入理解。

## 十、相关阅读

- [AI 辅助后端开发实战经验](/blog/ai-coding-for-backend-dev/)
- [AI 编程避坑指南：那些真实踩过的雷](/blog/ai-coding-mistakes-to-avoid/)
- [AI 辅助构建内部工具的完整流程](/blog/ai-coding-build-internal-tool/)
- [AI 编程成本到底多少钱？真实数据披露](/blog/ai-coding-monthly-cost-real/)

想用更稳定、更低成本的 Claude / GPT-4 辅助数据库设计？[YoTradeApi](https://yotradeapi.com) 提供多模型统一接入，按量计费，无需翻墙。
