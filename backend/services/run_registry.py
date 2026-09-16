"""Durable identity and source snapshot for each Agent invocation."""

import hashlib
import subprocess
from pathlib import Path

from services.database import get_conn

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent


def _tree_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(BACKEND_ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:20]


def runtime_snapshot() -> dict:
    source_paths = [p for p in BACKEND_ROOT.rglob("*.py") if "__pycache__" not in p.parts and ".venv" not in p.parts]
    prompt_paths = list((BACKEND_ROOT / "prompts").glob("*.py"))
    try:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True,
            text=True, check=True, timeout=2,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        git_commit = ""
    return {
        "source_hash": _tree_hash(source_paths),
        "prompt_hash": _tree_hash(prompt_paths),
        "git_commit": git_commit,
    }


def start_run(run_id: str, session_id: str, project_id: str, flow: str, agent_version: str, model: str) -> None:
    snap = runtime_snapshot()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO agent_runs
               (run_id, session_id, project_id, flow, agent_version, git_commit, model, source_hash, prompt_hash)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (run_id, session_id, project_id, flow, agent_version,
             snap["git_commit"], model, snap["source_hash"], snap["prompt_hash"]),
        )


def finish_run(run_id: str, status: str, error_type: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE agent_runs SET status=?, error_type=?, finished_at=datetime('now') WHERE run_id=?",
            (status, error_type[:100], run_id),
        )


def fail_run_if_running(run_id: str, error_type: str) -> bool:
    """Close an abandoned stream without overwriting a completed result."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT status FROM agent_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if not row or row["status"] != "running":
            return False
        conn.execute(
            "UPDATE agent_runs SET status='failed', error_type=?, finished_at=datetime('now') WHERE run_id=?",
            (error_type[:100], run_id),
        )
        return True
