---
title: Open WebUI 自托管聊天界面国内接入教程
description: Open WebUI 自托管 LLM 前端在国内通过中转的接入方法，含 Docker 部署、模型管理、RAG、用户体系完整配置。
keywords:
- open webui 国内
- open webui 配置
- open webui docker
- 自托管 llm
- open webui 中转
pubDate: '2026-05-19'
updatedDate: '2026-05-19'
canonical: https://blog.yotradeapi.com/blog/open-webui-cn-setup/
tags:
- Open WebUI
- 自托管
- Docker
- API 中转
- 配置教程
category: 工具配置
heroImage: ../../assets/blog-placeholder-5.jpg
---

# Open WebUI 自托管聊天界面国内接入教程

Open WebUI（前身 Ollama WebUI）是开源的 LLM 聊天界面，特点是「自托管、多用户、RAG 内置、UI 类似 ChatGPT」。对家庭 / 小团队提供"一个内部 ChatGPT"非常合适。本文给国内部署完整流程。

## 一、最小 Docker 部署

```bash
docker run -d \
  --name open-webui \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  -e OPENAI_API_BASE_URL=https://yotradeapi.com/v1 \
  -e OPENAI_API_KEY=sk-yo-... \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

启动后访问 `http://localhost:3000`。第一次注册的账号自动成为管理员。

## 二、关键环境变量

| 变量 | 作用 |
| --- | --- |
| `OPENAI_API_BASE_URL` | OpenAI 兼容 endpoint |
| `OPENAI_API_KEY` | API key |
| `WEBUI_AUTH` | 是否需要登录（true/false） |
| `WEBUI_NAME` | 站点名 |
| `WEBUI_URL` | 公网 URL（用于邀请链接） |
| `ENABLE_SIGNUP` | 是否允许注册 |
| `DEFAULT_MODELS` | 默认模型列表 |

家庭部署关 signup：

```bash
-e ENABLE_SIGNUP=false
```

需要登录、不允许公开：

```bash
-e WEBUI_AUTH=true
-e ENABLE_SIGNUP=false
```

## 三、多个 Provider

设置 → 管理员 → 模型 → 连接：

```
Provider 1:
  Name: YoTrade
  URL: https://yotradeapi.com/v1
  Key: sk-yo-...

Provider 2:
  Name: Local Ollama
  URL: http://host.docker.internal:11434/v1
  Key: ollama
```

同一界面切换云端 / 本地模型。

## 四、自动同步模型列表

Open WebUI 启动后自动 GET `/models` 拉网关的模型列表。如果中转的 `/models` 端点返回的不是 OpenAI 标准格式，模型选择下拉框可能为空。

**变通办法**：手动添加。设置 → 管理员 → 模型 → 添加：

```
Model ID: claude-sonnet-4-6
Display Name: Claude Sonnet 4.6
```

## 五、Pipelines 与函数

Open WebUI 支持插件（Pipelines）：

- 输入过滤
- 输出后处理
- RAG 自动注入
- 自定义工具调用

部署 pipelines 容器：

```bash
docker run -d \
  --name pipelines \
  -p 9099:9099 \
  -v pipelines:/app/pipelines \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/open-webui/pipelines:main
```

在 Open WebUI 设置里关联 pipelines URL。

## 六、RAG（知识库）

Open WebUI 内置文档上传与检索：

1. 主界面右上角"工作空间" → "知识库" → 新建
2. 上传 PDF / Markdown / 文本
3. 等索引完成（默认用 `text-embedding-3-small`）
4. 对话里 `#知识库名` 引用

embedding 模型也走中转：设置 → 文档 → Embedding 模型选 `text-embedding-3-large`。

## 七、用户与权限

管理员可以：

- 邀请用户
- 设置角色（admin / user / pending）
- 限制每个用户能用哪些模型
- 限制每个用户的日预算（通过 Pipelines）

家庭场景：admin 一个、家人各一个用户。

## 八、Nginx 反向代理

公网访问要走 HTTPS：

```nginx
server {
    listen 443 ssl http2;
    server_name chat.example.com;

    ssl_certificate /etc/letsencrypt/live/chat.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;          # 关键：保证 SSE
        proxy_read_timeout 600;       # 长任务别提前断
    }
}
```

`proxy_buffering off` 与长 `proxy_read_timeout` 是流式输出可用的前提。

## 九、备份

Open WebUI 所有数据存在 `/app/backend/data`（容器内）：

```bash
docker run --rm \
  -v open-webui:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/openwebui-$(date +%F).tar.gz -C /data .
```

每周跑一次，存到云端。

## 十、与 ChatBox / Cherry Studio 的差异

| 维度 | Open WebUI | ChatBox | Cherry Studio |
| --- | --- | --- | --- |
| 形态 | Web | 桌面 | 桌面 |
| 多用户 | ✓ | ✗ | ✗ |
| 远程访问 | ✓ | ✗ | ✗ |
| RAG | ✓ | 部分 | ✓ |
| MCP | 部分 | 部分 | ✓ |
| 部署难度 | 中（Docker） | 低 | 低 |

Open WebUI 的优势是 **多用户 + 远程访问**。家庭一台服务器跑一个，所有人共享。

## 十一、典型部署架构

```
你的家用 NAS / 小服务器
├── Docker
│   ├── open-webui          (3000)
│   ├── pipelines           (9099)
│   ├── nginx               (443)
│   └── postgres (可选)
└── Cloudflare Tunnel       (公网入口)
```

通过 Cloudflare Tunnel 让你的家用服务器不开放公网端口也能被访问，非常省心。

## 十二、常见问题

| 问题 | 解决 |
| --- | --- |
| 启动后模型列表空 | 手动添加模型 |
| SSE 流式断 | nginx `proxy_buffering off` |
| 文件上传 413 | nginx `client_max_body_size 100M` |
| Docker 没法访问 host.docker.internal | `--add-host=host.docker.internal:host-gateway` |
| 中转 429 | 给 Open WebUI 用的 Key 单独设较低预算保护 |

## 十三、相关阅读

- [Cherry Studio 国内 API 中转配置指南](/blog/cherry-studio-cn-config/)
- [Continue.dev 国内 API 配置](/blog/continue-dev-cn-setup/)
- [OpenAI SDK base_url 国内配置实战](/blog/openai-sdk-base-url-cn/)
- [中文 RAG 工程实战](/blog/rag-cn-best-practices/)

需要一把 Key 支持 chat + embedding + 多模型的中转给 Open WebUI 用？[YoTradeApi](https://yotradeapi.com) 创建独立 Key 后按上面 docker 命令直接接入。
