"""SQLite persistence for CareAI's local health-memory prototype."""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.schemas import (
    ActionPlanState, ComprehensionCheckRequest, ComprehensionCheckResult, ComprehensionFeedback,
    HealthDataInput, HealthReport, HealthTrendPoint, PlanTask, PrivacyPreferences,
    PrivacyPreferencesUpdate, ReportHistoryItem, RuleAssessment, UserProfile, UserProfileInput,
    WeeklyPlanDraft, WeeklyReview,
)


def _database_path() -> Path:
    configured_path = os.getenv("CAREAI_DB_PATH")
    return Path(configured_path) if configured_path else Path(__file__).resolve().parent / "data" / "careai.db"


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def initialize_database() -> None:
    """Create Stage 2 tables and safely migrate the Stage 1 report table."""
    with _connect() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, display_name TEXT NOT NULL, age INTEGER, gender TEXT,
            health_goal TEXT, medical_history TEXT, long_term_medication TEXT, allergies TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
        connection.execute("""CREATE TABLE IF NOT EXISTS health_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, input_json TEXT NOT NULL,
            assessment_json TEXT NOT NULL, report_json TEXT NOT NULL)""")
        _ensure_column(connection, "health_reports", "user_id", "TEXT NOT NULL DEFAULT 'demo-user'")
        _ensure_column(connection, "health_reports", "recorded_at", "TEXT NOT NULL DEFAULT '2026-01-01'")
        _ensure_column(connection, "health_reports", "source", "TEXT NOT NULL DEFAULT 'manual'")
        _ensure_column(connection, "health_reports", "generation_source", "TEXT NOT NULL DEFAULT 'legacy_unknown'")
        _ensure_column(connection, "health_reports", "generation_model", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(connection, "health_reports", "agent_version", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(connection, "health_reports", "rule_version", "TEXT NOT NULL DEFAULT 'unknown'")
        connection.execute("""CREATE TABLE IF NOT EXISTS action_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, report_id INTEGER NOT NULL UNIQUE, user_id TEXT NOT NULL,
            goal TEXT NOT NULL, week_start TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(report_id) REFERENCES health_reports(id))""")
        connection.execute("""CREATE TABLE IF NOT EXISTS plan_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id INTEGER NOT NULL, day_number INTEGER NOT NULL,
            content TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, completion_reason TEXT,
            completed_at TEXT, FOREIGN KEY(plan_id) REFERENCES action_plans(id))""")
        connection.execute("""CREATE TABLE IF NOT EXISTS weekly_plan_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, goal TEXT NOT NULL,
            summary TEXT NOT NULL, adjustment_reason TEXT NOT NULL, created_at TEXT NOT NULL,
            confirmed_at TEXT)""")
        _ensure_column(connection, "weekly_plan_drafts", "version", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(connection, "weekly_plan_drafts", "previous_draft_id", "INTEGER")
        _ensure_column(connection, "weekly_plan_drafts", "experiment_variable", "TEXT NOT NULL DEFAULT '保持当前计划'")
        _ensure_column(connection, "weekly_plan_drafts", "difficulty", "INTEGER NOT NULL DEFAULT 2")
        _ensure_column(connection, "weekly_plan_drafts", "experiment_snapshot_json", "TEXT NOT NULL DEFAULT '{}'")
        connection.execute("""CREATE TABLE IF NOT EXISTS weekly_plan_draft_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, draft_id INTEGER NOT NULL, day_number INTEGER NOT NULL,
            content TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, completion_reason TEXT,
            completed_at TEXT, FOREIGN KEY(draft_id) REFERENCES weekly_plan_drafts(id))""")
        connection.execute("""CREATE TABLE IF NOT EXISTS privacy_preferences (
            user_id TEXT PRIMARY KEY, ai_processing_enabled INTEGER NOT NULL DEFAULT 1,
            save_reports INTEGER NOT NULL DEFAULT 1, retention_days INTEGER NOT NULL DEFAULT 365,
            summary_export_enabled INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id))""")
        connection.execute("""CREATE TABLE IF NOT EXISTS comprehension_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, report_id INTEGER NOT NULL, user_id TEXT NOT NULL,
            meaning_answer TEXT NOT NULL, boundary_answer TEXT NOT NULL, action_answer TEXT NOT NULL,
            score INTEGER NOT NULL, passed INTEGER NOT NULL, attempts INTEGER NOT NULL,
            feedback_json TEXT NOT NULL, submitted_at TEXT NOT NULL,
            FOREIGN KEY(report_id) REFERENCES health_reports(id))""")
        now = _utc_now()
        connection.execute("""INSERT OR IGNORE INTO users (id, display_name, created_at, updated_at)
            VALUES ('demo-user', '健康记忆演示用户', ?, ?)""", (now, now))
        connection.execute("CREATE INDEX IF NOT EXISTS idx_reports_user_date ON health_reports(user_id, recorded_at DESC, id DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_plans_user_week ON action_plans(user_id, week_start DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_checks_report_user ON comprehension_checks(report_id, user_id, id DESC)")


def _to_user_profile(row: sqlite3.Row) -> UserProfile:
    return UserProfile(**dict(row))


def list_user_profiles() -> list[UserProfile]:
    initialize_database()
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM users ORDER BY created_at ASC").fetchall()
    return [_to_user_profile(row) for row in rows]


def get_user_profile(user_id: str) -> UserProfile | None:
    initialize_database()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _to_user_profile(row) if row else None


def save_user_profile(data: UserProfileInput) -> UserProfile:
    initialize_database()
    now = _utc_now()
    with _connect() as connection:
        existing = connection.execute("SELECT created_at FROM users WHERE id = ?", (data.id,)).fetchone()
        created_at = existing["created_at"] if existing else now
        connection.execute("""INSERT INTO users (id, display_name, age, gender, health_goal, medical_history,
            long_term_medication, allergies, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name, age=excluded.age,
            gender=excluded.gender, health_goal=excluded.health_goal, medical_history=excluded.medical_history,
            long_term_medication=excluded.long_term_medication, allergies=excluded.allergies,
            updated_at=excluded.updated_at""", (
            data.id, data.display_name, data.age, data.gender.value if data.gender else None, data.health_goal,
            data.medical_history, data.long_term_medication, data.allergies, created_at, now,
        ))
    profile = get_user_profile(data.id)
    assert profile is not None
    return profile


def _ensure_user_for_input(data: HealthDataInput) -> None:
    if get_user_profile(data.user_id) is None:
        save_user_profile(UserProfileInput(id=data.user_id, display_name=data.user_id, age=data.age, gender=data.gender, health_goal=data.health_goal))


def save_health_report(
    data: HealthDataInput,
    assessment: RuleAssessment,
    report: HealthReport,
    generation_source: str = "legacy_unknown",
    generation_model: str = "unknown",
    agent_version: str = "unknown",
    rule_version: str = "unknown",
) -> ReportHistoryItem:
    """Persist a completed report and its initial plan for one local profile."""
    initialize_database()
    _ensure_user_for_input(data)
    created_at = _utc_now()
    with _connect() as connection:
        cursor = connection.execute("""INSERT INTO health_reports
            (created_at, input_json, assessment_json, report_json, user_id, recorded_at, source,
             generation_source, generation_model, agent_version, rule_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            created_at, json.dumps(data.model_dump(mode="json"), ensure_ascii=False),
            json.dumps(assessment.model_dump(mode="json"), ensure_ascii=False),
            json.dumps(report.model_dump(mode="json"), ensure_ascii=False), data.user_id,
            data.recorded_at.isoformat(), data.source, generation_source, generation_model,
            agent_version, rule_version,
        ))
        report_id = int(cursor.lastrowid)
        plan_cursor = connection.execute("""INSERT INTO action_plans
            (report_id, user_id, goal, week_start, created_at) VALUES (?, ?, ?, ?, ?)""", (
            report_id, data.user_id, data.health_goal or "建立可持续的健康习惯", data.recorded_at.isoformat(), created_at,
        ))
        plan_id = int(plan_cursor.lastrowid)
        connection.executemany("INSERT INTO plan_tasks (plan_id, day_number, content) VALUES (?, ?, ?)",
            [(plan_id, index + 1, content) for index, content in enumerate(report.action_plan)])
    return ReportHistoryItem(
        id=report_id, created_at=created_at, input=data, assessment=assessment, report=report,
        generation_source=generation_source, generation_model=generation_model,
        agent_version=agent_version, rule_version=rule_version,
    )


def _to_history_item(row: sqlite3.Row) -> ReportHistoryItem:
    input_data = json.loads(row["input_json"])
    input_data.setdefault("user_id", row["user_id"])
    input_data.setdefault("recorded_at", row["recorded_at"])
    input_data.setdefault("source", row["source"])
    return ReportHistoryItem(id=int(row["id"]), created_at=row["created_at"],
        input=HealthDataInput.model_validate(input_data),
        assessment=RuleAssessment.model_validate(json.loads(row["assessment_json"])),
        report=HealthReport.model_validate(json.loads(row["report_json"])),
        generation_source=row["generation_source"], generation_model=row["generation_model"],
        agent_version=row["agent_version"], rule_version=row["rule_version"])


def list_health_reports(user_id: str = "demo-user", limit: int = 20) -> list[ReportHistoryItem]:
    initialize_database()
    safe_limit = min(max(limit, 1), 100)
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM health_reports WHERE user_id = ? ORDER BY recorded_at DESC, id DESC LIMIT ?", (user_id, safe_limit)).fetchall()
    return [_to_history_item(row) for row in rows]


def get_health_report(report_id: int, user_id: str = "demo-user") -> ReportHistoryItem | None:
    initialize_database()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM health_reports WHERE id = ? AND user_id = ?", (report_id, user_id)).fetchone()
    return _to_history_item(row) if row else None


def delete_health_report(report_id: int, user_id: str) -> bool:
    initialize_database()
    with _connect() as connection:
        plan = connection.execute("SELECT id FROM action_plans WHERE report_id = ? AND user_id = ?", (report_id, user_id)).fetchone()
        if plan:
            connection.execute("DELETE FROM plan_tasks WHERE plan_id = ?", (plan["id"],))
            connection.execute("DELETE FROM action_plans WHERE id = ?", (plan["id"],))
        connection.execute("DELETE FROM comprehension_checks WHERE report_id = ? AND user_id = ?", (report_id, user_id))
        deleted = connection.execute("DELETE FROM health_reports WHERE id = ? AND user_id = ?", (report_id, user_id))
    return deleted.rowcount > 0


def get_health_trends(user_id: str = "demo-user", limit: int = 12) -> list[HealthTrendPoint]:
    reports = list_health_reports(user_id, limit)
    points = [HealthTrendPoint(report_id=item.id, created_at=item.input.recorded_at.isoformat(), bmi=item.assessment.bmi,
        sleep_hours=item.input.sleep_hours, exercise_frequency=item.input.exercise_days_per_week,
        risk_level=item.report.risk_level) for item in reports]
    return list(reversed(points))


def _to_action_plan(row: sqlite3.Row, connection: sqlite3.Connection) -> ActionPlanState:
    tasks = connection.execute("SELECT * FROM plan_tasks WHERE plan_id = ? ORDER BY day_number", (row["id"],)).fetchall()
    return ActionPlanState(id=int(row["id"]), report_id=int(row["report_id"]), user_id=row["user_id"], goal=row["goal"],
        week_start=row["week_start"], created_at=row["created_at"], tasks=[PlanTask(id=int(task["id"]), day_number=task["day_number"],
        content=task["content"], completed=bool(task["completed"]), completion_reason=task["completion_reason"], completed_at=task["completed_at"]) for task in tasks])


def get_action_plan_for_report(report_id: int, user_id: str) -> ActionPlanState | None:
    initialize_database()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM action_plans WHERE report_id = ? AND user_id = ?", (report_id, user_id)).fetchone()
        return _to_action_plan(row, connection) if row else None


def update_plan_task(task_id: int, user_id: str, completed: bool, completion_reason: str | None) -> PlanTask | None:
    initialize_database()
    with _connect() as connection:
        row = connection.execute("""SELECT plan_tasks.* FROM plan_tasks JOIN action_plans ON action_plans.id = plan_tasks.plan_id
            WHERE plan_tasks.id = ? AND action_plans.user_id = ?""", (task_id, user_id)).fetchone()
        if row is None:
            return None
        completed_at = _utc_now() if completed else None
        connection.execute("UPDATE plan_tasks SET completed = ?, completion_reason = ?, completed_at = ? WHERE id = ?",
            (int(completed), completion_reason, completed_at, task_id))
        updated = connection.execute("SELECT * FROM plan_tasks WHERE id = ?", (task_id,)).fetchone()
    return PlanTask(id=int(updated["id"]), day_number=updated["day_number"], content=updated["content"],
        completed=bool(updated["completed"]), completion_reason=updated["completion_reason"], completed_at=updated["completed_at"])


def update_weekly_plan_draft_task(task_id: int, user_id: str, completed: bool, completion_reason: str | None) -> PlanTask | None:
    """Only confirmed weekly plans can contribute completed tasks to future reviews."""
    initialize_database()
    with _connect() as connection:
        row = connection.execute("""SELECT weekly_plan_draft_tasks.* FROM weekly_plan_draft_tasks
            JOIN weekly_plan_drafts ON weekly_plan_drafts.id = weekly_plan_draft_tasks.draft_id
            WHERE weekly_plan_draft_tasks.id = ? AND weekly_plan_drafts.user_id = ? AND weekly_plan_drafts.confirmed_at IS NOT NULL""",
            (task_id, user_id)).fetchone()
        if row is None:
            return None
        completed_at = _utc_now() if completed else None
        connection.execute("UPDATE weekly_plan_draft_tasks SET completed = ?, completion_reason = ?, completed_at = ? WHERE id = ?",
            (int(completed), completion_reason, completed_at, task_id))
        updated = connection.execute("SELECT * FROM weekly_plan_draft_tasks WHERE id = ?", (task_id,)).fetchone()
    return PlanTask(id=int(updated["id"]), day_number=updated["day_number"], content=updated["content"],
        completed=bool(updated["completed"]), completion_reason=updated["completion_reason"], completed_at=updated["completed_at"])


def get_weekly_review(user_id: str) -> WeeklyReview:
    initialize_database()
    with _connect() as connection:
        draft = connection.execute("SELECT * FROM weekly_plan_drafts WHERE user_id = ? AND confirmed_at IS NOT NULL ORDER BY confirmed_at DESC LIMIT 1", (user_id,)).fetchone()
        if draft is not None:
            totals = connection.execute("SELECT COUNT(*) AS total, SUM(completed) AS completed FROM weekly_plan_draft_tasks WHERE draft_id = ?", (draft["id"],)).fetchone()
            total, completed = int(totals["total"] or 0), int(totals["completed"] or 0)
            rate = round(completed / total * 100) if total else None
            summary = ("已确认下周计划，完成任务后可继续复盘。" if not completed else
                f"已完成 {completed}/{total} 项已确认计划；下次 AI 调整会参考这些完成记录。")
            return WeeklyReview(user_id=user_id, week_start=draft["created_at"][:10], completed_tasks=completed,
                total_tasks=total, completion_rate=rate, summary=summary)
        plan = connection.execute("SELECT * FROM action_plans WHERE user_id = ? ORDER BY week_start DESC, id DESC LIMIT 1", (user_id,)).fetchone()
        if plan is None:
            return WeeklyReview(user_id=user_id, completed_tasks=0, total_tasks=0, summary="尚未建立行动计划；完成一次健康分析后即可开始追踪。")
        totals = connection.execute("SELECT COUNT(*) AS total, SUM(completed) AS completed FROM plan_tasks WHERE plan_id = ?", (plan["id"],)).fetchone()
    total, completed = int(totals["total"] or 0), int(totals["completed"] or 0)
    rate = round(completed / total * 100) if total else None
    summary = ("本周尚无可复盘的行动任务。" if rate is None else
        f"本周已完成 {completed}/{total} 项行动，可保持当前节奏并观察指标变化。" if rate >= 80 else
        f"本周完成 {completed}/{total} 项行动；下周可优先保留最容易坚持的步骤。" if rate >= 40 else
        f"本周仅完成 {completed}/{total} 项行动；建议缩小下周目标，并记录阻碍原因。")
    return WeeklyReview(user_id=user_id, week_start=plan["week_start"], completed_tasks=completed,
        total_tasks=total, completion_rate=rate, summary=summary)


def _to_weekly_plan_draft(row: sqlite3.Row, connection: sqlite3.Connection) -> WeeklyPlanDraft:
    tasks = connection.execute("SELECT * FROM weekly_plan_draft_tasks WHERE draft_id = ? ORDER BY day_number", (row["id"],)).fetchall()
    return WeeklyPlanDraft(id=int(row["id"]), user_id=row["user_id"], goal=row["goal"], summary=row["summary"],
        adjustment_reason=row["adjustment_reason"], created_at=row["created_at"], confirmed_at=row["confirmed_at"],
        version=int(row["version"]), previous_draft_id=row["previous_draft_id"],
        experiment_variable=row["experiment_variable"], difficulty=int(row["difficulty"]),
        experiment_snapshot=json.loads(row["experiment_snapshot_json"] or "{}"),
        tasks=[PlanTask(id=int(task["id"]), day_number=task["day_number"], content=task["content"], completed=bool(task["completed"]), completion_reason=task["completion_reason"], completed_at=task["completed_at"]) for task in tasks],
        safety_notice="本计划仅用于生活方式管理，不构成医疗诊断、处方或用药建议。")


def save_weekly_plan_draft(
    user_id: str,
    goal: str,
    summary: str,
    adjustment_reason: str,
    tasks: list[str],
    experiment_variable: str = "保持当前计划",
    difficulty: int = 2,
    experiment_snapshot: dict[str, str | int] | None = None,
) -> WeeklyPlanDraft:
    initialize_database()
    created_at = _utc_now()
    with _connect() as connection:
        previous = connection.execute("SELECT id, version FROM weekly_plan_drafts WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
        version = int(previous["version"]) + 1 if previous else 1
        previous_id = int(previous["id"]) if previous else None
        cursor = connection.execute("""INSERT INTO weekly_plan_drafts
            (user_id, goal, summary, adjustment_reason, created_at, version, previous_draft_id,
             experiment_variable, difficulty, experiment_snapshot_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, goal, summary, adjustment_reason, created_at, version, previous_id,
             experiment_variable, difficulty, json.dumps(experiment_snapshot or {}, ensure_ascii=False)))
        draft_id = int(cursor.lastrowid)
        connection.executemany("INSERT INTO weekly_plan_draft_tasks (draft_id, day_number, content) VALUES (?, ?, ?)",
            [(draft_id, index + 1, task) for index, task in enumerate(tasks)])
        row = connection.execute("SELECT * FROM weekly_plan_drafts WHERE id = ?", (draft_id,)).fetchone()
        return _to_weekly_plan_draft(row, connection)


def get_latest_weekly_plan_draft(user_id: str) -> WeeklyPlanDraft | None:
    initialize_database()
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM weekly_plan_drafts WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone()
        return _to_weekly_plan_draft(row, connection) if row else None


def is_plan_task_unlocked(task_id: int, user_id: str) -> bool:
    """Action tracking starts only after the report's latest understanding check passed."""
    initialize_database()
    with _connect() as connection:
        row = connection.execute("""SELECT action_plans.report_id FROM plan_tasks
            JOIN action_plans ON action_plans.id = plan_tasks.plan_id
            WHERE plan_tasks.id = ? AND action_plans.user_id = ?""", (task_id, user_id)).fetchone()
        if row is None:
            return False
        passed = connection.execute("""SELECT passed FROM comprehension_checks
            WHERE report_id = ? AND user_id = ? ORDER BY id DESC LIMIT 1""",
            (row["report_id"], user_id)).fetchone()
    return bool(passed and passed["passed"])


def confirm_weekly_plan_draft(draft_id: int, user_id: str) -> WeeklyPlanDraft | None:
    initialize_database()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM weekly_plan_drafts WHERE id = ? AND user_id = ?", (draft_id, user_id)).fetchone()
        if row is None:
            return None
        if row["confirmed_at"] is None:
            connection.execute("UPDATE weekly_plan_drafts SET confirmed_at = ? WHERE id = ?", (_utc_now(), draft_id))
        updated = connection.execute("SELECT * FROM weekly_plan_drafts WHERE id = ?", (draft_id,)).fetchone()
        return _to_weekly_plan_draft(updated, connection)


def get_privacy_preferences(user_id: str) -> PrivacyPreferences:
    initialize_database()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM privacy_preferences WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            now = _utc_now()
            connection.execute("INSERT INTO privacy_preferences (user_id, updated_at) VALUES (?, ?)", (user_id, now))
            row = connection.execute("SELECT * FROM privacy_preferences WHERE user_id = ?", (user_id,)).fetchone()
    return PrivacyPreferences(
        user_id=user_id,
        ai_processing_enabled=bool(row["ai_processing_enabled"]),
        save_reports=bool(row["save_reports"]),
        retention_days=int(row["retention_days"]),
        summary_export_enabled=bool(row["summary_export_enabled"]),
        updated_at=row["updated_at"],
    )


def save_privacy_preferences(user_id: str, data: PrivacyPreferencesUpdate) -> PrivacyPreferences:
    initialize_database()
    now = _utc_now()
    with _connect() as connection:
        connection.execute("""INSERT INTO privacy_preferences
            (user_id, ai_processing_enabled, save_reports, retention_days, summary_export_enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET ai_processing_enabled=excluded.ai_processing_enabled,
            save_reports=excluded.save_reports, retention_days=excluded.retention_days,
            summary_export_enabled=excluded.summary_export_enabled, updated_at=excluded.updated_at""",
            (user_id, int(data.ai_processing_enabled), int(data.save_reports), data.retention_days,
             int(data.summary_export_enabled), now))
    purge_expired_reports(user_id, data.retention_days)
    return get_privacy_preferences(user_id)


def purge_expired_reports(user_id: str, retention_days: int) -> int:
    if retention_days == 0:
        return 0
    initialize_database()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).date().isoformat()
    with _connect() as connection:
        report_rows = connection.execute(
            "SELECT id FROM health_reports WHERE user_id = ? AND recorded_at < ?", (user_id, cutoff)
        ).fetchall()
    deleted = 0
    for row in report_rows:
        deleted += int(delete_health_report(int(row["id"]), user_id))
    return deleted


def delete_all_health_data(user_id: str) -> int:
    """Delete reports, plans, reviews and comprehension checks while retaining the local profile."""
    initialize_database()
    with _connect() as connection:
        report_count = int(connection.execute(
            "SELECT COUNT(*) AS count FROM health_reports WHERE user_id = ?", (user_id,)
        ).fetchone()["count"])
        plan_ids = [row["id"] for row in connection.execute("SELECT id FROM action_plans WHERE user_id = ?", (user_id,))]
        draft_ids = [row["id"] for row in connection.execute("SELECT id FROM weekly_plan_drafts WHERE user_id = ?", (user_id,))]
        for plan_id in plan_ids:
            connection.execute("DELETE FROM plan_tasks WHERE plan_id = ?", (plan_id,))
        for draft_id in draft_ids:
            connection.execute("DELETE FROM weekly_plan_draft_tasks WHERE draft_id = ?", (draft_id,))
        connection.execute("DELETE FROM action_plans WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM weekly_plan_drafts WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM comprehension_checks WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM health_reports WHERE user_id = ?", (user_id,))
    return report_count


def save_comprehension_check(
    report_id: int, user_id: str, data: ComprehensionCheckRequest
) -> ComprehensionCheckResult | None:
    initialize_database()
    with _connect() as connection:
        owned = connection.execute(
            "SELECT id FROM health_reports WHERE id = ? AND user_id = ?", (report_id, user_id)
        ).fetchone()
        if owned is None:
            return None
        previous = connection.execute(
            "SELECT COUNT(*) AS count FROM comprehension_checks WHERE report_id = ? AND user_id = ?",
            (report_id, user_id),
        ).fetchone()
        attempts = int(previous["count"]) + 1
        answers = [
            ("报告含义", data.meaning_answer == "health_education", "这是健康教育和生活方式提示，不是医疗结论。"),
            ("安全边界", data.boundary_answer == "repeat_and_seek_help", "明显异常应复测；持续异常或伴随不适时应咨询线下专业人员。"),
            ("下一步行动", data.action_answer == "choose_one_small_step", "先选择一个低负担行动并记录执行情况，更容易判断什么有帮助。"),
        ]
        feedback = [ComprehensionFeedback(question=q, correct=ok, explanation=detail) for q, ok, detail in answers]
        score = sum(item.correct for item in feedback)
        passed = score == 3
        submitted_at = _utc_now()
        connection.execute("""INSERT INTO comprehension_checks
            (report_id, user_id, meaning_answer, boundary_answer, action_answer, score, passed, attempts, feedback_json, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                report_id, user_id, data.meaning_answer, data.boundary_answer, data.action_answer,
                score, int(passed), attempts,
                json.dumps([item.model_dump() for item in feedback], ensure_ascii=False), submitted_at,
            ))
    return ComprehensionCheckResult(
        report_id=report_id, user_id=user_id, score=score, passed=passed,
        attempts=attempts, feedback=feedback, submitted_at=submitted_at,
    )


def get_latest_comprehension_check(report_id: int, user_id: str) -> ComprehensionCheckResult | None:
    initialize_database()
    with _connect() as connection:
        row = connection.execute("""SELECT * FROM comprehension_checks
            WHERE report_id = ? AND user_id = ? ORDER BY id DESC LIMIT 1""", (report_id, user_id)).fetchone()
    if row is None:
        return None
    return ComprehensionCheckResult(
        report_id=report_id, user_id=user_id, score=int(row["score"]), passed=bool(row["passed"]),
        attempts=int(row["attempts"]),
        feedback=[ComprehensionFeedback.model_validate(item) for item in json.loads(row["feedback_json"])],
        submitted_at=row["submitted_at"],
    )
