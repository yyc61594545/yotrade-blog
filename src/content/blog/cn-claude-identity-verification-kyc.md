---
title: Claude 身份验证（KYC）怎么过：Quick identity check 全流程与被拒排查
description: Claude 弹出 Quick identity check 要验证身份（KYC）？讲清要准备的证件、Persona 验证页怎么走、哪些证件不收，以及卡住或被拒后的排查顺序。
keywords:
  - Claude KYC
  - Claude 身份验证
  - Claude 实名认证
  - Claude Quick identity check
  - Claude Persona 验证
pubDate: '2026-10-11'
updatedDate: '2026-10-11'
canonical: https://blog.yotradeapi.com/blog/cn-claude-identity-verification-kyc/
tags:
  - Claude
  - 身份验证
  - KYC
  - 国内场景
category: 小白入门
---

用着 Claude，突然弹出一个「Quick identity check」窗口，要你拍证件、拍自拍——这就是大家说的 Claude KYC（身份验证）。它和注册时的手机验证码是两回事：手机验证确认的是「这个号码能收短信」，身份验证确认的是「账号背后是一个真实的人」。

本文按官方帮助页（[Identity verification on Claude](https://support.claude.com/en/articles/14328960-identity-verification-on-claude)）和实际会看到的页面，讲清楚三件事：要准备什么、流程怎么走、卡住或被拒了怎么查。

## 一、什么时候会被要求身份验证

官方的说法是：身份验证目前只在「少数场景」逐步启用。你可能在这几种情况下遇到：

| 场景 | 常见表现 |
|---|---|
| 使用某些功能时 | 点开某个功能，弹出验证窗口 |
| 平台例行的完整性检查 | 正常使用中突然弹出 |
| 其他安全与合规要求 | 账号被限制，要求先验证身份 |

官方没有公布具体的触发规则，所以「别人没遇到、我遇到了」是正常的，不代表账号出了问题。

## 二、要准备什么

官方要求两样东西：

1. **本人的、实体的、政府签发的带照片证件**：护照、驾照、身份证这类。证件要清晰、无破损、没过期、有照片。官方说大多数国家的有效证件都可以，没有公布具体国家名单。
2. **能用摄像头的手机或电脑**：可能要求现场自拍。

下面这些**不收**，用了只会被拒：

- 复印件、截图、扫描件，或者「对着照片再拍一张」
- 电子证件、手机里的电子驾照
- 学生证、工牌、银行卡等非政府证件
- 临时纸质证件

## 三、验证流程怎么走

1. **Claude 弹出「Quick identity check」**：提示要确认身份，大约 2 分钟。点 Start。
2. **跳转到 Persona 的验证页**：地址是 `inquiry.withpersona.com`。Persona 是 Anthropic 选的官方验证合作方。按提示拍证件、拍自拍，全程在你自己的设备上完成。
3. **看到「Congratulations, you're done!」就是提交成功**：点 Done 回到 Claude，等审核结果。

关于隐私，官方帮助页写得很明确：证件和自拍由 Persona 保存，不存在 Anthropic 的系统里；Anthropic 只在需要时（比如申诉）通过 Persona 查看，不会拿这些数据训练模型。

**一个安全提醒**：Persona 的验证链接带着只属于你这次验证的凭证。不要复制、截图或发给任何人——包括自称「客服」「代过」的人。验证必须由账号持有人本人完成，让别人代做既违反规则，也等于把证件交了出去。

## 四、卡住或被拒，按这个顺序查

| 顺序 | 现象 | 先做什么 |
|---|---|---|
| 1 | 页面一直转圈、上传失败 | 换稳定的网络，关掉浏览器的翻译和广告拦截插件，在手机自带浏览器里重开链接 |
| 2 | 拍照不过、提示看不清 | 换光线充足、背景干净的地方，证件放平、四角拍全，不要反光 |
| 3 | 提示证件不被接受 | 对照第二节的「不收」清单；换一种有效证件，比如用护照代替身份证 |
| 4 | 提交后被拒 | 官方允许多次尝试，先按 2、3 两步调整后重试 |
| 5 | 次数用完仍未通过 | 走官方的身份验证帮助表单（帮助页里有入口） |
| 6 | 账号直接被封 | 这通常和多次违反使用政策有关，与验证本身不同；认为误封的，按官方申诉表单提交 |

排查时，把页面上的**提示文字原样抄下来**最有用。大多数问题看提示就能判断是网络、拍照还是证件类型的问题。

## 五、和手机验证别搞混

很多人把这两步混在一起：

- **手机验证码**：注册或登录时要求填手机号收短信。国内 +86 号通常不被接受，需要一个能收短信的海外号。详见 [注册 Claude 要不要手机验证](/blog/cn-claude-register-phone-verify/)。只需要过这一次验证的话，可以用 [Claude 美国号验证码代收](https://yotradeapi.com/sms/claude?utm_source=blog&utm_medium=inline&utm_content=cn-claude-identity-verification-kyc)。
- **身份验证（KYC）**：拍证件和自拍，只能本人用自己的证件完成，没有任何「代收」「代过」的办法。

## 六、自己搞不定怎么办

按上面的顺序走一遍，大部分问题都能解决。如果一直卡在某一步、被拒了看不懂原因，可以找我们的 [Claude KYC 验证协助](https://yotradeapi.com/claudekyc?utm_source=blog&utm_medium=inline&utm_content=cn-claude-identity-verification-kyc)：客服在订单页一对一讲流程、帮你判断卡在哪。我们是第三方协助服务，不是 Anthropic 官方；不代操作、不收证件和照片，验证能不能通过由官方审核决定，我们不保证结果。

## 七、相关阅读

- [注册 Claude 要不要手机验证：国内情况说明](/blog/cn-claude-register-phone-verify/)
- [国内注册 Claude 账号完整流程](/blog/cn-claude-register-cn-guide/)
- [Claude 提示所在地区不支持：原因与替代方案](/blog/cn-claude-supported-region-error/)
