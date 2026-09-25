---
title: Codex 账号怎么开：国内从注册到命令行登录一次走通
description: 国内开 Codex 账号会在三处卡住：注册、订阅、CLI 登录验证手机号。本文按实际顺序给出准备清单和每一步的判断标准，避免走到一半发现前置没做。
keywords:
  - codex账号
  - Codex 怎么注册
  - Codex CLI 登录教程
  - Codex 国内使用
  - codex login 失败
pubDate: '2026-09-25'
updatedDate: '2026-09-25'
canonical: https://blog.yotradeapi.com/blog/cn-codex-account-cn-guide/
tags:
  - Codex
  - 小白入门
  - 手机验证
  - 国内场景
category: 小白入门
---

国内开 Codex 这件事，真正难的不是任何一步，是**顺序**。很多人先装了 CLI，敲 `codex login` 才发现没订阅；或者先订阅了，登录时才发现要验证手机号而手上没号。每次返工都要重来一遍。

这篇按实际该走的顺序列一遍，每步说清楚「做完后怎么算过关」，以及卡住时往哪篇文章翻。目标是一次走通。

## 一、先把清单过一遍

动手前确认这四样，缺哪样先补哪样：

| 需要的东西 | 判断标准 | 没有怎么办 |
|---|---|---|
| 一个 OpenAI 账号 | 能登进 chatgpt.com | 见第二节 |
| 一个付费订阅 | 账号里能看到 Plus / Pro 状态 | 见第三节 |
| Node.js 环境 | `node -v` 输出 ≥ 20 | 见第四节 |
| 一个能收验证码的海外号 | 手上就有，不是「到时候再说」 | 见第五节 |

**最后一行是本文最重要的一句。** `codex login` 会跳浏览器验证手机号，终端那边在等回调且有超时。你要是登录之后才去找号，很可能号还没到手，终端已经超时退出了。号必须在敲命令之前就准备好。

## 二、第一步：注册 OpenAI 账号

用邮箱注册即可，邮箱本身没有特殊要求。

2026 年的实际情况是：**网页版普通注册多数已不强制手机验证**。所以这一步大概率比你想的顺利。如果弹出了手机验证，通常是命中了风控或地区策略，换个干净的浏览器环境重走一遍往往就过了。

注册环节要是真卡住，分两类：

- 卡在收不到邮箱验证码 → 见《[ChatGPT 邮箱验证码收不到怎么办](/blog/cn-chatgpt-email-verification-missing/)》
- 卡在手机验证 → 见《[没有海外手机号怎么注册 ChatGPT（2026 实测方案）](/blog/cn-chatgpt-register-without-foreign-phone/)》

**过关标准**：浏览器里能正常登录 chatgpt.com 并发出一条消息。

## 三、第二步：订阅

Codex 不是免费的。用 ChatGPT 订阅登录的话，需要账号上有有效的付费订阅，额度按套餐算。

选哪档、额度怎么分配、CLI 和 IDE 扩展共不共用，这几件事《[Codex 额度是怎么算的](/blog/cn-codex-quota-explained/)》讲得比较全，这里只给一条判断：**按你打算让 Codex 跑多少活来选，不是按你平时聊天的需求选**。这两个用量差一个数量级。

付款方式和失败排查见《[Codex 订阅国内开通指南](/blog/cn-codex-subscribe-cn-guide/)》。国内卡付不过去是常事，路径选择可以参考姊妹站的《[ChatGPT 海外订阅 2026 指南](https://www.yotradellc.com/blog/chatgpt-overseas-subscription-2026-guide)》。不想自己折腾开通的，我们也做 ChatGPT Pro 的订阅代充，报价微信咨询。

**过关标准**：账号设置页里能看到订阅状态是 active，而不是 past due 或空白。

## 四、第三步：装 CLI

Codex CLI 走 npm 安装，先确认 Node 版本：

```bash
# 检查 Node 版本，需要 20 或更高
node -v

# 安装 Codex CLI
npm install -g @openai/codex

# 确认装上了
codex --version
```

几个常见问题：

- **`node -v` 提示命令不存在** → 没装 Node，先去 nodejs.org 装 LTS 版本。
- **版本号低于 20** → 升级，不要凑合。旧版本会在运行时报一些看不懂的错。
- **npm install 卡住或超时** → 国内网络问题，换 npm 镜像源或走代理。这一步和账号无关，纯粹是下载。
- **装完 `codex` 命令找不到** → npm 全局目录不在 PATH 里，按 npm 的提示把它加进去。

**过关标准**：`codex --version` 能输出版本号。

## 五、第四步：准备好号，再登录

这一步是全流程唯一有时间压力的地方。

`codex login` 会自动打开浏览器做授权，授权流程里要求验证手机号。终端在等浏览器回调，**有超时**。所以正确顺序是：

1. 号码先到手（或者接码页面已经开着、号已经拿到）
2. 浏览器里已登录 OpenAI 账号
3. 然后才敲 `codex login`

关于怎么拿一个能收码的号，三种路子各自的代价：

| 方式 | 成本 | 适合 |
|---|---|---|
| 接码平台 | 单价几毛到几元，但多数要先充值，失败自己承担 | 愿意研究号段、能接受多试几次 |
| [美国号验证码代收](https://yotradeapi.com/sms?utm_source=blog&utm_medium=inline&utm_content=cn-codex-account-cn-guide) | ¥29.90 一次，支付宝微信付款，不用注册和充值，收不到自动换号，换号仍失败全额退款 | 只验这一次，不想研究号段 |
| 海外 eSIM / 实体卡 | 几十到上百元/月，号码独享长期持有 | 长期用，以后还会被要求重新验证 |

需要说清楚：**这三种都只解决「收到这条验证码」，不承诺注册一定成功或账号不被风控**。

选哪个本质看你还要验几次，详细对比见《[Codex 手机号验证怎么办：国内三种办法的成本与成功率对比](/blog/cn-codex-phone-verify-what-to-do/)》。

**过关标准**：终端提示登录成功，且没有报超时。

## 六、第五步：跑一次确认真的通了

登录成功不等于能用。找个空目录跑一下：

```bash
mkdir codex-test && cd codex-test
codex
```

进入交互界面后让它做件小事（比如「建一个 hello.py 打印 hello」），看它是不是真的执行了。

如果这里报额度或权限相关的错，问题多半在订阅那一层，不在登录——回第三节确认订阅状态。

**过关标准**：它真的改了文件，而不是只回了一段文字。

## 七、登录成功后立刻做的两件事

别跳过，这两件事决定你以后还要不要重走一遍：

1. **把账号的恢复方式配全**。恢复邮箱、绑定的登录方式（Google / Apple / 密码）都设好。如果账号的唯一凭据挂在一个临时号码上，号码一失效，账号基本就废了一半。
2. **记下这次验证成功的组合**：哪种方式、哪个国家的号、哪个号段。换设备或换网络后被要求重新验证时，直接复用这个组合，不用从零试。

第 2 点看着琐碎，但重新验证是会发生的——触发条件不公开，换设备、换网络、改密码之后都可能遇上。

## 八、卡住了往哪翻

| 现象 | 大概率原因 | 去哪看 |
|---|---|---|
| 注册时弹「电话号码是必填项」 | 表单校验或风控 | [验证弹窗逐句解释](/blog/cn-chatgpt-phone-required-field/) |
| 提示号码无效 / 不支持 | 号码类型或地区问题 | [号码无效的原因与解决](/blog/cn-chatgpt-phone-number-not-supported/) |
| 提示号码已被使用 | 号码历史问题，换一个号 | [号码已被使用怎么办](/blog/cn-chatgpt-phone-already-used/) |
| 一直收不到短信 | 投递层问题 | [收不到验证码的逐项排查](/blog/cn-chatgpt-verification-code-not-received/) |
| 终端超时退出 | 回调超时，和号码无关 | 号准备好后重新执行 `codex login` |
| 订阅付款失败 | 卡被拒 | [Codex 订阅国内开通指南](/blog/cn-codex-subscribe-cn-guide/) |
| 跑起来提示额度不足 | 套餐层面的问题 | [Codex 额度是怎么算的](/blog/cn-codex-quota-explained/) |

对号入座再动手，比在一个地方硬试快得多。**尤其别在收不到码时连点「重新发送」**——触发频率限制之后，这个号短时间内就废了，还得等冷却。

## 九、相关阅读

- [没有海外手机号怎么注册 ChatGPT（2026 实测方案）](/blog/cn-chatgpt-register-without-foreign-phone/)
- [Codex 登录要求验证手机号：国内用户怎么过](/blog/cn-codex-login-phone-verification/)
- [Codex 手机号验证怎么办：国内三种办法的成本与成功率对比](/blog/cn-codex-phone-verify-what-to-do/)
- [Codex 订阅国内开通指南](/blog/cn-codex-subscribe-cn-guide/)
- [Codex 额度是怎么算的](/blog/cn-codex-quota-explained/)

清单里就差一个能收码的号，[YoTradeApi 的美国号验证码代收](https://yotradeapi.com/sms?utm_source=blog&utm_medium=inline&utm_content=cn-codex-account-cn-guide)按次付款、不用注册和充值，收不到自动换号，换号仍失败全额退款。
