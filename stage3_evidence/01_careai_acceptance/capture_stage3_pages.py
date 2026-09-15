"""Capture the two authenticated third-stage pages from the simulated test DB."""

import argparse
import json
import sqlite3
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--web", default="http://127.0.0.1:3002")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    project = conn.execute(
        "SELECT * FROM projects WHERE name LIKE 'CareAI 第三阶段流程测试%' ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    if not project:
        raise SystemExit("simulated CareAI project not found")

    def identity(role: str) -> tuple[dict, str]:
        if role == "student":
            user = conn.execute("SELECT * FROM users WHERE user_id=?", (project["owner_id"],)).fetchone()
        else:
            user = conn.execute(
                "SELECT * FROM users WHERE role='teacher' AND username LIKE 'stage3_teacher_%' ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
        token = conn.execute(
            "SELECT token FROM auth_tokens WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user["user_id"],)
        ).fetchone()["token"]
        return dict(user), token

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        for role, path, target, filename in (
            ("student", "/student/stage3", "立项、成果与验收证据", "student-stage3.png"),
            ("teacher", "/teacher/stage3", "立项复审与终局验收", "teacher-stage3.png"),
        ):
            user, token = identity(role)
            context = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
            context.add_cookies([{"name": "token", "value": token, "url": args.web}])
            user_data = {k: user.get(k, "") for k in ("user_id", "username", "role", "display_name")}
            context.add_init_script(
                "sessionStorage.setItem('token', " + json.dumps(token) + ");"
                "sessionStorage.setItem('user', " + json.dumps(json.dumps(user_data, ensure_ascii=False)) + ");"
            )
            page = context.new_page()
            page.goto(f"{args.web}{path}?project_id={project['project_id']}", wait_until="networkidle")
            page.get_by_text(target, exact=False).first.wait_for(timeout=15000)
            page.wait_for_timeout(1000)
            output = args.output_dir / filename
            page.screenshot(path=str(output), full_page=False)
            print(f"saved {output}")
            context.close()
        browser.close()


if __name__ == "__main__":
    main()
