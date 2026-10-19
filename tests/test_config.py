"""配置层测试：Provider 注册表完整性与环境变量覆盖。"""
from __future__ import annotations

import pytest

from app import config


def test_all_providers_have_required_fields():
    for name, meta in config.PROVIDERS.items():
        assert meta["label"], f"{name} 缺少 label"
        assert meta["env_prefix"], f"{name} 缺少 env_prefix"
        assert meta["env_prefix"].isupper(), f"{name} 的 env_prefix 应为大写"
        assert meta["protocol"] in ("openai", "anthropic"), f"{name} 的 protocol 非法"
        assert meta["default_base_url"].startswith("http"), f"{name} 的 base_url 非法"
        assert meta["default_model"], f"{name} 缺少 default_model"


def test_default_provider_is_registered():
    assert config.DEFAULT_PROVIDER in config.PROVIDERS


def test_env_override(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_MODEL", "my-test-model")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "http://127.0.0.1:9/v1")
    cfg = config.get_provider_config("deepseek")
    assert cfg["model"] == "my-test-model"
    assert cfg["base_url"] == "http://127.0.0.1:9/v1"


def test_get_provider_config_protocol_field():
    assert config.get_provider_config("anthropic")["protocol"] == "anthropic"
    assert config.get_provider_config("local")["protocol"] == "openai"


def test_unknown_provider_raises_keyerror():
    with pytest.raises(KeyError):
        config.get_provider_config("no-such-provider")


def test_local_provider_needs_no_key():
    """本地模型即使没配 Key 也必须可用（零门槛演示的关键）。"""
    assert config.get_provider_config("local")["protocol"] == "openai"
    assert "127.0.0.1" in config.get_provider_config("local")["base_url"]
