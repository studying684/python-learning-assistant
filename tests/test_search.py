"""搜索层测试：Key 缺失、鉴权头、失败降级。"""
from __future__ import annotations

import httpx
import pytest

from app import search


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)


def test_no_keys_returns_empty():
    assert search.search("python 教程") == []
    assert search.search_enabled() is False


def test_tavily_uses_bearer_header(monkeypatch):
    """Tavily 鉴权必须走 Authorization 头，api_key 不能塞请求体。"""
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        # 必须把 request 挂到 Response 上，否则 raise_for_status 会报
        # "request instance has not been set"（这是测试替身的坑，不是产品缺陷）
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"title": "T", "url": "https://example.com", "content": "S"},
                ]
            },
            request=request,
        )

    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setattr(search.httpx, "post", fake_post)

    results = search.search("python")

    assert captured["headers"]["Authorization"] == "Bearer tvly-test"
    assert "api_key" not in captured["json"]
    assert results == [{"title": "T", "url": "https://example.com", "snippet": "S"}]


def test_serpapi_fallback_when_tavily_missing_key(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert params["api_key"] == "serp-test"
        return httpx.Response(
            200,
            json={"organic_results": [{"title": "G", "link": "https://example.com", "snippet": ""}]},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setenv("SERPAPI_API_KEY", "serp-test")
    monkeypatch.setattr(search.httpx, "get", fake_get)

    results = search.search("python")
    assert results == [{"title": "G", "url": "https://example.com", "snippet": ""}]


def test_tavily_error_falls_through_to_serpapi(monkeypatch):
    def boom_post(url, **kwargs):
        request = httpx.Request("POST", url)
        raise httpx.HTTPStatusError("429", request=request, response=httpx.Response(429, request=request))

    def fake_get(url, params=None, timeout=None):
        return httpx.Response(
            200,
            json={"organic_results": [{"title": "G", "link": "https://example.com", "snippet": ""}]},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("SERPAPI_API_KEY", "serp-test")
    monkeypatch.setattr(search.httpx, "post", boom_post)
    monkeypatch.setattr(search.httpx, "get", fake_get)

    results = search.search("python")
    assert len(results) == 1


def test_tavily_quota_exhausted_logs_and_falls_through(monkeypatch, capsys):
    """429 要打日志并继续降级，日志内容要说清是配额用尽。"""
    def boom_post(url, **kwargs):
        request = httpx.Request("POST", url)
        raise httpx.HTTPStatusError("429", request=request, response=httpx.Response(429, request=request))

    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setattr(search.httpx, "post", boom_post)

    assert search.search("python") == []
    assert "配额已用尽" in capsys.readouterr().err


def test_all_failures_return_empty(monkeypatch):
    def boom_post(url, **kwargs):
        raise httpx.ConnectError("network down")

    def boom_get(url, **kwargs):
        raise httpx.ConnectError("network down")

    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("SERPAPI_API_KEY", "serp-test")
    monkeypatch.setattr(search.httpx, "post", boom_post)
    monkeypatch.setattr(search.httpx, "get", boom_get)

    assert search.search("python") == []


def test_search_enabled_with_either_key(monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "serp-test")
    assert search.search_enabled() is True
