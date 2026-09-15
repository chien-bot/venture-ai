"""Read the grader result saved after the validation client's timeout."""

import argparse
import json
import sqlite3
from pathlib import Path

import httpx


HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.raw.read_text())
    case = next(item for item in raw["cases"] if item["case_id"] == "grader_uploaded_only")
    project = raw["setup"]["project"]["body"]
    conn = sqlite3.connect(HERE / "ventureai_careai_test.db")
    token = conn.execute(
        "SELECT token FROM auth_tokens WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (project["owner_id"],),
    ).fetchone()[0]
    with httpx.Client(base_url="http://127.0.0.1:8001", timeout=30) as client:
        response = client.get(
            f"/api/chat/history/{case['session_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        history = response.json()
    last_message = history["messages"][-1]
    debug_logs = last_message.get("debug_logs") or []
    result = {
        "source": "authorized_history_after_validation_client_timeout",
        "history_http_status": response.status_code,
        "session_id": case["session_id"],
        "project_id": project["project_id"],
        "input": case["input"],
        "reply": last_message["content"],
        "run_id": next((log.get("run_id") for log in debug_logs if log.get("run_id")), None),
        "rubric_full": history.get("rubric_full"),
        "agent_type": history.get("agent_type"),
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({"status": response.status_code, "reply_chars": len(result["reply"]), "rubric_items": len(result["rubric_full"] or {})}, ensure_ascii=False))


if __name__ == "__main__":
    main()
