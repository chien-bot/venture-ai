from pydantic import BaseModel
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"


class LoginRequest(BaseModel):
    username: str
    password: str
    role: UserRole


class LoginResponse(BaseModel):
    token: str
    user_id: str
    username: str
    role: UserRole


class UserProfile(BaseModel):
    user_id: str
    username: str
    role: UserRole
    display_name: str = ""
    class_id: Optional[str] = None


# ── Student Project ──
class ProjectCreate(BaseModel):
    name: str
    industry: str = ""
    description: str = ""


class ProjectInfo(BaseModel):
    project_id: str
    name: str
    industry: str = ""
    description: str = ""
    stage: str = "discovery"  # discovery / ideation / modeling / execution / pitching
    owner_id: str = ""
    scores: dict = {}
    diagnosis: list = []
    created_at: str = ""


# ── Chat / Coaching ──
class ChatMessage(BaseModel):
    role: str  # user / assistant
    content: str


class ChatRequest(BaseModel):
    session_id: str
    project_id: str
    message: str
    agent_type: str = "coach"  # coach / tutor / competition / grader


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    scores: Optional[dict] = None
    diagnosis: Optional[list] = None
    stage: Optional[str] = None
    rubric_scores: Optional[dict] = None
    intent: Optional[str] = None
    knowledge_recommendations: Optional[list] = None


# ── Teacher Dashboard ──
class ClassSummary(BaseModel):
    class_id: str
    total_students: int
    total_projects: int
    avg_scores: dict = {}
    top_mistakes: list = []
    high_risk_projects: list = []
    suggestions: list = []


class ProjectReview(BaseModel):
    project_id: str
    rubric_scores: dict = {}
    evidence_trace: list = []
    revision_suggestions: list = []
    instructor_notes: str = ""


# ── Rubric ──
class RubricItem(BaseModel):
    id: str
    name: str
    description: str
    weight: float = 0.1
    score: float = 0.0
    justification: str = ""
    missing_evidence: list = []


class RubricReport(BaseModel):
    project_id: str
    items: list[RubricItem] = []
    total_score: float = 0.0
    summary: str = ""
