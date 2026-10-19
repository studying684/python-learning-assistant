"""项目库测试：种子数据、CRUD、难度归一（全部走临时数据库）。"""
from __future__ import annotations

import pydantic
import pytest

from app import llm, projects


def test_init_db_writes_seed_projects(temp_db):
    projects.init_db()
    rows = projects.list_projects()
    assert len(rows) == len(projects.SEED_PROJECTS)
    assert all(r["source"] == "builtin" for r in rows)


def test_init_db_is_idempotent(temp_db):
    projects.init_db()
    projects.init_db()
    assert len(projects.list_projects()) == len(projects.SEED_PROJECTS)


def test_row_to_dict_decodes_json_columns(temp_db):
    projects.init_db()
    row = projects.list_projects()[0]
    assert isinstance(row["knowledge_points"], list)
    assert isinstance(row["acceptance_criteria"], list)
    assert isinstance(row["done"], bool)


def test_add_and_list_project(temp_db):
    projects.init_db()
    created = projects.add_project(
        {
            "language": "C",
            "difficulty": "进阶",
            "title": "指针练习",
            "description": "写一个交换函数",
            "knowledge_points": ["指针"],
            "acceptance_criteria": ["能交换两个 int"],
        },
        source="generated",
    )
    assert created["language"] == "C"
    assert created["source"] == "generated"

    only_c = projects.list_projects(language="C")
    assert [p["id"] for p in only_c] == [created["id"]]


def test_filter_by_difficulty(temp_db):
    projects.init_db()
    for r in projects.list_projects(difficulty="入门"):
        assert r["difficulty"] == "入门"


def test_mark_done(temp_db):
    projects.init_db()
    pid = projects.list_projects()[0]["id"]
    projects.mark_done(pid, True)
    assert projects.list_projects()[0]["done"] is True
    projects.mark_done(pid, False)
    assert projects.list_projects()[0]["done"] is False


def test_delete_project(temp_db):
    projects.init_db()
    pid = projects.list_projects()[0]["id"]
    before = len(projects.list_projects())
    projects.delete_project(pid)
    after = projects.list_projects()
    assert len(after) == before - 1
    assert pid not in [p["id"] for p in after]


def test_list_languages(temp_db):
    projects.init_db()
    assert projects.list_languages() == ["Python"]


def test_generated_project_difficulty_normalized():
    """模型乱写难度时必须归一到白名单，否则前端筛选会漏项。"""
    item = projects.GeneratedProject(
        title="测试项目",
        difficulty="地狱",
        description="",
        knowledge_points=[],
        acceptance_criteria=[],
    )
    assert item.to_row("Java")["difficulty"] == "进阶"
    assert item.to_row("Java")["language"] == "Java"


def test_generated_project_requires_title():
    with pytest.raises(pydantic.ValidationError):
        projects.GeneratedProject(difficulty="入门")


def test_generate_projects_parses_llm_output(monkeypatch, temp_db):
    """端到端：LLM 输出 → pydantic 校验 → 入库。"""
    projects.init_db()
    monkeypatch.setattr(
        projects.llm,
        "chat",
        lambda *a, **k: '[{"title":"A","difficulty":"入门"},{"title":"B","difficulty":"进阶"}]',
    )
    created = projects.generate_projects("C", count=2, topic="")
    assert [c["title"] for c in created] == ["A", "B"]
    assert all(c["language"] == "C" for c in created)


def test_generate_projects_rejects_non_array(monkeypatch, temp_db):
    monkeypatch.setattr(projects.llm, "chat", lambda *a, **k: '{"title":"不是数组"}')
    with pytest.raises(llm.LLMError, match="不是数组|无法解析"):
        projects.generate_projects("C")


def test_generate_projects_rejects_bad_json(monkeypatch, temp_db):
    monkeypatch.setattr(projects.llm, "chat", lambda *a, **k: "完全不是 JSON")
    with pytest.raises(llm.LLMError, match="无法解析"):
        projects.generate_projects("C")


def test_generate_projects_all_titles_empty_raises(monkeypatch, temp_db):
    monkeypatch.setattr(projects.llm, "chat", lambda *a, **k: '[{"title":"  "}]')
    with pytest.raises(llm.LLMError, match="有效项目"):
        projects.generate_projects("C")
