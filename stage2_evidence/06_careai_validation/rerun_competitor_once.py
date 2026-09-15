"""Repeat the same competitor prompt in its saved CareAI session."""

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
    project = raw["setup"]["project"]["body"]
    case = next(x for x in raw["cases"] if x["case_id"] == "coach_competitor_followup")
    conn = sqlite3.connect(HERE / "ventureai_careai_test.db")
    token = conn.execute(
        "SELECT token FROM auth_tokens WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (project["owner_id"],),
    ).fetchone()[0]
    with httpx.Client(base_url="http://127.0.0.1:8001", timeout=360) as client:
        response = client.post("/api/chat/message", headers={"Authorization": f"Bearer {token}"}, json={
            "session_id": case["session_id"],
            "project_id": project["project_id"],
            "agent_type": "coach",
            "message": case["input"],
        })
    result = {
        "source": "real_model_repeat_same_prompt_in_saved_session",
        "http_status": response.status_code,
        "session_id": case["session_id"],
        "project_id": project["project_id"],
        "input": case["input"],
        "body": response.json(),
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({"status": response.status_code, "run_id": result["body"].get("run_id"), "reply_chars": len(result["body"].get("reply", ""))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
