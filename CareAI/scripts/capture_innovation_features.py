"""Browser QA and screenshots for CareAI innovation features."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "innovation-evidence"
OUT.mkdir(parents=True, exist_ok=True)

console_errors: list[str] = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    desktop = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
    page = desktop.new_page()
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.goto("http://127.0.0.1:5173")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=OUT / "careai-home-innovation.png", full_page=True)

    page.get_by_role("button", name="隐私中心").click()
    page.get_by_role("heading", name="你的数据，由你决定").wait_for()
    ai_toggle = page.get_by_label("允许受限AI解释")
    if ai_toggle.is_checked():
        ai_toggle.uncheck()
    page.get_by_role("button", name="保存设置").click()
    page.get_by_text("隐私设置已保存。").wait_for()
    page.screenshot(path=OUT / "careai-privacy-center.png", full_page=True)

    page.get_by_role("button", name="健康分析").click()
    page.get_by_role("button", name="作息待改善案例").click()
    page.get_by_role("button", name="生成健康报告").click()
    page.get_by_role("heading", name="你的健康分析结果").wait_for()
    page.get_by_text("建议证据卡").wait_for()
    page.screenshot(path=OUT / "careai-report-evidence.png", full_page=True)

    page.get_by_text("健康教育与生活方式提示", exact=True).click()
    page.get_by_text("复测，并在需要时咨询线下专业人员", exact=True).click()
    page.get_by_text("先选择一个低负担行动", exact=True).click()
    page.get_by_role("button", name="检查我的理解").click()
    page.get_by_text("理解确认通过").wait_for()
    page.screenshot(path=OUT / "careai-comprehension-passed.png", full_page=True)

    page.get_by_role("button", name="历史记录").click()
    page.get_by_role("heading", name="健康时间轴与趋势").wait_for()
    page.get_by_label("本轮只改变一个变量").select_option(label="提醒时间")
    assert page.get_by_label("目标难度").is_disabled()
    page.get_by_role("button", name="生成行动实验").click()
    page.get_by_text("只调整：提醒时间").wait_for()
    page.screenshot(path=OUT / "careai-single-variable-experiment.png", full_page=True)

    page.get_by_role("button", name="隐私中心").click()
    page.get_by_role("heading", name="你的数据，由你决定").wait_for()
    save_toggle = page.get_by_label("保存报告与行动计划")
    if save_toggle.is_checked():
        save_toggle.uncheck()
    page.get_by_role("button", name="保存设置").click()
    page.get_by_text("隐私设置已保存。").wait_for()
    page.get_by_role("button", name="健康分析").click()
    page.get_by_role("button", name="作息待改善案例").click()
    page.get_by_role("button", name="生成健康报告").click()
    page.get_by_role("heading", name="你的健康分析结果").wait_for()
    page.get_by_text("本次检查只保留在当前页面。").wait_for()
    plan_section = page.locator("section").filter(has=page.get_by_role("heading", name="7 天行动实验"))
    assert plan_section.locator("ol button").first.is_disabled()
    page.get_by_text("健康教育与生活方式提示", exact=True).click()
    page.get_by_text("复测，并在需要时咨询线下专业人员", exact=True).click()
    page.get_by_text("先选择一个低负担行动", exact=True).click()
    page.get_by_role("button", name="检查我的理解").click()
    page.get_by_text("理解确认通过").wait_for()
    assert plan_section.locator("ol button").first.is_enabled()
    page.screenshot(path=OUT / "careai-private-session-comprehension.png", full_page=True)

    page.get_by_role("button", name="安全实验室").click()
    page.get_by_role("heading", name="健康AI安全实验室").wait_for()
    page.get_by_text("全部安全回归通过").wait_for()
    page.screenshot(path=OUT / "careai-safety-lab.png", full_page=True)

    mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    mobile_page = mobile.new_page()
    mobile_page.on("console", lambda message: console_errors.append("mobile: " + message.text) if message.type == "error" else None)
    mobile_page.goto("http://127.0.0.1:5173")
    mobile_page.wait_for_load_state("networkidle")
    mobile_page.screenshot(path=OUT / "careai-mobile-home.png", full_page=True)
    mobile.close()
    desktop.close()
    browser.close()

result = {
    "screenshots": sorted(path.name for path in OUT.glob("*.png")),
    "console_errors": console_errors,
}
(OUT / "browser-qa.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
if console_errors:
    raise SystemExit(1)
