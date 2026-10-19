"""大模型调用适配层：统一 OpenAI 兼容协议，多 Provider 可切换。

对外暴露两个函数：
- available_providers()：列出当前已配置好（有 Key）的 Provider，供前端下拉选择。
- chat()：发送对话消息，返回模型文本输出；json_mode=True 时尽量要求模型输出 JSON。
"""
from __future__ import annotations

from openai import OpenAI

from . import config


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


def _client(provider: str) -> tuple[OpenAI, dict]:
    """按 Provider 名称创建 OpenAI 客户端，返回 (client, config)。"""
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
    api_key = cfg["api_key"] or "not-needed"  # 本地模型无需 Key
    client = OpenAI(api_key=api_key, base_url=cfg["base_url"])
    return client, cfg


def chat(
    messages: list[dict],
    provider: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """调用大模型完成一次对话，返回回复文本。

    json_mode=True 时优先使用 response_format 约束 JSON 输出；
    个别兼容端点不支持该参数，会自动降级重试一次（由调用方自行解析 JSON）。
    """
    provider = provider or config.DEFAULT_PROVIDER
    client, cfg = _client(provider)

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
