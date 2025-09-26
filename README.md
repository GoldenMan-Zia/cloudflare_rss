# Cloudflare Blog 自动化播报机器人

该项目提供一个可部署的工作流，用于自动监控 Cloudflare Blog RSS、拉取原文、生成中文简报，并通过企业微信机器人推送到团队群。

## 功能流程

1. **轮询 RSS**：使用 `feedparser` 获取 Cloudflare Blog 最新文章。
2. **去重入库**：使用 SQLite 记录已处理文章，避免重复推送。
3. **抓取正文**：下载博客 HTML 并提取主要内容。
4. **AI 简报**：调用 OpenAI API（或使用内置回退逻辑）生成中文摘要。
5. **消息推送**：通过企业微信 Webhook 发送 Markdown 消息，包含摘要与原文链接。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 设置 OPENAI_API_KEY 与 WECOM_WEBHOOK
python src/main.py
```


运行脚本后会自动创建/更新 SQLite 数据库 `cloudflare_blog.db` 并推送新增文章。首次同步时，所有历史文章都会入库，但仅会为最新的若干篇（默认 5 篇，可配置）生成摘要并推送，以避免刷屏。

## 配置项

通过环境变量或 `.env` 文件（例如使用 `direnv` / `docker` 传入）配置：

| 变量名 | 说明 |
| --- | --- |
| `CF_BLOG_FEED` | RSS 地址，默认 `https://blog.cloudflare.com/rss/` |
| `CF_BLOG_DB` | SQLite 数据库存储路径 |
| `OPENAI_API_KEY` | OpenAI API Key，用于生成中文摘要 |
| `LLM_API_URL` | （可选）自定义 LLM HTTP 接口地址，设置后将优先使用该接口 |
| `LLM_API_KEY` | （可选）自定义 LLM 的鉴权 Token，将自动加到 `Authorization: Bearer` 头中 |
| `LLM_MODEL` | （可选）自定义 LLM 模型名称；对 OpenAI 与自定义接口同时生效 |
| `LLM_MESSAGE_KEY` | （可选）自定义接口中承载对话内容的字段名，默认为 `messages` |
| `WECOM_WEBHOOK` | 企业微信机器人 webhook URL |
| `CF_BLOG_INITIAL_SUMMARY_LIMIT` | 首次同步时生成并推送摘要的最大文章数，默认为 5 |

### 使用自定义 LLM 接口

当需要接入非 OpenAI 的模型服务时，只需提供兼容的 HTTP Chat Completion 接口。例如以下 EdgeFn API：

```python
import requests

url = "https://api.edgefn.net/v1/chat/completions"
headers = {
    "Authorization": "Bearer <YOUR_API_KEY>",
    "Content-Type": "application/json",
}
data = {
    "model": "Qwen3-Next-80B-A3B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}],
}
```

在 `.env` 中设置：

```dotenv
LLM_API_URL=https://api.edgefn.net/v1/chat/completions
LLM_API_KEY=<YOUR_API_KEY>
LLM_MODEL=Qwen3-Next-80B-A3B-Instruct
LLM_MESSAGE_KEY=messages
```

程序会按照上述配置自动构造 `POST` 请求并解析常见的 `choices[].message.content`、`choices[].text`、`output_text` 等字段返回的摘要。如果接口返回非标准结构，可在 `_extract_text_from_response` 中扩展解析逻辑。

## 部署建议

### 1. 定时任务

* **Cron / systemd timer**：在 Linux 服务器上创建 cron 任务，每 10 分钟运行一次 `python /app/src/main.py`。
* **GitHub Actions / Cloudflare Workers Cron Triggers**：如果希望云端运行，可将项目容器化并部署到支持定时任务的平台。

### 2. 容器化

建议使用 Docker 镜像部署，示例 `Dockerfile` 如下：

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src

CMD ["python", "src/main.py"]
```

构建并运行：

```bash
docker build -t cloudflare-rss-bot .
docker run --env-file .env -v $(pwd)/data:/app/data cloudflare-rss-bot
```

将 `CF_BLOG_DB` 设置为 `/app/data/cloudflare_blog.db` 可实现持久化。

### 3. 环境安全

* 使用密钥管理服务（如 1Password Connect、AWS Secrets Manager）注入 `OPENAI_API_KEY` 与 `WECOM_WEBHOOK`。
* 为运行容器的机器限制网络访问，仅允许访问 Cloudflare Blog、OpenAI API 与企业微信域名。

### 4. 监控与告警

* 将日志输出重定向到集中式日志系统（如 CloudWatch、ELK）。
* 为企业微信推送失败设置重试或告警逻辑，以保证重要信息送达。

## 结构

```
src/
├── cloudflare_bot/
│   ├── article.py        # 抓取与解析正文
│   ├── config.py         # 读取环境配置
│   ├── notifier.py       # 企业微信推送
│   ├── rss.py            # RSS 解析
│   ├── storage.py        # SQLite 持久化
│   ├── summarizer.py     # 中文摘要生成
│   └── __init__.py
└── main.py               # 工作流入口
```

## 后续扩展

* 将摘要与原文存入知识库，支持历史检索。
* 引入异步队列（Celery/Cloud Tasks）处理高并发推送。
* 对接更多渠道（邮件、飞书等）分发摘要。
