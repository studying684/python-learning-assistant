# 🐍 Python 学习路线助手 · Python Learning Path Assistant

[简体中文](README.zh-CN.md) · **English**

> If the two versions ever disagree, the Chinese one ([README.zh-CN.md](README.zh-CN.md)) is authoritative.

---

A web app built on **LLM APIs**: describe what you already know and what you want to learn, and the AI generates a personalized Python learning path. It ships with a graded **hands-on project library** and can generate new projects on demand — in any language (C, Java, …). Path generation can optionally call a **search API** to ground its references in real links, which reduces hallucination.

> A good practice / portfolio project for the "AI application development" track: a multi-provider architecture + pluggable search + structured output + a complete front-end/back-end loop.

> **A note on language** — this README is bilingual, but the web UI, the AI prompts and the code comments are currently **in Chinese**: the app is built for Chinese-speaking learners. The API, the architecture and the provider layer are language-agnostic, so an English UI is a welcome first contribution (open an issue and I'll help you scope it).

## ✨ Features

- **AI learning-path planning**: fill in your background / goal / time budget → get a 4–6 stage path (topics, hands-on project, acceptance criteria, references, suggested number of weeks)
- **Ask for projects in the same sentence**: say "also add 3 C projects" while describing your goal, and a single call returns both the path and the new projects, which are stored and show up immediately
- **Built-in project library**: 8 graded Python projects (beginner / intermediate / advanced) you can browse, filter, mark as done and delete
- **AI-generated projects** (two entry points): (1) ask for them as part of the path request (above); (2) use the standalone form under the library — pick any language and topic, and generated projects are stored automatically (e.g. learning C → generate pointer exercises)
- **Swappable model providers**: DeepSeek / GPT / Claude / Kimi / Qwen / Grok / Gemini / Zhipu GLM / Doubao Ark / local models — switch from a dropdown
- **Search augmentation (anti-hallucination)**: pluggable Tavily / SerpAPI; real links are fed into the prompt and the model is required to cite them; falls back to a plain LLM call when no key is configured
- **Local storage**: SQLite, no server dependencies, one command to start (`python run.py`)

## 📸 UI preview

The UI is two cards:

1. **Generate a learning path**: describe your goal in the text box → click "生成路线" → a staged path is rendered (each stage carries topic tags, a hands-on project, references, acceptance criteria and a suggested week count). You can ask for extra projects in the same sentence (e.g. "also add 3 C projects"); afterwards a notice reports "N projects added to the library" and the list below refreshes automatically.
2. **Hands-on project library**: filter project cards by language / difficulty (each card lists topics and acceptance criteria) and tick "done" when finished. The form below takes a language and a topic and asks the AI to generate new projects into the library — an independent entry point that does not interfere with the in-path project generation.

> Two screenshots can be added here once you have run it (suggested: a generated path, and the library right after AI generation).

## 🚀 Quick start

### 1. Requirements

- Python 3.10+
- One LLM API key (DeepSeek recommended — about ¥10 lasts a long time; or run it for free against a local llama.cpp / Ollama server)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

For development (running the tests):

```bash
pip install -r requirements-dev.txt
```

### 3. Configure the API

```bash
copy .env.example .env      # Windows
# cp .env.example .env      # Linux / macOS
```

Edit `.env` and fill in the key of any single provider, for example:

```ini
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

### 4. Start

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

## 🔌 Supported model APIs (switchable providers)

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

## 🔍 Search configuration (optional)

| Service | Env var | Free tier |
|---|---|---|
| Tavily | `TAVILY_API_KEY` | 1,000 calls / month |
| SerpAPI | `SERPAPI_API_KEY` | 100 calls / month |

- Configuring either one enables "search augmentation"; with neither, the app degrades to plain LLM generation (still fully functional)
- Models with built-in web access (e.g. Zhipu GLM, Kimi) also let you skip the search key

## 📁 Project layout

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
├── README.md            # English docs (this file)
└── README.zh-CN.md      # Chinese docs (简体中文)
```

## ⚙️ How it works

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

## ❓ FAQ

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

## 📄 License

[MIT](LICENSE)

## 🧪 Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite is fully offline: no real API is called (httpx/openai are stubbed) and your `data/learning.db` is never touched (the database is redirected to a pytest temp directory). See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for CI.
