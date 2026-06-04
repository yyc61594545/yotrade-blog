---
title: 用 AI 做数据库迁移实战：踩坑记录与可复用模式
description: 记录用 Claude / GPT-4o 辅助完成三次真实数据库迁移的经验——DDL 生成、数据清洗、灰度切流的具体做法。
keywords:
  - AI 数据库迁移
  - LLM 辅助 SQL 迁移
  - PostgreSQL 迁移实战
  - AI 写 DDL
  - 数据库重构 AI
pubDate: '2026-06-04'
updatedDate: '2026-06-04'
canonical: https://blog.yotradeapi.com/blog/ai-helping-with-database-migration/
tags:
  - 数据库迁移
  - AI 实战
  - 后端开发
  - SQL
category: 实战经验
heroImage: ../../assets/blog-placeholder-3.jpg
---

数据库迁移是让后端工程师最谨慎的操作之一——一个字段类型改错，几十万行数据可能需要人工修复。过去一年，有越来越多的团队开始用 AI 辅助这个流程。本文记录三次真实迁移场景的经验：PostgreSQL 大表加字段、MySQL 到 PostgreSQL 跨库迁移、以及遗留系统的 Schema 反规范化拆分。

---

## 一、AI 在数据库迁移中能做什么、不能做什么

先划清边界，避免期望管理失败。

| 任务 | AI 胜任度 | 说明 |
|------|----------|------|
| 生成 DDL 语句 | ★★★★★ | 标准任务，Claude 几乎不出错 |
| 写数据清洗 SQL | ★★★★☆ | 需要提供样本数据和约束 |
| 设计迁移策略（蓝绿/影子表） | ★★★★☆ | 需结合业务并发量决策 |
| 检查 DDL 的锁影响 | ★★★☆☆ | 依赖版本信息，需人工验证 |
| 执行迁移、监控 | ★☆☆☆☆ | 只能给建议，操作要人来做 |
| 判断业务数据是否正确 | ★☆☆☆☆ | 不了解业务语义，必须人工 |

核心原则：**AI 负责生成和审核代码，人工负责决策和执行**。

---

## 二、场景一：PostgreSQL 大表加字段（1.2 亿行）

### 背景

`orders` 表有 1.2 亿行，需要加一个 `payment_channel` 字段，默认值 `'unknown'`。

### 踩坑：直接 ALTER TABLE 导致全表锁

直接执行 `ALTER TABLE orders ADD COLUMN payment_channel VARCHAR(50) DEFAULT 'unknown'` 在 PostgreSQL 12+ 会加 ACCESS EXCLUSIVE 锁，期间所有读写阻塞。

把场景描述给 Claude，它给出了更安全的方案：

```sql
-- 步骤 1：加字段，不设默认值（瞬时操作）
ALTER TABLE orders ADD COLUMN payment_channel VARCHAR(50);

-- 步骤 2：分批 UPDATE（避免长事务）
DO $$
DECLARE
  batch_size INT := 10000;
  offset_val INT := 0;
  rows_updated INT;
BEGIN
  LOOP
    UPDATE orders
    SET payment_channel = 'unknown'
    WHERE id IN (
      SELECT id FROM orders
      WHERE payment_channel IS NULL
      ORDER BY id
      LIMIT batch_size
    );
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    EXIT WHEN rows_updated = 0;
    PERFORM pg_sleep(0.05);  -- 给 replica 追上的时间
  END LOOP;
END $$;

-- 步骤 3：加 NOT NULL 约束（PostgreSQL 11+ 支持不重写表）
ALTER TABLE orders
  ALTER COLUMN payment_channel SET DEFAULT 'unknown',
  ALTER COLUMN payment_channel SET NOT NULL;
```

**AI 的贡献**：它主动提示了 PostgreSQL 版本差异——PostgreSQL 11 之前加 `NOT NULL` + `DEFAULT` 会触发全表重写，而 11+ 不会。这个细节在文档里分散在多处，人工查容易漏。

### 迁移脚本的 Prompt 技巧

给 AI 的 prompt 要包含：

```
表结构：（粘贴 \d orders 输出）
数据量：1.2 亿行，日均写入 50 万
PostgreSQL 版本：14.2
要求：
1. 避免全表锁，允许在线迁移
2. 每批操作不超过 10000 行
3. 提供回滚方案
4. 列出每个步骤的锁类型
```

---

## 三、场景二：MySQL 到 PostgreSQL 跨库迁移

### 背景

一个运行了 6 年的 MySQL 5.7 系统，迁移到 PostgreSQL 15。表数量 82 张，部分表有触发器和存储过程。

### 用 AI 做 Schema 转换

把 MySQL 的 `SHOW CREATE TABLE` 输出批量给 Claude，让它转为 PostgreSQL DDL。主要差异点：

| MySQL 语法 | PostgreSQL 等价语法 |
|-----------|-------------------|
| `AUTO_INCREMENT` | `SERIAL` 或 `GENERATED ALWAYS AS IDENTITY` |
| `TINYINT(1)` | `BOOLEAN` |
| `DATETIME` | `TIMESTAMP WITH TIME ZONE` |
| `ENUM('a','b')` | 自定义类型或 `VARCHAR` + CHECK 约束 |
| `ON UPDATE CURRENT_TIMESTAMP` | 触发器实现 |

Claude 在处理 `ENUM` 时给出了两种方案并解释了各自的 trade-off：

- **方案 A**：转为 PostgreSQL ENUM 类型——类型安全，但加值需要 DDL（`ALTER TYPE`）
- **方案 B**：转为 `VARCHAR(50)` + CHECK 约束——灵活，允许在线加值

对于数据变化频繁的枚举（如状态码），我们采用了方案 B。这个决策建议直接让 AI 展示 trade-off，而不是让它"选一个最好的"——最好的取决于你的业务。

### 存储过程迁移

MySQL 存储过程的 PL/SQL 语法和 PostgreSQL 的 PL/pgSQL 差异较大。AI 的转换成功率大约 80%，剩下 20% 是游标操作和动态 SQL，需要人工修正。

经验：**不要一次性提交整个存储过程文件**。按函数拆分，每次提交一个，附带测试用例，转换质量明显更高。

### 数据清洗 SQL

MySQL 对 `'0000-00-00'` 日期的处理在 PostgreSQL 里会直接报错。让 AI 生成清洗脚本：

```sql
-- 在 MySQL 导出前，先清洗无效日期
UPDATE legacy_orders
SET created_at = '1970-01-01 00:00:00'
WHERE created_at = '0000-00-00 00:00:00';

-- 同时检查其他非法值
SELECT id, created_at
FROM legacy_orders
WHERE created_at < '1970-01-01'
   OR created_at > NOW() + INTERVAL 1 DAY;
```

---

## 四、场景三：遗留 Schema 反规范化拆分

### 背景

一张宽表 `user_profile` 有 78 个字段，业务发展导致其中 30 个字段只有特定用户类型才会用到。需要拆分为 `user_core` + `user_merchant_ext` + `user_consumer_ext`。

### AI 辅助的迁移步骤

**1. 让 AI 分析字段使用率**

把 `user_profile` 的 DDL 和各字段的业务说明给 Claude，让它按用户类型归类字段，并标出"边界不清晰"的字段供人工决策。

**2. 影子表策略**

拆分期间需要新旧两套表并存，AI 帮助生成了同步触发器：

```sql
-- 往新表同步的触发器（旧表 → 新表）
CREATE OR REPLACE FUNCTION sync_to_new_tables()
RETURNS TRIGGER AS $$
BEGIN
  -- 同步核心字段
  INSERT INTO user_core (user_id, username, email, created_at)
  VALUES (NEW.user_id, NEW.username, NEW.email, NEW.created_at)
  ON CONFLICT (user_id) DO UPDATE
    SET username = EXCLUDED.username,
        email = EXCLUDED.email;

  -- 按用户类型同步扩展字段
  IF NEW.user_type = 'merchant' THEN
    INSERT INTO user_merchant_ext (user_id, shop_name, business_license)
    VALUES (NEW.user_id, NEW.shop_name, NEW.business_license)
    ON CONFLICT (user_id) DO UPDATE
      SET shop_name = EXCLUDED.shop_name,
          business_license = EXCLUDED.business_license;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_user_profile
AFTER INSERT OR UPDATE ON user_profile
FOR EACH ROW EXECUTE FUNCTION sync_to_new_tables();
```

**3. 灰度切流**

用功能开关控制读取路径：1% 流量读新表 → 观察一周 → 逐步放量 → 100% 切新表 → 下线旧表。AI 帮助生成了每个阶段的验证 SQL（字段值一致性校验），这部分脚本工作量大、重复性高，正是 AI 最能节省时间的地方。

---

## 五、Prompt 工程：让 AI 生成高质量迁移脚本

### 必须提供的上下文

```
1. 数据库版本（MySQL 8.0 / PostgreSQL 14 等）
2. 目标表的 DDL（SHOW CREATE TABLE 输出）
3. 数据量和写入频率（影响锁策略选择）
4. 业务约束（允许停机时间、事务一致性要求）
5. 已知的数据质量问题（如存在 NULL 的非 NULL 字段）
```

### 要求 AI 输出的内容

```
1. 每个步骤的 SQL 语句
2. 每个步骤持有的锁类型（ACCESS EXCLUSIVE / SHARE 等）
3. 预计执行时间（数量级）
4. 回滚方案
5. 验证脚本（迁移后如何确认数据正确性）
```

---

## 六、不要让 AI 做的事

- **不要让 AI 直接连数据库执行**：生成脚本后，必须人工审查再执行
- **不要跳过测试环境**：用生产数据量的 10% 在测试环境先跑一遍
- **不要信任 AI 的时间估算**：I/O 性能差异巨大，要实测
- **不要让 AI 生成包含具体连接信息的脚本**：敏感信息不应出现在 prompt 里

---

## 七、相关阅读

- [AI 辅助后端开发实战](/blog/ai-coding-for-backend-dev/)
- [AI 重构遗留单体应用](/blog/ai-refactor-legacy-monolith/)
- [AI 重构设计模式总结](/blog/ai-refactoring-patterns/)
- [Python 遗留项目用 Aider 重构实录](/blog/legacy-python-refactor-with-aider/)

稳定调用 Claude 或 GPT-4o 来处理 SQL 生成和迁移脚本，[YoTradeApi](https://yotradeapi.com) 提供高可用 API 中转，无需海外信用卡，按量计费。
