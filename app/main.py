"""FastAPI 入口：提供前端页面与全部后端接口。

启动方式（项目根目录下）：
    python run.py
然后浏览器访问 http://127.0.0.1:8000
接口文档（FastAPI 自带）：http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, llm, planner, projects, search

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 首次启动初始化数据库（建表 + 写入种子项目）。
    # 放在 lifespan 里而不是 import 阶段：uvicorn --reload 与测试
    # 直接 import app 时不会重复执行，也不会有 import 副作用。
    projects.init_db()
    yield


app = FastAPI(
    title="Python 学习路线助手",
    description="输入学习需求 → AI 生成个性化学习路线；内置练手项目库，支持 AI 生成新项目（多语言）。",
    version="0.2.0",
    lifespan=lifespan,
)


# ---------- 请求体模型 ----------

class RouteRequest(BaseModel):
    user_input: str = Field(..., description="用户的学习需求描述")
    provider: str | None = Field(None, description="使用的模型 Provider，空则用默认")
    use_search: bool = Field(True, description="是否启用搜索增强")


class GenerateProjectsRequest(BaseModel):
    language: str = Field("Python", description="目标语言")
    count: int = Field(3, ge=1, le=10, description="生成项目数量")
    topic: str = Field("", description="主题/方向，可空")
    provider: str | None = Field(None, description="使用的模型 Provider")


class DoneRequest(BaseModel):
    done: bool = Field(True, description="是否标记为完成")


# ---------- 页面 ----------

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


# ---------- 元信息 ----------

@app.get("/api/models")
def get_models():
    """返回默认 Provider、可用 Provider 列表和搜索是否可用。"""
    return {
        "default_provider": config.DEFAULT_PROVIDER,
        "providers": llm.available_providers(),
        "search_enabled": search.search_enabled(),
    }


# ---------- 学习路线 ----------

@app.post("/api/route")
def create_route(req: RouteRequest):
    """生成学习路线；若用户在同一句话里要求加练手项目，
    模型输出的 generated_projects 会自动校验并写入项目库。"""
    if not req.user_input.strip():
        raise HTTPException(status_code=400, detail="请描述你的学习需求")
    try:
        route = planner.generate_route(
            req.user_input.strip(),
            provider=req.provider,
            use_search=req.use_search,
        )
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 模型按用户要求输出了新项目 → 校验后入库
    added = []
    for item in route.get("generated_projects") or []:
        if not str(item.get("title", "")).strip():
            continue
        data = {
            "language": str(item.get("language", "")).strip() or "Python",
            "difficulty": str(item.get("difficulty", "入门")).strip() or "入门",
            "title": str(item.get("title", "")).strip(),
            "description": str(item.get("description", "")).strip(),
            "knowledge_points": item.get("knowledge_points") or [],
            "acceptance_criteria": item.get("acceptance_criteria") or [],
        }
        added.append(projects.add_project(data, source="generated"))

    return {
        "route": route,
        "added_projects": added,
    }


# ---------- 项目库 ----------

@app.get("/api/projects")
def get_projects(language: str | None = None, difficulty: str | None = None):
    """项目列表，附带全部语言清单（供前端筛选下拉使用）。"""
    return {
        "languages": projects.list_languages(),
        "projects": projects.list_projects(language=language, difficulty=difficulty),
    }


@app.post("/api/projects/generate")
def create_projects(req: GenerateProjectsRequest):
    """让 AI 生成新项目并入库（支持任意语言，如 C、Java）。"""
    try:
        return projects.generate_projects(
            req.language.strip(),
            count=req.count,
            topic=req.topic.strip(),
            provider=req.provider,
        )
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/done")
def update_done(project_id: int, req: DoneRequest):
    projects.mark_done(project_id, req.done)
    return {"ok": True}


@app.delete("/api/projects/{project_id}")
def remove_project(project_id: int):
    projects.delete_project(project_id)
    return {"ok": True}


# ---------- 搜索（查资料/调试用） ----------

@app.get("/api/search")
def do_search(q: str = Query(..., min_length=1, max_length=200, description="搜索关键词")):
    """测试搜索能力，返回原始搜索结果。

    注意：这是调试口，每次调用都会消耗搜索 API 配额，日常请用页面上的
    「搜索增强」开关（路线生成时才搜索）。
    """
    return {"results": search.search(q)}


# 挂载静态资源目录（CSS/JS 内联在 index.html 中，此目录目前仅备用）
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
