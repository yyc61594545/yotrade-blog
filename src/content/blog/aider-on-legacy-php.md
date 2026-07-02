---
title: 用 Aider 重构遗留 PHP 项目的实战记录
description: 真实案例：用 Aider 重构一个 8 年历史的 PHP 单体项目，从 PHP 5.6 语法、mysqli 裸查询到 PHP 8.3 + PDO 的完整过程与踩坑记录。
keywords:
  - aider 重构 php
  - php 遗留项目升级
  - php 5.6 升级 8.3
  - aider 实战案例
  - mysqli 迁移 pdo
pubDate: '2026-07-02'
updatedDate: '2026-07-02'
canonical: https://blog.yotradeapi.com/blog/aider-on-legacy-php/
tags:
  - Aider
  - PHP
  - 重构
  - 实战案例
category: 实战经验
heroImage: ../../assets/blog-placeholder-3.jpg
---

接手一个跑了 8 年的 PHP 电商后台：没有框架，全是过程式代码混杂零星面向对象，PHP 5.6 语法，SQL 拼接裸跑在 mysqli 上，没有 Composer，没有测试。本文记录用 Aider 把它升级到 PHP 8.3 + PDO 预处理语句的全过程，以及和 Python 遗留项目重构相比，PHP 特有的坑在哪。

## 一、项目初始状态

```
total: 26,400 行 PHP（不含模板）
PHP 版本目标: 5.6 语法风格，服务器已跑 7.4
框架: 无，自研路由 + 全局函数库
数据库访问: mysqli_query() 直接拼接变量，SQL 注入风险点 40+ 处
依赖管理: 无 composer.json，第三方库手动拷贝进 vendor/ 目录
测试: 0
命名空间: 未使用，函数全局注册，重名两次导致过 fatal error
```

目标：

1. 引入 Composer，做依赖与 autoload 现代化
2. 全部 SQL 查询从字符串拼接改为 PDO 预处理语句
3. 语法升级到 PHP 8.3（类型声明、match、nullsafe operator）
4. 补关键路径测试（PHPUnit），覆盖到 40%+
5. 引入 PSR-12 代码风格

这一步和之前那篇 [Python 遗留项目重构](/blog/legacy-python-refactor-with-aider/) 的整体方法论一致（先建保护网、按模块切、每步跑测试），但 PHP 项目的风险点分布完全不同——本文只讲 PHP 特有的坑，配置和方法论重叠的部分不再重复。

## 二、准备工作

```bash
$ aider --version   # 0.86+
$ cd legacy-shop
$ git checkout -b php-modernize
```

`.aider.conf.yml` 关键差异（相比通用配置，PHP 项目多加两行）：

```yaml
model: openai/claude-sonnet-4-6
architect: true
weak-model: openai/claude-haiku-4-5

auto-commits: false
auto-test: true
test-cmd: vendor/bin/phpunit --stop-on-failure

lint-cmd: vendor/bin/phpcs --standard=PSR12
```

`.aiderignore`：

```
vendor/
cache/
uploads/
*.log
runtime/
```

中转配置照搬 [Aider 中文配置指南](/blog/aider-cn-config-guide/) 里的方式即可，这里不重复贴。

## 三、Step 1：先补 Composer，不动业务逻辑

PHP 项目最容易踩的第一个坑：**手动 vendor 目录**。三个第三方库被直接拷进项目，版本号无从查证，甚至有一个被本地改过还没人记得改了什么。

```
$ aider
> /add composer.json（不存在，先让它创建）
> 分析 vendor/ 下现有三个库的来源和版本号，生成对应的 composer.json require 项。
> 如果某个库本地被改过，标记出来，列出具体改动位置，不要直接覆盖。
```

Aider 通过读取库内注释和 changelog 片段，识别出两个是标准 Guzzle 和 PHPMailer，一个是被本地 patch 过的日志库。第三个我手工确认改动后决定保留 patch，用 `composer patch` 插件锁定。

**关键纪律**：涉及"这段代码是不是被改过"的判断，让 AI 列证据，人来拍板，不要让它自己决定覆盖还是保留。

## 四、Step 2：SQL 注入点批量修复——最耗时也最不能偷懒的一步

这是整个重构里工作量最大的部分。40 多处 `mysqli_query("SELECT * FROM users WHERE id=" . $_GET['id'])` 这种写法，散落在没有统一入口的代码里。

不能一次性全改，会漂移。按文件切：

```
> /add includes/user.php
> 这个文件里所有 mysqli_query 拼接字符串的调用，改成 PDO 预处理语句。
> 具体要求：
> 1. 保留原函数签名不变（调用方不用改）
> 2. 所有 $_GET / $_POST / $_COOKIE 来源的变量必须走 bindValue，不能再拼接
> 3. 改完跑一遍 grep 确认这个文件里没有残留的字符串拼接 SQL
> 4. 每个函数改完在下面加一行注释标注 "// PDO migrated"（方便后续 review 用 grep 定位剩余文件）
```

单个文件（约 400 行）改完，跑 `phpcs` + 手工 review diff，确认逻辑等价后再进下一个文件。**26 个文件，每个独立 commit**，两天跑完。

**这一步不能信任自动跑完不检查**。用一个脚本做二次校验：

```bash
$ grep -rn "mysqli_query.*\$_\(GET\|POST\|COOKIE\)" includes/ | wc -l
0   # 改完后必须是 0
```

跑完发现漏了 3 处——都是变量先赋值给一个中间变量再拼接，正则没扫到，Aider 也没主动查这种间接拼接。**这类"变量别名绕过检测"的风险，必须人工再过一遍，不能只信 AI 报告的"已全部修复"。**

## 五、Step 3：全局函数命名空间化

8 年下来全局函数库有 300+ 个函数，两次重名靠"后加载的覆盖前面的"侥幸没崩，属于定时炸弹。

```
> /add includes/functions/
> 把这个目录下所有函数按文件名分组，加上对应命名空间（App\Functions\<文件名>）。
> 调用方全部加 use 语句更新，不要漏改调用点。
> 先只处理 order.php 一个文件，改完跑 phpunit 确认没有 fatal error。
```

命名空间化本身对 Sonnet 是结构化机械任务，跑得很稳。真正的风险在**调用点遗漏**——PHP 没有强制的 import 检查，漏改一个调用点不会在语法层面报错，只会在运行到那行时 500。

解决办法：让 Aider 改完之后自己写一个静态扫描脚本，而不是只靠 phpunit 覆盖：

```
> 写一个 PHP 脚本，扫描 includes/ 和 templates/ 下所有 .php 文件，
> 找出调用了已迁移函数但没有对应 use 语句或完整命名空间前缀的地方，列出文件名和行号。
```

这个脚本跑出来又抓到 8 个漏改点，全在几乎没人维护的旧后台模板里，PHPUnit 测试完全没覆盖到。

## 六、Step 4：PHP 8.3 语法升级

```
> 升级到 PHP 8.3 兼容。具体动作：
> 1. composer.json 里 require.php 改成 "^8.3"
> 2. 函数参数和返回值加类型声明（先加 public 方法，private 方法第二轮再加）
> 3. 用 match 替换掉明显冗长的 switch-case
> 4. 用 nullsafe operator (?->) 简化连续的 isset 判断链
> 5. 跑 phpunit 和 phpcs 双重验证
```

这一步暴露了一个 PHP 特有的隐患：**大量代码依赖弱类型隐式转换**，比如把字符串 `"0"` 当 falsy 用、数组和字符串混用 `+`。加了严格类型声明后，有 6 处直接触发 `TypeError`。

```
> 上面这 6 个 TypeError，逐个分析是隐式转换依赖问题还是真实 bug，
> 给出修复方案，优先保持原有业务行为不变。
```

Aider 分析出：5 处是纯粹的隐式转换依赖（加个 `(int)` 强转即可保持行为一致），1 处是真实的历史 bug（一个优惠券金额比较用了 `==` 而不是 `===`，导致空字符串被判定等于 0，一直在被动放行本该拒绝的请求）。**这个真实 bug 是靠严格类型升级过程中意外挖出来的**，如果没做这次重构可能还在生产环境悄悄跑着。

## 七、Step 5：补 PHPUnit 测试

裸项目没有任何测试基础设施，先搭骨架：

```
> 初始化 PHPUnit 配置。
> 为 SQL 注入修复涉及的 26 个文件里，优先给订单、支付、用户认证三个模块补测试。
> 每个公开函数至少 2 个 case：正常输入 + 恶意输入（模拟 SQL 注入 payload）。
```

**恶意输入 case 是这次和 Python 项目重构最大的不同**——PHP 遗留项目补测试，第一优先级不是覆盖率数字，是"验证刚才的 SQL 注入修复真的挡住了注入"。跑完这批测试，覆盖率只有 32%，但这 32% 覆盖的正是风险最高的路径，比盲目追求覆盖率百分比更有意义。

## 八、整体总结

| 阶段 | 时间 | Token 估算 | 成本 |
| --- | --- | --- | --- |
| Composer 化 | 半天 | 300k | $2 |
| SQL 注入修复（26 文件） | 2 天 | 3.5M | $22 |
| 命名空间化 | 1 天 | 1.2M | $8 |
| PHP 8.3 升级 | 1 天 | 1M | $6 |
| PHPUnit 骨架 + 关键测试 | 1 天 | 1.5M | $10 |
| **总计** | **约 5.5 个工作日** | **7.5M** | **~$48** |

如果纯手工排查 40 多处 SQL 拼接并逐个验证，估计至少 3 周——手工排查最容易漏掉的恰恰是间接拼接和跨文件调用，AI 辅助的静态扫描脚本比人工 grep 更彻底。

## 九、PHP 项目相比 Python 项目的三个特有风险点

1. **弱类型隐式转换的隐蔽依赖**：升级到严格类型后才会暴露，必须留出时间处理 TypeError，不能假设"加类型声明"是无风险的机械操作。
2. **全局函数重名靠加载顺序侥幸不崩**：命名空间化过程中必须用静态扫描脚本二次校验调用点，不能只信 phpunit 的绿色状态。
3. **SQL 拼接的间接变量绕过**：正则和字面量扫描抓不住"先赋值给中间变量再拼接"的写法，AI 报告的"已全部修复"需要人工再过一遍确认。

## 十、不该用 AI 处理的

- ❌ 支付金额比较逻辑的最终验证（哪怕是 AI 挖出的 bug，修复方案也要人工二次确认）
- ❌ 涉及历史数据兼容的字段类型变更
- ❌ 鉴权与 session 处理逻辑
- ❌ 未覆盖测试路径的大范围自动改动（先补测试，再动代码）

## 十一、相关阅读

- [Aider 中文配置与最佳实践](/blog/aider-cn-config-guide/)
- [用 Aider 重构 5 年遗留 Python 项目的完整记录](/blog/legacy-python-refactor-with-aider/)
- [Aider Test-Driven 重构工作流](/blog/aider-test-driven-refactor/)
- [Claude Code vs Aider 该怎么选](/blog/claude-code-vs-aider-comparison/)
- [AI 重构遗留单体项目的模式总结](/blog/ai-refactor-legacy-monolith/)

遗留项目重构往往需要跑大量长上下文的 diff 分析和多轮修复，[YoTradeApi](https://yotradeapi.com) 提供 Claude 全系模型稳定中转，按这篇文章的 yaml 配置直接接入即可开始。
