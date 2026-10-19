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


def test_connection_is_reused_across_calls(temp_db):
    """连接应在进程内复用，而不是每个请求重开。"""
    projects.init_db()
    assert projects._connection() is projects._connection()


def test_reset_connection_reopens_new_path(temp_db, tmp_path):
    """重定向 DB_PATH 后必须 reset，否则仍连在旧文件上。"""
    projects.init_db()
    projects.add_project({"language": "C", "difficulty": "入门", "title": "旧库里的项目",
                          "description": "", "knowledge_points": [], "acceptance_criteria": []})
    old = projects.DB_PATH
    projects.DB_PATH = tmp_path / "other.db"
    projects.reset_connection()
    projects.init_db()
    titles = [p["title"] for p in projects.list_projects()]
    assert "旧库里的项目" not in titles
    assert len(titles) == len(projects.SEED_PROJECTS)
    projects.DB_PATH = old
    projects.reset_connection()


def test_writes_survive_new_connection(temp_db):
    """提交必须真正落盘：换连接后应仍能读到（锁+复用不能吃掉写入）。"""
    projects.init_db()
    created = projects.add_project(
        {
            "language": "C", "difficulty": "入门", "title": "持久化检查",
            "description": "", "knowledge_points": [], "acceptance_criteria": [],
        }
    )
    projects.reset_connection()
    rows = projects.list_projects(language="C")
    assert [r["id"] for r in rows] == [created["id"]]
