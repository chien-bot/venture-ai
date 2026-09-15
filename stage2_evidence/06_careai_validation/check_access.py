"""Record whether project and conversation data require authentication."""

import glob
import argparse
import json
from pathlib import Path

import httpx


folder = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--raw", type=Path)
parser.add_argument("--output", type=Path, default=folder / "unauthenticated_access_after.json")
args = parser.parse_args()
raw_path = args.raw or Path(sorted(glob.glob(str(folder / "careai-live-*.json")))[-1])
raw = json.loads(raw_path.read_text())
project_id = raw["setup"]["project"]["body"]["project_id"]
session_id = raw["cases"][0]["session_id"]

with httpx.Client(base_url="http://127.0.0.1:8001", timeout=30.0) as client:
    project_list = client.get("/api/projects/")
    project = client.get(f"/api/projects/{project_id}")
    history = client.get(f"/api/chat/history/{session_id}")

result = {
    "request_authentication": "none",
    "project_list": {
        "status": project_list.status_code,
        "contains_careai": project_id in [p.get("project_id") for p in project_list.json().get("projects", [])],
    },
    "project_detail": {
        "status": project.status_code,
        "contains_rubric": bool(project.json().get("rubric_full")),
    },
    "chat_history": {
        "status": history.status_code,
        "message_count": len(history.json().get("messages", [])),
    },
}
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False))
