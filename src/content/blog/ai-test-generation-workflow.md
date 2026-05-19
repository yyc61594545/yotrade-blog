---
title: 用 AI 批量生成单元测试的工程化方法
description: 用 Claude / GPT 高质量批量生成单元测试的实战方法：prompt 设计、覆盖率优化、mutation testing 验证、CI 集成。
keywords:
- ai 写测试
- ai 生成 单元测试
- claude 写测试
- ai test generation
- mutation testing
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/ai-test-generation-workflow/
tags:
- 测试
- AI 自动化
- 工程实战
- 覆盖率
- Quality
category: 工程实战
heroImage: ../../assets/blog-placeholder-5.jpg
---

# 用 AI 批量生成单元测试的工程化方法

测试是后端 / 前端项目最容易"债"的地方。AI 写测试一年来效果显著提升，能在一天内把项目从 30% 覆盖率拉到 80%。本文给完整工程化方法。

## 一、AI 写测试的优势与陷阱

### 优势

- 速度快（人手工 5 分钟一个，AI 30 秒）
- 不疲劳（写 50 个测试不烦）
- 覆盖边界全（容易记得各种 edge case）
- 风格统一（按 rules）

### 陷阱

- 写出"看起来对实际无效"的测试（**最大坑**）
- 同质化（测试假设 = 代码假设，没真验证）
- 不挑战业务逻辑
- 测试通过但不发现 bug

## 二、最简模板

```
你是测试工程师。给以下函数写完整单元测试。

# 函数
```typescript
[贴代码]
```

# 要求
- 用 vitest
- 覆盖：正常路径 / 边界值 / 异常输入
- 每个 case 一个 it()，描述具体
- 不 mock 内部依赖（如有）：[列出真实可用的 mock]
- 测试名清晰，"should xxx when yyy"
- 不要测私有函数

# 输出
仅 *.test.ts 文件内容，不要解释。
```

直接产出能跑的测试。

## 三、覆盖率驱动

跑 `pnpm test --coverage` 后，让 AI **针对未覆盖行写**：

```
> 当前覆盖率报告：
> src/utils.ts 60% (uncovered: 30-40, 55-60)
> 
> 我贴 src/utils.ts 内容：[贴]
> 
> 为未覆盖的行 30-40 和 55-60 写测试。
> 已有的测试在 src/utils.test.ts：[贴现有测试]
> 不要重复已有测试，只补缺的。
```

精确补缺，**比"全写一遍"省 70% token**。

## 四、Mutation Testing 验证

最容易被忽略的：**测试通过 ≠ 测试有效**。

Mutation testing 改一个字符（== → !=、+ → -），看测试是否还通过。**通过 = 测试没真测**。

```bash
# Node
npm install -D stryker-mutator
npx stryker run

# Python
pip install mutmut
mutmut run
```

跑 mutation 看 "mutation score"：

| Score | 含义 |
| --- | --- |
| > 80% | 测试质量高 |
| 60–80% | 中等 |
| < 60% | 测试薄弱 |

AI 写完跑一次，**低分的让 AI 重写**：

```
> 以下测试 mutation score 只有 50%：
> [贴 test + 函数]
> 这些 mutation 没被检测到：
> - line 12: + → -
> - line 15: == → !=
> 修改测试让这些 mutation 被检测到。
```

## 五、写完跑一遍

AI 给的测试 **强制跑一遍验证**：

```bash
# Aider 配置
auto-test: true
test-cmd: pnpm test --run
```

通过的留下，失败的 AI 自己修。

## 六、Mock 策略

```
# Mock 规则
- 数据库：用 src/test/db.ts 的 testDb
- HTTP：用 msw（src/test/mocks/handlers.ts 已有定义）
- 时间：用 vi.useFakeTimers()
- ID 生成：用 vi.spyOn(crypto, 'randomUUID')
- 文件：用 memfs

# 不 mock 的
- 纯函数（直接调）
- 项目工具（src/lib/*）
- 类型
```

写清楚团队约定，AI 不会乱 mock。

## 七、参数化测试

减少重复：

```typescript
it.each([
  [0, 0, 0],
  [1, 2, 3],
  [-1, 1, 0],
  [Number.MAX_SAFE_INTEGER, 1, Number.MAX_SAFE_INTEGER + 1],
])("add(%d, %d) → %d", (a, b, expected) => {
  expect(add(a, b)).toBe(expected);
});
```

让 AI 自动用 `it.each`，**比一个个 `it()` 简洁**。

## 八、Snapshot 测试

```typescript
it("renders correctly", () => {
  expect(render(<Button />).toJSON()).toMatchSnapshot();
});
```

简单但**容易"测了寂寞"**——snapshot 一改就全过，没真验证。

**纪律**：

- 只对**稳定输出**用 snapshot
- 不在 PR 里随手 update snapshot
- review 时 snapshot diff 当 source code 看

## 九、Property-based Testing

```typescript
import fc from "fast-check";

it("sort is idempotent", () => {
  fc.assert(
    fc.property(fc.array(fc.integer()), (arr) => {
      expect(sort(sort(arr))).toEqual(sort(arr));
    })
  );
});
```

让 AI 写 property-based 测试——**通用 invariant** 比手写 100 个 case 强。

## 十、E2E 测试

让 AI 写 Playwright：

```
> 写 Playwright e2e 测试用户注册：
> 1. visit /signup
> 2. 填 form: email, password
> 3. 点 Submit
> 4. expect redirect /onboarding
> 5. expect 页面显示用户邮箱
>
> 用 page.getByRole / getByLabel 优先，不要 selector。
> 跑前确保 dev server 已起。
```

详见 [前端开发者用 AI 编程的实战工作流](/blog/ai-coding-for-frontend-dev/)。

## 十一、API 测试

```typescript
import { test, expect } from "vitest";
import { app } from "@/app";
import { testDb } from "@/test/db";

test("POST /api/users creates user", async () => {
  await testDb.reset();
  const res = await fetch(`${app.url}/api/users`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: "alice@test.com" }),
  });
  expect(res.status).toBe(201);
  const json = await res.json();
  expect(json.ok).toBe(true);
});
```

AI 按 OpenAPI spec 一次性写全套。

## 十二、批量改造

把项目从 0 拉到 80% 覆盖率：

```bash
# 1. 拉清单
pnpm test --coverage --reporter=json > coverage.json

# 2. 逐文件让 AI 写
for file in $(jq -r '.coverageMap | keys[]' coverage.json | head -20); do
    claude --headless --task "为 $file 补充单元测试到 80%+ 覆盖" 
done

# 3. 跑测试看通过
pnpm test --coverage
```

一晚上跑完。第二天 review。

## 十三、避坑

- ❌ 测试通过就 commit 不 review
- ❌ Mutation score 不跑（测试可能无效）
- ❌ 全用 snapshot
- ❌ Mock 一切（测试和真实代码脱钩）
- ❌ 让 AI 改业务代码"让测试过"

## 十四、相关阅读

- [AI 代码评审实战](/blog/ai-code-review-workflow/)
- [Claude Code CI/CD 接入](/blog/claude-code-ci-integration/)
- [AI Agent Prompt Engineering 中文实战](/blog/agent-prompt-engineering-cn/)
- [AI 编程的 12 个常见错误与避坑指南](/blog/ai-coding-mistakes-to-avoid/)
- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)

批量测试生成走 [YoTradeApi](https://yotradeapi.com/register) 中转，按上面流程一晚拉到 80% 覆盖。
