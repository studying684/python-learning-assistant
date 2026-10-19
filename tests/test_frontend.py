"""前端静态检查：不需要浏览器，用字符串断言守住几个关键点。

这里刻意不引 Node/无头浏览器——本项目定位是零依赖练手项目，
为测试引入一个 Node 运行时不划算。断言的都是"改了就会出事"的点：
XSS 转义是否还在、是否有 alert/confirm 残留、生成流程是否禁用了按钮。
"""
from __future__ import annotations

import re
from pathlib import Path

HTML = (Path(__file__).resolve().parent.parent / "static" / "index.html").read_text(encoding="utf-8")


def _body() -> str:
    """去掉 <style> 后的部分，避免把 CSS 注释也当成 JS 断言。"""
    return HTML.split("</style>", 1)[1]


def test_no_native_dialogs_left():
    """原生 alert/confirm 会阻塞渲染且样式不受控，必须清零。"""
    js = _body()
    for name in ("alert(", "confirm(", "prompt("):
        assert name not in js, f"仍在调用原生 {name}"


def test_escape_html_is_used_for_user_content():
    assert "function escapeHtml(s)" in HTML
    # 渲染模型输出的三处都必须走转义
    js = _body()
    assert js.count("escapeHtml(") >= 6


def test_notice_and_dialog_wiring_exists():
    for elem in ("notice", "confirmOverlay", "confirmTitle", "confirmMessage",
                 "confirmOk", "confirmCancel"):
        assert f'id="{elem}"' in HTML, f"缺少 #{elem}"
    js = _body()
    assert "function showNotice(" in js
    assert "function showConfirm(" in js


def test_generate_projects_has_loading_and_disable():
    """生成期间必须禁用按钮并给出 loading，否则用户会重复点击。"""
    js = _body()
    assert 'btn.disabled = true' in js
    assert 'class="loading"' in js
    assert "finally" in js


def test_single_page_loads_without_build_step():
    """保持"无构建单文件前端"的定位：不能出现 script src / link href 外链。"""
    assert "<script src" not in HTML
    assert '<link rel="stylesheet"' not in HTML


def test_html_tags_balanced_for_sections():
    """粗粒度结构检查：section/main/script 数量成对。"""
    for tag in ("main", "section", "script", "style", "body", "html"):
        opens = len(re.findall(rf"<{tag}[\s>]", HTML))
        closes = len(re.findall(rf"</{tag}>", HTML))
        assert opens == closes, f"<{tag}> 开闭标签不配对：{opens} vs {closes}"
