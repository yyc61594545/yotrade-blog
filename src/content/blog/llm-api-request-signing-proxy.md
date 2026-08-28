---
title: AI API 网关请求签名与防重放实现
description: 自建或评估 AI API 网关时如何设计请求签名机制，防止重放攻击与密钥被盗用后的滥刷，含 HMAC 签名方案与时间窗口校验的具体实现。
keywords:
  - API 请求签名
  - 防重放攻击
  - HMAC 签名
  - AI 网关安全
  - API 密钥防盗刷
pubDate: '2026-08-28'
updatedDate: '2026-08-28'
canonical: https://blog.yotradeapi.com/blog/llm-api-request-signing-proxy/
tags:
  - LLM 网关
  - 安全合规
  - 工程实战
  - API管理
category: 技术深度
heroImage: ../../assets/blog-placeholder-2.jpg
---

如果你在 [自建 LLM 网关的路由层](/blog/llm-gateway-routing-implementation/) 之后开始考虑对外暴露 API，签名和防重放就是绕不开的一步——网关转发的是真金白银的模型调用额度，一旦密钥泄露或者请求被截获重放，损失是直接体现在账单上的。本文聚焦请求签名机制的具体设计，不是通用安全清单（那部分参考 [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)）。

## 一、为什么单纯的 API Key 不够

最基础的鉴权方式是在请求头里带一个静态 API Key，这在内部系统之间够用，但暴露给客户端或第三方调用方时有两个明显问题：

1. **Key 一旦被截获（网络嗅探、日志泄露、客户端逆向），可以无限次重放使用**，攻击者拿着同一个 Key 就能一直消耗你的模型调用额度
2. **无法区分"合法请求被重放"和"新的合法请求"**，静态 Key 本身不携带请求的时间和内容信息

请求签名机制的核心思路：每次请求除了带 Key，还要带一个基于请求内容 + 时间戳 + 密钥计算出的签名，网关校验签名合法性和时间窗口，过期或签名不匹配的请求直接拒绝。

## 二、HMAC 签名方案设计

签名算法选 HMAC-SHA256——足够安全、计算开销低、几乎所有语言都有标准库支持。签名覆盖的字段需要包含能唯一确定这次请求的所有关键信息：

```python
import hmac
import hashlib
import time

def generate_signature(secret_key: str, method: str, path: str,
                        body: str, timestamp: int, nonce: str) -> str:
    """
    生成请求签名。
    签名串顺序固定，双方必须完全一致，任何一个字段变化签名都会不同。
    """
    sign_string = f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        sign_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return signature

def build_signed_headers(secret_key: str, method: str, path: str, body: str) -> dict:
    timestamp = int(time.time())
    nonce = generate_nonce()  # 随机字符串，见下文防重放部分
    signature = generate_signature(secret_key, method, path, body, timestamp, nonce)
    return {
        "X-Timestamp": str(timestamp),
        "X-Nonce": nonce,
        "X-Signature": signature,
    }
```

客户端每次请求都用自己的 `secret_key` 重新计算签名，网关侧用同样的算法和存储的 `secret_key` 重新计算一遍，两者比对：

```python
def verify_signature(secret_key: str, method: str, path: str, body: str,
                      timestamp: int, nonce: str, provided_signature: str) -> bool:
    expected = generate_signature(secret_key, method, path, body, timestamp, nonce)
    # 用 hmac.compare_digest 防止时序攻击，不要用 == 直接比较
    return hmac.compare_digest(expected, provided_signature)
```

**关键细节**：签名比对必须用 `hmac.compare_digest`，不能用普通的字符串 `==`。普通比较是逐字符短路的，攻击者可以通过测量响应时间差异逐字节猜出正确签名，这是真实存在过的漏洞类型。

## 三、时间窗口校验：防止签名被截获后重放

签名本身防不住"原样重放同一个请求"——如果攻击者截获了一个完整的合法请求（包括正确的签名），照样能重新发送一次。这就是时间窗口 + nonce 组合要解决的问题。

### 时间窗口校验

```python
MAX_TIMESTAMP_SKEW = 300  # 5 分钟，超出则拒绝

def check_timestamp_window(request_timestamp: int) -> bool:
    now = int(time.time())
    return abs(now - request_timestamp) <= MAX_TIMESTAMP_SKEW
```

窗口不宜设置过短（客户端和服务端时钟可能有几秒到几十秒的偏差，网络延迟也要留余量），也不宜过长（窗口越长，重放攻击的可用时间越长）。5 分钟是比较常见的折中值。

### Nonce 去重：同一签名不能用第二次

单纯的时间窗口校验挡不住"5 分钟内立刻重放"，还需要 nonce（一次性随机数）配合 Redis 做去重：

```python
import redis

r = redis.Redis()

def check_and_store_nonce(nonce: str, timestamp: int) -> bool:
    """
    返回 True 表示 nonce 首次出现（合法），False 表示已使用过（拒绝）。
    key 的过期时间设置为略大于时间窗口，窗口外的请求本来就会被时间戳校验拦掉，
    不需要永久存储 nonce。
    """
    key = f"nonce:{nonce}"
    # SET ... NX 是原子操作，天然避免并发场景下的竞态问题
    is_new = r.set(key, "1", nx=True, ex=MAX_TIMESTAMP_SKEW + 60)
    return bool(is_new)
```

完整校验流程是三层依次判断，任何一层失败都直接拒绝请求：

```python
def authenticate_request(secret_key: str, method: str, path: str, body: str,
                          timestamp: int, nonce: str, signature: str) -> tuple:
    if not check_timestamp_window(timestamp):
        return False, "请求时间戳超出允许窗口"

    if not check_and_store_nonce(nonce, timestamp):
        return False, "nonce 已被使用，疑似重放攻击"

    if not verify_signature(secret_key, method, path, body, timestamp, nonce, signature):
        return False, "签名校验失败"

    return True, "ok"
```

## 四、密钥分发与轮换

签名机制的安全性完全依赖 `secret_key` 不泄露，密钥管理上有几个实践要点：

- **签名密钥和展示给用户的 API Key 分离**：API Key 用于计费和身份识别可以出现在日志里，签名密钥永远不落日志、不出现在错误信息里
- **支持密钥轮换而不中断服务**：给每个密钥加一个 `key_id`，请求头里带上 `key_id`，网关按 `key_id` 查找对应的 `secret_key` 做校验，轮换时新旧密钥并行有效一段时间，客户端逐步切换后再吊销旧密钥
- **密钥吊销要实时生效**：吊销操作不能依赖缓存过期，用 Redis 维护一个吊销列表，校验时先查吊销列表

```python
def is_key_revoked(key_id: str) -> bool:
    return r.sismember("revoked_keys", key_id)
```

## 五、性能考量：签名校验不能成为网关瓶颈

网关是所有请求的必经之路，签名校验逻辑跑在每一个请求上，性能设计上要注意：

- **HMAC-SHA256 计算本身很快**（微秒级），瓶颈通常在 Redis 的 nonce 查重上，用 pipeline 或者本地 LRU 缓存热点 key 可以减轻 Redis 压力
- **避免在校验失败时做过多日志 I/O**——被攻击时失败请求可能瞬间暴涨，同步写日志会拖垮整个网关，异步批量写或采样记录更稳妥
- **签名校验失败要限流而不是无限重试提示**，给出模糊的错误信息（"认证失败"而非"签名不匹配，你的时间戳是 xxx"），避免攻击者根据报错信息逐步试探出校验逻辑细节

## 六、相关阅读

- [自建 LLM 网关的路由实现：从零设计转发逻辑](/blog/llm-gateway-routing-implementation/)
- [AI API 中转的安全与合规边界](/blog/api-relay-security-compliance/)
- [LiteLLM 自部署网关中国区实践](/blog/litellm-cn-gateway-self-host/)
- [工具调用可靠性实测：Claude / GPT-5 / Gemini 谁更稳](/blog/llm-tool-call-reliability-bench/)

如果你不想自己维护这套签名与防重放体系，[YoTradeApi](https://yotradeapi.com) 已经把密钥管理、请求鉴权和多模型转发都做好了，直接接入即可，省去自建网关安全层的精力。
