[English](README.md) · **简体中文**

# 🐍 Python 学习路线助手

一个调用**大模型 API** 的 Web 应用：输入你的学习需求和现状，AI 生成个性化 Python 学习路线；内置分级**练手项目库**，并支持让 AI 按需生成新项目、扩展到任意语言（C、Java…）。路线生成时可接入**搜索 API** 查证真实资源，降低 AI 编造幻觉。

> 适合作为「AI 应用开发」方向的练手/简历项目：多模型可切换架构 + 可插拔搜索 + 结构化输出 + 完整前后端闭环。

## ✨ 功能特性

- **AI 学习路线规划**：填写基础 / 目标 / 时间 → 生成 4~6 阶段路线（知识点、练手项目、验收标准、参考资源、建议周数）
- **一句话顺带加项目**：描述需求时可直接说"另外帮我加 3 个 C 语言项目"，一次调用同时产出路线并自动入库，项目库即时刷新
- **内置项目库**：8 个分级 Python 练手项目（入门 / 进阶 / 实战），可浏览、筛选、标记完成、删除
- **AI 生成新项目**（两个入口）：① 路线需求里顺带要求（同上）；② 项目库下方的独立表单——输入任意语言和主题，AI 生成练手项目自动入库（例如：想学 C → 生成 C 语言指针练习项目）
- **多模型可切换**：DeepSeek / GPT / Claude / Kimi / 通义 / Grok / Gemini / 智谱 / 豆包方舟 / 本地模型，下拉即切
- **搜索增强（防幻觉）**：Tavily / SerpAPI 可插拔，把真实资料链接喂给模型要求其引用；不配 Key 自动降级为纯 LLM
- **数据本地存储**：SQLite，零服务器依赖，`python run.py` 一条命令启动

## 📸 界面预览

界面由两个卡片组成：

1. **生成学习路线**：文本框描述需求 → 点击「生成路线」→ 展示分阶段路线卡片（每阶段含知识点标签、练手项目、参考资源、验收标准、建议周数）。描述里可以顺带要求加项目（如"另外帮我加 3 个 C 语言项目"），生成后会提示"已新增 N 个项目到项目库"并自动刷新下方列表
2. **练手项目库**：按语言 / 难度筛选项目卡片（含知识点、验收标准），可勾选「已完成」；下方表单输入语言和主题，一键让 AI 生成新项目入库（独立入口，与路线里的顺带加项目互不干扰）

> 运行后可在本小节补充两张截图（建议：路线生成结果页、项目库 + AI 生成结果页）。

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- 一个大模型 API Key（推荐 DeepSeek，约 ¥10 可用很久；或用本地 llama.cpp / Ollama 零成本跑通）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API

```bash
copy .env.example .env      # Windows
# cp .env.example .env      # Linux / macOS
```

编辑 `.env`，填入任意一个 Provider 的 Key 即可，例如：

```ini
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

### 4. 启动

```bash
python run.py
```

浏览器打开 **http://127.0.0.1:8000**（接口文档在 http://127.0.0.1:8000/docs）。

## 🔌 支持的模型 API（多 Provider 可切换）

| Provider | 环境变量前缀 | 默认模型 | 备注 |
|---|---|---|---|
| DeepSeek | `DEEPSEEK_` | deepseek-flash | 便宜，推荐默认 |
| OpenAI | `OPENAI_` | gpt-6.1-sol | GPT 系列 |
| Anthropic | `ANTHROPIC_` | claude-sonnet-5-5 | 原生 Messages 协议，代码内自动分流 |
| Kimi | `MOONSHOT_` | kimi-k3 | 月之暗面（旧型号已下线） |
| 通义千问 | `DASHSCOPE_` | qwen3.8-max | 阿里云百炼 |
| Grok | `XAI_` | grok-4.7 | xAI，500K 上下文 |
| Gemini | `GEMINI_` | gemini-3.8-flash | Google，走官方 OpenAI 兼容层 |
| 智谱 GLM | `ZHIPU_` | glm-5.3-flash | 部分模型自带联网 |
| 豆包方舟 | `VOLC_` | doubao-seed-2.1-pro | 火山引擎 |
| 本地模型 | `LOCAL_` | qwen3.8-27b | llama.cpp / Ollama，无需 Key |

只需在 `.env` 填对应的 `XXX_API_KEY`（`LOCAL_` 除外），前端下拉即可切换。

其中 9 家走 **OpenAI 兼容协议**（openai SDK 直连，Gemini 用官方 `/v1beta/openai/` 兼容层）；Anthropic 是唯一例外——它的原生 Messages API（`POST /v1/messages` + `x-api-key` + `anthropic-version`）与 OpenAI 的 `/chat/completions` 不是一套协议，因此 `app/llm.py` 内按 `protocol` 字段分流到独立实现，**调用方代码零改动**。

> 模型型号更新换代很快，表中默认值是 2026-10 在售的主流型号。想换型号不用改代码：在 `.env` 里加一行 `XXX_MODEL=<型号>` 即可（见 `.env.example`）。

## 🔍 搜索配置（可选）

| 服务 | 环境变量 | 免费额度 |
|---|---|---|
| Tavily | `TAVILY_API_KEY` | 1000 次/月 |
| SerpAPI | `SERPAPI_API_KEY` | 100 次/月 |

- 配置任一即可启用「搜索增强」；都不配置时自动降级为纯 LLM 生成（功能完整可用）
- 使用自带联网的模型（如智谱 GLM、Kimi）时，也可以不配置搜索 Key

## 📁 项目结构

```
python-learning-assistant/
├── app/
│   ├── main.py          # FastAPI 入口与全部接口
│   ├── config.py        # 多 Provider 配置加载（.env）
│   ├── llm.py           # 大模型调用适配层（OpenAI 兼容 + Anthropic 原生分流）
│   ├── search.py        # 搜索增强层（Tavily / SerpAPI 可插拔）
│   ├── planner.py       # 学习路线生成（结构化 JSON 输出）
│   └── projects.py       # 项目库（SQLite + 种子数据 + AI 生成入库）
├── static/
│   └── index.html       # 单页前端（原生 HTML/CSS/JS，无构建步骤）
├── data/                # SQLite 数据库（运行时自动生成，已被 git 忽略）
├── run.py               # 一键启动：python run.py
├── requirements.txt
├── .env.example         # 环境变量模板（复制为 .env 使用）
├── README.md            # 英文版
└── README.zh-CN.md      # 中文版（本文件）
```

## ⚙️ 工作原理

```
用户输入学习需求（可顺带要求加项目）
      │
      ▼
[搜索增强层] ──(可选)──▶ Tavily / SerpAPI ──▶ 真实资料链接
      │                                        │
      ▼                                        ▼
[LLM 适配层] ◀── OpenAI 兼容协议 + Anthropic 原生协议 ◀── DeepSeek / GPT / Claude / 本地模型…
      │
      ▼
结构化 JSON（学习路线 + generated_projects）
      │
      ├──▶ 前端渲染学习路线
      └──▶ generated_projects 校验入库 → 项目库自动刷新
```

几个可讲的实现要点：

- **结构化输出**：通过 system prompt 把模型输出约束为固定 JSON schema，前端直接渲染，避免解析散文
- **复合需求一次搞定**：同一句话里"规划路线 + 加 N 个 XX 语言项目"，模型在一个 JSON 里同时输出，后端校验入库
- **防幻觉**：把搜索 API 返回的真实链接附进提示词，要求模型引用真实资源而非编造
- **多 Provider 抽象**：9 家 OpenAI 兼容端点直连，Anthropic 按原生协议分流，换模型只需改配置，业务代码零改动
- **降级策略**：搜索 Key 缺失、JSON 解析失败、`response_format` 不被支持、`generated_projects` 字段缺失时均有自动兜底，功能不中断

## ❓ 常见问题

- **报错「尚未配置 API Key」**：复制 `.env.example` 为 `.env`，填写对应 Provider 的 Key
- **想用本地模型**：下载 Qwen3.8-27B 的 GGUF（`Qwen/Qwen3.8-27B-GGUF`）后用 llama.cpp 启动，注意加 `--jinja`（Qwen3.8 的 chat template 依赖它，否则输出乱码）：

  ```bash
  llama-server -m qwen3.8-27b-q4_k_m.gguf --jinja -ngl 99 -c 32768 --port 8080
  ```

  Ollama 则 `ollama run qwen3.8:27b`；然后 `.env` 设 `LLM_PROVIDER=local`、`LOCAL_MODEL=<GGUF 文件名>`。
- **不想用搜索**：页面取消勾选「搜索增强」，或 `.env` 不填任何搜索 Key
- **生成很慢**：多为模型侧响应慢（本地 27B 模型尤甚），换 DeepSeek / GPT 等云端模型会快很多

## 📄 License

[MIT](LICENSE)
