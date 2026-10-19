"""搜索增强层：可插拔的搜索 Provider。

优先级：Tavily → SerpAPI →（都不配置时）不搜索。
- 未配置任何搜索 Key 时，search() 返回空列表，主流程自动降级为「纯 LLM 生成」；
- 若使用本身就支持联网的模型（如智谱 GLM、Kimi），也可以完全不配搜索 Key，
  直接在提示词里让模型联网搜索。
"""
from __future__ import annotations

import os

import httpx

# 搜索请求超时（秒）
_TIMEOUT = 30.0


def _tavily(query: str) -> list[dict] | None:
    """Tavily Search API：专为大模型设计，免费额度 1000 次/月。"""
    key = os.getenv("TAVILY_API_KEY", "")
    if not key:
        return None
    resp = httpx.post(
        "https://api.tavily.com/search",
        json={"api_key": key, "query": query, "max_results": 5, "search_depth": "basic"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return [
        {"title": item.get("title", ""), "url": item.get("url", ""), "snippet": item.get("content", "")}
        for item in resp.json().get("results", [])
    ]


def _serpapi(query: str) -> list[dict] | None:
    """SerpAPI：Google 搜索结果 API，免费额度 100 次/月。"""
    key = os.getenv("SERPAPI_API_KEY", "")
    if not key:
        return None
    resp = httpx.get(
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": query, "api_key": key, "num": 5},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return [
        {"title": item.get("title", ""), "url": item.get("link", ""), "snippet": item.get("snippet", "")}
        for item in resp.json().get("organic_results", [])
    ]


def search(query: str) -> list[dict]:
    """按优先级尝试各个搜索 Provider，返回 [{"title","url","snippet"}]。

    所有 Provider 都失败（未配置 Key / 请求报错）时返回空列表，由调用方降级处理。
    """
    for fn in (_tavily, _serpapi):
        try:
            results = fn(query)
            if results:
                return results
        except Exception:
            # 单个搜索源失败不影响整体，继续尝试下一个
            continue
    return []


def search_enabled() -> bool:
    """是否已配置至少一个搜索 Key（用于前端展示搜索开关状态）。"""
    return bool(os.getenv("TAVILY_API_KEY") or os.getenv("SERPAPI_API_KEY"))
