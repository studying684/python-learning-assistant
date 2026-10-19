"""配置加载模块：从 .env 读取所有 API 凭据与偏好设置。

本项目的核心设计是「多 Provider 可切换」：
- 所有主流大模型服务都支持统一的 OpenAI 兼容协议（OpenAI、DeepSeek、Kimi、
  通义千问、智谱 GLM、豆包方舟、本地 llama.cpp/Ollama 均支持）；
- 因此切换模型只需改 base_url / api_key / model 三个配置项，代码不用动。
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
PROVIDERS = {
    "deepseek": {
        "label": "DeepSeek（便宜，推荐）",
        "env_prefix": "DEEPSEEK",
        "default_base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
    "openai": {
        "label": "OpenAI（GPT 系列）",
        "env_prefix": "OPENAI",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
    },
    "anthropic": {
        "label": "Anthropic（Claude 系列）",
        "env_prefix": "ANTHROPIC",
        "default_base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-latest",
    },
    "moonshot": {
        "label": "Kimi（月之暗面）",
        "env_prefix": "MOONSHOT",
        "default_base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
    },
    "dashscope": {
        "label": "通义千问（阿里云百炼）",
        "env_prefix": "DASHSCOPE",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
    },
    "zhipu": {
        "label": "智谱 GLM（支持联网）",
        "env_prefix": "ZHIPU",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "default_model": "glm-4-flash",
    },
    "volcengine": {
        "label": "豆包方舟（火山引擎）",
        "env_prefix": "VOLC",
        "default_base_url": "https://ark.cn-beijing.volces.com/api/v3/",
        "default_model": "doubao-1-5-pro-32k-250115",
    },
    "local": {
        "label": "本地模型（llama.cpp / Ollama）",
        "env_prefix": "LOCAL",
        "default_base_url": "http://127.0.0.1:8080/v1",
        "default_model": "qwen3-8b",
    },
}


def get_provider_config(name: str) -> dict:
    """返回指定 Provider 的完整配置（base_url / api_key / model）。

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
        "base_url": os.getenv(f"{prefix}_BASE_URL", meta["default_base_url"]),
        "api_key": os.getenv(f"{prefix}_API_KEY", ""),
        "model": os.getenv(f"{prefix}_MODEL", meta["default_model"]),
    }
