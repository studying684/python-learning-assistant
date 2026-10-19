"""API 层测试：用 TestClient 打真实路由（lifespan 会建临时库）。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config, main, projects


@pytest.fixture()
def client(temp_db, monkeypatch):
    """TestClient + 临时数据库 + 清空 Key（保证 /api/models 只报 local）。"""
    monkeypatch.setattr(projects, "DATA_DIR", temp_db.parent)
    monkeypatch.setattr(projects, "DB_PATH", temp_db)
    for meta in config.PROVIDERS.values():
        prefix = meta["env_prefix"]
        monkeypatch.delenv(f"{prefix}_API_KEY", raising=False)
        monkeypatch.delenv(f"{prefix}_MODEL", raising=False)
    with TestClient(main.app) as c:
        yield c


def test_index_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Python" in resp.text


def test_api_models(client):
    resp = client.get("/api/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["default_provider"] == config.DEFAULT_PROVIDER
    assert body["search_enabled"] is False
    # 没有 Key 时只有本地模型可用
    assert [p["id"] for p in body["providers"]] == ["local"]
    assert body["providers"][0]["model"] == "qwen3.8-27b"


def test_api_projects_seeded_by_lifespan(client):
    """数据库初始化必须在 lifespan 里完成，而不是 import 阶段。"""
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["projects"]) == len(projects.SEED_PROJECTS)
    assert body["languages"] == ["Python"]


def test_api_projects_filter(client):
    resp = client.get("/api/projects", params={"language": "Python", "difficulty": "入门"})
    assert resp.status_code == 200
    for p in resp.json()["projects"]:
        assert p["difficulty"] == "入门"


def test_api_search_requires_query(client):
    """空参数应被 FastAPI 参数校验拦成 422，而不是打光搜索配额。"""
    assert client.get("/api/search").status_code == 422
    assert client.get("/api/search", params={"q": ""}).status_code == 422


def test_api_search_too_long_rejected(client):
    long_q = "x" * 201
    assert client.get("/api/search", params={"q": long_q}).status_code == 422


def test_api_search_returns_empty_without_keys(client, monkeypatch):
    monkeypatch.setattr(main.search, "search", lambda q: [])
    resp = client.get("/api/search", params={"q": "python"})
    assert resp.status_code == 200
    assert resp.json() == {"results": []}


def test_api_route_empty_input_rejected(client):
    resp = client.post("/api/route", json={"user_input": "   "})
    assert resp.status_code == 400
    assert "学习需求" in resp.json()["detail"]


def test_api_route_llm_error_becomes_502(client, monkeypatch):
    def boom(*args, **kwargs):
        raise main.llm.LLMError("模型调用失败")

    monkeypatch.setattr(main.planner, "generate_route", boom)
    resp = client.post("/api/route", json={"user_input": "我想学爬虫"})
    assert resp.status_code == 502
    assert "模型调用失败" in resp.json()["detail"]


def test_api_route_success_adds_projects(client, monkeypatch):
    route = {
        "summary": "s",
        "stages": [{"title": "第一阶段"}],
        "generated_projects": [
            {
                "language": "C",
                "difficulty": "入门",
                "title": "指针练习",
                "description": "写一个交换函数",
                "knowledge_points": ["指针"],
                "acceptance_criteria": ["能交换两个 int"],
            },
            {"language": "C", "title": "  "},  # title 为空的应被跳过
        ],
    }
    monkeypatch.setattr(main.planner, "generate_route", lambda *a, **k: route)

    resp = client.post("/api/route", json={"user_input": "帮我学 C，再加 2 个项目"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["route"]["summary"] == "s"
    assert [p["title"] for p in body["added_projects"]] == ["指针练习"]
    # 入库后列表里能查到
    titles = [p["title"] for p in client.get("/api/projects").json()["projects"]]
    assert "指针练习" in titles


def test_api_projects_generate_success(client, monkeypatch):
    monkeypatch.setattr(main.projects, "generate_projects", lambda *a, **k: [{"title": "A"}])
    resp = client.post("/api/projects/generate", json={"language": "Java", "count": 1})
    assert resp.status_code == 200
    assert resp.json() == [{"title": "A"}]


def test_api_projects_generate_rejects_bad_count(client):
    resp = client.post("/api/projects/generate", json={"language": "Java", "count": 99})
    assert resp.status_code == 422


def test_api_projects_done_and_delete(client):
    pid = client.get("/api/projects").json()["projects"][0]["id"]

    resp = client.post(f"/api/projects/{pid}/done", json={"done": True})
    assert resp.status_code == 200
    done = [p for p in client.get("/api/projects").json()["projects"] if p["id"] == pid][0]
    assert done["done"] is True

    resp = client.delete(f"/api/projects/{pid}")
    assert resp.status_code == 200
    ids = [p["id"] for p in client.get("/api/projects").json()["projects"]]
    assert pid not in ids


def test_app_version_is_current(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["version"] == "0.2.0"
