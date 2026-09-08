# -*- coding: utf-8 -*-
"""Create the six-slide Stage 1 briefing deck from verified submission facts."""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

OUT = Path(__file__).resolve().parent / "第一阶段最终汇报PPT_5分钟_含证据页.pptx"
NAVY = RGBColor(17, 37, 64)
BLUE = RGBColor(39, 100, 163)
TEAL = RGBColor(20, 136, 137)
RED = RGBColor(191, 56, 56)
ORANGE = RGBColor(210, 121, 31)
WHITE = RGBColor(255, 255, 255)
TEXT = RGBColor(34, 45, 59)
MUTED = RGBColor(92, 105, 120)
PALE = RGBColor(239, 245, 251)
MIST = RGBColor(247, 250, 253)
SKY = RGBColor(214, 236, 247)
MINT = RGBColor(208, 237, 232)


def text_box(slide, text, x, y, w, h, size=18, color=TEXT, bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = frame.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = "Microsoft YaHei"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return box


def bullet_box(slide, items, x, y, w, h, size=16, color=TEXT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    for idx, item in enumerate(items):
        p = frame.paragraphs[0] if idx == 0 else frame.add_paragraph()
        p.text = item
        p.level = 0
        p.font.name = "Microsoft YaHei"
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.space_after = Pt(10)
        p.bullet = True
    return box


def header(slide, index, title, subtitle=""):
    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.72))
    band.fill.solid(); band.fill.fore_color.rgb = NAVY; band.line.fill.background()
    text_box(slide, f"{index:02d}", 0.45, 0.08, 0.55, 0.45, 20, RGBColor(150, 212, 235), True)
    text_box(slide, title, 1.0, 0.08, 8.9, 0.45, 25, WHITE, True)
    if subtitle:
        text_box(slide, subtitle, 9.6, 0.12, 3.2, 0.35, 10, RGBColor(203, 220, 235), False, PP_ALIGN.RIGHT)
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(0.72), Inches(13.333), Inches(0.055))
    accent.fill.solid(); accent.fill.fore_color.rgb = RGBColor(85, 192, 196); accent.line.fill.background()
    text_box(slide, "CareAI × VentureAI  ｜  Phase 1", 9.35, 7.08, 3.3, 0.18, 8.5, MUTED, False, PP_ALIGN.RIGHT)


def card(slide, title, body, x, y, w, h, accent=BLUE):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid(); shape.fill.fore_color.rgb = WHITE
    shape.line.color.rgb = RGBColor(218, 230, 240)
    strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(0.08), Inches(h))
    strip.fill.solid(); strip.fill.fore_color.rgb = accent; strip.line.fill.background()
    text_box(slide, title, x + 0.25, y + 0.14, w - 0.45, 0.35, 16, accent, True)
    text_box(slide, body, x + 0.25, y + 0.58, w - 0.45, h - 0.72, 12.5, TEXT)


def new_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid(); bg.fore_color.rgb = MIST
    # Subtle, editable geometric texture for visual depth without harming text contrast.
    for x, y, size, color, transparency in [
        (11.45, 0.78, 2.05, SKY, 28),
        (12.35, 1.55, 1.20, MINT, 10),
        (-0.65, 6.15, 1.85, SKY, 42),
        (0.15, 6.55, 0.90, MINT, 18),
    ]:
        circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(size), Inches(size))
        circle.fill.solid(); circle.fill.fore_color.rgb = color; circle.fill.transparency = transparency
        circle.line.fill.background()
    return slide


def main():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide = new_slide(prs)
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    shape.fill.solid(); shape.fill.fore_color.rgb = NAVY; shape.line.fill.background()
    # Cover-only layered arcs create a richer backdrop while staying editable.
    for x, y, size, color, transparency in [
        (-1.35, -1.1, 4.0, BLUE, 38),
        (10.7, -0.9, 4.1, TEAL, 34),
        (9.6, 4.85, 3.4, BLUE, 55),
        (-0.6, 5.8, 2.2, TEAL, 48),
    ]:
        blob = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(size), Inches(size))
        blob.fill.solid(); blob.fill.fore_color.rgb = color; blob.fill.transparency = transparency
        blob.line.fill.background()
    cover_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(4.15), Inches(3.65), Inches(5.05), Inches(0.05))
    cover_line.fill.solid(); cover_line.fill.fore_color.rgb = RGBColor(93, 205, 203); cover_line.line.fill.background()
    text_box(slide, "CareAI × VentureAI", 0.85, 1.25, 11.6, 0.8, 34, WHITE, True, PP_ALIGN.CENTER)
    text_box(slide, "第一阶段：项目立项与 Agent V1 诊断基线", 0.85, 2.15, 11.6, 0.5, 22, RGBColor(171, 220, 238), True, PP_ALIGN.CENTER)
    text_box(slide, "82 组｜2026-09-06｜约 5 分钟", 0.85, 3.0, 11.6, 0.35, 14, RGBColor(210, 224, 236), False, PP_ALIGN.CENTER)
    text_box(slide, "CareAI 是本阶段创业项目；VentureAI 是冻结并被测试的教学 Agent V1。", 1.2, 4.35, 10.9, 0.6, 17, WHITE, False, PP_ALIGN.CENTER)
    text_box(slide, "跨组测试、跨组互评与同伴评分已由课程要求取消。", 1.2, 5.15, 10.9, 0.35, 13, RGBColor(255, 205, 136), True, PP_ALIGN.CENTER)

    slide = new_slide(prs)
    header(slide, 2, "项目定位、依据与边界", "A 区：不把假设写成事实")
    card(slide, "项目与用户", "CareAI：面向成年人的非诊断性健康风险教育与习惯管理原型。\n\n目标：愿意主动记录基础健康数据的成年人（H）。\n\n不适用：未成年人、急重症、诊疗或用药决策。", 0.55, 1.15, 3.9, 5.55, TEAL)
    card(slide, "公开依据（F）", "国家卫健委《健康中国行动》\nWHO 身体活动建议\nCDC 睡眠建议\n个人信息保护法敏感信息要求\n\n均为可定位的权威公开资料。", 4.75, 1.15, 3.9, 5.55, BLUE)
    card(slide, "证据边界", "F：公开资料 / 代码事实\nI：基于事实的解释\nH：待验证假设\nS：Agent 或情境模拟\n\n本阶段未做问卷、访谈、试用、订单、临床或运营验证。", 8.95, 1.15, 3.85, 5.55, ORANGE)

    slide = new_slide(prs)
    header(slide, 3, "方案、创新与风险", "B 区：规则优先，不作医疗诊断")
    text_box(slide, "健康数据录入  →  本地规则提示  →  受限 AI 解释与 7 天计划  →  历史趋势", 0.75, 1.1, 11.8, 0.55, 22, NAVY, True, PP_ALIGN.CENTER)
    card(slide, "创新机制（H）", "1. 风险判断与生成解释分层\n2. 指标—原因—建议—行动计划闭环\n3. 非诊断边界在输入、报告和规则中可见", 0.7, 2.0, 3.8, 3.7, TEAL)
    card(slide, "替代做法", "自行看数据：指标零散\n通用搜索 / 对话：边界与来源未必清晰\n不用工具：难以持续记录\n\nCareAI 仅提出机制差异，尚未宣称效果更好。", 4.78, 2.0, 3.8, 3.7, BLUE)
    card(slide, "关键风险", "医疗安全：非诊断、需专业复核\n数据合规：授权、最小化、删除和访问控制\n技术：外部模型不可用\n证据：无真实用户验证", 8.86, 2.0, 3.8, 3.7, RED)

    slide = new_slide(prs)
    header(slide, 4, "V1 首测保留，V1.1 独立复测", "C 区：不以修复版本覆盖首次失败")
    text_box(slide, "V1：c456aef（首次基线） ｜ V1.1：6299e2c（独立修复标签） ｜ 13 项 V1 关键文件哈希一致", 0.7, 1.05, 12.0, 0.5, 15, NAVY, True, PP_ALIGN.CENTER)
    card(slide, "T1 理论学习", "V1：被路由为 coach，未完成。\n\nV1.1：intent=tutor；完成定义、正反例、常见错误、练习任务和 3 个理解检查。\n\n复测：通过。", 0.6, 2.0, 3.9, 3.95, TEAL)
    card(slide, "T2 项目指导", "V1：一次输出多项诊断与问题。\n\nV1.1：intent=coach；只给一个问题和一个验收标准，不要求虚构访谈。\n\n复测：通过。", 4.72, 2.0, 3.9, 3.95, TEAL)
    card(slide, "T3 项目评审", "V1：返回 coach 式通用诊断。\n\nV1.1：intent=grader；完成社会价值、实践依据、创新、前景和团队五维评审。\n\n复测：通过。", 8.84, 2.0, 3.9, 3.95, TEAL)

    slide = new_slide(prs)
    header(slide, 5, "真实问题案例与任务影响", "D 区：5 个可复现案例，覆盖 ≥2 个流程")
    card(slide, "P0：环境依赖冲突", "默认全局环境无法启动；隔离环境只用于保留并复现首次基线。", 0.55, 1.05, 4.0, 1.6, RED)
    card(slide, "P1：显式流程被覆盖", "指定 tutor / grader 后仍返回 coach，T1/T3/C2 目标失效。", 4.72, 1.05, 4.0, 1.6, RED)
    card(slide, "P1：F/I/H/S 边界失效", "对“未做真实验证”的材料仍要求补写访谈等事实，或产生无来源风险。", 8.89, 1.05, 3.9, 1.6, ORANGE)
    card(slide, "P1：单步指导失效", "要求每步一个任务和验收标准，仍一次输出多项诊断。", 0.55, 3.0, 4.0, 1.6, ORANGE)
    card(slide, "P1：分类请求误拦截", "C3 的 F/I/H/S 与健康隐私检查被误判为代写，未完成分类。", 4.72, 3.0, 4.0, 1.6, RED)
    text_box(slide, "5 个案例均含原始对话、时间、会话 ID、人工干预与复现步骤；完整案例卡已写入最终报告。", 0.8, 5.55, 11.8, 0.45, 15, MUTED, False, PP_ALIGN.CENTER)

    slide = new_slide(prs)
    header(slide, 6, "原始运行证据：V1 失败与 V1.1 修复对照", "把截图拖入下方两个框内即可")
    text_box(slide, "同一个任务：对 CareAI 的四句话进行 F / I / H / S 分类，并说明医疗与隐私边界", 0.7, 1.0, 11.9, 0.42, 16, NAVY, True, PP_ALIGN.CENTER)
    for x, title, subtitle, accent, note in [
        (0.65, "V1 首次基线：错误拦截", "会话 83618b05-396b-42cc-9985-34ec142752a4", RED, "把 V1 的截图放在这里\n\n说明：系统把材料分类请求误判成“代写”，没有完成 F/I/H/S 审阅。"),
        (6.88, "V1.1 独立复测：正确完成", "会话 5b369e6c-4377-4587-844c-0418014cad24", TEAL, "把 V1.1 的截图放在这里\n\n说明：系统将无来源主张标为 H、模拟反馈标为 S，并提示医疗与隐私边界。"),
    ]:
        frame = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(1.65), Inches(5.8), Inches(3.65))
        frame.fill.solid(); frame.fill.fore_color.rgb = WHITE
        frame.line.color.rgb = accent
        frame.line.width = Pt(2)
        text_box(slide, title, x + 0.18, 1.82, 5.45, 0.30, 16, accent, True, PP_ALIGN.CENTER)
        text_box(slide, subtitle, x + 0.18, 2.15, 5.45, 0.23, 9.5, MUTED, False, PP_ALIGN.CENTER)
        text_box(slide, "截图放置区", x + 0.18, 2.56, 5.45, 0.32, 17, RGBColor(158, 172, 184), True, PP_ALIGN.CENTER)
        text_box(slide, "插入图片后，可删除本框内的提示文字", x + 0.18, 2.94, 5.45, 0.23, 10.5, RGBColor(158, 172, 184), False, PP_ALIGN.CENTER)
        card(slide, "你要讲的话", note, x, 5.55, 5.8, 1.0, accent)
    text_box(slide, "关键结论：我们保留首次失败，也保留修复后的新会话；V1.1 没有替代或覆盖 V1。", 0.8, 6.8, 11.7, 0.28, 13.5, MUTED, True, PP_ALIGN.CENTER)

    slide = new_slide(prs)
    header(slide, 7, "阶段结论与下一步", "E 区：G1–G5 的证据链已齐备")
    card(slide, "本阶段结论", "CareAI 已完成有边界的立项与可追溯证据整理。\n\nVentureAI V1 的首次失败被完整保留；V1.1 已在独立提交中完成 T1/T2/T3 和 F/I/H/S 复测。", 0.7, 1.25, 5.8, 4.9, TEAL)
    card(slide, "第二阶段优先级", "1. 持续验证锁定依赖环境\n2. 扩展显式路由回归测试\n3. 细化 F/I/H/S 证据追踪\n4. 评估单步协议的多轮体验\n5. 继续区分材料评审与代写拦截\n\n保留 V1 与 V1.1 全部日志。", 6.85, 1.25, 5.8, 4.9, BLUE)
    text_box(slide, "谢谢｜问题、局限与下一步均可回溯至正式提交材料", 0.8, 6.55, 11.7, 0.3, 13, MUTED, False, PP_ALIGN.CENTER)

    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
