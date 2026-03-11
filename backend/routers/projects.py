from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.schemas import ProjectCreate, ProjectInfo
from services.session_store import get_project, set_project, get_all_projects
from services.database import (
    get_projects_for_user, add_team_member, remove_team_member,
    get_team_members, get_user_by_username,
)
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/")
def list_projects(owner_id: str = None):
    if owner_id:
        projects = get_projects_for_user(owner_id)
    else:
        projects = get_all_projects()
    return {"projects": projects}


@router.get("/{project_id}")
def get_project_detail(project_id: str):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    return proj


@router.post("/", response_model=ProjectInfo)
def create_project(req: ProjectCreate, owner_id: str = "student_001"):
    project_id = f"proj_{uuid.uuid4().hex[:6]}"
    project = {
        "project_id": project_id,
        "name": req.name,
        "industry": req.industry,
        "description": req.description,
        "stage": "discovery",
        "owner_id": owner_id,
        "scores": {},
        "diagnosis": [],
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    set_project(project_id, project)
    # Auto-add owner as team member
    add_team_member(project_id, owner_id, "owner")
    return ProjectInfo(**project)


# ── Team Management (F6-adv) ────────────────────────────────────────

class AddMemberRequest(BaseModel):
    username: str


@router.get("/{project_id}/team")
def get_team(project_id: str):
    members = get_team_members(project_id)
    return {"project_id": project_id, "members": members}


@router.post("/{project_id}/team")
def add_member(project_id: str, req: AddMemberRequest):
    user = get_user_by_username(req.username)
    if not user:
        raise HTTPException(status_code=404, detail=f"用户 '{req.username}' 不存在")
    add_team_member(project_id, user["user_id"], "member")
    return {"ok": True, "user_id": user["user_id"], "username": req.username}


@router.delete("/{project_id}/team/{user_id}")
def remove_member(project_id: str, user_id: str):
    remove_team_member(project_id, user_id)
    return {"ok": True}
