---
title: 国内订阅 Codex 完整路径：支付方式与失败排查
description: Codex 没有独立订阅，它随 ChatGPT Plus / Pro / Business 一起开通。本文按“账号→套餐→付款→登录 Codex”四步梳理国内用户的完整路径，对比网页绑卡、App Store、代充三种付款方式，并给出每一步失败时的排查入口。
keywords:
  - 国内订阅 Codex
  - Codex 怎么开通
  - Codex 付款方式
  - Codex 订阅失败
  - ChatGPT Plus 开通 Codex
  - Codex 国内使用
pubDate: '2026-09-21'
updatedDate: '2026-09-21'
canonical: https://blog.yotradeapi.com/blog/cn-codex-subscribe-cn-guide/
tags:
  - Codex
  - 订阅付款
  - ChatGPT Plus
  - 国内场景
category: 国内场景
---

搜“怎么订阅 Codex”的人，第一个要纠正的认知是：**Codex 不单独卖**。它是 ChatGPT 订阅的一部分，Plus、Pro、Business、Enterprise、Edu 都自带 Codex 使用权，免费账号不能用 ChatGPT 登录方式使用 Codex。所以“订阅 Codex”实际等于“把 ChatGPT 付费套餐开通，然后用这个账号登录 Codex”。

这篇按完整路径走一遍，每一步只讲判断和分叉，具体操作细节链接到站内已有的专题文章。文中价格为官方公开价，仅作参考，以官网当前显示为准。

## 一、四步路径总览

```text
第 1 步  账号      能正常登录网页版 ChatGPT，账号地区为受支持地区
第 2 步  选套餐    Plus（$20/月）/ Pro（$200/月）/ Business（按席位）
第 3 步  付款      网页绑卡 / App Store 内购 / 代充
第 4 步  登录 Codex  CLI、IDE 扩展或网页版，用 ChatGPT 账号登录
```

任何一步失败都有独立的排查入口，不要跳步：第 3 步付款失败时去检查 Codex 配置是没有意义的。

## 二、第 1 步：账号先过关

如果你还没有 ChatGPT 账号，注册时最常卡在手机验证，见 [没有海外手机号怎么注册 ChatGPT（2026 实测方案）](/blog/cn-chatgpt-register-without-foreign-phone/)。已有账号的用户重点核对两件事：

1. **账号地区**：在设置里能看到，或者从付款页显示的货币和税率推断。地区不受支持会在付款或登录 Codex 时被拦，排查见 [ChatGPT 登录提示地区不支持怎么解决](/blog/cn-chatgpt-login-region-error/)。
2. **邮箱类型**：部分邮箱域名在付费和验证时更容易被要求补充验证，选择建议见 [注册 ChatGPT 用哪种邮箱不容易被封](/blog/cn-chatgpt-email-choice-guide/)。

## 三、第 2 步：选套餐，按 Codex 用量而不是按聊天需求

三档套餐对 Codex 的差异主要在额度：

| 套餐 | 官方价 | Codex 额度体感 | 适合 |
|---|---|---|---|
| Plus | $20 / 月 | 每天集中写 1–2 小时够用，连续跑重活会撞窗口 | 个人日常辅助 |
| Pro | $200 / 月 | 约 Plus 的 5–10 倍，全天使用基本不撞 | 重度使用者、自由职业者 |
| Business | 按席位，两席起 | 接近 Pro，管理员统一管理 | 团队 |

额度机制的完整说明见 [Codex 额度机制详解](/blog/cn-codex-quota-explained/)。一个实用的选法：**先开 Plus，用一周，撞短窗口超过三次再升 Pro**。Pro 的国内开通细节见 [ChatGPT Pro $200 月卡国内开通教程](/blog/cn-chatgpt-pro-200-dollar-payment/)；团队席位见 [ChatGPT Team 版国内开通与分摊实战](/blog/cn-chatgpt-team-plan-cn-guide/)。

## 四、第 3 步：三种付款方式怎么选

| 方式 | 前置条件 | 优点 | 主要风险 |
|---|---|---|---|
| 网页绑卡 | 一张账单地址与账号地区一致的境外卡 | 价格是官方价，续费自动 | 卡被拒、风控 |
| App Store / Google Play 内购 | 对应地区的 Apple ID / Google 账号 + 该区礼品卡或付款方式 | 不需要境外卡 | 价格略高，退款和管理绕商店 |
| 代充 | 无 | 不用自己搞卡和账号地区 | 要选对渠道，确认账号控制权归自己 |

三个判断：

- 手上有能用的境外卡 → 直接网页绑卡，最省事。怎么拿到一张境外卡见 [国内申请可付 AI 服务的境外卡路径对比](/blog/cn-overseas-card-application-path/)。
- 没有境外卡但有海外区 Apple ID → 走内购，注意内购开的订阅要在商店里管理，网页上改不了，见 [通过 Apple ID 切区订阅 AI 服务实操](/blog/cn-apple-id-region-ai-subscribe/)。
- 两样都没有、也不想折腾 → 代充。选渠道的底线是：账号是你自己注册的、付款后你能改密码、对方不要求你交出邮箱。

## 五、付款失败的排查入口

付款失败的报错文案通常很笼统，先按“卡”和“账号”两个方向拆：

**卡的问题**（报错在输入卡号后立即出现，或 3D 验证失败）：

- 虚拟卡：先看 [虚拟卡支付 ChatGPT 被拒的排查清单](/blog/cn-virtual-card-declined-fix/)。
- 真实境外卡：核对账单地址、姓名顺序、卡的国家是否与账号地区一致。

**账号的问题**（卡没问题，但反复提示无法完成、或付款成功后被退回）：

- 多半是风控：账号地区、卡地区、IP、手机号国家不一致。原因和处理见 [AI 服务支付风控触发原因与规避](/blog/cn-ai-payment-risk-control/)。
- 已扣款但套餐没生效：先看邮件里的收据，等待数小时后仍未生效再联系官方支持，不要重复付款。

**内购的问题**：Apple ID 地区和礼品卡地区不一致、余额不足、或该区不提供 ChatGPT 内购。切区和礼品卡的注意事项在 Apple ID 那篇文章里。

## 六、第 4 步：登录 Codex 及其常见失败

套餐生效后，安装 Codex CLI 或 IDE 扩展，选择“Sign in with ChatGPT”。国内环境的安装和代理配置见 [Codex CLI 国内配置与使用指南](/blog/codex-cli-cn-setup/)。这一步常见的三种失败：

1. **浏览器回调打不开**：登录在浏览器完成后要回调到本机端口，代理软件的规则可能拦截了 localhost。临时关闭系统代理对 localhost 的接管即可。
2. **要求验证手机号**：这是账号层的安全要求，网页版不要求不代表 Codex 不要求。处理方法见 [Codex 登录要求验证手机号：国内用户怎么过](/blog/cn-codex-login-phone-verification/)。
3. **登录成功但提示无可用套餐**：多半是你登录的账号不是刚付费的那个（多账号常见），或套餐生效有延迟。在网页版确认当前账号的套餐状态再重试。

登录成功后立刻做两件事：在 CLI 里执行 `/status` 确认额度窗口显示正常；在项目里放一份 `AGENTS.md`，避免第一次使用就因为上下文混乱而怀疑“账号有问题”。

## 七、续费与退出：开通时就把出口想好

订阅是按月自动续的，续费失败会导致 Codex 立即不可用：

- 网页绑卡：卡到期、额度不足、发卡行拒付都会导致续费失败。虚拟卡用户尤其要提前充值。续费失败的处理见 [ChatGPT 自动续费失败怎么办](/blog/cn-chatgpt-recurring-failed-fix/)。
- 内购：在商店的订阅管理里续或取消，网页上看到的取消按钮对内购无效。
- 代充：确认对方是一次性代付还是持续代管，避免到期才发现没人续。

想退订或退款，规则和流程见 [AI 订阅退款申请全流程（OpenAI/Anthropic）](/blog/cn-ai-subscription-refund-guide/)。

## 八、相关阅读

- [没有海外手机号怎么注册 ChatGPT（2026 实测方案）](/blog/cn-chatgpt-register-without-foreign-phone/)
- [Codex 额度机制详解：Plus / Pro / 网页版额度能不能通用](/blog/cn-codex-quota-explained/)
- [Codex 登录要求验证手机号：国内用户怎么过](/blog/cn-codex-login-phone-verification/)
- [国内申请可付 AI 服务的境外卡路径对比](/blog/cn-overseas-card-application-path/)
- [ChatGPT Pro $200 月卡国内开通教程](/blog/cn-chatgpt-pro-200-dollar-payment/)

如果卡在付款这一步不想再折腾，可以通过 [YoTradeApi](https://yotradeapi.com) 咨询 ChatGPT Pro 订阅代充，账号由你本人注册和控制，报价微信咨询。姊妹站的 [ChatGPT 海外订阅 2026 指南](https://www.yotradellc.com/blog/chatgpt-overseas-subscription-2026-guide) 从非技术用户角度讲了整个订阅流程，可配合本文看。
