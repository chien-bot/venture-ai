"""Session store — now backed by SQLite via database.py."""

from services.database import (
    get_project as _db_get_project,
    save_project as _db_save_project,
    get_all_projects as _db_get_all_projects,
    update_project_scores as _db_update_project_scores,
    create_session as _db_create_session,
    bind_session_to_project as _db_bind,
    get_project_for_session as _db_get_proj_for_session,
    append_chat as _db_append_chat,
    get_chat_history as _db_get_chat_history,
    get_latest_session_for_project as _db_get_latest_session,
)

# Keep a tiny in-memory dict for arbitrary session metadata (not persisted)
_sessions: dict = {}


def get_session(session_id: str) -> dict | None:
    return _sessions.get(session_id)


def set_session(session_id: str, data: dict):
    _sessions[session_id] = data


def get_project(project_id: str) -> dict | None:
    return _db_get_project(project_id)


def set_project(project_id: str, data: dict):
    data["project_id"] = project_id
    _db_save_project(data)


def update_project_scores(project_id: str, scores: dict, stage: str | None, diagnosis: list | None):
    _db_update_project_scores(project_id, scores, stage, diagnosis or [])


def get_all_projects(owner_id: str | None = None) -> list[dict]:
    return _db_get_all_projects(owner_id)


def bind_session_to_project(session_id: str, project_id: str):
    _db_bind(session_id, project_id)


def get_project_for_session(session_id: str) -> str:
    return _db_get_proj_for_session(session_id) or ""


def get_chat_history(session_id: str) -> list[dict]:
    return _db_get_chat_history(session_id)


def append_chat(session_id: str, role: str, content: str):
    _db_append_chat(session_id, role, content)


def create_session(session_id: str, project_id: str = "", agent_type: str = "coach", owner_id: str = ""):
    _db_create_session(session_id, project_id, agent_type, owner_id)


def get_latest_session_for_project(project_id: str) -> dict | None:
    return _db_get_latest_session(project_id)


def clear_chat(session_id: str):
    pass  # Chat messages persist; clearing not needed for SQLite
