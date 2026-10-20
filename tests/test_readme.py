"""README 双语自检：README.md 是英文主入口，README.zh-CN.md 是中文版。

为什么是两份文件而不是单文件双语：点进仓库的第一屏就该是英文（GitHub 上
英文读者占多数），中文读者走顶部语言栏一次点击即可拿到完整中文——这符合
GitHub 上主流通行的做法，也比在同一页里上下翻找更省事。

代价是两份文档容易各改各的，慢慢就漂了。这里把它们钉在一起。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN = (ROOT / "README.md").read_text(encoding="utf-8")
ZH = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

BOTH = (("README.md", EN), ("README.zh-CN.md", ZH))

# 只在这边出现的章节标题，用来抓"两边混进了对方的内容"
ZH_ONLY = ("快速开始", "常见问题", "工作原理", "功能特性", "项目结构", "界面预览")
EN_ONLY = ("Quick start", "How it works", "Project layout", "UI preview")


def _headings(text: str, level: int) -> list[str]:
    """只取代码围栏之外的标题（bash 里的 `# 注释` 不是标题）。"""
    marker = "#" * level + " "
    out, in_fence = [], False
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and ln.startswith(marker):
            out.append(ln[level + 1:].strip())
    return out


def test_both_readmes_exist():
    assert (ROOT / "README.md").is_file()
    assert (ROOT / "README.zh-CN.md").is_file()


def test_entrypoint_is_english():
    """点进仓库看到的是 README.md，所以它必须是英文的。"""
    assert _headings(EN, 2), "README.md 没有二级标题"
    assert "Quick start" in EN
    leaked = [p for p in ZH_ONLY if p in EN]
    assert not leaked, f"英文入口混入了中文标题：{leaked}"


def test_chinese_readme_is_chinese():
    assert _headings(ZH, 2), "README.zh-CN.md 没有二级标题"
    assert "快速开始" in ZH
    leaked = [p for p in EN_ONLY if p in ZH]
    assert not leaked, f"中文版混入了英文标题：{leaked}"


def test_language_switcher_links_both_ways():
    """语言栏必须是真实链接，且指向的文件确实存在。"""
    assert "[简体中文](README.zh-CN.md)" in EN
    assert "[English](README.md)" in ZH
    assert (ROOT / "README.zh-CN.md").is_file()
    assert (ROOT / "README.md").is_file()


def test_exactly_one_h1_each():
    for name, text in BOTH:
        assert len(_headings(text, 1)) == 1, f"{name} 的 H1 数量是 {len(_headings(text, 1))}"


def test_code_fences_balanced():
    """围栏不成对会让整页渲染塌掉——README 最致命的格式错误。"""
    for name, text in BOTH:
        n = len([ln for ln in text.splitlines() if ln.lstrip().startswith("```")])
        assert n % 2 == 0, f"{name} 代码围栏不成对（{n} 个，应为偶数）"


def test_same_section_structure():
    """两份文档的章节数必须一致，否则翻译就是慢慢漏项的。"""
    en_n = len(_headings(EN, 2))
    zh_n = len(_headings(ZH, 2))
    assert en_n == zh_n, f"章节数不一致：英文 {en_n} vs 中文 {zh_n}"


def test_provider_table_matches_registry():
    """文档里的 Provider 表必须和 app/config.py 的注册表逐一对齐。

    这样"加了 Provider 却忘了写文档"会直接测试失败，而不是等用户发现。
    """
    from app import config

    # config.PROVIDERS 的 env_prefix 不带尾部下划线（拼环境变量名时才补），
    # 文档表格里展示的是 `PREFIX_` 这种完整形态。
    missing = [
        (name, side)
        for name, meta in config.PROVIDERS.items()
        for side, text in BOTH
        if f"`{meta['env_prefix']}_`" not in text
    ]
    assert not missing, f"以下 Provider 未在文档中记录：{missing}"


def test_key_facts_present_in_both():
    """招牌事实翻译时最容易漏，逐个点名。"""
    facts = ["deepseek-flash", "grok-4.7", "qwen3.8-27b", "claude-sonnet-5-5",
             "--jinja", "DEBUG_ENDPOINTS", "[MIT](LICENSE)", ".github/workflows/ci.yml"]
    missing = [
        (fact, side)
        for fact in facts
        for side, text in BOTH
        if fact not in text
    ]
    assert not missing, f"以下事实缺一种语言的翻译：{missing}"


def test_project_tree_lists_both_readmes():
    """结构树里两份文件都要列出，且各自把「本文件」标在自己身上。"""
    for name, text in BOTH:
        assert "README.md" in text and "README.zh-CN.md" in text, name
    assert "README.md            # English docs (this file)" in EN
    assert "README.zh-CN.md      # 简体中文文档（本文件）" in ZH


def test_authoritative_version_is_stated():
    """两份文档都要写明"以中文为准"，避免翻译漂移时扯皮。"""
    assert "is authoritative" in EN
    assert "以本文件为准" in ZH
