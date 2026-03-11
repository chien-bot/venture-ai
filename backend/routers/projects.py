from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from models.schemas import ProjectCreate, ProjectInfo
from services.session_store import get_project, set_project, get_all_projects, bind_session_to_project
from services.database import (
    get_projects_for_user, add_team_member, remove_team_member,
    get_team_members, get_user_by_username, get_user_by_token,
)
import uuid
import re
from datetime import datetime

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_current_user(request: Request) -> dict | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        return get_user_by_token(token)
    return None


@router.get("/")
def list_projects(request: Request):
    user = _get_current_user(request)
    if user and user.get("role") == "student":
        projects = get_projects_for_user(user["user_id"])
    elif user and user.get("role") == "teacher":
        projects = get_all_projects()
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
def create_project(req: ProjectCreate, request: Request, owner_id: str = "student_001"):
    user = _get_current_user(request)
    if user:
        owner_id = user["user_id"]
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


# ── Auto-infer project from chat text ──────────────────────────────

class AutoInferRequest(BaseModel):
    text: str


# Industry keywords for heuristic matching
_INDUSTRY_PATTERNS = [
    (["医疗", "健康", "诊断", "眼科", "病", "患者", "医院", "药"], "医疗健康"),
    (["教育", "学习", "学生", "课程", "培训", "考试"], "教育科技"),
    (["农业", "农村", "种植", "养殖", "农民"], "农业科技"),
    (["金融", "理财", "投资", "银行", "保险", "支付"], "金融科技"),
    (["物流", "仓储", "配送", "运输", "供应链"], "物流供应链"),
    (["环保", "碳", "新能源", "光伏", "储能", "绿色"], "节能环保"),
    (["零售", "电商", "购物", "消费", "商城"], "新零售"),
    (["餐饮", "食品", "外卖", "烹饪", "厨房"], "餐饮食品"),
    (["房地产", "建筑", "装修", "物业"], "房地产建筑"),
    (["旅游", "酒店", "民宿", "景区", "出行"], "文旅出行"),
    (["游戏", "娱乐", "直播", "内容", "短视频"], "文娱传媒"),
    (["制造", "工业", "自动化", "机器人", "生产"], "先进制造"),
    (["AI", "人工智能", "大模型", "机器学习", "深度学习"], "人工智能"),
]


def _heuristic_infer(text: str) -> dict:
    """Extract project name and industry from free text using heuristics."""
    # Try to find project name patterns
    name_patterns = [
        r"(做|做一个|开发|研发|想做|计划做)\s*[一个]?\s*([^\s，。！？、,!?]{4,20}(?:系统|平台|APP|应用|产品|工具|服务|方案))",
        r"([^\s，。！？、,!?]{2,15}(?:系统|平台|APP|应用|产品|工具|服务|方案))",
        r"(我的项目[是叫]?|项目名[称叫]?|项目[是叫]?)[：:「]?\s*([^\s，。！？「」,!?]{3,20})",
    ]
    name = ""
    for pattern in name_patterns:
        m = re.search(pattern, text)
        if m:
            name = m.group(2) if len(m.groups()) >= 2 else m.group(1)
            name = name.strip("「」""''")
            if len(name) >= 4:
                break

    # Fallback: take first sentence as rough name
    if not name:
        first = re.split(r"[，。！？\n]", text)[0].strip()
        if 5 <= len(first) <= 25:
            name = first

    # Detect industry
    industry = ""
    for keywords, label in _INDUSTRY_PATTERNS:
        if any(kw in text for kw in keywords):
            industry = label
            break

    return {"name": name[:30] if name else "", "industry": industry, "description": ""}


@router.post("/auto-infer")
def auto_infer_project(req: AutoInferRequest, request: Request):
    """
    Infer project name and industry from free text.
    First tries LLM, falls back to heuristics.
    """
    from config import USE_MOCK_API
    result = {"name": "", "industry": "", "description": ""}

    if not USE_MOCK_API:
        try:
            from services.claude_client import chat_completion
            from config import MODEL_LIGHT
            system = """从用户描述中提取创业项目信息。
只输出 JSON，格式：{"name": "项目名称", "industry": "行业", "description": "一句话描述"}
- name: 4-20字，描述项目的核心产品/服务，不要包含"我的项目"等词
- industry: 从以下选择：医疗健康/教育科技/农业科技/金融科技/物流供应链/节能环保/新零售/餐饮食品/人工智能/先进制造/文旅出行/文娱传媒/其他
- description: 一句话说明项目价值主张
如果信息不足，name 输出空字符串""。"""
            msgs = [{"role": "user", "content": req.text}]
            raw = chat_completion(system, msgs, model=MODEL_LIGHT)
            import json
            m = re.search(r'\{.*?\}', raw, re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))
                result = {
                    "name": parsed.get("name", "")[:30],
                    "industry": parsed.get("industry", ""),
                    "description": parsed.get("description", ""),
                }
        except Exception:
            pass

    # Fallback to heuristics if LLM failed or returned empty name
    if not result.get("name"):
        result = _heuristic_infer(req.text)

    return result


# ── Bind session to project ─────────────────────────────────────────

class BindSessionRequest(BaseModel):
    session_id: str
    project_id: str


@router.post("/bind-session")
def bind_session(req: BindSessionRequest):
    bind_session_to_project(req.session_id, req.project_id)
    return {"ok": True}


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
