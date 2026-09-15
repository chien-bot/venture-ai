"""Capture the real VentureAI chat UI for a saved CareAI test session."""

import argparse
import json
import sqlite3
from pathlib import Path

from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent
DB = HERE / "ventureai_careai_test.db"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--phrase", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--last", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    session = conn.execute("SELECT * FROM chat_sessions WHERE session_id=?", (args.session,)).fetchone()
    if not session:
        raise SystemExit("Session not found")
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (session["owner_id"],)).fetchone()
    token = conn.execute("SELECT token FROM auth_tokens WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (session["owner_id"],)).fetchone()
    if not user or not token:
        raise SystemExit("Test-user session or token not found")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        context.add_cookies([{"name": "token", "value": token["token"], "url": "http://127.0.0.1:3000"}])
        user_data = {"user_id": user["user_id"], "username": user["username"], "role": user["role"], "display_name": user["display_name"]}
        context.add_init_script(
            "sessionStorage.setItem('token', " + json.dumps(token["token"]) + ");"
            "sessionStorage.setItem('user', " + json.dumps(json.dumps(user_data)) + ");"
        )
        page = context.new_page()
        page.goto(f"http://127.0.0.1:3000/student/chat?project_id={session['project_id']}", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        sessions = page.locator("div.group.rounded-lg.cursor-pointer")
        print("URL:", page.url, "sessions:", sessions.count())
        print("body-preview:", page.locator("body").inner_text()[:1000])
        session_row = sessions.filter(has_text=args.phrase).first
        if not session_row.count():
            raise SystemExit(f"Cannot find session preview containing {args.phrase!r}")
        session_row.click()
        page.wait_for_timeout(1800)
        print("chat-preview:", page.locator("body").inner_text()[-2600:])
        targets = page.get_by_text(args.target, exact=False)
        target = targets.last if args.last else targets.first
        if not target.count():
            raise SystemExit(f"Cannot find target response containing {args.target!r}")
        target.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out), full_page=False)
        print("Saved:", out)
        browser.close()


if __name__ == "__main__":
    main()
