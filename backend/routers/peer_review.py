"""Peer review router for anonymous student-to-student reviews (F4-adv)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import uuid

from services.database import (
    create_review_assignment, get_review_assignments,
    save_peer_review, get_peer_reviews_for_project,
    get_all_projects, get_project, get_conn,
)

from services.access_control import require_project, require_teacher, require_user

router = APIRouter(prefix="/api/peer-review", tags=["peer-review"], dependencies=[Depends(require_user)])


def _same_class(student_id: str, project: dict) -> bool:
    with get_conn() as conn:
        student = conn.execute("SELECT class_id FROM users WHERE user_id=?", (student_id,)).fetchone()
        owner = conn.execute("SELECT class_id FROM users WHERE user_id=?", (project.get("owner_id"),)).fetchone()
    return bool(student and owner and student["class_id"] and student["class_id"] == owner["class_id"])


class AssignReviewRequest(BaseModel):
    reviewer_id: str
    project_id: str
    assigned_by: str = "volunteer"


class SubmitReviewRequest(BaseModel):
    assignment_id: str
    project_id: str
    scores: dict       # {empathy: 7, ideation: 6, ...}
    comments: dict     # {empathy: "comment", ...}
    overall_comment: str = ""


@router.get("/assignments/{user_id}")
def get_my_assignments(user_id: str, request: Request):
    """Get all review assignments for a student."""
    user = require_user(request)
    if user.get("role") not in ("teacher", "admin") and user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="无权查看他人的评审任务")
    assignments = get_review_assignments(reviewer_id=user_id)
    return {"assignments": assignments}


@router.post("/assign")
def assign_review(req: AssignReviewRequest, request: Request):
    """Assign a review task (teacher or volunteer)."""
    user = require_user(request)
    reviewer_id = req.reviewer_id
    assigned_by = req.assigned_by
    if user.get("role") == "student":
        reviewer_id = user["user_id"]
        assigned_by = "volunteer"
    else:
        require_teacher(request)
    proj = get_project(req.project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    if user.get("role") == "student" and not _same_class(reviewer_id, proj):
        raise HTTPException(status_code=403, detail="只能评审本班已开放的项目")
    if user.get("role") in ("teacher", "admin"):
        require_project(request, req.project_id)
    if proj.get("owner_id") == reviewer_id:
        raise HTTPException(status_code=400, detail="不能评审自己的项目")

    # Check if already assigned
    existing = get_review_assignments(reviewer_id=reviewer_id)
    for a in existing:
        if a["project_id"] == req.project_id and a["status"] == "pending":
            return {"ok": True, "assignment_id": a["assignment_id"], "message": "已分配"}

    assignment_id = f"assign_{uuid.uuid4().hex[:8]}"
    create_review_assignment(assignment_id, reviewer_id, req.project_id, assigned_by)
    return {"ok": True, "assignment_id": assignment_id}


@router.post("/submit")
def submit_review(req: SubmitReviewRequest, request: Request):
    """Submit a peer review with scores and comments."""
    user = require_user(request)
    # Validate scores
    dims = ["empathy", "ideation", "business", "execution", "pitching"]
    if set(req.scores) != set(dims) or set(req.comments) != set(dims):
        raise HTTPException(status_code=422, detail="必须完成五个维度的评分与意见")
    for d in dims:
        if d in req.scores and not (0 <= req.scores[d] <= 10):
            raise HTTPException(status_code=400, detail=f"{d} 分数必须在 0-10 之间")

    review_id = f"review_{uuid.uuid4().hex[:8]}"
    # reviewer_id derived from assignment
    assignments = get_review_assignments(project_id=req.project_id)
    assignment = next((a for a in assignments if a["assignment_id"] == req.assignment_id), None)
    if not assignment:
        raise HTTPException(status_code=404, detail="评审任务不存在")
    if user.get("role") not in ("teacher", "admin") and assignment["reviewer_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="无权提交此评审任务")

    save_peer_review(
        review_id=review_id,
        assignment_id=req.assignment_id,
        reviewer_id=assignment["reviewer_id"],
        project_id=req.project_id,
        scores=req.scores,
        comments=req.comments,
        overall_comment=req.overall_comment,
    )
    return {"ok": True, "review_id": review_id}


@router.get("/received/{project_id}")
def get_received_reviews(project_id: str, request: Request):
    """Get all anonymized reviews for a project."""
    require_project(request, project_id)
    reviews = get_peer_reviews_for_project(project_id)
    return {"project_id": project_id, "reviews": reviews, "total": len(reviews)}


@router.get("/available")
def get_available_projects(request: Request, user_id: str = ""):
    """List projects available for volunteer review (exclude own)."""
    user = require_user(request)
    user_id = user["user_id"]
    all_projects = get_all_projects()
    available = [
        {"project_id": p["project_id"], "name": p["name"], "industry": p.get("industry", ""),
         "description": p.get("description", "")[:100], "stage": p.get("stage", "")}
        for p in all_projects
        if p.get("owner_id") != user_id and (user.get("role") != "student" or _same_class(user_id, p))
    ]
    return {"projects": available}
