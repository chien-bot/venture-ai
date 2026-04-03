"""
routers/playbook.py
────────────────────────────────────────────────────────────────
创业范式库 API — Playbook listing / matching / detail
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.playbook_engine import (
    get_all_playbooks, get_playbook,
    match_playbook, cluster_projects_to_playbooks,
    format_playbook_for_student,
)

router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])


class MatchRequest(BaseModel):
    description: str = ""
    industry: str = ""
    biz_model: str = ""
    techs: list[str] = []


@router.get("/")
def list_playbooks():
    """返回全部 7 个范式概要。"""
    return {"playbooks": get_all_playbooks()}


@router.get("/{playbook_id}")
def playbook_detail(playbook_id: str):
    """返回单个范式详情 + 学生友好 markdown。"""
    pb = get_playbook(playbook_id)
    if not pb:
        raise HTTPException(status_code=404, detail="范式不存在")
    return {**pb, "student_markdown": format_playbook_for_student(playbook_id)}


@router.post("/match")
def match(req: MatchRequest):
    """根据项目描述匹配 1-2 个最佳范式。"""
    results = match_playbook(
        description=req.description,
        industry=req.industry,
        biz_model=req.biz_model,
        techs=req.techs,
    )
    return {"matches": results}


@router.post("/cluster")
def cluster():
    """从超图数据聚类，把 85 个项目匹配到 7 个范式。"""
    stats = cluster_projects_to_playbooks()
    return stats
