"""配置加载模块：从 .env 读取所有 API 凭据与偏好设置。

本项目的核心设计是「多 Provider 可切换」：
- 主流大模型服务（OpenAI、DeepSeek、Kimi、通义千问、智谱 GLM、豆包方舟、
  Grok、Gemini、本地 llama.cpp/Ollama）都支持 OpenAI 兼容协议，切换只需改
  base_url / api_key / model 三个配置项，业务代码不用动；
- Anthropic 是唯一的例外：它的原生 Messages API（POST /v1/messages）与
  OpenAI 协议不兼容，因此这里用 protocol 字段标记，由 llm.py 自动分流，
  上层调用方依然零改动。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（python-learning-assistant/）
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载 .env（文件不存在时静默跳过，此时除本地模型外所有 Provider 不可用）
load_dotenv(BASE_DIR / ".env")

# 默认使用的模型 Provider（可通过 .env 中的 LLM_PROVIDER 覆盖）
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").strip().lower()

# 支持的 Provider 注册表。
# env_prefix：该服务在 .env 中使用的环境变量前缀，例如 DEEPSEEK_API_KEY。
# protocol：openai = 走 OpenAI 兼容协议（openai SDK 直连）；
#           anthropic = 走 Anthropic 原生 Messages 协议（llm.py 内部分流）。
# default_model：2026-10 在售的主流型号，均可被 <PREFIX>_MODEL 覆盖。
PROVIDERS = {
    "deepseek": {
        "label": "DeepSeek（便宜，推荐）",
        "env_prefix": "DEEPSEEK",
        "protocol": "openai",
        "default_base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-flash",
    },
    "openai": {
        "label": "OpenAI（GPT 系列）",
        "env_prefix": "OPENAI",
        "protocol": "openai",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-6.1-sol",
    },
    "anthropic": {
        "label": "Anthropic（Claude 系列）",
        "env_prefix": "ANTHROPIC",
        "protocol": "anthropic",
        "default_base_url": "https://api.anthropic.com",
        "default_model": "claude-sonnet-5-5",
    },
    "moonshot": {
        "label": "Kimi（月之暗面）",
        "env_prefix": "MOONSHOT",
        "protocol": "openai",
        "default_base_url": "https://api.moonshot.cn/v1",
        "default_model": "kimi-k3",
    },
    "dashscope": {
        "label": "通义千问（阿里云百炼）",
        "env_prefix": "DASHSCOPE",
        "protocol": "openai",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen3.8-max",
    },
    "xai": {
        "label": "Grok（xAI）",
        "env_prefix": "XAI",
        "protocol": "openai",
        "default_base_url": "https://api.x.ai/v1",
        "default_model": "grok-4.7",
    },
    "gemini": {
        "label": "Gemini（Google）",
        "env_prefix": "GEMINI",
        "protocol": "openai",
        "default_base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-3.8-flash",
    },
    "zhipu": {
        "label": "智谱 GLM（支持联网）",
        "env_prefix": "ZHIPU",
        "protocol": "openai",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "default_model": "glm-5.3-flash",
    },
    "volcengine": {
        "label": "豆包方舟（火山引擎）",
        "env_prefix": "VOLC",
        "protocol": "openai",
        "default_base_url": "https://ark.cn-beijing.volces.com/api/v3/",
        "default_model": "doubao-seed-2.1-pro",
    },
    "local": {
        "label": "本地模型（llama.cpp / Ollama）",
        "env_prefix": "LOCAL",
        "protocol": "openai",
        "default_base_url": "http://127.0.0.1:8080/v1",
        "default_model": "qwen3.8-27b",
    },
}


def get_provider_config(name: str) -> dict:
    """返回指定 Provider 的完整配置（protocol/base_url/api_key/model）。

    每个 Provider 支持三个环境变量覆盖默认值：
        <PREFIX>_API_KEY   API Key
        <PREFIX>_BASE_URL  接口地址（一般无需修改）
        <PREFIX>_MODEL     模型名
    """
    name = name.strip().lower()
    if name not in PROVIDERS:
        raise KeyError(f"未知的 Provider：{name}，可选：{', '.join(PROVIDERS)}")
    meta = PROVIDERS[name]
    prefix = meta["env_prefix"]
    return {
        "protocol": meta["protocol"],
        "base_url": os.getenv(f"{prefix}_BASE_URL", meta["default_base_url"]),
        "api_key": os.getenv(f"{prefix}_API_KEY", ""),
        "model": os.getenv(f"{prefix}_MODEL", meta["default_model"]),
    }
