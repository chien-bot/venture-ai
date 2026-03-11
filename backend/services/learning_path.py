"""Personalized learning path generator (F5-adv).

Generates tasks based on weak dimensions (score < 6).
Each dimension has 2-3 template tasks with completion keywords.
"""

import uuid
from services.database import (
    get_learning_tasks, save_learning_task, get_project,
)

# ── Task templates per dimension ──────────────────────────────────
TASK_TEMPLATES = {
    "empathy": [
        {
            "title": "完成5份用户访谈",
            "description": "找到5位目标用户，围绕痛点进行深度访谈（每次≥15分钟），记录关键发现。",
            "completion_keywords": ["访谈", "用户", "采访", "调研", "interview"],
        },
        {
            "title": "绘制用户旅程地图",
            "description": "基于访谈数据，绘制用户从发现问题到尝试解决的完整旅程，标注痛点和机会点。",
            "completion_keywords": ["旅程", "journey", "地图", "流程图", "用户路径"],
        },
        {
            "title": "撰写 JTBD 声明",
            "description": "用 'When...I want to...so that...' 格式写出至少3条用户任务声明。",
            "completion_keywords": ["JTBD", "任务", "when", "want", "job"],
        },
    ],
    "ideation": [
        {
            "title": "竞品分析报告",
            "description": "分析至少3个竞品/替代方案的优劣势，找到差异化定位点。",
            "completion_keywords": ["竞品", "竞争", "对手", "分析", "差异化"],
        },
        {
            "title": "提出3种解决方案",
            "description": "针对核心痛点，头脑风暴至少3种不同方案，并评估可行性。",
            "completion_keywords": ["方案", "解决", "idea", "创意", "头脑风暴"],
        },
    ],
    "business": [
        {
            "title": "完成商业模式画布",
            "description": "填写完整的 Business Model Canvas 9个模块。",
            "completion_keywords": ["画布", "canvas", "商业模式", "BMC", "盈利"],
        },
        {
            "title": "估算 TAM/SAM/SOM",
            "description": "用自上而下或自下而上方法估算市场规模，提供数据来源。",
            "completion_keywords": ["TAM", "SAM", "SOM", "市场规模", "市场"],
        },
        {
            "title": "设计收入模型",
            "description": "明确定价策略、收入来源、单位经济模型（LTV/CAC）。",
            "completion_keywords": ["收入", "定价", "LTV", "CAC", "变现"],
        },
    ],
    "execution": [
        {
            "title": "制作 MVP 原型",
            "description": "用低成本方式（Figma/纸质原型/低代码）构建最小可行产品。",
            "completion_keywords": ["MVP", "原型", "prototype", "Figma", "demo"],
        },
        {
            "title": "获取早期用户反馈",
            "description": "让至少5位目标用户试用 MVP，收集结构化反馈。",
            "completion_keywords": ["反馈", "试用", "feedback", "测试", "体验"],
        },
    ],
    "pitching": [
        {
            "title": "撰写电梯演讲稿",
            "description": "用30秒版本和3分钟版本分别写出项目核心价值主张。",
            "completion_keywords": ["演讲", "pitch", "路演", "电梯", "演示"],
        },
        {
            "title": "准备路演 PPT",
            "description": "按7模块结构（问题→方案→市场→模式→团队→牵引力→需求）制作路演幻灯片。",
            "completion_keywords": ["PPT", "幻灯片", "slide", "路演", "deck"],
        },
    ],
}

DIM_LABELS = {
    "empathy": "痛点发现", "ideation": "方案策划",
    "business": "商业建模", "execution": "资源杠杆", "pitching": "路演表达",
}


def generate_learning_path(project_id: str) -> list[dict]:
    """Generate learning tasks based on weak dimensions (score < 6)."""
    proj = get_project(project_id)
    if not proj:
        return []

    scores = proj.get("scores", {})
    owner_id = proj.get("owner_id", "")
    tasks = []

    for dim, templates in TASK_TEMPLATES.items():
        score = scores.get(dim, 0)
        if score < 6:  # Weak dimension
            for tmpl in templates:
                task_id = f"task_{uuid.uuid4().hex[:8]}"
                task = {
                    "task_id": task_id,
                    "project_id": project_id,
                    "owner_id": owner_id,
                    "dimension": dim,
                    "title": tmpl["title"],
                    "description": tmpl["description"],
                    "completion_keywords": tmpl["completion_keywords"],
                    "status": "pending",
                }
                save_learning_task(**task)
                tasks.append(task)

    return tasks


def get_or_generate_learning_path(project_id: str) -> dict:
    """Get existing tasks or generate new ones."""
    existing = get_learning_tasks(project_id)
    if not existing:
        existing = generate_learning_path(project_id)

    # Group by dimension
    by_dim: dict[str, list] = {}
    for t in existing:
        dim = t.get("dimension", "unknown")
        by_dim.setdefault(dim, []).append(t)

    total = len(existing)
    completed = sum(1 for t in existing if t.get("status") == "completed")

    return {
        "project_id": project_id,
        "tasks": existing,
        "by_dimension": by_dim,
        "total": total,
        "completed": completed,
        "progress": round(completed / total * 100) if total else 0,
    }
