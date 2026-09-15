"""Verify the endpoint used by the chat UI with a real CareAI project."""

import argparse
import json
import sqlite3
from pathlib import Path

import httpx


HERE = Path(__file__).resolve().parent
DB = HERE / "ventureai_careai_test.db"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.raw.read_text())
    project = raw["setup"]["project"]["body"]
    conn = sqlite3.connect(DB)
    token_row = conn.execute(
        "SELECT token FROM auth_tokens WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (project["owner_id"],),
    ).fetchone()
    if not token_row:
        raise SystemExit("Evaluation user token unavailable")
    prompt = (
        "请按 F/I/H/S 判断：用户愿意付费、系统能提前发现慢性病、"
        "Agent 模拟用户说7天计划很方便。题干没有提供任何真实来源。"
    )
    with httpx.Client(
        base_url="http://127.0.0.1:8001", timeout=180,
        headers={"Authorization": f"Bearer {token_row[0]}"},
    ) as client:
        started = client.post(
            f"/api/chat/start?agent_type=coach&project_id={project['project_id']}", json={}
        )
        started.raise_for_status()
        session_id = started.json()["session_id"]
        tokens, done = [], None
        with client.stream("POST", "/api/chat/message/stream", json={
            "session_id": session_id,
            "project_id": project["project_id"],
            "agent_type": "coach",
            "message": prompt,
        }) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    if event.get("type") == "token":
                        tokens.append(event.get("content", ""))
                    elif event.get("type") == "done":
                        done = event
    result = {
        "mode": "stream_short_circuit_evidence_review",
        "session_id": session_id,
        "project_id": project["project_id"],
        "prompt": prompt,
        "reply": "".join(tokens),
        "done": {k: done.get(k) for k in ("intent", "run_id", "agent_version")},
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({"session_id": session_id, "run_id": result["done"]["run_id"], "reply_chars": len(result["reply"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
