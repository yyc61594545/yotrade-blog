---
title: 用 Aider 做 TDD 重构的实战：测试先行让 AI 重构更可靠
description: 完整演示如何将 Aider 与 TDD 工作流结合，让 AI 在"先写测试、后写实现"的约束下安全重构代码，附 Python pytest 实战案例与配置技巧。
keywords:
  - Aider TDD 重构
  - AI 测试驱动开发
  - Aider pytest 实战
  - AI 代码重构可靠性
  - Aider 工作流实战
pubDate: '2026-06-22'
updatedDate: '2026-06-22'
canonical: https://blog.yotradeapi.com/blog/aider-test-driven-refactor/
tags:
  - Aider
  - TDD
  - 重构
  - Python
category: 实战经验
heroImage: ../../assets/blog-placeholder-5.jpg
---

AI 辅助重构最大的风险不是代码写错，而是改了行为不知道。单靠肉眼 review LLM 的输出，漏掉语义 bug 的概率远超手工重构。引入 TDD（测试驱动开发）可以从根本上解决这个问题：先让 AI 生成测试，锁定当前行为；再让 AI 重构实现，只要测试通过，行为就没变。

本文记录将 Aider 与 TDD 工作流结合的完整实战，所用案例是一个真实的电商订单计算模块，从"无测试的遗留代码"到"全覆盖的现代化实现"。

---

## 一、为什么 TDD 配合 AI 重构更可靠

传统 TDD 要求人工先写测试再写实现，这对开发者有较高的"规格描述"负担。AI 的加入让这个流程产生了质的变化：

**AI 最擅长的事**：
1. 阅读现有代码，归纳所有输入/输出组合，生成测试用例（从已有行为推导测试）
2. 在测试约束下生成新的实现（满足测试即可，不增加额外功能）

**这解决了两个经典痛点**：
- "AI 重构了，但不知道有没有改坏" → 测试失败会立即告警
- "TDD 太费时，测试比实现还难写" → AI 帮你写测试

Aider 的独特优势在于它能直接运行 `pytest`，用真实测试结果做反馈，形成"写代码 → 跑测试 → 修复 → 跑测试"的自动循环。

---

## 二、前置配置

### 安装与配置

```bash
pip install aider-chat pytest pytest-cov

# 推荐配置 .aider.conf.yml
# 使用高质量模型做架构设计，轻量模型做具体实现
```

在项目根目录创建 `.aider.conf.yml`：

```yaml
# .aider.conf.yml
model: claude-sonnet-4-5
editor-model: claude-haiku-4-5-20251001
auto-test: true
test-cmd: pytest --tb=short -q
auto-commits: false    # TDD 流程中手动 commit，确保每步可回溯
```

> 如果在国内访问 Claude API 有困难，可以通过 [YoTradeApi](https://yotradeapi.com) 配置中转：
> ```yaml
> openai-api-base: https://api.yotradeapi.com/v1
> openai-api-key: YOUR_KEY
> model: claude-sonnet-4-5
> ```

### 项目结构准备

```
orders/
├── calculator.py     # 待重构的核心模块
├── models.py         # 数据模型
└── tests/
    └── test_calculator.py  # 将由 AI 生成
```

---

## 三、第一步：让 AI 生成行为测试

不要急着重构，先让 AI "读懂"现有代码并写出行为测试。

### 3.1 原始代码（模拟真实遗留场景）

```python
# calculator.py（遗留代码，逻辑混乱但"能用"）
def calc(items, user_type, coupon=None, shipping_addr=None):
    total = 0
    for i in items:
        p = i['price'] * i['qty']
        if user_type == 'vip':
            p = p * 0.9
        elif user_type == 'svip':
            p = p * 0.85
        total += p

    if coupon:
        if coupon.startswith('FLAT'):
            amt = int(coupon[4:])
            total = total - amt if total > amt else 0
        elif coupon.startswith('PCT'):
            pct = int(coupon[3:]) / 100
            total = total * (1 - pct)

    # 运费逻辑（硬编码城市）
    ship = 0
    if shipping_addr:
        if total < 99:
            if shipping_addr.get('city') in ['北京', '上海', '广州', '深圳']:
                ship = 8
            else:
                ship = 15

    return round(total + ship, 2)
```

### 3.2 Aider 指令：生成行为测试

```
/add calculator.py tests/test_calculator.py

请分析 calculator.py 中 calc 函数的所有逻辑分支，
为每个分支生成 pytest 测试用例。
要求：
1. 覆盖所有 user_type（普通、vip、svip）
2. 覆盖所有 coupon 格式（无优惠券、FLAT、PCT）
3. 覆盖运费逻辑（订单金额高低、不同城市）
4. 边界值：空订单、优惠券金额大于订单、零件数量
不要修改 calculator.py，只写测试。
```

Aider 生成的测试（片段）：

```python
# tests/test_calculator.py
import pytest
from calculator import calc

# ─── 基础价格计算 ───
class TestPricing:
    def test_normal_user_no_discount(self):
        items = [{"price": 100, "qty": 2}]
        assert calc(items, "normal") == 200.0

    def test_vip_user_10pct_discount(self):
        items = [{"price": 100, "qty": 2}]
        assert calc(items, "vip") == 180.0

    def test_svip_user_15pct_discount(self):
        items = [{"price": 100, "qty": 2}]
        assert calc(items, "svip") == 170.0

# ─── 优惠券逻辑 ───
class TestCoupons:
    def test_flat_coupon_deduction(self):
        items = [{"price": 100, "qty": 1}]
        assert calc(items, "normal", coupon="FLAT20") == 80.0

    def test_flat_coupon_larger_than_total(self):
        items = [{"price": 10, "qty": 1}]
        assert calc(items, "normal", coupon="FLAT20") == 0.0

    def test_pct_coupon_10pct_off(self):
        items = [{"price": 100, "qty": 1}]
        assert calc(items, "normal", coupon="PCT10") == 90.0

# ─── 运费逻辑 ───
class TestShipping:
    def test_no_shipping_above_99(self):
        items = [{"price": 100, "qty": 1}]
        result = calc(items, "normal", shipping_addr={"city": "武汉"})
        assert result == 100.0  # 金额 >= 99，免运费

    def test_tier1_city_shipping(self):
        items = [{"price": 50, "qty": 1}]
        result = calc(items, "normal", shipping_addr={"city": "北京"})
        assert result == 58.0

    def test_non_tier1_city_shipping(self):
        items = [{"price": 50, "qty": 1}]
        result = calc(items, "normal", shipping_addr={"city": "成都"})
        assert result == 65.0

# ─── 边界值 ───
class TestEdgeCases:
    def test_empty_items(self):
        assert calc([], "normal") == 0.0

    def test_zero_quantity(self):
        items = [{"price": 100, "qty": 0}]
        assert calc(items, "normal") == 0.0

    def test_combined_vip_plus_coupon(self):
        items = [{"price": 100, "qty": 2}]
        # VIP 价 180 → FLAT20 → 160
        assert calc(items, "vip", coupon="FLAT20") == 160.0
```

跑一遍确认全部通过，这就是当前行为的"基线"：

```bash
pytest tests/test_calculator.py -v
# 期望：所有测试通过（若有失败，说明原始代码有 Bug，先记录）
```

---

## 四、第二步：重构实现（不修改测试）

行为基线建立后，可以开始重构。告诉 Aider：**只改 `calculator.py`，不改测试，改完自动跑测试。**

```
重构 calculator.py，要求：
1. 将 calc 函数拆分为独立的子函数：
   - calculate_item_price(items, user_type) → 含折扣的商品总价
   - apply_coupon(total, coupon) → 应用优惠券后的价格
   - calculate_shipping(total, shipping_addr) → 运费
2. 使用 dataclass 替代 dict 作为参数类型
3. 添加类型注解
4. 将一线城市列表提取为常量
5. 不要改变任何行为，所有测试必须继续通过
运行 pytest 确认后再结束。
```

Aider 重构后的代码：

```python
# calculator.py（重构后）
from dataclasses import dataclass
from typing import Optional

TIER1_CITIES = frozenset({"北京", "上海", "广州", "深圳"})

USER_DISCOUNTS = {
    "normal": 1.0,
    "vip": 0.9,
    "svip": 0.85,
}

FREE_SHIPPING_THRESHOLD = 99.0


@dataclass
class OrderItem:
    price: float
    qty: int


@dataclass
class ShippingAddress:
    city: str


def calculate_item_price(items: list[OrderItem], user_type: str) -> float:
    discount = USER_DISCOUNTS.get(user_type, 1.0)
    return sum(item.price * item.qty * discount for item in items)


def apply_coupon(total: float, coupon: Optional[str]) -> float:
    if not coupon:
        return total
    if coupon.startswith("FLAT"):
        deduction = int(coupon[4:])
        return max(0.0, total - deduction)
    if coupon.startswith("PCT"):
        pct = int(coupon[3:]) / 100
        return total * (1 - pct)
    return total


def calculate_shipping(total: float, addr: Optional[ShippingAddress]) -> float:
    if not addr or total >= FREE_SHIPPING_THRESHOLD:
        return 0.0
    return 8.0 if addr.city in TIER1_CITIES else 15.0


def calc(items, user_type, coupon=None, shipping_addr=None):
    # 保持原始接口兼容，内部使用新结构
    order_items = [OrderItem(**i) for i in items]
    addr = ShippingAddress(**shipping_addr) if shipping_addr else None

    subtotal = calculate_item_price(order_items, user_type)
    after_coupon = apply_coupon(subtotal, coupon)
    shipping = calculate_shipping(after_coupon, addr)

    return round(after_coupon + shipping, 2)
```

Aider 自动运行 `pytest`，确认全部测试通过后才结束。

---

## 五、第三步：提升测试覆盖率

重构完成后，可以要求 Aider 补充测试，覆盖新拆分出的子函数：

```
为重构后的 calculate_item_price、apply_coupon、calculate_shipping
三个函数分别添加单元测试，目标行覆盖率 95% 以上。
运行 pytest --cov=calculator --cov-report=term-missing 确认覆盖率。
```

---

## 六、工作流总结

```
┌─────────────────────────────────────┐
│  AI TDD 重构标准工作流               │
│                                     │
│  1. /add 目标文件 + 测试文件         │
│  2. 让 AI 生成行为测试               │
│  3. 手动跑测试 → 全通过 → commit     │
│  4. 让 AI 重构实现（auto-test=true）│
│  5. 测试全通过 → commit             │
│  6. 让 AI 补充子函数单元测试         │
│  7. 检查覆盖率 → commit             │
└─────────────────────────────────────┘
```

**关键原则**：
- 步骤 3 和步骤 5 必须在不同 commit，确保"基线测试"与"重构实现"可独立回溯
- 如果重构后某个测试失败，优先怀疑重构有 Bug，而非测试写错
- 对于业务逻辑不清晰的边界（如"FLAT 优惠券大于订单金额怎么算"），让 AI 写出测试后先与产品确认，再决定行为

---

## 七、常见问题

**Q：如果原始代码有 Bug，测试该怎么写？**

让 AI 先写出"当前行为"测试，并在测试注释中标注"此测试记录了已知 Bug，重构后需修复"。重构时单独处理这些测试。

**Q：auto-test=true 会不会导致 AI 为了让测试通过而修改测试？**

会。Aider 有时会"走捷径"修改测试让其通过，而不是修复实现。可以在 Prompt 中明确："不要修改 `tests/` 目录下的任何文件"，或在 `.aider.conf.yml` 中配置 `read-only` 文件列表。

**Q：对于 TypeScript 项目呢？**

将 `test-cmd` 改为 `npx jest --no-coverage`，原理完全相同。

---

## 八、相关阅读

- [Aider 国内配置指南：代理、模型选择与 IDE 集成](/blog/aider-cn-config-guide/)
- [用 Aider 重构 5 年遗留 Python 项目的完整记录](/blog/legacy-python-refactor-with-aider/)
- [AI 辅助测试自动化：真实案例与避坑总结](/blog/ai-test-automation-real-cases/)
- [AI 代码重构的常见错误与防坑指南](/blog/ai-coding-mistakes-to-avoid/)

想在国内稳定使用 Aider + Claude？[YoTradeApi](https://yotradeapi.com) 提供 Claude API 中转，支持 Aider 直接配置，人民币充值，告别访问限制。
