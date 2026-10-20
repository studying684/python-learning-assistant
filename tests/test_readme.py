"""README 双语自检：落地页是访客看到的第一屏，不能只靠肉眼。

这个仓库的 README 是**单文件双语**（中文在上、英文在下，顶部锚点互跳），
代价是两半容易各改各的、慢慢漂移。这里钉住"两半必须同步"的硬约束。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = (ROOT / "README.md").read_text(encoding="utf-8")
LINES = TEXT.splitlines()


def _split_halves() -> tuple[str, str]:
    zh = next(i for i, ln in enumerate(LINES) if ln.strip() == "## 简体中文")
    en = next(i for i, ln in enumerate(LINES) if ln.strip() == "## English")
    assert zh < en, "中文小节应在英文小节之前"
    return "\n".join(LINES[zh:en]), "\n".join(LINES[en:])


def _headings(level: int) -> list[str]:
    """只取代码围栏之外的标题（bash 里的 `# 注释` 不是标题）。"""
    marker = "#" * level + " "
    out, in_fence = [], False
    for ln in LINES:
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and ln.startswith(marker):
            out.append(ln[level + 1:].strip())
    return out


def test_single_bilingual_readme():
    """单文件双语：不再保留第二份中文 README，避免两处都要改。"""
    assert not (ROOT / "README.zh-CN.md").exists(), "中文已并入 README.md，不应再有独立文件"


def test_exactly_one_h1():
    assert len(_headings(1)) == 1


def test_language_sections_exist():
    h2 = _headings(2)
    assert "简体中文" in h2
    assert "English" in h2


def test_language_nav_anchors_resolve():
    """顶部语言栏的锚点必须指向真实存在的标题，否则点了没反应。"""
    assert "**简体中文**" in TEXT
    assert "[English](#english)" in TEXT
    assert "[简体中文](#简体中文)" in TEXT


def test_code_fences_are_balanced():
    """围栏不成对会让整页渲染塌掉——这是 README 最致命的格式错误。"""
    assert len([ln for ln in LINES if ln.lstrip().startswith("```")]) % 2 == 0


def test_both_halves_have_same_section_count():
    zh, en = _split_halves()
    zh_n = len([ln for ln in zh.splitlines() if ln.startswith("### ")])
    en_n = len([ln for ln in en.splitlines() if ln.startswith("### ")])
    assert zh_n == en_n, f"中英章节数不一致：中文 {zh_n} vs 英文 {en_n}"


def test_provider_table_is_complete_in_both_halves():
    """README 的 Provider 表必须和 app/config.py 的注册表逐一对齐。

    这样"加了 Provider 却忘了写文档"会直接测试失败，而不是等用户发现。
    """
    from app import config

    zh, en = _split_halves()
    # config.PROVIDERS 里的 env_prefix 不带尾部下划线（拼环境变量名时才补），
    # 而 README 表格里展示的是 `PREFIX_` 这种完整形态。
    missing = [
        (name, side)
        for name, meta in config.PROVIDERS.items()
        for side, half in (("中文", zh), ("English", en))
        if f"`{meta['env_prefix']}_`" not in half
    ]
    assert not missing, f"以下 Provider 未在 README 中记录：{missing}"


def test_key_facts_present_in_both_halves():
    """这些是本项目的招牌事实，翻译时最容易漏。"""
    zh, en = _split_halves()
    facts = ["deepseek-flash", "grok-4.7", "qwen3.8-27b", "claude-sonnet-5-5",
             "--jinja", "DEBUG_ENDPOINTS", "[MIT](LICENSE)", ".github/workflows/ci.yml"]
    missing = [(f, side) for f in facts for side, half in
               (("中文", zh), ("English", en)) if f not in half]
    assert not missing, f"以下事实缺翻译：{missing}"


def test_no_stale_mentions_of_removed_file():
    assert "README.zh-CN" not in TEXT
