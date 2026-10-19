"""学习路线生成：约束大模型输出结构化 JSON，并可选接入搜索增强（防幻觉）。

简历可讲点：
1. 结构化输出设计——用 system prompt 把模型输出约束为固定 JSON schema，
   前端直接渲染，而不是解析散文；
2. 搜索增强——把真实资料链接喂给模型，要求其引用真实链接，降低编造幻觉。
"""
from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from . import llm, search

# 系统提示词：要求模型只输出 JSON，字段结构固定
SYSTEM_PROMPT = """你是一名资深的编程学习规划师。用户会告诉你他的基础、目标和可投入时间，
请你为他生成一份个性化、可执行的学习路线。

要求：
1. 只输出一个 JSON 对象，不要输出任何 markdown、解释或多余文字。
2. JSON 结构固定如下：
{
  "summary": "一句话概括这条路线",
  "stages": [
    {
      "title": "阶段名称",
      "goal": "本阶段学习目标",
      "topics": ["知识点1", "知识点2"],
      "projects": ["练手项目1（要具体、可执行）", "练手项目2"],
      "resources": ["参考资源（尽量给出真实可查的教程名或链接）"],
      "estimated_weeks": 2,
      "checklist": ["本阶段验收标准1", "验收标准2"]
    }
  ],
  "generated_projects": [
    {
      "language": "C",
      "difficulty": "入门 / 进阶 / 实战 三选一",
      "title": "项目名称",
      "description": "项目简介（2-3 句话，说明要做什么）",
      "knowledge_points": ["涉及的知识点1", "知识点2"],
      "acceptance_criteria": ["验收标准1（可检验）", "验收标准2"]
    }
  ]
}
3. stages 数量 4 到 6 个，由浅入深、循序渐进。
4. 如果用户给出了明确的学习目标（如数据分析、爬虫、Web 开发），
   路线要围绕该目标设计，不要泛泛而谈。
5. estimated_weeks 必须是整数，代表建议投入的周数。
6. generated_projects：只有当用户明确要求"生成/增加/添加 练手项目"时才填写；
   language（语言）、数量、主题必须取自用户原话，难度从低到高排列；
   用户没有提出任何加项目的要求时，必须输出空数组 []。
"""

# LLM 输出的结构约束（pydantic 校验，容忍字段缺失与多余字段）
_DIFFICULTIES = ("入门", "进阶", "实战")


class RouteProject(BaseModel):
    """generated_projects 数组元素的结构。"""

    language: str = "Python"
    difficulty: str = "入门"
    title: str
    description: str = ""
    knowledge_points: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class RouteStage(BaseModel):
    """stages 数组元素的结构。"""

    title: str = ""
    goal: str = ""
    topics: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    estimated_weeks: int = 2
    checklist: list[str] = Field(default_factory=list)


class Route(BaseModel):
    """整条学习路线的结构。"""

    summary: str
    stages: list[RouteStage]
    generated_projects: list[RouteProject] = Field(default_factory=list)


def _extract_json(text: str) -> dict:
    """从模型输出中稳健地解析 JSON（容忍 markdown 代码块等噪音）。"""
    text = text.strip()
    # 去掉可能的 ```json ... ``` 代码块包裹
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 退而求其次：截取第一个 { 到最后一个 } 之间的内容再解析
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
        raise


def generate_route(
    user_input: str,
    provider: str | None = None,
    use_search: bool = True,
) -> dict:
    """根据用户描述生成学习路线（结构化 JSON）。

    参数：
        user_input: 用户填写的现状与目标描述
        provider:   指定使用哪个大模型 Provider（None 则用默认）
        use_search: 是否启用搜索增强（把真实资料链接喂给模型，降低幻觉）
    """
    user_content = f"我的情况：{user_input}\n请为我生成学习路线。"

    if use_search:
        # 搜索真实资料并附进提示词，让模型引用真实链接而不是编造
        results = search.search(f"{user_input} 学习路线 教程")
        if results:
            links = "\n".join(f"- {item['title']} {item['url']}" for item in results[:5])
            user_content += (
                "\n\n下面是我搜索到的真实参考资料，"
                "请尽量引用其中的链接（这些链接经核实，比你自己编造更可靠）：\n"
                + links
            )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    text = llm.chat(messages, provider=provider, json_mode=True)
    try:
        raw = _extract_json(text)
    except Exception as exc:
        raise llm.LLMError(f"模型输出无法解析为路线 JSON：{exc}") from exc

    # pydantic 兜底校验：模型漏字段/类型错时给明确错误，而不是到前端才崩
    try:
        route = Route.model_validate(raw)
    except Exception as exc:
        raise llm.LLMError(f"模型输出不符合路线结构：{exc}") from exc

    return route.model_dump()
