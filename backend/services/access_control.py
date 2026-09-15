"""Shared authorization checks for student project and conversation data."""

from fastapi import HTTPException, Request

from services.database import (
    get_conn, get_project, get_projects_for_user, get_user_by_token,
    get_teacher_class_ids, get_students_in_classes,
)


def require_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    user = get_user_by_token(auth[7:]) if auth.startswith("Bearer ") else None
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def require_teacher(request: Request) -> dict:
    user = require_user(request)
    if user.get("role") not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="仅教师或管理员可操作")
    return user


def require_admin(request: Request) -> dict:
    user = require_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    return user


def require_project(request: Request, project_id: str) -> dict:
    user = require_user(request)
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if user.get("role") == "teacher":
        class_ids = get_teacher_class_ids(user["user_id"])
        allowed_students = get_students_in_classes(class_ids) if class_ids else set()
        if project.get("owner_id") not in allowed_students:
            raise HTTPException(status_code=403, detail="无权访问其他班级项目")
    elif user.get("role") != "admin":
        visible_ids = {p["project_id"] for p in get_projects_for_user(user["user_id"])}
        if project_id not in visible_ids:
            raise HTTPException(status_code=403, detail="无权访问此项目")
    return project


def require_session(request: Request, session_id: str) -> dict:
    user = require_user(request)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT session_id, project_id, owner_id FROM chat_sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="对话不存在")
    session = dict(row)
    if user.get("role") not in ("teacher", "admin") and session["owner_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="无权访问此对话")
    if session["project_id"]:
        require_project(request, session["project_id"])
    return session


def require_message_access(request: Request, session_id: str, project_id: str) -> dict:
    session = require_session(request, session_id)
    if project_id:
        require_project(request, project_id)
        if session["project_id"] and session["project_id"] != project_id:
            raise HTTPException(status_code=403, detail="对话与项目不匹配")
    return session
