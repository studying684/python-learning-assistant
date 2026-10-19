"""LLM 适配层测试：协议分流、Key 检查、错误包装（全部离线，不打真实请求）。"""
from __future__ import annotations

import httpx
import pytest

from app import config, llm


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch):
    """默认清掉所有 Key，保证每个用例都从「未配置」状态出发。"""
    for meta in config.PROVIDERS.values():
        prefix = meta["env_prefix"]
        monkeypatch.delenv(f"{prefix}_API_KEY", raising=False)
        monkeypatch.delenv(f"{prefix}_BASE_URL", raising=False)
        monkeypatch.delenv(f"{prefix}_MODEL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


def test_missing_key_raises_llm_error():
    with pytest.raises(llm.LLMError) as exc:
        llm.chat([{"role": "user", "content": "hi"}], provider="deepseek")
    assert "API Key" in str(exc.value)


def test_unknown_provider_falls_back_to_default(monkeypatch):
    """provider 不在注册表时应回落默认 Provider，而不是 KeyError。

    注意：DEFAULT_PROVIDER 是 config 在 import 时从环境读的快照，
    所以这个用例要用 monkeypatch 直接改 llm.config.DEFAULT_PROVIDER，
    光设 LLM_PROVIDER 环境变量对已 import 的模块不生效。
    """
    monkeypatch.setattr(llm.config, "DEFAULT_PROVIDER", "openai")
    with pytest.raises(llm.LLMError) as exc:
        llm.chat([{"role": "user", "content": "hi"}], provider="bogus")
    # 报的是 openai 的错，说明回落生效（而不是 KeyError）
    assert "OpenAI（GPT 系列）" in str(exc.value)


def test_anthropic_chat_sends_native_protocol(monkeypatch):
    """验证 Anthropic 走原生 Messages 协议，而不是 OpenAI 兼容端点。"""
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "你好"}, {"type": "text", "text": "世界"}]},
        )

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    text = llm.chat(
        [
            {"role": "system", "content": "你是老师"},
            {"role": "user", "content": "讲课"},
        ],
        provider="anthropic",
        json_mode=True,
    )

    assert text == "你好\n世界"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["headers"]["anthropic-version"] == llm.ANTHROPIC_VERSION
    # system 必须抽到顶层，不能混在 messages 里
    assert captured["body"]["system"] == "你是老师"
    assert all(m["role"] != "system" for m in captured["body"]["messages"])
    assert captured["body"]["output_config"]["format"]["type"] == "json_schema"


def test_anthropic_http_error_raises_llm_error(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return httpx.Response(401, text="invalid api key")

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "bad-key")
    with pytest.raises(llm.LLMError) as exc:
        llm.chat([{"role": "user", "content": "hi"}], provider="anthropic")
    assert "401" in str(exc.value)


def test_anthropic_output_config_unsupported_retries_without_it(monkeypatch):
    """老端点不认识 output_config（400）时应去掉再重试一次。"""
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        if "output_config" in json:
            return httpx.Response(400, text="unknown field output_config")
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    text = llm.chat([{"role": "user", "content": "hi"}], provider="anthropic", json_mode=True)
    assert text == "ok"
    assert len(calls) == 2
    assert "output_config" not in calls[1]


def test_anthropic_empty_text_raises(monkeypatch):
    monkeypatch.setattr(
        llm.httpx,
        "post",
        lambda *a, **k: httpx.Response(200, json={"content": [{"type": "tool_use", "id": "x"}]}),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with pytest.raises(llm.LLMError) as exc:
        llm.chat([{"role": "user", "content": "hi"}], provider="anthropic")
    assert "为空" in str(exc.value)


def test_openai_connection_error_is_translated(monkeypatch):
    """本地 llama.cpp 没起时应得到可读的连接失败提示（含构造阶段的错误）。"""
    from openai import APIConnectionError

    def boom(*args, **kwargs):
        raise APIConnectionError(request=httpx.Request("POST", "http://127.0.0.1:8080/v1"))

    monkeypatch.setattr(llm, "OpenAI", boom)
    with pytest.raises(llm.LLMError) as exc:
        llm.chat([{"role": "user", "content": "hi"}], provider="local")
    assert "连接失败" in str(exc.value)
    assert "local" in str(exc.value)


def test_openai_chat_error_is_translated(monkeypatch):
    """调用阶段的连接错误同样要转成 LLMError，而不是裸 SDK 异常。"""
    from openai import APIConnectionError

    def boom(*args, **kwargs):
        raise APIConnectionError(request=httpx.Request("POST", "http://127.0.0.1:8080/v1"))

    monkeypatch.setattr(llm, "_openai_chat", boom)
    with pytest.raises(llm.LLMError) as exc:
        llm.chat([{"role": "user", "content": "hi"}], provider="local")
    assert "连接失败" in str(exc.value)


def test_available_providers_always_contains_local():
    result = llm.available_providers()
    assert "local" in [p["id"] for p in result]
    assert all({"id", "label", "model", "base_url"} <= set(p) for p in result)
