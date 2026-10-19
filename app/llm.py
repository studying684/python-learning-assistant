"""大模型调用适配层：多 Provider 可切换（OpenAI 兼容 + Anthropic 原生）。

对外暴露两个函数：
- available_providers()：列出当前已配置好（有 Key）的 Provider，供前端下拉选择。
- chat()：发送对话消息，返回模型文本输出；json_mode=True 时尽量要求模型输出 JSON。

协议分流（对调用方透明）：
- protocol="openai"：用 openai SDK 直连各家 OpenAI 兼容端点；
- protocol="anthropic"：用 httpx 直连 Anthropic 原生 Messages API
  （POST /v1/messages + x-api-key + anthropic-version），
  与 OpenAI 的 /chat/completions 不是一套协议，不能只改 base_url。
"""
from __future__ import annotations

import httpx
from openai import APIConnectionError as _OpenAIConnectionError
from openai import OpenAI

from . import config

# Anthropic Messages API 要求的版本头
ANTHROPIC_VERSION = "2023-06-01"

# 单次 LLM 调用超时（秒）。长路线生成可能接近该上限，
# 超时后 openai SDK 会抛 APITimeoutError，由上层统一转成 LLMError。
_TIMEOUT = 60.0


class LLMError(Exception):
    """大模型调用相关的统一异常（前端会显示其 message）。"""


def available_providers() -> list[dict]:
    """返回可用的 Provider 列表：本地模型永远可用，其余需要已配置 API Key。"""
    result = []
    for name in config.PROVIDERS:
        cfg = config.get_provider_config(name)
        if name == "local" or cfg["api_key"]:
            result.append(
                {
                    "id": name,
                    "label": config.PROVIDERS[name]["label"],
                    "model": cfg["model"],
                    "base_url": cfg["base_url"],
                }
            )
    return result


def _openai_chat(
    client: OpenAI,
    cfg: dict,
    messages: list[dict],
    json_mode: bool,
    temperature: float,
    max_tokens: int,
) -> str:
    """OpenAI 兼容协议的一次调用（含 response_format 降级重试）。"""
    kwargs = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as exc:
        # 若因 response_format 不被支持而失败，去掉该参数再试一次
        if json_mode and "response_format" in kwargs:
            kwargs.pop("response_format")
            try:
                resp = client.chat.completions.create(**kwargs)
            except Exception as exc2:
                raise LLMError(f"模型调用失败：{exc2}") from exc2
        else:
            raise LLMError(f"模型调用失败：{exc}") from exc

    content = resp.choices[0].message.content
    if content is None:
        raise LLMError("模型返回内容为空")
    return content


def _anthropic_chat(
    cfg: dict,
    messages: list[dict],
    json_mode: bool,
    temperature: float,
    max_tokens: int,
) -> str:
    """Anthropic 原生 Messages API 的一次调用。

    要点：
    - 端点是 POST {base_url}/v1/messages，鉴权走 x-api-key 头
      （不是 Authorization: Bearer）；
    - system 提示词必须抽出来单独传，不能混在 messages 数组里；
    - 结构化输出：优先用 output_config.format = json_schema，
      不被支持时退回 prompt 约束，由调用方自行解析。
    """
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    turns = [m for m in messages if m["role"] != "system"]

    body: dict = {
        "model": cfg["model"],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": turns,
    }
    if system:
        body["system"] = system
    if json_mode:
        body["output_config"] = {
            "format": {
                "type": "json_schema",
                "schema": {"type": "object"},
            }
        }

    headers = {
        "x-api-key": cfg["api_key"],
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    url = cfg["base_url"].rstrip("/") + "/v1/messages"

    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=120.0)
    except httpx.HTTPError as exc:
        raise LLMError(f"模型调用失败：{exc}") from exc

    if resp.status_code >= 400:
        # output_config 老端点不认识时，退回纯 prompt 约束重试一次
        if json_mode and "output_config" in body and resp.status_code in (400, 422):
            body.pop("output_config")
            try:
                retry = httpx.post(url, headers=headers, json=body, timeout=120.0)
            except httpx.HTTPError as exc:
                raise LLMError(f"模型调用失败：{exc}") from exc
            if retry.status_code < 400:
                return _anthropic_text(retry)
        raise LLMError(f"模型调用失败：HTTP {resp.status_code} {resp.text[:200]}")

    return _anthropic_text(resp)


def _anthropic_text(resp: httpx.Response) -> str:
    """把 Anthropic 响应体里的文本块拼成字符串。"""
    try:
        data = resp.json()
        parts = [
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
    except Exception as exc:
        raise LLMError(f"模型响应解析失败：{exc}") from exc
    text = "\n".join(p for p in parts if p).strip()
    if not text:
        raise LLMError("模型返回内容为空")
    return text


def chat(
    messages: list[dict],
    provider: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """调用大模型完成一次对话，返回回复文本。

    json_mode=True 时优先约束模型输出 JSON；个别端点不支持该能力时
    会自动降级重试一次（由调用方自行解析 JSON）。
    """
    if provider not in config.PROVIDERS:
        provider = config.DEFAULT_PROVIDER
    cfg = config.get_provider_config(provider)
    if provider != "local" and not cfg["api_key"]:
        label = config.PROVIDERS[provider]["label"]
        prefix = config.PROVIDERS[provider]["env_prefix"]
        raise LLMError(
            f"Provider「{label}」尚未配置 API Key，"
            f"请复制 .env.example 为 .env 并填写 {prefix}_API_KEY。"
        )

    if cfg["protocol"] == "anthropic":
        return _anthropic_chat(cfg, messages, json_mode, temperature, max_tokens)

    api_key = cfg["api_key"] or "not-needed"  # 本地模型无需 Key
    try:
        # 客户端构造也放进 try：openai SDK 在校验 base_url / api_key 时
        # 同样可能抛 APIConnectionError，必须统一转成可读的 LLMError。
        client = OpenAI(api_key=api_key, base_url=cfg["base_url"], timeout=_TIMEOUT)
        return _openai_chat(client, cfg, messages, json_mode, temperature, max_tokens)
    except _OpenAIConnectionError as exc:
        # 本地 llama.cpp/Ollama 没起、或网络不通时会走到这里
        raise LLMError(f"Provider「{provider}」连接失败：{exc}") from exc
