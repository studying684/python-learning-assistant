# 🐍 Python 学习路线助手 · Python Learning Path Assistant

**简体中文** · [English](#english)

---

## 简体中文

一个调用**大模型 API** 的 Web 应用：输入你的学习需求和现状，AI 生成个性化 Python 学习路线；内置分级**练手项目库**，并支持让 AI 按需生成新项目、扩展到任意语言（C、Java…）。路线生成时可接入**搜索 API** 查证真实资源，降低 AI 编造幻觉。

> 适合作为「AI 应用开发」方向的练手/简历项目：多模型可切换架构 + 可插拔搜索 + 结构化输出 + 完整前后端闭环。

### ✨ 功能特性

- **AI 学习路线规划**：填写基础 / 目标 / 时间 → 生成 4~6 阶段路线（知识点、练手项目、验收标准、参考资源、建议周数）
- **一句话顺带加项目**：描述需求时可直接说"另外帮我加 3 个 C 语言项目"，一次调用同时产出路线并自动入库，项目库即时刷新
- **内置项目库**：8 个分级 Python 练手项目（入门 / 进阶 / 实战），可浏览、筛选、标记完成、删除
- **AI 生成新项目**（两个入口）：① 路线需求里顺带要求（同上）；② 项目库下方的独立表单——输入任意语言和主题，AI 生成练手项目自动入库（例如：想学 C → 生成 C 语言指针练习项目）
- **多模型可切换**：DeepSeek / GPT / Claude / Kimi / 通义 / Grok / Gemini / 智谱 / 豆包方舟 / 本地模型，下拉即切
- **搜索增强（防幻觉）**：Tavily / SerpAPI 可插拔，把真实资料链接喂给模型要求其引用；不配 Key 自动降级为纯 LLM
- **数据本地存储**：SQLite，零服务器依赖，`python run.py` 一条命令启动

### 📸 界面预览

界面由两个卡片组成：

1. **生成学习路线**：文本框描述需求 → 点击「生成路线」→ 展示分阶段路线卡片（每阶段含知识点标签、练手项目、参考资源、验收标准、建议周数）。描述里可以顺带要求加项目（如"另外帮我加 3 个 C 语言项目"），生成后会提示"已新增 N 个项目到项目库"并自动刷新下方列表
2. **练手项目库**：按语言 / 难度筛选项目卡片（含知识点、验收标准），可勾选「已完成」；下方表单输入语言和主题，一键让 AI 生成新项目入库（独立入口，与路线里的顺带加项目互不干扰）

> 运行后可在本小节补充两张截图（建议：路线生成结果页、项目库 + AI 生成结果页）。

### 🚀 快速开始

#### 1. 环境要求

- Python 3.10+
- 一个大模型 API Key（推荐 DeepSeek，约 ¥10 可用很久；或用本地 llama.cpp / Ollama 零成本跑通）

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

开发（跑测试）额外装：

```bash
pip install -r requirements-dev.txt
```

#### 3. 配置 API

```bash
copy .env.example .env      # Windows
# cp .env.example .env      # Linux / macOS
```

编辑 `.env`，填入任意一个 Provider 的 Key 即可，例如：

```ini
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

#### 4. 启动

```bash
python run.py
```

启动参数：

```bash
python run.py                              # 正常启动（默认不开热重载）
python run.py --reload                     # 开发模式：改代码自动重启
python run.py --host 0.0.0.0 --port 9000   # 允许局域网访问
```

浏览器打开 **http://127.0.0.1:8000**（接口文档在 http://127.0.0.1:8000/docs）。

### 🔌 支持的模型 API（多 Provider 可切换）

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

### 🔍 搜索配置（可选）

| 服务 | 环境变量 | 免费额度 |
|---|---|---|
| Tavily | `TAVILY_API_KEY` | 1000 次/月 |
| SerpAPI | `SERPAPI_API_KEY` | 100 次/月 |

- 配置任一即可启用「搜索增强」；都不配置时自动降级为纯 LLM 生成（功能完整可用）
- 使用自带联网的模型（如智谱 GLM、Kimi）时，也可以不配置搜索 Key

### 📁 项目结构

```
python-learning-assistant/
├── app/
│   ├── main.py          # FastAPI 入口与全部接口
│   ├── config.py        # 多 Provider 配置加载（.env）
│   ├── llm.py           # 大模型调用适配层（OpenAI 兼容 + Anthropic 原生分流）
│   ├── search.py        # 搜索增强层（Tavily / SerpAPI 可插拔）
│   ├── planner.py       # 学习路线生成（结构化 JSON 输出）
│   └── projects.py      # 项目库（SQLite + 种子数据 + AI 生成入库）
├── static/
│   └── index.html       # 单页前端（原生 HTML/CSS/JS，无构建步骤）
├── tests/               # pytest 测试（不打包，仅开发用）
│   ├── conftest.py      # 把数据库重定向到临时目录的 fixture
│   ├── test_config.py   # Provider 注册表完整性
│   ├── test_llm.py      # 协议分流 / Key 检查 / 错误包装（离线）
│   ├── test_planner.py  # JSON 抽取 + pydantic 兜底校验
│   ├── test_projects.py # 项目库 CRUD + 难度归一 + 连接复用
│   ├── test_search.py   # 搜索鉴权头与失败降级
│   ├── test_api.py      # TestClient 打真实路由
│   └── test_frontend.py # 前端静态断言（零构建 / 无 alert-confirm）
├── data/                # SQLite 数据库（运行时自动生成，已被 git 忽略）
├── run.py               # 一键启动：python run.py（--reload / --host / --port）
├── requirements.txt     # 应用依赖（版本锁定）
├── requirements-dev.txt # 测试依赖
├── pytest.ini
├── .github/workflows/ci.yml  # GitHub Actions：3.10/3.11/3.12 跑测试
├── .env.example         # 环境变量模板（复制为 .env 使用）
└── README.md            # 本文件（中英双语）
```

### ⚙️ 工作原理

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

- **结构化输出**：system prompt 约束 JSON schema，再用 pydantic 模型兜底校验，坏输出在入口就被拦住并转成可读错误，不会带到前端
- **生命周期**：数据库初始化放在 FastAPI lifespan 里，`uvicorn --reload` 与测试导入都不会重复执行
- **单连接 + 锁**：SQLite 连接在进程内复用，读写用 `threading.RLock` 串行化——单机单用户场景下省掉每请求的开销，也避免并发写触发 `database is locked`
- **前端零构建**：单文件 HTML，CSS/JS 全内联；交互层自绘提示条与确认框替代原生 `alert/confirm`，不阻塞渲染、样式统一
- **复合需求一次搞定**：同一句话里"规划路线 + 加 N 个 XX 语言项目"，模型在一个 JSON 里同时输出，后端校验入库
- **防幻觉**：把搜索 API 返回的真实链接附进提示词，要求模型引用真实资源而非编造
- **多 Provider 抽象**：9 家 OpenAI 兼容端点直连，Anthropic 按原生协议分流，换模型只需改配置，业务代码零改动
- **降级策略**：搜索 Key 缺失、JSON 解析失败、`response_format` 不被支持、`generated_projects` 字段缺失时均有自动兜底，功能不中断；搜索源失败只写一行 stderr 日志并自动降级为纯 LLM
- **调试口默认关闭**：`GET /api/search` 会直接消耗搜索 API 配额，默认不注册（返回 404），只在 `.env` 写 `DEBUG_ENDPOINTS=1` 时启用
- **依赖锁定与 CI**：`requirements.txt` 锁死精确版本，任何机器 `pip install` 结果一致；GitHub Actions 在 Python 3.10/3.11/3.12 三个版本上跑 pytest，改动不会悄悄破坏兼容性

### ❓ 常见问题

- **报错「尚未配置 API Key」**：复制 `.env.example` 为 `.env`，填写对应 Provider 的 Key
- **想用本地模型**：下载 Qwen3.8-27B 的 GGUF（`Qwen/Qwen3.8-27B-GGUF`）后用 llama.cpp 启动，注意加 `--jinja`（Qwen3.8 的 chat template 依赖它，否则输出乱码）：

  ```bash
  llama-server -m qwen3.8-27b-q4_k_m.gguf --jinja -ngl 99 -c 32768 --port 8080
  ```

  Ollama 则 `ollama run qwen3.8:27b`；然后 `.env` 设 `LLM_PROVIDER=local`、`LOCAL_MODEL=<GGUF 文件名>`。
- **不想用搜索**：页面取消勾选「搜索增强」，或 `.env` 不填任何搜索 Key
- **生成很慢**：多为模型侧响应慢（本地 27B 模型尤甚），换 DeepSeek / GPT 等云端模型会快很多
- **改了代码想自动重启**：`python run.py --reload`；正式跑不要开，会多起一个看门狗进程
- **提示 `database is locked`**：正常不会出现（读写已加锁串行化）；若是用其他工具直接打开了 `data/learning.db` 并持有写事务，关掉那个工具即可

### 📄 License

[MIT](LICENSE)

### 🧪 运行测试

```bash
pip install -r requirements-dev.txt
pytest
```

测试全部离线，不调用任何真实 API（httpx/openai 调用用测试替身），也不碰你的 `data/learning.db`（数据库被重定向到 pytest 临时目录）。CI 见 [`.github/workflows/ci.yml`](.github/workflows/ci.yml)。

---

## English

A web app built on **LLM APIs**: describe what you already know and what you want to learn, and the AI generates a personalized Python learning path. It ships with a graded **hands-on project library** and can generate new projects on demand — in any language (C, Java, …). Path generation can optionally call a **search API** to ground its references in real links, which reduces hallucination.

> A good practice / portfolio project for the "AI application development" track: a multi-provider architecture + pluggable search + structured output + a complete front-end/back-end loop.

### ✨ Features

- **AI learning-path planning**: fill in your background / goal / time budget → get a 4–6 stage path (topics, hands-on project, acceptance criteria, references, suggested number of weeks)
- **Ask for projects in the same sentence**: say "also add 3 C projects" while describing your goal, and a single call returns both the path and the new projects, which are stored and show up immediately
- **Built-in project library**: 8 graded Python projects (beginner / intermediate / advanced) you can browse, filter, mark as done and delete
- **AI-generated projects** (two entry points): (1) ask for them as part of the path request (above); (2) use the standalone form under the library — pick any language and topic, and generated projects are stored automatically (e.g. learning C → generate pointer exercises)
- **Swappable model providers**: DeepSeek / GPT / Claude / Kimi / Qwen / Grok / Gemini / Zhipu GLM / Doubao Ark / local models — switch from a dropdown
- **Search augmentation (anti-hallucination)**: pluggable Tavily / SerpAPI; real links are fed into the prompt and the model is required to cite them; falls back to a plain LLM call when no key is configured
- **Local storage**: SQLite, no server dependencies, one command to start (`python run.py`)

### 📸 UI preview

The UI is two cards:

1. **Generate a learning path**: describe your goal in the text box → click "生成路线" → a staged path is rendered (each stage carries topic tags, a hands-on project, references, acceptance criteria and a suggested week count). You can ask for extra projects in the same sentence (e.g. "also add 3 C projects"); afterwards a notice reports "N projects added to the library" and the list below refreshes automatically.
2. **Hands-on project library**: filter project cards by language / difficulty (each card lists topics and acceptance criteria) and tick "done" when finished. The form below takes a language and a topic and asks the AI to generate new projects into the library — an independent entry point that does not interfere with the in-path project generation.

> Two screenshots can be added here once you have run it (suggested: a generated path, and the library right after AI generation).

### 🚀 Quick start

#### 1. Requirements

- Python 3.10+
- One LLM API key (DeepSeek recommended — about ¥10 lasts a long time; or run it for free against a local llama.cpp / Ollama server)

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

For development (running the tests):

```bash
pip install -r requirements-dev.txt
```

#### 3. Configure the API

```bash
copy .env.example .env      # Windows
# cp .env.example .env      # Linux / macOS
```

Edit `.env` and fill in the key of any single provider, for example:

```ini
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

#### 4. Start

```bash
python run.py
```

Then open **http://127.0.0.1:8000** (API docs at http://127.0.0.1:8000/docs).

Command-line options:

```bash
python run.py                              # normal start (auto-reload is off by default)
python run.py --reload                     # dev mode: restart when files change
python run.py --host 0.0.0.0 --port 9000   # expose the app to your LAN
```

### 🔌 Supported model APIs (switchable providers)

| Provider | Env prefix | Default model | Notes |
|---|---|---|---|
| DeepSeek | `DEEPSEEK_` | deepseek-flash | Cheap; recommended default |
| OpenAI | `OPENAI_` | gpt-6.1-sol | GPT family |
| Anthropic | `ANTHROPIC_` | claude-sonnet-5-5 | Native Messages protocol, dispatched automatically |
| Kimi | `MOONSHOT_` | kimi-k3 | Moonshot AI (older models retired) |
| Qwen | `DASHSCOPE_` | qwen3.8-max | Alibaba Cloud Bailian |
| Grok | `XAI_` | grok-4.7 | xAI, 500K context |
| Gemini | `GEMINI_` | gemini-3.8-flash | Google, via the official OpenAI-compatible layer |
| Zhipu GLM | `ZHIPU_` | glm-5.3-flash | Some models have built-in web access |
| Doubao Ark | `VOLC_` | doubao-seed-2.1-pro | Volcengine |
| Local models | `LOCAL_` | qwen3.8-27b | llama.cpp / Ollama, no API key needed |

Just set the matching `XXX_API_KEY` in `.env` (`LOCAL_` excepted), then pick the provider from the dropdown.

Nine of them speak the **OpenAI-compatible protocol** (called directly through the openai SDK; Gemini goes through the official `/v1beta/openai/` compatibility layer). Anthropic is the one exception — its native Messages API (`POST /v1/messages` + `x-api-key` + `anthropic-version`) is a different protocol from OpenAI's `/chat/completions`, so `app/llm.py` dispatches on a `protocol` field to a separate implementation, **with zero changes to calling code**.

> Model names turn over fast; the defaults above are mainstream models on sale in 2026-10. You don't need to touch code to change one: add `XXX_MODEL=<model-id>` to `.env` (see `.env.example`).

### 🔍 Search configuration (optional)

| Service | Env var | Free tier |
|---|---|---|
| Tavily | `TAVILY_API_KEY` | 1,000 calls / month |
| SerpAPI | `SERPAPI_API_KEY` | 100 calls / month |

- Configuring either one enables "search augmentation"; with neither, the app degrades to plain LLM generation (still fully functional)
- Models with built-in web access (e.g. Zhipu GLM, Kimi) also let you skip the search key

### 📁 Project layout

```
python-learning-assistant/
├── app/
│   ├── main.py          # FastAPI entry point and all endpoints
│   ├── config.py        # Multi-provider configuration (.env)
│   ├── llm.py           # LLM adapter (OpenAI-compatible + native Anthropic)
│   ├── search.py        # Search augmentation (pluggable Tavily / SerpAPI)
│   ├── planner.py       # Learning-path generation (structured JSON output)
│   └── projects.py      # Project library (SQLite + seeds + AI-generated rows)
├── static/
│   └── index.html       # Single-page front end (vanilla HTML/CSS/JS, no build step)
├── tests/               # pytest suite (dev only, not packaged)
│   ├── conftest.py      # Fixture redirecting the database to a temp dir
│   ├── test_config.py   # Provider registry integrity
│   ├── test_llm.py      # Protocol dispatch / key checks / error wrapping (offline)
│   ├── test_planner.py  # JSON extraction + pydantic validation
│   ├── test_projects.py # CRUD + difficulty normalisation + connection reuse
│   ├── test_search.py   # Auth headers and failure fallback
│   ├── test_api.py      # Real routes through TestClient
│   └── test_frontend.py # Static assertions (no build step, no alert/confirm)
├── data/                # SQLite database (created at runtime, git-ignored)
├── run.py               # Launcher: python run.py (--reload / --host / --port)
├── requirements.txt     # Runtime dependencies (pinned)
├── requirements-dev.txt # Test dependencies
├── pytest.ini
├── .github/workflows/ci.yml  # GitHub Actions: tests on 3.10 / 3.11 / 3.12
├── .env.example         # Environment template (copy to .env)
└── README.md            # This file (bilingual)
```

### ⚙️ How it works

```
User describes what they want to learn (optionally asking for projects)
      │
      ▼
[Search layer] ──(optional)──▶ Tavily / SerpAPI ──▶ real reference links
      │                                              │
      ▼                                              ▼
[LLM adapter] ◀── OpenAI-compatible + native Anthropic ◀── DeepSeek / GPT / Claude / local…
      │
      ▼
Structured JSON (learning path + generated_projects)
      │
      ├──▶ front end renders the path
      └──▶ generated_projects validated and stored → library refreshes
```

A few implementation points worth talking about:

- **Structured output**: the system prompt pins a JSON schema and pydantic models act as a second gate — bad output is rejected at the boundary and turned into a readable error instead of reaching the front end
- **Lifespan**: database initialisation lives in FastAPI's lifespan, so neither `uvicorn --reload` nor a test import runs it twice
- **One connection + a lock**: the SQLite connection is reused process-wide and reads/writes are serialised with `threading.RLock` — for a single-user desktop app this removes the per-request connect cost and avoids `database is locked` under concurrent writes
- **Zero-build front end**: a single HTML file with inline CSS/JS; a hand-rolled toast and confirm dialog replace native `alert/confirm`, so nothing blocks rendering and styling stays consistent
- **Compound requests in one shot**: "plan a path + add N projects in language X" is answered in a single JSON, then validated and stored by the backend
- **Anti-hallucination**: real links returned by the search API are embedded in the prompt, and the model is asked to cite them rather than invent resources
- **Multi-provider abstraction**: nine OpenAI-compatible endpoints are called directly and Anthropic is dispatched to its native protocol — switching models is a config change, with no changes to business code
- **Graceful degradation**: a missing search key, a JSON parse failure, an unsupported `response_format` or a missing `generated_projects` field all fall back automatically, so functionality never breaks; a failing search source only writes one line to stderr and degrades to a plain LLM call
- **Debug endpoint off by default**: `GET /api/search` burns search quota, so it is not registered at all by default (404) and only appears when `DEBUG_ENDPOINTS=1` is set in `.env`
- **Pinned dependencies and CI**: `requirements.txt` pins exact versions so `pip install` resolves identically everywhere, and GitHub Actions runs pytest on Python 3.10 / 3.11 / 3.12 so changes cannot silently break compatibility

### ❓ FAQ

- **"No API key configured" error**: copy `.env.example` to `.env` and fill in the key for the matching provider
- **I want to use a local model**: download the Qwen3.8-27B GGUF (`Qwen/Qwen3.8-27B-GGUF`) and start it with llama.cpp. Remember `--jinja` (Qwen3.8's chat template depends on it; without it the output is garbled):

  ```bash
  llama-server -m qwen3.8-27b-q4_k_m.gguf --jinja -ngl 99 -c 32768 --port 8080
  ```

  With Ollama, run `ollama run qwen3.8:27b` instead; then set `LLM_PROVIDER=local` and `LOCAL_MODEL=<gguf file name>` in `.env`.
- **I don't want search**: untick "search augmentation" in the UI, or leave every search key empty in `.env`
- **Generation is slow**: usually model-side latency (especially a local 27B model); a cloud model such as DeepSeek or GPT is much faster
- **I changed the code and want a restart**: `python run.py --reload`; don't use it for a real run — it spawns an extra watchdog process
- **`database is locked`**: it should not happen (reads and writes are serialised by a lock); if another tool has `data/learning.db` open while holding a write transaction, close that tool

### 📄 License

[MIT](LICENSE)

### 🧪 Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite is fully offline: no real API is called (httpx/openai are stubbed) and your `data/learning.db` is never touched (the database is redirected to a pytest temp directory). See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for CI.

---

<sub>中文版见上方 [简体中文](#简体中文) 小节；若两种语言表述有出入，以中文版为准。· The Chinese version is the [简体中文](#简体中文) section above; if the two ever disagree, the Chinese one is authoritative.</sub>
