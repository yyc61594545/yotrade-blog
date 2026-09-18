---
title: Codex 登录要求验证手机号：国内用户怎么过
description: codex login 跳转浏览器后卡在 Verify your phone number？本文讲清 Codex 为什么比网页版多这一道验证、两种登录方式的差别、失败排查和只验一次的做法。
keywords:
  - Codex 登录手机验证
  - codex login 验证手机号
  - Codex CLI 国内登录
  - ChatGPT 订阅登录 Codex
  - Codex 验证码收不到
pubDate: '2026-09-18'
updatedDate: '2026-09-18'
canonical: https://blog.yotradeapi.com/blog/cn-codex-login-phone-verification/
tags:
  - Codex
  - 手机验证
  - OpenAI
  - 国内场景
category: 国内场景
---

装好 Codex CLI，敲下 `codex login`，浏览器自动弹出授权页，正准备点确认——页面要求先验证手机号。填大陆号码提示不支持，终端那边还在转圈等回调，最后超时退出。

这是 2026 年国内用户用 Codex 最常见的第一道坎，而且很容易误判成"网络问题"或"CLI 装错了"。本文只解决这一步。

## 一、先分清是哪一种"登录失败"

`codex login` 失败有几种完全不同的表现，处理方式互不通用，先对号入座：

| 现象 | 真实原因 | 处理方向 |
|---|---|---|
| 浏览器打不开 / 回调地址 localhost 拒绝连接 | 端口被占用或远程环境无浏览器 | 换端口，或用 `--api-key` 方式 |
| 页面提示 Unsupported country | 网络出口地区被判定不支持 | 属于地区限制，见文末相关阅读 |
| **页面提示 Verify your phone number** | **账号未完成手机验证** | **本文内容** |
| 验证过了但终端仍报 401 | 回调没打通或订阅不含 Codex 权限 | 重新 login，或检查套餐 |

只有第三种才是手机验证问题。判断方法很直接：**报错文案里出现手机号输入框**，就是这一类。

## 二、为什么网页版能用、Codex 却要验证

很多人不理解：同一个账号，ChatGPT 网页聊天从来没让我验证过手机号，凭什么一登 Codex 就要验？

因为 OpenAI 把手机验证放在了"开始产生程序化调用"这个位置，而不是"注册"这个位置。2026 年普通注册和网页对话在多数情况下已不强制手机验证，但下面这几类动作会触发同一套账号级验证：

- 首次在 platform.openai.com 创建 API Key
- Codex CLI / IDE 插件首次登录授权
- 换设备、换网络后被风控要求重新确认
- 部分地区和网络环境下的新账号注册

**关键事实：这道验证记在账号（organization）上，不记在设备或 Key 上。**所以它有两个推论：

- 重装 CLI、换电脑、删掉 `~/.codex/auth.json` 重新 login，都绕不过去
- 反过来，如果你之前为了建 API Key 已经验证过一次，Codex 登录通常就不会再问了

也就是说，这一关一辈子只需要过一次（除非后续被风控重新要求）。想清楚这点，就不会为它去包月养一个海外号。

## 三、两种登录方式，只有一种躲得开

Codex CLI 支持两种认证路径，它们对手机验证的要求不一样：

**方式 A：ChatGPT 订阅登录（`codex login`）**
走浏览器 OAuth，用 Plus / Pro / Team 订阅额度。首次授权会触发账号级手机验证，**躲不开**。

**方式 B：API Key 登录（`codex login --api-key ...`）**
用 platform 上的密钥计费。看起来绕过了登录页，但你得先有一把 Key——而首次创建 API Key 同样要过手机验证，**本质上是把同一道关挪到了前面**。这一步的细节我在《[创建 OpenAI API Key 提示验证手机号怎么办](/blog/cn-openai-api-key-phone-verification/)》里写过。

```bash
# 方式 A：走订阅额度，浏览器授权
codex login

# 方式 B：走 API 计费，前提是你已经有 Key
export OPENAI_API_KEY="sk-..."
codex login --api-key "$OPENAI_API_KEY"

# 确认当前登录状态
codex login status
```

唯一真正不需要你自己过验证的情况，是用别人（公司、团队）已经验证过的组织账号加入进来——个人开发者没有这条路。

## 四、怎么拿到一个能收码的美国号

需要的是一个**真实运营商号码**。Google Voice、TextNow 这类纯 VoIP 号 2026 年基本会被识别拦截，报错和大陆号一样是 "not supported"，但原因完全不同，别在这上面浪费时间。

三种路径的取舍：

| 方式 | 前置成本 | 单次代价 | 适合谁 |
|---|---|---|---|
| 自己用接码平台 | 注册平台账号 + 先充值（通常三十几元起），界面多为英文或俄文 | 几毛到几元，需自己挑国家挑服务、判断超时退号 | 以后还会反复接码的人 |
| [美国号验证码代收](https://yotradeapi.com/sms?utm_source=blog&utm_medium=inline&utm_content=cn-codex-login-phone-verification) | 无，不用注册和充值 | ¥29.90 一次，支付宝微信付款，收不到自动换号，换号仍失败全额退款 | 只需要过这一次验证的人 |
| eSIM / 实体卡 | 几十到上百元/月 | 号码独享，可长期复用 | 账号要长期用、以后还会频繁收码的人 |

因为这道验证一个账号只需要过一次，**按次解决在这个场景下性价比最高**——为一条短信包月养号，第二个月就是纯浪费。只有在你同时要管多个账号、或者预期会频繁触发风控重验时，自己持号才划算。

各家接码平台的可用性变化很快，为什么"今日实测可用榜单"没有参考价值，见《[ChatGPT 注册接码平台横评 2026](/blog/cn-sms-verification-platform-review/)》。

**操作顺序很重要**：先在浏览器里走到手机号输入框那一步，再去取号。接码号码有效期通常只有几分钟，先拿号再慢慢操作，大概率白花一次。

## 五、验证环节的逐项排查

**填号码就报 not supported**
- 大陆号码：无解，必须换海外号
- 海外号码也报：大概率是 VoIP 号被识别，换真实运营商号段
- 检查是否重复输入国家码（已选 +1，输入框里又写了 1 开头）

**点了发送，一直收不到**
- 先确认接码页面手动刷新过（部分平台不自动推送）
- 超过 2 分钟没到就换号，继续等没有意义
- 优先选美国号，其他国家号段在 Codex 授权页的表现不如美国稳定

**提示尝试次数过多**
- 号码被用过太多次 → 换号，不要重试
- 同一账号短时间内尝试过密 → 等 24 小时

**验证通过了，但终端还在转圈**
- 浏览器已完成授权、CLI 没收到回调，属于本地端口问题
- `Ctrl+C` 后重新 `codex login`，验证状态已经存在账号上，不会再问第二次

**验证通过、登录成功，但一跑就报权限错误**
- 手机验证和使用权限是两件事：订阅套餐是否包含 Codex、API 账号是否已充值，都要单独确认
- `codex login status` 先确认当前用的是订阅还是 API Key，两条计费路径的报错含义不同

## 六、登录成功后立刻做的两件事

1. **确认计费路径。**订阅登录走套餐额度，API Key 登录按量扣费，两者成本模型完全不同。别在没意识到的情况下用 Key 跑长任务。
2. **备份 auth 状态。**认证信息存在 `~/.codex/` 下，换机器前先确认能重新登录（验证已过，重登通常不会再要手机号），别在没网的环境里临时抓瞎。

之后的配置——模型选择、approval policy、沙箱、多 profile——属于另一个话题，见《[Codex CLI 国内配置与使用指南](/blog/codex-cli-cn-setup/)》。

## 七、几个常见误区

**"换个账号重新登就不用验了"**——新账号照样要验，而且同一号码能验证的账号数量有限，多开几个只会更快把号码耗废。

**"挂了代理就不用验手机号了"**——代理解决的是地区可达性，和账号级手机验证是两套判断，网络再干净也不会跳过这一步。

**"验证一次以后就永远不用管了"**——正常情况不会再问，但换设备、换网络、长期不登录后被风控标记，仍可能被要求重新验证。处理方式和本文完全一致。

## 八、相关阅读

- [没有海外手机号怎么注册 ChatGPT（2026 实测方案）](/blog/cn-chatgpt-register-without-foreign-phone/)
- [创建 OpenAI API Key 提示验证手机号怎么办](/blog/cn-openai-api-key-phone-verification/)
- [ChatGPT 注册接码平台横评 2026：哪家还能用](/blog/cn-sms-verification-platform-review/)
- [ChatGPT 登录提示地区不支持怎么解决](/blog/cn-chatgpt-login-region-error/)
- [Codex CLI 国内配置与使用指南](/blog/codex-cli-cn-setup/)

如果只差这一条验证码就能把 Codex 登进去，不用为它包月养号，[YoTradeApi 的美国号验证码代收](https://yotradeapi.com/sms?utm_source=blog&utm_medium=inline&utm_content=cn-codex-login-phone-verification)按次付款，收不到自动换号，换号仍失败全额退款。
