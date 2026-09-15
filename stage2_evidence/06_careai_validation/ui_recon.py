"""Capture VentureAI's rendered login screen for a browser smoke test."""

from pathlib import Path

from playwright.sync_api import sync_playwright


OUT = Path(__file__).resolve().parent

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.goto("http://127.0.0.1:3000/", wait_until="networkidle", timeout=30000)
    page.screenshot(path=str(OUT / "ventureai-login.png"), full_page=True)
    print("title:", page.title())
    print("url:", page.url)
    print("buttons:", page.locator("button").all_text_contents())
    print("inputs:", page.locator("input").evaluate_all("els => els.map(e => ({type:e.type, placeholder:e.placeholder}))"))
    page.get_by_placeholder("student01").fill("student01")
    page.get_by_placeholder("123456").fill("123456")
    page.get_by_role("button", name="以学生身份登录").click()
    page.wait_for_url("**/student/projects", timeout=30000)
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "ventureai-projects.png"), full_page=True)
    print("projects_url:", page.url)
    print("projects_excerpt:", page.locator("body").inner_text()[:1000])
    page.goto("http://127.0.0.1:3000/student/chat", wait_until="networkidle", timeout=30000)
    page.screenshot(path=str(OUT / "ventureai-chat.png"), full_page=True)
    print("chat_url:", page.url)
    print("chat_excerpt:", page.locator("body").inner_text()[:1200])
    skip = page.get_by_role("button", name="跳过，直接开始对话")
    if skip.count() and skip.is_visible():
        skip.click()
        page.wait_for_timeout(250)
    page.screenshot(path=str(OUT / "ventureai-chat-ready.png"), full_page=True)
    print("chat_ready_excerpt:", page.locator("body").inner_text()[-900:])
    print("console_errors:", errors)
    browser.close()
