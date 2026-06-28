---
title: 给 Rails 项目写 Cursor Rules：从约定到自动化
description: 为 Ruby on Rails 项目定制 .cursorrules 的实战指南，涵盖 MVC 约定、Active Record、RSpec、Hotwire 等场景的规则写法与团队协作策略。
keywords:
  - Cursor Rules Rails 项目
  - Rails .cursorrules 配置
  - Ruby on Rails AI 编程
  - Cursor Rails 最佳实践
  - Active Record Cursor 规则
pubDate: '2026-06-28'
updatedDate: '2026-06-28'
canonical: https://blog.yotradeapi.com/blog/cursor-rules-for-rails-project/
tags:
  - Cursor
  - Rails
  - 实战经验
  - Ruby
category: 实战经验
heroImage: ../../assets/blog-placeholder-3.jpg
---

Ruby on Rails 有一套极其强烈的约定——Convention over Configuration。这既是它的优势，也是让 AI 助手"写错"的高频原因：没有约定背景的 AI 倾向于生成"合法但不地道"的 Rails 代码，比如绕过 Active Record 回调直接写 SQL、用非 RESTful 路由命名、在 Controller 里堆业务逻辑。

一套针对 Rails 项目的 Cursor Rules，本质上是把 Rails Way 翻译成 AI 能理解的指令集。本文分享实战中积累的规则体系，按场景分层组织。

## 一、为什么 Rails 项目特别需要定制规则

一般框架的 AI 错误是语法层面的，容易被 linter 拦住。Rails 的 AI 错误更多是**架构层面的**：

- 在 Model 里写本该放 Service Object 的逻辑
- 用 `find_by_sql` 代替 scope
- 忽略 Rails 的 `before_action`，直接在每个 action 里重复鉴权
- 生成 migration 时不遵守 `add_index` 与 `references` 的惯用法
- 忽视 Turbo/Hotwire，用 JavaScript 手写本可用 Turbo Frame 替代的交互

这些错误通过 RuboCop 也只能部分发现。所以需要在 Cursor Rules 层面就把 Rails 约定明确化。

## 二、文件组织：单文件还是多文件规则

Cursor 支持两种规则组织方式，详细说明可参考 [.cursorrules 最佳实践](/blog/cursor-rules-best-practices/)。对 Rails 项目，**推荐多文件结构**：

```
.cursor/
  rules/
    00-project-overview.md     # 项目背景、技术栈版本
    10-ruby-style.md           # Ruby 代码风格
    20-rails-conventions.md    # Rails 核心约定
    30-active-record.md        # Active Record 规则
    40-testing.md              # RSpec / Minitest 规则
    50-frontend.md             # Hotwire / ViewComponent 规则
    60-security.md             # 安全要求
```

每个文件 100–300 行，专注一个维度。Cursor 会根据你当前编辑的文件类型自动加载最相关的规则文件。

## 三、项目概览规则（00-project-overview.md）

这是所有规则的基座，每个 AI 对话都会加载：

```markdown
# 项目背景
这是一个 Ruby on Rails 7.2 项目，使用 PostgreSQL 数据库。
前端使用 Hotwire（Turbo + Stimulus），无独立 SPA 框架。
部署在 Heroku，使用 Sidekiq 处理后台任务。

# 技术约束
- Ruby >= 3.2
- Rails >= 7.2
- PostgreSQL 16
- Sidekiq 7.x（后台任务，不使用 Delayed::Job）
- RSpec 3.x（测试框架，不使用 Minitest）
- ViewComponent（组件化 UI，不使用 Cells）

# 禁止引入的依赖
- 不引入 React / Vue / Angular
- 不使用 jQuery（已从项目移除）
- 不使用 Pundit（权限用自定义 Policy 类）
```

## 四、Rails 核心约定规则（20-rails-conventions.md）

这是最重要的规则文件，覆盖 MVC 分层和 RESTful 约定：

```markdown
# Controller 约定
- Controller 只负责 HTTP 层：参数白名单、调用 Service、渲染响应
- 不在 Controller 里写业务逻辑，复杂逻辑提取到 app/services/ 或 app/commands/
- 始终使用 before_action 进行鉴权，不在每个 action 里重复
- 使用标准 7 个 RESTful action：index / show / new / create / edit / update / destroy
- 非 RESTful 操作考虑新建 Controller（如 Sessions::OauthController）

示例结构：
  def create
    @user = UserRegistrationService.call(user_params)
    if @user.persisted?
      redirect_to @user, notice: "注册成功"
    else
      render :new, status: :unprocessable_entity
    end
  end

# Model 约定
- Model 包含：关联关系、验证、scope、实例方法（面向对象行为）
- 不在 Model 里写跨 Model 的业务协调逻辑
- scope 优先于类方法，使用 lambda 语法：scope :active, -> { where(status: :active) }
- 回调（before_save 等）只用于"总是需要"的数据一致性操作，不用于触发邮件等副作用

# 路由约定
- 优先使用 resources / resource，嵌套不超过 2 层
- 自定义路由用 member / collection 块，不散落在 namespace 外
- 路由文件按模块分组，用 namespace 或 scope 区隔
```

## 五、Active Record 专项规则（30-active-record.md）

Active Record 是 Rails 最容易被 AI "写坏"的部分：

```markdown
# 查询约定
- 使用 scope 和关联方法，避免裸写 SQL 字符串
- N+1 查询：凡涉及关联数据，必须使用 includes / eager_load / preload
- 不使用 find_by_sql，除非有明确性能测试证明必要
- 批量操作用 find_each（遍历大量记录）或 insert_all（批量插入）

# Migration 约定
- 列名遵循 Rails 惯例（外键用 _id 后缀，布尔值用 is_ 前缀不强制但需一致）
- 添加外键时同时添加索引：add_reference :orders, :user, foreign_key: true
- 不在 migration 里写业务逻辑或调用 Model 方法（Model 结构可能已变）
- 每个 migration 只做一件事，命名清晰：add_status_to_orders

# 校验
- 数据库层面加约束（null: false、uniqueness index），Model 层面写对应 validation
- 两层约束都要有，不能只依赖 Model validation

示例 migration：
  def change
    add_column :orders, :status, :string, null: false, default: "pending"
    add_index :orders, :status
  end
```

## 六、测试规则（40-testing.md）

Rails 项目测试往往是 Cursor 最难写对的部分，因为 RSpec 的 DSL 和 Rails helper 组合复杂：

```markdown
# RSpec 基本约定
- 文件结构镜像 app/ 目录：app/models/user.rb → spec/models/user_spec.rb
- 用 describe 描述类/方法，用 context 描述场景，用 it 描述预期行为
- 每个 it 块只测一件事（One Expectation Per Test 不强制，但尽量）

# Factory vs Fixture
- 使用 FactoryBot，不使用 Rails fixtures
- Factory 定义在 spec/factories/ 下，一个文件对应一个 Model
- 用 create_list / build_list 创建批量数据，不循环 create

# 示例结构
  RSpec.describe Order, type: :model do
    describe "validations" do
      it "requires status" do
        order = build(:order, status: nil)
        expect(order).not_to be_valid
        expect(order.errors[:status]).to include("can't be blank")
      end
    end

    describe "#total_price" do
      context "when order has items" do
        it "returns sum of item prices" do
          order = create(:order, :with_items, item_count: 3)
          expect(order.total_price).to eq(order.items.sum(:price))
        end
      end
    end
  end

# 禁止
- 不在 spec 里直接调用 ActiveRecord 查询测试 UI 逻辑（用 request spec）
- 不 mock ActiveRecord 关联，用真实 DB（测试数据库）
```

## 七、Hotwire / 前端规则（50-frontend.md）

这是现代 Rails 项目最常被 AI"走偏"的地方——AI 容易自动引入 React/Vue，或用 JavaScript 实现本可用 Turbo 完成的交互：

```markdown
# Turbo 优先原则
- 页面局部更新优先使用 Turbo Frame，不写手动 fetch + DOM 操作
- 表单提交使用 Turbo（Rails 7 默认），响应返回 Turbo Stream 或重定向
- 不使用 $.ajax 或 fetch 实现本可用 Turbo 替代的功能

# Stimulus 控制器
- 复杂 JS 交互才使用 Stimulus，轻交互（toggle、简单动画）用内联 data 属性
- 控制器放在 app/javascript/controllers/ 下
- 命名：功能描述 + _controller.js，如 dropdown_controller.js

# ViewComponent
- 可复用 UI 片段（如 Alert、Badge、Table Row）用 ViewComponent 封装
- 放在 app/components/ 下，对应 spec/components/ 写测试
- 不在 partial 里写复杂逻辑，复杂 partial 考虑迁移到 ViewComponent

# 禁止
- 不引入 React / Vue 解决局部更新问题，这是 Turbo 应该做的
- 不使用 Rails UJS（已废弃），只使用 Turbo
```

## 八、安全规则（60-security.md）

```markdown
# SQL 注入防护
- 永远不用字符串插值拼 SQL：where("name = '#{params[:name]}'") 是错误的
- 使用参数化查询：where("name = ?", params[:name]) 或 where(name: params[:name])

# Mass Assignment
- 始终使用 strong parameters（params.require(:user).permit(...)）
- 不使用 params[:user].to_unsafe_h

# XSS
- ERB 模板默认 HTML 转义，不使用 raw() 或 html_safe 除非有明确的安全验证
- 如果数据来自用户输入，不允许标记为 html_safe

# 认证与鉴权
- before_action :authenticate_user! 放在 ApplicationController，子 Controller 用 skip_before_action
- 不在 action 里手动判断 current_user，抽象到 Policy 类
```

## 九、团队协作：让规则落地

规则写好只是开始，更重要的是让团队真正用起来：

**1. 把规则文件纳入 Git 版本控制**

```bash
git add .cursor/rules/
git commit -m "chore: 添加 Cursor Rules for Rails 项目"
```

**2. 在 PR 模板里加一行检查**

```markdown
- [ ] 是否遵循了 .cursor/rules/ 中的约定（AI 生成代码请特别检查）
```

**3. 定期回顾和迭代**

每两周的迭代会议里，花 15 分钟讨论"AI 生成了什么不符合规范的代码"，然后更新对应的规则文件。规则应该是活的文档，随项目演化而迭代。

关于规则在不同项目中的演化规律，可参考 [Cursor Rules 在真实项目中的演化](/blog/cursor-rules-real-projects/)。

## 十、完整规则模板下载

把本文的所有规则整合成一个可用的模板目录，初始化方式：

```bash
mkdir -p .cursor/rules

# 创建完整规则集（把本文各节内容复制进去）
touch .cursor/rules/00-project-overview.md
touch .cursor/rules/10-ruby-style.md
touch .cursor/rules/20-rails-conventions.md
touch .cursor/rules/30-active-record.md
touch .cursor/rules/40-testing.md
touch .cursor/rules/50-frontend.md
touch .cursor/rules/60-security.md

# 纳入版本控制
echo ".cursor/rules/" >> .gitignore-remove  # 确保不在 .gitignore 里
git add .cursor/rules/
```

初始化后，在每个规则文件里填入适合你项目的具体内容。项目背景、禁用依赖、团队约定这些是最值得花时间写清楚的部分——AI 不知道的信息，规则文件帮你补全。

## 相关阅读

- [.cursorrules 最佳实践：让 Cursor 真正懂你的项目](/blog/cursor-rules-best-practices/)
- [Cursor Rules 在真实项目中的演化](/blog/cursor-rules-real-projects/)
- [Cursor 团队推广三个月复盘：落地痛点与真实收益](/blog/cursor-team-rollout-3months/)
- [AI 代码审查工作流：提升团队代码质量的实践方案](/blog/ai-code-review-workflow/)

在 Rails 项目里配好 Cursor Rules 后，AI 生成的代码质量会有明显提升。如果你的团队同时使用多种 AI 模型（如 Claude、GPT-4o），[YoTradeApi](https://yotradeapi.com) 提供统一的 API 中转端点，可直接在 Cursor 自定义模型配置中使用，按需切换模型而不改动代码。
