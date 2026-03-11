"""SQLite persistence layer for VentureAI."""

import sqlite3
import json
import os
from pathlib import Path
from mock.responses import MOCK_USERS, MOCK_PROJECTS

DB_PATH = Path(__file__).parent.parent / "venture_ai.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables and seed initial data if empty."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     TEXT PRIMARY KEY,
                username    TEXT UNIQUE NOT NULL,
                password    TEXT NOT NULL,
                role        TEXT NOT NULL,
                display_name TEXT,
                class_id    TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS auth_tokens (
                token       TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS projects (
                project_id   TEXT PRIMARY KEY,
                owner_id     TEXT NOT NULL,
                name         TEXT NOT NULL,
                industry     TEXT,
                description  TEXT,
                stage        TEXT DEFAULT 'discovery',
                scores_json  TEXT DEFAULT '{}',
                diagnosis_json TEXT DEFAULT '[]',
                created_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id  TEXT PRIMARY KEY,
                project_id  TEXT,
                agent_type  TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS score_snapshots (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id   TEXT NOT NULL,
                scores_json  TEXT NOT NULL,
                stage        TEXT,
                round_num    INTEGER DEFAULT 1,
                created_at   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS interview_analyses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id   TEXT NOT NULL,
                raw_text     TEXT NOT NULL,
                result_json  TEXT NOT NULL,
                created_at   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS pitch_checks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id   TEXT NOT NULL,
                outline_text TEXT NOT NULL,
                result_json  TEXT NOT NULL,
                created_at   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS annotations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  TEXT NOT NULL,
                session_id  TEXT NOT NULL,
                message_idx INTEGER NOT NULL,
                teacher_id  TEXT NOT NULL,
                action      TEXT NOT NULL,
                note_text   TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS session_ratings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL UNIQUE,
                project_id  TEXT NOT NULL,
                student_id  TEXT NOT NULL,
                rating      INTEGER NOT NULL,
                comment     TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS team_members (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                role        TEXT DEFAULT 'member',
                joined_at   TEXT DEFAULT (datetime('now')),
                UNIQUE(project_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS uploaded_files (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id         TEXT UNIQUE NOT NULL,
                project_id      TEXT,
                session_id      TEXT,
                filename        TEXT NOT NULL,
                file_type       TEXT NOT NULL,
                extracted_text  TEXT DEFAULT '',
                file_size       INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS weekly_reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      TEXT NOT NULL,
                owner_id        TEXT NOT NULL,
                week_start      TEXT NOT NULL,
                week_end        TEXT NOT NULL,
                summary_json    TEXT NOT NULL,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS review_assignments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id   TEXT UNIQUE NOT NULL,
                reviewer_id     TEXT NOT NULL,
                project_id      TEXT NOT NULL,
                status          TEXT DEFAULT 'pending',
                assigned_by     TEXT DEFAULT 'system',
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS peer_reviews (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id       TEXT UNIQUE NOT NULL,
                assignment_id   TEXT NOT NULL,
                reviewer_id     TEXT NOT NULL,
                project_id      TEXT NOT NULL,
                scores_json     TEXT NOT NULL,
                comments_json   TEXT NOT NULL,
                overall_comment TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS learning_tasks (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id             TEXT UNIQUE NOT NULL,
                project_id          TEXT NOT NULL,
                owner_id            TEXT NOT NULL,
                dimension           TEXT NOT NULL,
                title               TEXT NOT NULL,
                description         TEXT DEFAULT '',
                completion_keywords TEXT DEFAULT '[]',
                status              TEXT DEFAULT 'pending',
                completed_at        TEXT,
                created_at          TEXT DEFAULT (datetime('now'))
            );
        """)

        # Add competition_date column if not exists (safe migration)
        try:
            conn.execute("ALTER TABLE projects ADD COLUMN competition_date TEXT")
        except Exception:
            pass  # column already exists

        # Seed users
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing == 0:
            for user in MOCK_USERS.values():
                conn.execute(
                    "INSERT OR IGNORE INTO users (user_id, username, password, role, display_name, class_id) VALUES (?,?,?,?,?,?)",
                    (user["user_id"], user["username"], user["password"],
                     user["role"], user["display_name"], user["class_id"])
                )

        # Seed projects
        existing_proj = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if existing_proj == 0:
            for proj in MOCK_PROJECTS:
                conn.execute(
                    """INSERT OR IGNORE INTO projects
                       (project_id, owner_id, name, industry, description, stage, scores_json, diagnosis_json, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (proj["project_id"], proj["owner_id"], proj["name"],
                     proj.get("industry", ""), proj.get("description", ""),
                     proj.get("stage", "discovery"),
                     json.dumps(proj.get("scores", {})),
                     json.dumps(proj.get("diagnosis", [])),
                     proj.get("created_at", "2026-01-01"))
                )

        # Seed team_members (owners as role='owner')
        existing_tm = conn.execute("SELECT COUNT(*) FROM team_members").fetchone()[0]
        if existing_tm == 0:
            rows = conn.execute("SELECT project_id, owner_id FROM projects").fetchall()
            for r in rows:
                conn.execute(
                    "INSERT OR IGNORE INTO team_members (project_id, user_id, role) VALUES (?,?,?)",
                    (r["project_id"], r["owner_id"], "owner")
                )


# ── User / Auth ────────────────────────────────────────────────────

def get_user_by_username(username: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None


def save_token(token: str, user_id: str):
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO auth_tokens (token, user_id) VALUES (?,?)", (token, user_id))


def get_user_by_token(token: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT u.* FROM users u JOIN auth_tokens t ON u.user_id=t.user_id WHERE t.token=?",
            (token,)
        ).fetchone()
        return dict(row) if row else None


def delete_token(token: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM auth_tokens WHERE token=?", (token,))


# ── Projects ───────────────────────────────────────────────────────

def get_project(project_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if not row:
            return None
        return _hydrate_project(dict(row))


def get_all_projects(owner_id: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if owner_id:
            rows = conn.execute("SELECT * FROM projects WHERE owner_id=? ORDER BY created_at DESC", (owner_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [_hydrate_project(dict(r)) for r in rows]


def save_project(project: dict):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO projects
               (project_id, owner_id, name, industry, description, stage, scores_json, diagnosis_json, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (project["project_id"], project["owner_id"], project["name"],
             project.get("industry", ""), project.get("description", ""),
             project.get("stage", "discovery"),
             json.dumps(project.get("scores", {})),
             json.dumps(project.get("diagnosis", [])),
             project.get("created_at", ""))
        )


def update_project_scores(project_id: str, scores: dict, stage: str | None, diagnosis: list):
    proj = get_project(project_id)
    if not proj:
        return
    if scores:
        proj["scores"] = scores
    if diagnosis:
        proj["diagnosis"] = diagnosis
    new_stage = proj.get("stage", "discovery")
    if stage:
        new_stage = _auto_advance_stage(proj.get("stage", "discovery"), stage)
        proj["stage"] = new_stage
    save_project(proj)
    # Auto-snapshot scores for timeline
    if scores and any(v > 0 for v in scores.values()):
        save_score_snapshot(project_id, scores, new_stage)


def _auto_advance_stage(current: str, suggested: str) -> str:
    ORDER = ["discovery", "ideation", "modeling", "execution", "pitching"]
    ci = ORDER.index(current) if current in ORDER else 0
    si = ORDER.index(suggested) if suggested in ORDER else 0
    return ORDER[max(ci, si)]


def _hydrate_project(row: dict) -> dict:
    row["scores"] = json.loads(row.pop("scores_json", "{}") or "{}")
    row["diagnosis"] = json.loads(row.pop("diagnosis_json", "[]") or "[]")
    return row


# ── Chat Sessions ──────────────────────────────────────────────────

def create_session(session_id: str, project_id: str = "", agent_type: str = "coach"):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO chat_sessions (session_id, project_id, agent_type) VALUES (?,?,?)",
            (session_id, project_id, agent_type)
        )


def bind_session_to_project(session_id: str, project_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE chat_sessions SET project_id=? WHERE session_id=?", (project_id, session_id))


def get_project_for_session(session_id: str) -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT project_id FROM chat_sessions WHERE session_id=?", (session_id,)).fetchone()
        return row["project_id"] if row else ""


def append_chat(session_id: str, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?,?,?)",
            (session_id, role, content)
        )


def get_chat_history(session_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE session_id=? ORDER BY id",
            (session_id,)
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]


def get_all_chat_messages(session_id: str) -> list[dict]:
    """Return full rows including created_at for export."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM chat_messages WHERE session_id=? ORDER BY id",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_sessions_for_project(project_id: str) -> list[dict]:
    """Return all chat sessions associated with a project."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT session_id, agent_type, created_at FROM chat_sessions WHERE project_id=? ORDER BY created_at DESC",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_latest_session_for_project(project_id: str) -> dict | None:
    """Return the most recent chat session for a project, with its messages."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT session_id, agent_type, created_at FROM chat_sessions WHERE project_id=? ORDER BY created_at DESC LIMIT 1",
            (project_id,)
        ).fetchone()
        if not row:
            return None
        session = dict(row)
        session["messages"] = get_chat_history(session["session_id"])
        return session


def get_sessions_for_user(owner_id: str) -> list[dict]:
    """Return all sessions for projects owned by a user."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT cs.session_id, cs.project_id, cs.agent_type, cs.created_at, p.name as project_name
               FROM chat_sessions cs
               JOIN projects p ON cs.project_id = p.project_id
               WHERE p.owner_id = ?
               ORDER BY cs.created_at DESC""",
            (owner_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── Score Snapshots (Timeline) ──────────────────────────────────────

def save_score_snapshot(project_id: str, scores: dict, stage: str):
    """Record a timestamped score snapshot for the timeline."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM score_snapshots WHERE project_id=?",
            (project_id,)
        ).fetchone()
        round_num = (row["cnt"] or 0) + 1
        conn.execute(
            "INSERT INTO score_snapshots (project_id, scores_json, stage, round_num) VALUES (?,?,?,?)",
            (project_id, json.dumps(scores), stage, round_num)
        )


def get_score_snapshots(project_id: str) -> list[dict]:
    """Return all score snapshots ordered by time."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT round_num, scores_json, stage, created_at FROM score_snapshots WHERE project_id=? ORDER BY id",
            (project_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["scores"] = json.loads(d.pop("scores_json", "{}") or "{}")
            result.append(d)
        return result


# ── Interview Analyses ──────────────────────────────────────────────

def save_interview_analysis(project_id: str, raw_text: str, result: dict):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO interview_analyses (project_id, raw_text, result_json) VALUES (?,?,?)",
            (project_id, raw_text, json.dumps(result, ensure_ascii=False))
        )


def get_interview_analyses(project_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, raw_text, result_json, created_at FROM interview_analyses WHERE project_id=? ORDER BY id DESC",
            (project_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["result"] = json.loads(d.pop("result_json", "{}") or "{}")
            result.append(d)
        return result


# ── Pitch Checks ────────────────────────────────────────────────────

def save_pitch_check(project_id: str, outline_text: str, result: dict):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO pitch_checks (project_id, outline_text, result_json) VALUES (?,?,?)",
            (project_id, outline_text, json.dumps(result, ensure_ascii=False))
        )


def get_pitch_checks(project_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, outline_text, result_json, created_at FROM pitch_checks WHERE project_id=? ORDER BY id DESC",
            (project_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["result"] = json.loads(d.pop("result_json", "{}") or "{}")
            result.append(d)
        return result


# ── Competition Date ─────────────────────────────────────────────────

def set_competition_date(project_id: str, competition_date: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE projects SET competition_date=? WHERE project_id=?",
            (competition_date, project_id)
        )


def get_competition_date(project_id: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT competition_date FROM projects WHERE project_id=?",
            (project_id,)
        ).fetchone()
        return row["competition_date"] if row else None


# ── Teacher Annotations ──────────────────────────────────────────────

def save_annotation(project_id: str, session_id: str, message_idx: int,
                    teacher_id: str, action: str, note_text: str = ""):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO annotations
               (project_id, session_id, message_idx, teacher_id, action, note_text)
               VALUES (?,?,?,?,?,?)""",
            (project_id, session_id, message_idx, teacher_id, action, note_text)
        )


def get_annotations_for_project(project_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM annotations WHERE project_id=? ORDER BY created_at DESC",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_latest_annotations_for_coach(project_id: str, limit: int = 5) -> list[dict]:
    """Return the most recent note-type annotations with text, for coach prompt injection."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM annotations WHERE project_id=? AND action='note' AND note_text != ''
               ORDER BY created_at DESC LIMIT ?""",
            (project_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


# ── Session Ratings ──────────────────────────────────────────────────

def save_session_rating(session_id: str, project_id: str, student_id: str,
                        rating: int, comment: str = ""):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO session_ratings
               (session_id, project_id, student_id, rating, comment)
               VALUES (?,?,?,?,?)""",
            (session_id, project_id, student_id, rating, comment)
        )


def get_rating_for_session(session_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM session_ratings WHERE session_id=?",
            (session_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_ratings() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT sr.*, p.name as project_name
               FROM session_ratings sr
               LEFT JOIN projects p ON sr.project_id = p.project_id
               ORDER BY sr.created_at DESC""",
        ).fetchall()
        return [dict(r) for r in rows]


# ── Team Members (F6-adv) ──────────────────────────────────────────

def add_team_member(project_id: str, user_id: str, role: str = "member"):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO team_members (project_id, user_id, role) VALUES (?,?,?)",
            (project_id, user_id, role)
        )


def remove_team_member(project_id: str, user_id: str):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM team_members WHERE project_id=? AND user_id=? AND role != 'owner'",
            (project_id, user_id)
        )


def get_team_members(project_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT tm.user_id, tm.role, tm.joined_at,
                      u.username, u.display_name
               FROM team_members tm
               JOIN users u ON tm.user_id = u.user_id
               WHERE tm.project_id=?
               ORDER BY tm.role DESC, tm.joined_at""",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_projects_for_user(user_id: str) -> list[dict]:
    """Return all projects where user is owner OR team member."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT DISTINCT p.* FROM projects p
               LEFT JOIN team_members tm ON p.project_id = tm.project_id
               WHERE p.owner_id = ? OR tm.user_id = ?
               ORDER BY p.created_at DESC""",
            (user_id, user_id)
        ).fetchall()
        return [_hydrate_project(dict(r)) for r in rows]


# ── Uploaded Files (F3-adv) ─────────────────────────────────────────

def save_uploaded_file(file_id: str, project_id: str, session_id: str,
                       filename: str, file_type: str, extracted_text: str, file_size: int):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO uploaded_files
               (file_id, project_id, session_id, filename, file_type, extracted_text, file_size)
               VALUES (?,?,?,?,?,?,?)""",
            (file_id, project_id, session_id, filename, file_type, extracted_text, file_size)
        )


def get_uploaded_files(session_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM uploaded_files WHERE session_id=? ORDER BY created_at DESC",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_uploaded_files_for_project(project_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM uploaded_files WHERE project_id=? ORDER BY created_at DESC",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── Weekly Reports (F2-adv) ─────────────────────────────────────────

def save_weekly_report(project_id: str, owner_id: str, week_start: str,
                       week_end: str, summary: dict):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO weekly_reports (project_id, owner_id, week_start, week_end, summary_json)
               VALUES (?,?,?,?,?)""",
            (project_id, owner_id, week_start, week_end, json.dumps(summary, ensure_ascii=False))
        )


def get_weekly_reports(project_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM weekly_reports WHERE project_id=? ORDER BY week_start DESC",
            (project_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["summary"] = json.loads(d.pop("summary_json", "{}") or "{}")
            result.append(d)
        return result


def get_all_weekly_reports(week_start: str = None) -> list[dict]:
    with get_conn() as conn:
        if week_start:
            rows = conn.execute(
                """SELECT wr.*, p.name as project_name
                   FROM weekly_reports wr LEFT JOIN projects p ON wr.project_id = p.project_id
                   WHERE wr.week_start = ? ORDER BY wr.created_at DESC""",
                (week_start,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT wr.*, p.name as project_name
                   FROM weekly_reports wr LEFT JOIN projects p ON wr.project_id = p.project_id
                   ORDER BY wr.week_start DESC, wr.created_at DESC"""
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["summary"] = json.loads(d.pop("summary_json", "{}") or "{}")
            result.append(d)
        return result


def get_project_activity_in_range(project_id: str, start: str, end: str) -> dict:
    """Aggregate chat messages, score snapshots, and diagnosis for a date range."""
    with get_conn() as conn:
        # Session count in range
        session_row = conn.execute(
            "SELECT COUNT(DISTINCT session_id) as cnt FROM chat_sessions WHERE project_id=? AND created_at BETWEEN ? AND ?",
            (project_id, start, end)
        ).fetchone()
        session_count = session_row["cnt"] if session_row else 0

        # Message count
        msg_row = conn.execute(
            """SELECT COUNT(*) as cnt FROM chat_messages cm
               JOIN chat_sessions cs ON cm.session_id = cs.session_id
               WHERE cs.project_id=? AND cm.created_at BETWEEN ? AND ?""",
            (project_id, start, end)
        ).fetchone()
        message_count = msg_row["cnt"] if msg_row else 0

        # Score snapshots in range
        snap_rows = conn.execute(
            "SELECT scores_json, stage, round_num, created_at FROM score_snapshots WHERE project_id=? AND created_at BETWEEN ? AND ? ORDER BY id",
            (project_id, start, end)
        ).fetchall()
        snapshots = []
        for s in snap_rows:
            d = dict(s)
            d["scores"] = json.loads(d.pop("scores_json", "{}") or "{}")
            snapshots.append(d)

        # Current project state
        proj = get_project(project_id)
        return {
            "session_count": session_count,
            "message_count": message_count,
            "score_snapshots": snapshots,
            "latest_scores": proj.get("scores", {}) if proj else {},
            "latest_diagnosis": proj.get("diagnosis", []) if proj else [],
            "stage": proj.get("stage", "") if proj else "",
        }


# ── Peer Review (F4-adv) ───────────────────────────────────────────

def create_review_assignment(assignment_id: str, reviewer_id: str,
                             project_id: str, assigned_by: str = "system"):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO review_assignments (assignment_id, reviewer_id, project_id, assigned_by) VALUES (?,?,?,?)",
            (assignment_id, reviewer_id, project_id, assigned_by)
        )


def get_review_assignments(reviewer_id: str = None, project_id: str = None) -> list[dict]:
    with get_conn() as conn:
        if reviewer_id:
            rows = conn.execute(
                """SELECT ra.*, p.name as project_name, p.industry, p.description
                   FROM review_assignments ra
                   JOIN projects p ON ra.project_id = p.project_id
                   WHERE ra.reviewer_id=? ORDER BY ra.created_at DESC""",
                (reviewer_id,)
            ).fetchall()
        elif project_id:
            rows = conn.execute(
                "SELECT * FROM review_assignments WHERE project_id=? ORDER BY created_at DESC",
                (project_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM review_assignments ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def complete_review_assignment(assignment_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE review_assignments SET status='completed' WHERE assignment_id=?", (assignment_id,))


def save_peer_review(review_id: str, assignment_id: str, reviewer_id: str,
                     project_id: str, scores: dict, comments: dict, overall_comment: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO peer_reviews
               (review_id, assignment_id, reviewer_id, project_id, scores_json, comments_json, overall_comment)
               VALUES (?,?,?,?,?,?,?)""",
            (review_id, assignment_id, reviewer_id, project_id,
             json.dumps(scores), json.dumps(comments, ensure_ascii=False), overall_comment)
        )
    complete_review_assignment(assignment_id)


def get_peer_reviews_for_project(project_id: str) -> list[dict]:
    """Return anonymized reviews (without reviewer_id)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT review_id, project_id, scores_json, comments_json, overall_comment, created_at FROM peer_reviews WHERE project_id=? ORDER BY created_at DESC",
            (project_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["scores"] = json.loads(d.pop("scores_json", "{}") or "{}")
            d["comments"] = json.loads(d.pop("comments_json", "{}") or "{}")
            result.append(d)
        return result


# ── Learning Tasks (F5-adv) ─────────────────────────────────────────

def save_learning_task(task_id: str, project_id: str, owner_id: str,
                       dimension: str, title: str, description: str,
                       completion_keywords: list):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO learning_tasks
               (task_id, project_id, owner_id, dimension, title, description, completion_keywords)
               VALUES (?,?,?,?,?,?,?)""",
            (task_id, project_id, owner_id, dimension, title, description,
             json.dumps(completion_keywords, ensure_ascii=False))
        )


def get_learning_tasks(project_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM learning_tasks WHERE project_id=? ORDER BY dimension, id",
            (project_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["completion_keywords"] = json.loads(d.get("completion_keywords", "[]") or "[]")
            result.append(d)
        return result


def update_learning_task_status(task_id: str, status: str):
    with get_conn() as conn:
        if status == "completed":
            conn.execute(
                "UPDATE learning_tasks SET status=?, completed_at=datetime('now') WHERE task_id=?",
                (status, task_id)
            )
        else:
            conn.execute(
                "UPDATE learning_tasks SET status=?, completed_at=NULL WHERE task_id=?",
                (status, task_id)
            )


def auto_detect_task_completion(project_id: str, message_text: str) -> list[str]:
    """Check pending tasks for keyword matches. Return completed task_ids."""
    tasks = get_learning_tasks(project_id)
    completed = []
    for task in tasks:
        if task["status"] != "pending":
            continue
        keywords = task.get("completion_keywords", [])
        if keywords and any(kw in message_text for kw in keywords):
            update_learning_task_status(task["task_id"], "completed")
            completed.append(task["task_id"])
    return completed
