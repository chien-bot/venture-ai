# -*- coding: utf-8 -*-
"""生成 VentureAI 验收文档 Word 版"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()

# ── 页边距 ──────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3)
    section.right_margin = Cm(2.5)

# ── 辅助函数 ────────────────────────────────────────────────
def set_run_font(run, size=11, bold=False, color=None, italic=False):
    run.font.name = '微软雅黑'
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)
    run._r.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

def add_heading(text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    sizes = {1: 16, 2: 13, 3: 12}
    colors = {1: (63, 81, 181), 2: (25, 118, 210), 3: (21, 101, 192)}
    set_run_font(run, size=sizes.get(level, 12), bold=True, color=colors.get(level, (0,0,0)))

def add_para(text, indent=0):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    run = p.add_run(text)
    set_run_font(run, size=11)
    return p

def add_bullet(text, level=1):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.left_indent = Cm(level * 0.8)
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    run = p.add_run(text)
    set_run_font(run, size=10.5)

def add_note(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.right_indent = Cm(0.8)
    shading = OxmlElement('w:shd')
    shading.set(qn('w:val'), 'clear')
    shading.set(qn('w:color'), 'auto')
    shading.set(qn('w:fill'), 'EEF2FF')
    p._p.pPr.append(shading)
    run = p.add_run(text)
    set_run_font(run, size=10, italic=True, color=(55, 65, 245))

def add_table(headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.paragraphs[0].clear()
        run = cell.paragraphs[0].add_run(h)
        set_run_font(run, size=10.5, bold=True, color=(255, 255, 255))
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), '3F51B5')
        tcPr.append(shd)
    for ri, row_data in enumerate(rows):
        row = table.rows[ri + 1]
        fill = 'F8F9FF' if ri % 2 == 0 else 'FFFFFF'
        for ci, cell_text in enumerate(row_data):
            cell = row.cells[ci]
            cell.paragraphs[0].clear()
            run = cell.paragraphs[0].add_run(str(cell_text))
            set_run_font(run, size=10)
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'), 'clear')
            shd.set(qn('w:color'), 'auto')
            shd.set(qn('w:fill'), fill)
            tcPr.append(shd)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return table

def add_hr():
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '3F51B5')
    pBdr.append(bottom)
    pPr.append(pBdr)

# ===============================================================
# 封面
# ===============================================================
doc.add_paragraph()
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('VentureAI 创新创业教学智能体')
set_run_font(run, size=26, bold=True, color=(63, 81, 181))

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = p2.add_run('项目验收文档')
set_run_font(run2, size=20, bold=True, color=(25, 118, 210))

doc.add_paragraph()
meta = [
    ('项目名称', 'VentureAI 创新创业教学智能体'),
    ('文档版本', 'v1.0'),
    ('日期', '2026-04-20'),
    ('服务器地址', 'http://121.14.82.109:8221'),
    ('前端技术', 'Next.js 14 + TypeScript + Tailwind CSS'),
    ('后端技术', 'Python FastAPI + SQLite'),
    ('AI 引擎', 'Anthropic Claude API'),
]
for k, v in meta:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run(k + '：')
    set_run_font(r1, size=12, bold=True, color=(55, 65, 81))
    r2 = p.add_run(v)
    set_run_font(r2, size=12, color=(75, 85, 99))

doc.add_page_break()

# ===============================================================
# 目录
# ===============================================================
add_heading('目录', 1)
add_hr()
toc_items = [
    '一、系统总览',
    '二、验收场景演示',
    '三、Prompt 设计说明',
    '四、知识图谱评估',
    '五、超图一致性评估',
    '六、引用正确性机制',
    '七、用户/角色/权限管理',
    '八、UI 美观度',
    '九、学生与班级画像',
    '十、商业计划书生成与下载',
    '十一、TAM/SAM/SOM 商业模型',
    '十二、商业型 vs 公益型项目测试',
    '十三、与两份参考文档的差距分析',
    '附录 A：录屏脚本',
    '附录 B：系统环境信息',
]
for item in toc_items:
    add_bullet(item)

doc.add_page_break()

# ===============================================================
# 一、系统总览
# ===============================================================
add_heading('一、系统总览', 1)
add_hr()
add_para('VentureAI 是一个面向高校创新创业教育的 AI 教学智能体平台，核心设计理念为：')
add_note(
    '用知识图谱"管知识"，用超图"管一致性"，用智能体"管过程"，用 Rubric"管评价"'
    '——把创新创业教学从"靠经验带项目"，升级为"可计算、可追溯、可规模化的教学系统"。'
)

add_heading('1.1 技术架构', 2)
add_table(
    ['层级', '技术选型'],
    [
        ['前端', 'Next.js 14 + TypeScript + Tailwind CSS'],
        ['后端', 'Python FastAPI'],
        ['AI 引擎', 'Anthropic Claude API（claude-sonnet / claude-haiku）'],
        ['知识层', '知识图谱 Schema（JSON）+ 超图约束规则（22条）'],
        ['数据层', 'SQLite（可扩展至 PostgreSQL）'],
    ],
    col_widths=[4, 12]
)

add_heading('1.2 五大智能体', 2)
add_table(
    ['智能体', '角色定位', '核心功能'],
    [
        ['Coach Agent', '项目教练', '苏格拉底追问 + 三轮诊断 + 隐性评分'],
        ['Tutor Agent', '学习辅导', 'KG 知识点讲解 + 先修关系 + 练习任务'],
        ['Competition Agent', '竞赛顾问', '对标评分 + 缺口分析 + 最小修复方案'],
        ['TA Agent', '教师助理', '班级画像 + 批量评估 + 预警提示'],
        ['Investor Agent', '投资模拟辩论', '质疑 + 反驳训练 + 思辨压力测试'],
    ],
    col_widths=[4, 4, 8]
)

add_heading('1.3 三层知识结构', 2)
add_table(
    ['结构层', '组件', '数量'],
    [
        ['知识图谱', '11 种节点类型 + 9 种关系类型', '完整实现'],
        ['超图约束', 'H1 到 H22 一致性规则', '22 条（超过蓝图要求 15 条）'],
        ['Rubric', 'R1 到 R11 评分维度', '11 条（超过蓝图要求 9 条）'],
    ],
    col_widths=[4, 9, 3]
)

doc.add_page_break()

# ===============================================================
# 二、验收场景演示
# ===============================================================
add_heading('二、验收场景演示', 1)
add_hr()

add_heading('2.1 商业型项目演示', 2)
add_para('演示项目：智能外卖配送优化 SaaS 平台')
add_table(
    ['步骤', '操作', '预期结果'],
    [
        ['1', '以 student01 登录学生端', '进入项目列表页面'],
        ['2', '创建新项目"餐饮配送优化平台"', '项目卡片生成，状态为草稿'],
        ['3', '启动 Coach Agent 对话', 'AI 开始苏格拉底式追问（Discovery 阶段）'],
        ['4', '回答痛点、用户、方案问题', '进入 Stress Test 阶段，AI 挑战逻辑一致性'],
        ['5', '触发超图检查', '系统检测到 H5（定价成本倒挂），给出修复建议'],
        ['6', '查看 Rubric 评分', 'R1 到 R11 各维度得分展示，含证据链'],
        ['7', '生成商业计划书', 'PDF/DOCX 下载，含 TAM/SAM/SOM 分析'],
    ],
    col_widths=[1, 6, 9]
)

add_heading('2.2 公益型项目演示', 2)
add_para('演示项目：农村留守儿童在线教育公益平台')
add_table(
    ['步骤', '操作', '预期结果'],
    [
        ['1', '以 student02 登录学生端', '进入项目列表页面'],
        ['2', '创建新项目"留守儿童教育平台"，选择公益型', '项目标注公益标签'],
        ['3', '启动 Coach Agent 对话', 'AI 关注社会影响力而非商业指标'],
        ['4', '讨论受益人群、公益模式、可持续资金', 'AI 引导考虑政府补贴/捐赠模式'],
        ['5', '触发 H10（公益逻辑一致性）检查', '超图检测公益承诺与运营模式是否一致'],
        ['6', '生成公益项目报告', '输出侧重社会价值而非盈利指标'],
    ],
    col_widths=[1, 6, 9]
)

add_heading('2.3 教师端演示', 2)
add_table(
    ['步骤', '操作', '预期结果'],
    [
        ['1', '以 teacher01 登录教师端', '进入教师仪表板'],
        ['2', '查看班级项目列表', '所有学生项目汇总，含评分进度'],
        ['3', '查看班级画像雷达图', 'R1 到 R11 各维度班级平均分可视化'],
        ['4', '点击某学生查看个人画像', '个人 Rubric 雷达图 + 对话证据钻取'],
        ['5', '使用 TA Agent 批量评估', 'AI 自动对比全班项目，生成弱项预警'],
        ['6', '上传教学材料（知识文件）', '文件被解析并注入 KG 知识库'],
    ],
    col_widths=[1, 6, 9]
)

add_heading('2.4 管理员端演示', 2)
add_table(
    ['步骤', '操作', '预期结果'],
    [
        ['1', '以 admin01 登录管理端', '进入管理员仪表板'],
        ['2', '查看用户列表', '所有用户、角色、注册时间展示'],
        ['3', '创建/删除班级', '班级管理 CRUD 操作成功'],
        ['4', '查看系统统计', '项目总数、对话次数、评分分布'],
        ['5', '修改 Rubric 权重', '权重更新后评分实时重算'],
    ],
    col_widths=[1, 6, 9]
)

doc.add_page_break()

# ===============================================================
# 三、Prompt 设计说明
# ===============================================================
add_heading('三、Prompt 设计说明', 1)
add_hr()
add_para(
    '系统采用分层 Prompt 架构：系统级（角色 + 规则）→ 情境级（KG/Rubric 上下文）→ '
    '任务级（当前对话任务），每条 Prompt 均可在代码库中追溯。'
)

agent_prompts = [
    (
        'Coach Agent',
        (
            '你是一位创业教练，不直接给答案，只用苏格拉底追问法引导学生。\n'
            '当前任务阶段：{stage}（Discovery / Stress Test / Feasibility Check）\n'
            '相关 Rubric 项：{rubric_items}\n'
            '已检测到的超图冲突：{hypergraph_issues}\n'
            '输出格式：\n'
            '- 当前最关键瓶颈（顶层诊断）\n'
            '- 使用的证据（显式引用）\n'
            '- 若不修复的影响\n'
            '- 下一步任务（ONLY ONE）：任务说明 + 模板 + 验收标准'
        ),
        '三轮诊断结构防止信息过载；隐性评分绑定每条建议；超图冲突自动注入'
    ),
    (
        'Tutor Agent',
        (
            '你是一位创业课程辅导员，基于以下 KG 上下文回答问题。\n'
            '知识节点：{kg_context}\n'
            '先修节点：{prereq_nodes}\n'
            '输出结构：\n'
            '1. 概念定义（清晰简洁）\n'
            '2. 实际案例（来自案例库）\n'
            '3. 常见错误（来自 KG Mistake 节点）\n'
            '4. 练习任务（一个可执行任务）\n'
            '5. 预期产物\n'
            '6. 评价标准（链接到 Rubric）'
        ),
        '每次引用 KG 节点字段，不凭空生成；输出结构固定，产出可评估证据'
    ),
    (
        'Competition Agent',
        (
            '对标互联网+/挑战杯 Rubric，评估当前项目。\n'
            '当前得分估算：{score_estimate}/100\n'
            '输出：\n'
            '- 逐条评分维度：当前得分 → 缺口证据 → 最小修复任务\n'
            '- 评委一眼扣分问题（直接指出）\n'
            '- 最高性价比的修复顺序'
        ),
        '超图竞赛评分映射超边；每个评分项至少需要 1 条落在材料具体位置的证据'
    ),
    (
        'TA Agent',
        (
            '你是教师助理，对全班项目进行横向对比分析。\n'
            '班级项目列表：{class_projects}\n'
            '输出：\n'
            '- 班级画像（各维度平均分雷达图数据）\n'
            '- Top 3 共性弱项\n'
            '- 需要重点关注的学生（低于 60 分）\n'
            '- 教学干预建议'
        ),
        '聚合全班 Rubric 数据；识别班级共性问题；生成个性化干预建议'
    ),
    (
        'Investor Agent',
        (
            '你是一位刻薄但专业的投资人，对学生的商业计划提出质疑。\n'
            '当前项目摘要：{project_summary}\n'
            '质疑重点：市场规模真实性、竞争壁垒、盈利模式可行性、团队能力\n'
            '风格：犀利、有逻辑、不接受模糊答案'
        ),
        '模拟真实投资问答；训练学生应对压力质疑；强化论证完整性'
    ),
]

for name, prompt_text, design_note in agent_prompts:
    add_heading(name + ' Prompt', 2)
    p = doc.add_paragraph()
    run = p.add_run(prompt_text)
    set_run_font(run, size=9.5)
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.space_before = Pt(2)
    add_note('设计说明：' + design_note)

doc.add_page_break()

# ===============================================================
# 四、知识图谱评估
# ===============================================================
add_heading('四、知识图谱评估', 1)
add_hr()
add_para(
    '知识图谱 Schema 定义于 backend/data/ontology/kg_schema.json，'
    '包含 11 种节点类型和 9 种关系类型，完全符合蓝图文档要求。'
)

add_heading('4.1 节点类型（11种）', 2)
add_table(
    ['节点类型', '说明', '示例'],
    [
        ['Concept', '核心概念', 'PMF、TAM、SAM、SOM、Value Proposition、Moat、CAC、LTV'],
        ['Method', '分析方法', 'Lean Canvas、JTBD、AARRR、SWOT、Porter Five Forces'],
        ['Task', '学习任务', '用户访谈、竞品分析、财务建模'],
        ['Artifact', '产出物', '用户访谈记录、竞争矩阵、财务预测表'],
        ['Metric', '评估指标', '月活跃用户、净推荐值、毛利率'],
        ['Case', '案例', '滴滴出行、美团外卖、拼多多早期增长'],
        ['RubricItem', '评分项', 'R1 到 R11 各维度'],
        ['Mistake', '常见错误', '目标用户过宽、定价依赖竞争对手'],
        ['Evidence', '证据', '对话中的具体引用片段'],
        ['Project', '项目实体', '学生的具体创业项目'],
        ['UserProfile', '用户画像', '学生各维度能力画像数据'],
    ],
    col_widths=[3, 4, 9]
)

add_heading('4.2 关系类型（9种）', 2)
add_table(
    ['关系类型', '含义', '示例'],
    [
        ['PREREQ', '先修关系', 'TAM → SAM（先理解总市场才能细分）'],
        ['USES', '方法使用', 'Task "用户访谈" USES Method "JTBD"'],
        ['PRODUCES', '产出关系', 'Task "竞品分析" PRODUCES Artifact "竞争矩阵"'],
        ['MEASURED_BY', '度量关系', 'Project MEASURED_BY Metric "月活跃用户"'],
        ['EVIDENCED_BY', '证据关系', 'RubricItem R2 EVIDENCED_BY Evidence "访谈截图"'],
        ['EVALUATED_BY', '评价关系', 'Project EVALUATED_BY RubricItem R1 到 R11'],
        ['COMMON_MISTAKE', '常见错误', 'Concept "定价" COMMON_MISTAKE "定价低于成本"'],
        ['FIX_STRATEGY', '修复策略', 'Mistake "目标用户过宽" FIX_STRATEGY Task "用户细分工作坊"'],
        ['EXEMPLIFIED_BY', '案例佐证', 'Concept "PMF" EXEMPLIFIED_BY Case "Slack 早期迭代"'],
    ],
    col_widths=[4, 4, 8]
)

add_heading('4.3 知识图谱触发机制', 2)
add_table(
    ['触发场景', '触发条件', '系统响应'],
    [
        ['学生提问概念', '关键词匹配 KG Concept 节点', 'Tutor Agent 注入 KG 上下文回答'],
        ['Coach 诊断阶段', '当前对话关联 Task/Artifact', '自动关联先修 Concept 节点'],
        ['评分时', 'Rubric 维度关联 Evidence', '从 KG Evidence 节点提取证据链'],
        ['竞赛辅导', 'Project 节点关联 RubricItem', 'Competition Agent 对标评分维度'],
        ['错误修复', '触发 Mistake 节点', 'FIX_STRATEGY 自动推荐修复任务'],
    ],
    col_widths=[4, 5, 7]
)

doc.add_page_break()

# ===============================================================
# 五、超图一致性评估
# ===============================================================
add_heading('五、超图一致性评估', 1)
add_hr()
add_para(
    '超图约束规则定义于 backend/data/rubric/constraint_rules.json，'
    '共 22 条规则（H1 到 H22），涵盖商业型和公益型项目，超过蓝图要求的 15 条。'
)

add_heading('5.1 H1 到 H11 核心约束（商业型）', 2)
add_table(
    ['规则ID', '类型', '严重度', '触发条件摘要', '关联 Rubric'],
    [
        ['H1', '客户价值主张错位', '高', '目标客户描述与价值主张不匹配', 'R1, R3'],
        ['H2', '方案痛点脱节', '高', '解决方案未针对核心痛点', 'R1, R3'],
        ['H3', '市场规模增长预期矛盾', '中', 'TAM 过小但增长率预测过高', 'R5, R6'],
        ['H4', '竞争分析缺失', '中', '未提及竞争对手或差异化策略', 'R5, R7'],
        ['H5', '定价成本倒挂', '高', '售价低于估算成本', 'R6'],
        ['H6', '团队能力执行计划不匹配', '中', '执行计划复杂但团队背景不足', 'R8'],
        ['H7', '用户证据缺失', '高', '未提供任何用户访谈/调研证据', 'R2'],
        ['H8', '财务逻辑断链', '高', '收入预测缺乏成本或增长假设', 'R6'],
        ['H9', '商业模式内部矛盾', '高', '免费模式与盈利目标冲突', 'R4'],
        ['H10', '可行性评估缺失', '中', '未讨论技术/法规/资源可行性', 'R3'],
        ['H11', '护城河缺失', '中', '有竞争对手但未说明差异化壁垒', 'R7'],
    ],
    col_widths=[2, 4, 2, 6, 2]
)

add_heading('5.2 H12 到 H22 扩展约束（含公益型）', 2)
add_table(
    ['规则ID', '类型', '严重度', '触发条件摘要', '关联 Rubric'],
    [
        ['H12', '增长策略缺失', '低', '有目标用户但无获客/增长计划', 'R11'],
        ['H13', '合规风险忽视', '中', '涉及金融/医疗/教育但未提监管', 'R10'],
        ['H14', '规模化路径不清', '低', '本地化项目但声称全国规模', 'R11'],
        ['H15', '关键假设未验证', '中', '核心商业假设无任何验证数据', 'R2, R3'],
        ['H16', '社会影响表述模糊', '中', '公益项目无具体社会影响指标', 'R10'],
        ['H17', 'LTV/CAC 比例失衡', '高', 'LTV 显著低于 CAC，单位经济不可行', 'R6'],
        ['H18', '渠道用户群错配', '中', '目标用户不活跃于所选渠道', 'R4, R5'],
        ['H19', '产品迭代计划缺失', '低', '无 MVP 或产品路线图', 'R3, R8'],
        ['H20', '资金需求使用计划不匹配', '中', '融资金额与用途说明不对应', 'R6, R8'],
        ['H21', '公益可持续性风险', '高', '公益项目无稳定资金来源说明', 'R6, R10'],
        ['H22', '竞争认知盲区', '中', '声称无竞争对手但市场已成熟', 'R5'],
    ],
    col_widths=[2, 4, 2, 6, 2]
)

add_heading('5.3 超图触发示例', 2)
add_note(
    '示例：学生项目描述"我们的 SaaS 平台月费 99 元，服务器成本约 150 元/用户"'
    ' → H5（定价成本倒挂）触发 → Coach Agent 自动询问'
    ' "你的单位经济是否可持续？请计算 LTV 和 CAC 的比值。"'
)

doc.add_page_break()

# ===============================================================
# 六、引用正确性机制
# ===============================================================
add_heading('六、引用正确性机制', 1)
add_hr()
add_para('系统实现了完整的证据链追溯机制，确保每一条 AI 评分和建议都有具体对话证据支撑。')

add_heading('6.1 证据链三层架构', 2)
add_table(
    ['层级', '内容', '存储位置'],
    [
        ['对话记录层', '每条学生发言原文 + 时间戳', '数据库 messages 表'],
        ['证据提取层', 'AI 从对话中提取的关键陈述片段', '数据库 evidences 表'],
        ['评分绑定层', 'Rubric 得分与证据 ID 的关联', '数据库 scores 表'],
    ],
    col_widths=[4, 8, 5]
)

add_heading('6.2 防幻觉机制', 2)
add_table(
    ['机制', '说明'],
    [
        ['KG 上下文注入', '每次 Tutor Agent 回答必须引用 KG 节点字段，不凭空生成'],
        ['证据显式引用', 'Coach Agent 必须在输出中注明"使用的证据（显式引用）"'],
        ['超图触发溯源', '每条超图警告必须对应具体对话片段'],
        ['Rubric 评分追溯', '每个 R1 到 R11 分数必须绑定至少 1 条证据 ID'],
        ['KG 节点验证', 'Tutor Agent 引用的概念必须存在于 KG Schema 中'],
    ],
    col_widths=[5, 11]
)

doc.add_page_break()

# ===============================================================
# 七、用户/角色/权限管理
# ===============================================================
add_heading('七、用户/角色/权限管理', 1)
add_hr()

add_heading('7.1 三角色权限矩阵', 2)
add_table(
    ['功能', '学生', '教师', '管理员'],
    [
        ['创建/编辑自己的项目', '是', '否', '否'],
        ['与智能体对话（Coach/Tutor）', '是', '否', '否'],
        ['与竞赛顾问/投资人对话', '是', '否', '否'],
        ['查看自己的 Rubric 评分', '是', '否', '否'],
        ['下载自己的商业计划书', '是', '否', '否'],
        ['查看班级所有学生项目', '否', '是', '是'],
        ['查看班级画像雷达图', '否', '是', '是'],
        ['使用 TA Agent 批量评估', '否', '是', '否'],
        ['上传/管理知识材料', '否', '是', '是'],
        ['修改 Rubric 权重', '否', '否', '是'],
        ['用户管理（创建/删除用户）', '否', '否', '是'],
        ['班级管理（创建/删除班级）', '否', '否', '是'],
        ['查看系统统计数据', '否', '否', '是'],
        ['查看所有班级数据', '否', '否', '是'],
    ],
    col_widths=[8, 2, 2, 2]
)

add_heading('7.2 认证机制', 2)
add_table(
    ['机制', '说明'],
    [
        ['JWT Token', '登录后签发，存储于 sessionStorage + Cookie'],
        ['角色校验', '每个 API 端点验证 token 中的 role 字段'],
        ['会话过期', 'Token 过期自动跳转登录页（携带 expired=1 参数）'],
        ['密码安全', '密码 bcrypt 哈希存储'],
        ['前端路由保护', 'Next.js middleware 拦截未登录/越权访问'],
    ],
    col_widths=[5, 11]
)

add_heading('7.3 测试账号', 2)
add_table(
    ['角色', '用户名', '密码', '班级'],
    [
        ['学生', 'student01', '123456', 'CLASS_A'],
        ['学生', 'student02', '123456', 'CLASS_A'],
        ['学生', 'student03', '123456', 'CLASS_B'],
        ['教师', 'teacher01', '123456', '管理 CLASS_A 和 CLASS_B'],
        ['管理员', 'admin01', '123456', '全系统权限'],
    ],
    col_widths=[3, 4, 3, 7]
)

doc.add_page_break()

# ===============================================================
# 八、UI 美观度
# ===============================================================
add_heading('八、UI 美观度', 1)
add_hr()

add_heading('8.1 设计语言', 2)
add_table(
    ['设计元素', '实现方式'],
    [
        ['色彩体系', '深色底（#0F1117）+ 蓝紫色主调（#6366F1）+ 青色点缀（#22D3EE）'],
        ['极光背景', '三层径向渐变 + animate-aurora 动画，营造科技感氛围'],
        ['玻璃拟态', '全局 glass 类：backdrop-blur + 半透明边框'],
        ['渐变文字', 'gradient-text 类：蓝紫到青色渐变标题'],
        ['悬停动效', 'hover:scale-105 + box-shadow 过渡，200ms ease'],
        ['加载状态', '旋转 spinner + 骨架屏（Skeleton）'],
        ['响应式布局', 'Tailwind md/lg 断点，支持平板和桌面'],
        ['图标体系', 'Emoji 图标（学生 教师 管理员）'],
    ],
    col_widths=[5, 11]
)

add_heading('8.2 页面列表', 2)
pages = [
    '登录/注册页（三角色切换，Aurora 动效背景）',
    '学生项目列表页（卡片网格，状态徽章）',
    '项目详情/对话页（左侧信息 + 右侧聊天界面）',
    'Rubric 评分展示页（进度条 + 雷达图）',
    '商业计划书生成页（结构化预览 + 下载按钮）',
    '教师仪表板（班级统计 + 学生列表 + 雷达图）',
    '学生个人画像页（多维度雷达图 + 证据钻取）',
    '管理员仪表板（用户管理 + 系统统计 + Rubric 配置）',
]
for pg in pages:
    add_bullet(pg)

add_heading('8.3 截图（请插入）', 2)
add_note('【请在此处插入：登录页截图、学生项目页截图、对话页截图、教师仪表板截图、管理员页截图】')

doc.add_page_break()

# ===============================================================
# 九、学生与班级画像
# ===============================================================
add_heading('九、学生与班级画像', 1)
add_hr()

add_heading('9.1 个人画像', 2)
add_para('每位学生的画像基于其所有对话的 Rubric 评分聚合生成，包含以下维度：')
add_table(
    ['维度', 'Rubric 项', '画像用途'],
    [
        ['痛点定义能力', 'R1', '能否清晰识别真实用户痛点'],
        ['用户研究能力', 'R2', '是否有实际用户访谈证据'],
        ['方案可行性', 'R3', '技术/资源/时间可行性'],
        ['商业模式设计', 'R4', '商业模式各要素是否一致'],
        ['市场分析能力', 'R5', '市场规模和竞争格局认知'],
        ['财务逻辑', 'R6', '收入/成本/盈利模型清晰度'],
        ['创新差异化', 'R7', '独特价值主张和护城河'],
        ['团队执行力', 'R8', '团队构成和执行计划'],
        ['表达与材料', 'R9', '方案陈述的完整性和说服力'],
        ['合规与社会责任', 'R10', '合规意识和社会影响考量'],
        ['增长规模化', 'R11', '增长路径和规模化策略'],
    ],
    col_widths=[5, 3, 8]
)
add_note(
    '雷达图以 R1 到 R11 为轴，0 到 5 分为半径，可视化学生能力分布；'
    '点击某个维度可钻取该维度的所有对话证据。'
)

add_heading('9.2 班级画像', 2)
add_table(
    ['功能', '说明'],
    [
        ['班级平均雷达图', '全班所有学生 R1 到 R11 平均分的雷达图叠加展示'],
        ['维度排名', '各维度全班得分排序，识别强项和共性弱项'],
        ['学生对比', '多个学生雷达图叠加对比'],
        ['预警列表', '低于 60 分（3/5 以下）的学生自动标红预警'],
        ['进度追踪', '同一学生多个时间点的评分曲线（成长轨迹）'],
    ],
    col_widths=[5, 11]
)

doc.add_page_break()

# ===============================================================
# 十、商业计划书生成与下载
# ===============================================================
add_heading('十、商业计划书生成与下载', 1)
add_hr()
add_para(
    '商业计划书由后端 generate_business_plan() 函数生成，基于项目对话历史和 Rubric 评分，'
    '输出结构化 Word 文档（.docx）。'
)

add_heading('10.1 商业计划书结构', 2)
add_table(
    ['章节', '内容来源', '字数估计'],
    [
        ['执行摘要', 'AI 从对话中提取核心要点', '300 到 500 字'],
        ['问题与机会', 'R1 痛点定义 + 用户证据', '500 到 800 字'],
        ['解决方案', 'R3 方案可行性对话内容', '500 到 800 字'],
        ['市场分析', 'R5 + TAM/SAM/SOM 计算', '600 到 1000 字'],
        ['商业模式', 'R4 商业模式一致性', '400 到 600 字'],
        ['竞争分析', 'R5 竞争格局 + 差异化', '400 到 600 字'],
        ['财务预测', 'R6 财务逻辑 + 数字模型', '400 到 700 字'],
        ['团队介绍', 'R8 团队与执行计划', '200 到 400 字'],
        ['融资需求', '来自项目设定', '200 到 300 字'],
        ['附录', 'Rubric 评分表 + 证据链', '自动生成'],
    ],
    col_widths=[4, 7, 5]
)

add_heading('10.2 下载功能', 2)
add_table(
    ['格式', '实现', '状态'],
    [
        ['Word (.docx)', 'python-docx 生成，含格式化样式', '已实现'],
        ['PDF', '前端 html2pdf.js 或后端 pdfkit 转换', '已实现'],
        ['Markdown', '纯文本结构化输出', '已实现'],
    ],
    col_widths=[4, 9, 3]
)

doc.add_page_break()

# ===============================================================
# 十一、TAM/SAM/SOM 商业模型
# ===============================================================
add_heading('十一、TAM/SAM/SOM 商业模型', 1)
add_hr()
add_para('系统引导学生完成三层市场规模分析，并将结果嵌入商业计划书中。')

add_heading('11.1 TAM/SAM/SOM 定义与计算框架', 2)
add_table(
    ['指标', '全称', '定义', '计算方法'],
    [
        ['TAM', '总可寻址市场', '某类产品/服务的全球/全国潜在市场规模', '自上而下：行业报告数据'],
        ['SAM', '可服务市场', 'TAM 中你的商业模式能触达的部分', '细分目标地区/人群'],
        ['SOM', '可获得市场', 'SAM 中你短期内实际能争取的份额', '参考竞品增速 + 自身资源'],
    ],
    col_widths=[2, 4, 5, 5]
)

add_heading('11.2 Coach Agent 引导流程', 2)
steps = [
    '询问行业：你的产品属于哪个细分行业？',
    '引入 TAM：该行业中国市场规模是多少？（引导查询行业报告）',
    '细化 SAM：你的目标地区和用户群是什么？从 TAM 中细分出来。',
    '估算 SOM：第一年，你计划获取 SAM 的百分之几？依据是什么？',
    '超图检查：H3（市场规模增长预期矛盾）触发验证',
    '写入计划书：将 TAM/SAM/SOM 数据写入市场分析章节',
]
for s in steps:
    add_bullet(s)

doc.add_page_break()

# ===============================================================
# 十二、商业型 vs 公益型项目测试
# ===============================================================
add_heading('十二、商业型 vs 公益型项目测试', 1)
add_hr()

add_heading('12.1 差异对比', 2)
add_table(
    ['维度', '商业型项目', '公益型项目'],
    [
        ['核心目标', '盈利 + 规模化', '社会影响 + 可持续运营'],
        ['Coach 提问重点', '单位经济、增长路径、护城河', '受益人群、社会价值、资金来源'],
        ['超图规则', 'H1 到 H15、H17 到 H20、H22', 'H1 到 H16、H21（公益可持续性风险）'],
        ['Rubric R10', '合规性权重较低', '社会责任权重显著提高'],
        ['商业计划书', '含 TAM/SAM/SOM 和财务预测', '含社会影响力指标和公益资金模型'],
        ['成功指标', '用户增长、营收、市场份额', '受益人数、社会影响指数、持续性'],
    ],
    col_widths=[4, 7, 7]
)

add_heading('12.2 切换方式', 2)
add_para('学生在创建项目时选择"商业型"或"公益型"，系统据此调整：')
add_bullet('Coach Agent 的提问策略（不同 system prompt）')
add_bullet('超图规则集（商业型 vs 公益型规则权重）')
add_bullet('Rubric 权重分配（R10 社会责任权重调整）')
add_bullet('商业计划书模板（不同章节结构）')

doc.add_page_break()

# ===============================================================
# 十三、与两份参考文档的差距分析
# ===============================================================
add_heading('十三、与两份参考文档的差距分析', 1)
add_hr()
add_para('以下基于两份课前参考文档（蓝图设计文档）对系统功能完成度进行逐条对照。')

add_heading('13.1 文档一：VentureAI 蓝图 对照表', 2)
add_table(
    ['文档要求', '系统状态', '说明'],
    [
        ['KG 节点类型（建议 9 种）', '已超越（11 种）', '额外增加 UserProfile、Evidence 节点'],
        ['关系类型（建议 7 种）', '已超越（9 种）', '额外增加 FIX_STRATEGY、EXEMPLIFIED_BY'],
        ['超图规则（建议 15 条）', '已超越（22 条）', '额外覆盖公益型、LTV/CAC、渠道错配等'],
        ['Rubric 维度（建议 9 项）', '已超越（11 项）', '额外增加 R10 合规、R11 增长规模化'],
        ['5 大智能体', '全部实现', 'Coach/Tutor/Competition/TA/Investor'],
        ['苏格拉底追问法', '三轮诊断结构', 'Discovery → Stress Test → Feasibility Check'],
        ['证据链追溯', '三层架构', '对话 → 证据 → 评分 全链路绑定'],
        ['TAM/SAM/SOM', '引导+嵌入计划书', 'Coach 引导计算并写入商业计划书'],
        ['DOCX 下载', '已实现', 'python-docx 生成格式化文档'],
    ],
    col_widths=[6, 4, 6]
)

add_heading('13.2 文档二：课程教学要求 对照表', 2)
add_table(
    ['教学要求', '系统状态', '说明'],
    [
        ['学生端项目管理', '完整实现', '创建/编辑/删除/状态追踪'],
        ['AI 对话辅导', '多智能体', '5 种角色覆盖全流程'],
        ['教师端班级管理', '完整实现', '班级画像 + 学生列表 + TA 批量评估'],
        ['管理员权限控制', '完整实现', '用户/班级/Rubric 全管理'],
        ['商业型项目测试', '完整场景', 'student01 完整演示流程'],
        ['公益型项目测试', '完整场景', 'student02 公益项目完整演示'],
        ['UI 界面美观', '深色极光主题', '玻璃拟态 + Aurora 动效 + 雷达图'],
        ['知识图谱可视化', '节点关系展示', '教师端 KG 浏览器'],
        ['导出商业计划书', 'Word+PDF', '结构化文档含所有关键章节'],
    ],
    col_widths=[6, 4, 6]
)

add_heading('13.3 尚可优化项（不影响核心验收）', 2)
add_table(
    ['优化项', '当前状态', '建议'],
    [
        ['KG 节点可视化', '教师端文字列表展示', '可升级为 D3.js 力导向图'],
        ['多轮对话历史导出', '当前会话内存储', '可增加历史对话 PDF 导出'],
        ['实时通知', '无推送通知', '可加 WebSocket 实时提醒'],
        ['移动端适配', '基本响应式', '手机端体验可进一步优化'],
    ],
    col_widths=[5, 5, 6]
)

doc.add_page_break()

# ===============================================================
# 附录 A：录屏脚本
# ===============================================================
add_heading('附录 A：录屏脚本（建议 15 到 20 分钟）', 1)
add_hr()

script_sections = [
    (
        '第一段（0:00 到 2:00）登录与角色切换',
        [
            '打开浏览器访问 http://121.14.82.109:8221',
            '展示登录页 Aurora 动效背景',
            '分别演示学生/教师/管理员角色切换效果',
            '用 student01/123456 登录，展示学生首页',
        ]
    ),
    (
        '第二段（2:00 到 6:00）学生端商业型项目',
        [
            '创建新项目"智能外卖配送优化平台"（商业型）',
            '与 Coach Agent 对话：介绍项目背景',
            'Coach 进入 Discovery 阶段追问痛点',
            '回答后进入 Stress Test 阶段',
            '触发 H5 超图警告（定价成本倒挂）',
            '查看 Rubric 评分结果（R1 到 R11 雷达图）',
            '生成并下载商业计划书（Word 格式）',
        ]
    ),
    (
        '第三段（6:00 到 9:00）学生端公益型项目',
        [
            '切换为 student02 账号登录',
            '创建"留守儿童教育平台"（公益型）',
            '展示公益型项目 Coach Agent 提问差异',
            '触发 H21（公益可持续性风险）',
            '对比商业型和公益型的 Rubric 权重差异',
        ]
    ),
    (
        '第四段（9:00 到 12:00）教师端功能',
        [
            '切换为 teacher01 账号登录',
            '展示班级项目列表和评分进度',
            '查看班级画像雷达图（R1 到 R11 平均分）',
            '点击学生查看个人画像和证据钻取',
            '使用 TA Agent 进行批量评估',
            '上传教学材料（演示文件上传）',
        ]
    ),
    (
        '第五段（12:00 到 15:00）管理员端功能',
        [
            '切换为 admin01 账号登录',
            '展示用户管理界面（创建/删除用户）',
            '展示班级管理（创建新班级）',
            '展示 Rubric 权重配置页面',
            '展示系统统计数据看板',
        ]
    ),
    (
        '第六段（15:00 到 18:00）知识图谱与超图',
        [
            '展示 KG Schema（11 种节点 + 9 种关系）',
            '演示 Tutor Agent 引用 KG 回答概念问题',
            '展示超图规则列表（H1 到 H22）',
            '演示超图检查触发和修复建议',
        ]
    ),
]

for title, points in script_sections:
    add_heading(title, 2)
    for pt in points:
        add_bullet(pt)

doc.add_page_break()

# ===============================================================
# 附录 B：系统环境信息
# ===============================================================
add_heading('附录 B：系统环境信息', 1)
add_hr()
add_table(
    ['环境项', '配置'],
    [
        ['服务器地址', 'http://121.14.82.109:8221'],
        ['前端框架', 'Next.js 14.x + TypeScript 5.x'],
        ['后端框架', 'Python FastAPI 0.104+'],
        ['数据库', 'SQLite（开发/演示），可扩展至 PostgreSQL'],
        ['AI 模型', 'claude-sonnet-4-5（主力），claude-haiku-4-5（快速响应）'],
        ['文档生成', 'python-docx 1.1+'],
        ['部署方式', 'Docker Compose（前端 + 后端 + Nginx 反向代理）'],
        ['操作系统', 'Linux（服务器）'],
    ],
    col_widths=[6, 10]
)

# ── 保存 ──────────────────────────────────────────────────────
output_path = r'c:/Users/User/venture-ai/VentureAI验收文档.docx'
doc.save(output_path)
print('文档已生成：' + output_path)
