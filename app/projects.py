"""练手项目库：SQLite 持久化 + 内置种子项目 + 由大模型生成新项目。

项目库是本项目的第二块核心能力：
- 内置一批 Python 练手项目（按难度分级），用户可浏览、筛选、勾选完成；
- 用户可以输入任意语言（如 C、Java）和主题，让大模型生成新项目并入库，
  从而把项目库从「Python 专属」扩展成「多语言」。
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from pydantic import BaseModel, Field

from . import llm

# 数据库文件位于 data/learning.db，首次运行自动创建
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "learning.db"

# 内置种子项目：只含 Python（体现「基础项目只有 Python 相关」），
# 其他语言的项目由「AI 生成新项目」功能动态加入。
SEED_PROJECTS = [
    {
        "language": "Python", "difficulty": "入门",
        "title": "猜数字游戏",
        "description": "程序随机生成 1-100 的整数，玩家通过输入不断猜测，直到猜中。",
        "knowledge_points": ["random 随机数", "while 循环", "条件判断 if/elif/else", "input 输入"],
        "acceptance_criteria": ["能提示数字偏大/偏小", "能统计猜的次数", "猜中后询问是否再来一局"],
    },
    {
        "language": "Python", "difficulty": "入门",
        "title": "命令行待办清单",
        "description": "在终端里管理待办事项：添加、查看、标记完成、删除。",
        "knowledge_points": ["列表与字典", "文件读写", "命令行交互"],
        "acceptance_criteria": ["数据能保存到本地文件", "重启程序后待办不丢失", "支持增删改查四种操作"],
    },
    {
        "language": "Python", "difficulty": "入门",
        "title": "简易计算器",
        "description": "支持加减乘除、括号和连续运算的命令行计算器。",
        "knowledge_points": ["函数定义", "异常处理 try/except", "字符串解析"],
        "acceptance_criteria": ["能处理除数为零的错误", "非法输入不崩溃", "支持连续运算"],
    },
    {
        "language": "Python", "difficulty": "进阶",
        "title": "天气查询工具",
        "description": "输入城市名，调用免费天气 API（如 wttr.in）查询并展示当前天气。",
        "knowledge_points": ["HTTP 请求 requests/urllib", "JSON 解析", "API 调用与错误处理"],
        "acceptance_criteria": ["能查询任意城市天气", "网络异常时有友好提示", "输出格式清晰易读"],
    },
    {
        "language": "Python", "difficulty": "进阶",
        "title": "豆瓣电影 Top250 爬虫",
        "description": "抓取豆瓣电影 Top250 榜单，提取片名、评分、导演等信息并导出为 CSV。",
        "knowledge_points": ["urllib/requests 请求", "HTML 解析", "CSV 导出", "请求频率控制"],
        "acceptance_criteria": ["能抓到完整 250 条", "导出 CSV 可用 Excel 打开", "请求间隔合理不触发封禁"],
    },
    {
        "language": "Python", "difficulty": "进阶",
        "title": "学生成绩统计分析",
        "description": "读取 CSV 格式的成绩表，计算总分、平均分、最高/最低分，并输出排名。",
        "knowledge_points": ["CSV 文件读取", "数据结构与统计", "可选：matplotlib 可视化"],
        "acceptance_criteria": ["支持任意列数的成绩表", "能按总分排序输出排名", "统计结果与手算一致"],
    },
    {
        "language": "Python", "difficulty": "实战",
        "title": "个人记账本（Web 版）",
        "description": "做一个浏览器访问的记账应用：记录收支、分类统计、按月汇总。",
        "knowledge_points": ["FastAPI/Flask 基础", "SQLite 数据库", "前端页面与后端接口"],
        "acceptance_criteria": ["能新增/删除收支记录", "能按分类统计占比", "数据持久化不丢失"],
    },
    {
        "language": "Python", "difficulty": "实战",
        "title": "文件自动整理器",
        "description": "扫描指定文件夹，按扩展名把文件自动归类到 图片/文档/视频/压缩包 等子目录。",
        "knowledge_points": ["os/shutil 文件操作", "pathlib 路径处理", "批处理与幂等性"],
        "acceptance_criteria": ["能按类型正确归类", "重复运行不产生重复文件", "支持干跑模式（只预览不移动）"],
    },
]


# ---- 单进程共享一个 SQLite 连接 ----
# 本项目是单机单用户应用，按请求新开连接的做法有三个问题：
#   1. 每次请求都做 mkdir + open + close，纯属浪费；
#   2. FastAPI 的同步路由跑在线程池里，多请求并发写同一文件时
#      SQLite 会抛 "database is locked"；
#   3. 测试要把 DB 重定向到临时文件，每请求重连会让替换时机变得难料。
# 因此连接在模块级惰性建立一次，所有读写共用，并用锁串行化。
# sqlite3.connect 的 check_same_thread=False 允许跨线程使用，
# 但真正保证安全的是我们自己这把锁（见 _locked）。
_conn: sqlite3.Connection | None = None
_lock = threading.RLock()


def _connection() -> sqlite3.Connection:
    """惰性建立（并复用）数据库连接；表结构在 init_db() 里建。"""
    global _conn
    if _conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _conn = conn
    return _conn


class _locked:
    """把临界区包起来的上下文管理器（可重入，读写的串行化都靠它）。"""

    def __enter__(self) -> sqlite3.Connection:
        _lock.acquire()
        return _connection()

    def __exit__(self, *exc_info) -> None:
        try:
            if exc_info[0] is None:
                _connection().commit()
        finally:
            _lock.release()


def reset_connection() -> None:
    """丢弃当前连接（测试重定向 DATA_DIR/DB_PATH 后必须调用，否则指向旧库）。"""
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


def init_db() -> None:
    """建表 + 首次运行时写入种子项目。"""
    with _locked() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                knowledge_points TEXT NOT NULL,
                acceptance_criteria TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'builtin',
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) AS c FROM projects").fetchone()["c"]
        if count == 0:
            for item in SEED_PROJECTS:
                conn.execute(
                    "INSERT INTO projects(language, difficulty, title, description, knowledge_points, acceptance_criteria, source)"
                    " VALUES (?, ?, ?, ?, ?, ?, 'builtin')",
                    (
                        item["language"],
                        item["difficulty"],
                        item["title"],
                        item["description"],
                        json.dumps(item["knowledge_points"], ensure_ascii=False),
                        json.dumps(item["acceptance_criteria"], ensure_ascii=False),
                    ),
                )


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "language": row["language"],
        "difficulty": row["difficulty"],
        "title": row["title"],
        "description": row["description"],
        "knowledge_points": json.loads(row["knowledge_points"]),
        "acceptance_criteria": json.loads(row["acceptance_criteria"]),
        "source": row["source"],
        "done": bool(row["done"]),
        "created_at": row["created_at"],
    }


def list_projects(language: str | None = None, difficulty: str | None = None) -> list[dict]:
    """查询项目库，支持按语言、难度过滤。"""
    sql = "SELECT * FROM projects WHERE 1=1"
    args: list = []
    if language:
        sql += " AND language = ?"
        args.append(language)
    if difficulty:
        sql += " AND difficulty = ?"
        args.append(difficulty)
    sql += " ORDER BY id"
    with _locked() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_languages() -> list[str]:
    """返回项目库中已有的语言列表（用于前端筛选）。"""
    with _locked() as conn:
        rows = conn.execute("SELECT DISTINCT language FROM projects ORDER BY language").fetchall()
    return [r["language"] for r in rows]


def mark_done(project_id: int, done: bool) -> None:
    with _locked() as conn:
        conn.execute("UPDATE projects SET done = ? WHERE id = ?", (1 if done else 0, project_id))


def delete_project(project_id: int) -> None:
    with _locked() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


def add_project(data: dict, source: str = "generated") -> dict:
    """写入一个项目，返回含自增 id 的完整记录。"""
    with _locked() as conn:
        cur = conn.execute(
            "INSERT INTO projects(language, difficulty, title, description, knowledge_points, acceptance_criteria, source)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                data["language"],
                data["difficulty"],
                data["title"],
                data["description"],
                json.dumps(data["knowledge_points"], ensure_ascii=False),
                json.dumps(data["acceptance_criteria"], ensure_ascii=False),
                source,
            ),
        )
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_to_dict(row)


# 生成新项目的提示词：约束模型只输出 JSON 数组
GENERATE_PROMPT = """你是一名编程教学专家。请根据用户要求生成练手项目。
要求：
1. 只输出一个 JSON 数组，不要输出任何 markdown、解释或多余文字。
2. 数组中的每个元素结构固定如下：
{
  "title": "项目名称",
  "difficulty": "入门 / 进阶 / 实战 三选一",
  "description": "项目简介（2-3 句话，说明要做什么）",
  "knowledge_points": ["涉及的知识点1", "知识点2"],
  "acceptance_criteria": ["验收标准1（可检验）", "验收标准2"]
}
3. 项目必须具体、可执行，难度从低到高排列。
4. 不要生成任何敏感、违法或与编程学习无关的内容。
"""

# 难度白名单：模型乱写时归一，保证前端筛选不会漏
_DIFFICULTIES = ("入门", "进阶", "实战")


class GeneratedProject(BaseModel):
    """LLM 生成的单个项目结构（缺字段时给默认值）。"""

    title: str
    difficulty: str = "入门"
    description: str = ""
    knowledge_points: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)

    def to_row(self, language: str) -> dict:
        """转成入库用的 dict，并把 difficulty 归一到白名单内。"""
        difficulty = self.difficulty if self.difficulty in _DIFFICULTIES else "进阶"
        return {
            "language": language,
            "difficulty": difficulty,
            "title": self.title.strip(),
            "description": self.description.strip(),
            "knowledge_points": self.knowledge_points,
            "acceptance_criteria": self.acceptance_criteria,
        }


def generate_projects(
    language: str,
    count: int = 3,
    topic: str = "",
    provider: str | None = None,
) -> list[dict]:
    """让大模型生成指定语言/主题的练手项目，逐个校验后写入项目库。"""
    user_content = f"语言：{language}。"
    if topic:
        user_content += f"主题/方向：{topic}。"
    user_content += f"请生成 {count} 个练手项目。"

    messages = [
        {"role": "system", "content": GENERATE_PROMPT},
        {"role": "user", "content": user_content},
    ]
    text = llm.chat(messages, provider=provider, json_mode=True)
    try:
        raw = json.loads(text)
        if not isinstance(raw, list):
            raise ValueError("模型输出不是数组")
        parsed = [GeneratedProject.model_validate(item) for item in raw]
    except Exception as exc:
        raise llm.LLMError(f"模型输出无法解析为项目列表：{exc}") from exc

    language = language.strip() or "Python"
    created = []
    for item in parsed[:count]:
        if not item.title.strip():
            continue
        created.append(add_project(item.to_row(language), source="generated"))
    if not created:
        raise llm.LLMError("模型没有生成出有效项目，请重试")
    return created
