"""测试公共工具：把数据库指到临时文件，避免测试污染真实 data/。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# 确保仓库根在 sys.path（pytest 的 pythonpath=. 之外再兜一层）
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """把 projects 的 DATA_DIR / DB_PATH 重定向到 pytest 临时目录。"""
    from app import projects

    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "DB_PATH", tmp_path / "learning.db")
    return tmp_path / "learning.db"
