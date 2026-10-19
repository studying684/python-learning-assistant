"""路线生成测试：JSON 抽取、pydantic 兜底校验。"""
from __future__ import annotations

import json

import pytest

from app import llm, planner


def test_extract_json_plain():
    assert planner._extract_json('{"summary": "s", "stages": []}') == {"summary": "s", "stages": []}


def test_extract_json_from_markdown_fence():
    text = '前面一堆解释\n```json\n{"a": 1}\n```\n后面还有话'
    assert planner._extract_json(text) == {"a": 1}


def test_extract_json_surrounded_by_prose():
    text = '好的，结果如下：{"a": 1} 希望对你有帮助'
    assert planner._extract_json(text) == {"a": 1}


def test_extract_json_raises_on_garbage():
    with pytest.raises(json.JSONDecodeError):
        planner._extract_json("完全不是 JSON")


def _full_route(**overrides):
    route = {
        "summary": "三个月入门爬虫",
        "stages": [
            {
                "title": "第一阶段",
                "goal": "打基础",
                "topics": ["HTTP 协议"],
                "projects": ["抓取豆瓣 Top250"],
                "resources": ["https://example.com"],
                "estimated_weeks": 2,
                "checklist": ["能发请求"],
            }
        ],
        "generated_projects": [
            {
                "language": "C",
                "difficulty": "入门",
                "title": "指针练习",
                "description": "写一个交换函数",
                "knowledge_points": ["指针"],
                "acceptance_criteria": ["能交换两个 int"],
            }
        ],
    }
    route.update(overrides)
    return route


def test_route_accepts_full_structure():
    route = planner.Route.model_validate(_full_route())
    assert route.summary == "三个月入门爬虫"
    assert len(route.stages) == 1


def test_route_rejects_missing_summary():
    """核心字段必须必填——给默认值会让校验形同虚设。"""
    bad = _full_route()
    del bad["summary"]
    with pytest.raises(Exception):
        planner.Route.model_validate(bad)


def test_route_rejects_missing_stages():
    bad = _full_route()
    del bad["stages"]
    with pytest.raises(Exception):
        planner.Route.model_validate(bad)


def test_route_rejects_non_integer_weeks():
    bad = _full_route()
    bad["stages"][0]["estimated_weeks"] = "两周"
    with pytest.raises(Exception):
        planner.Route.model_validate(bad)


def test_route_rejects_generated_project_without_title():
    bad = _full_route()
    bad["generated_projects"][0].pop("title")
    with pytest.raises(Exception):
        planner.Route.model_validate(bad)


def test_route_tolerates_missing_optional_stage_fields():
    """模型少写 topics/resources 之类的可选字段时应被默认值兜住。"""
    bad = _full_route()
    for key in ("topics", "projects", "resources", "checklist", "goal", "estimated_weeks"):
        bad["stages"][0].pop(key)
    route = planner.Route.model_validate(bad)
    assert route.stages[0].estimated_weeks == 2
    assert route.stages[0].topics == []


def test_generate_route_wraps_bad_json(monkeypatch):
    monkeypatch.setattr(planner.llm, "chat", lambda *a, **k: "不是 JSON")
    with pytest.raises(llm.LLMError) as exc:
        planner.generate_route("我想学爬虫", provider="local", use_search=False)
    assert "无法解析" in str(exc.value)


def test_generate_route_wraps_schema_violation(monkeypatch):
    monkeypatch.setattr(planner.llm, "chat", lambda *a, **k: '{"summary": "没有 stages"}')
    with pytest.raises(llm.LLMError) as exc:
        planner.generate_route("我想学爬虫", provider="local", use_search=False)
    assert "不符合路线结构" in str(exc.value)


def test_generate_route_appends_search_links(monkeypatch):
    """搜索开关打开时，真实链接必须进提示词。"""
    seen = {}

    def fake_chat(messages, **kwargs):
        seen["user"] = messages[-1]["content"]
        return json.dumps(_full_route(), ensure_ascii=False)

    monkeypatch.setattr(planner.llm, "chat", fake_chat)
    monkeypatch.setattr(
        planner.search,
        "search",
        lambda q: [{"title": "教程", "url": "https://example.com/a", "snippet": ""}],
    )
    planner.generate_route("我想学爬虫", provider="local", use_search=True)
    assert "https://example.com/a" in seen["user"]


def test_generate_route_works_without_search(monkeypatch):
    monkeypatch.setattr(
        planner.llm, "chat", lambda *a, **k: json.dumps(_full_route(), ensure_ascii=False)
    )
    monkeypatch.setattr(planner.search, "search", lambda q: [])
    route = planner.generate_route("我想学爬虫", provider="local", use_search=True)
    assert route["summary"] == "三个月入门爬虫"
