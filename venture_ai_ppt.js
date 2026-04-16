const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "VentureAI 创新创业教学智能体";

// ─── 颜色体系 ───────────────────────────────────────────────
const C = {
  dark:    "0D1B2A",   // 深海军蓝（主背景）
  dark2:   "112233",   // 略浅版背景
  panel:   "162A42",   // 卡片背景
  panel2:  "1A3050",   // 卡片次深
  accent:  "00C8A0",   // 青绿色主强调
  accent2: "1AD4B0",   // 青绿亮版
  blue:    "3A86FF",   // 蓝色
  purple:  "7B5EA7",   // 紫色
  orange:  "FF9E3D",   // 橙色
  red:     "FF5C5C",   // 红色
  white:   "FFFFFF",
  offwhite:"E8EDF2",
  muted:   "7A9BB8",
  gold:    "F5C518",
};

function makeShadow() {
  return { type: "outer", blur: 10, offset: 3, angle: 135, color: "000000", opacity: 0.25 };
}

// ─── 通用：深色背景 ──────────────────────────────────────────
function darkBg(slide) {
  slide.background = { color: C.dark };
  // 顶部细彩条
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: C.accent }, line: { color: C.accent }
  });
}

// ─── 通用：页脚 ──────────────────────────────────────────────
function addFooter(slide, label) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.42, w: 10, h: 0.21,
    fill: { color: C.panel2 }, line: { color: C.panel2 }
  });
  slide.addText(`VentureAI  ·  ${label}`, {
    x: 0.35, y: 5.42, w: 9.3, h: 0.21,
    fontSize: 8, color: C.muted, valign: "middle", margin: 0
  });
}

// ─── 通用：节标题标签 ────────────────────────────────────────
function sectionTag(slide, label, bgColor) {
  const color = bgColor || C.accent;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 0.28, w: 1.5, h: 0.28,
    fill: { color }, line: { color }
  });
  slide.addText(label, {
    x: 0.5, y: 0.28, w: 1.5, h: 0.28,
    fontSize: 9, bold: true, color: C.dark, align: "center", valign: "middle", margin: 0
  });
}

// ─── 通用：大标题 ────────────────────────────────────────────
function mainTitle(slide, text, sub, y) {
  const ty = y !== undefined ? y : 0.68;
  slide.addText(text, {
    x: 0.5, y: ty, w: 9, h: 0.62,
    fontSize: 26, bold: true, color: C.white, fontFace: "Arial Black", margin: 0
  });
  if (sub) {
    slide.addText(sub, {
      x: 0.5, y: ty + 0.65, w: 9, h: 0.3,
      fontSize: 12, color: C.muted, italic: true, margin: 0
    });
  }
}

// ─── SLIDE 1：封面 ───────────────────────────────────────────
(function () {
  const s = pres.addSlide();
  s.background = { color: C.dark };

  // 装饰色块
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 3.8, h: 5.625,
    fill: { color: C.panel }, line: { color: C.panel }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.accent }, line: { color: C.accent }
  });

  // 标题
  s.addText("VentureAI", {
    x: 0.2, y: 1.0, w: 3.5, h: 1.1,
    fontSize: 38, bold: true, color: C.accent, fontFace: "Arial Black", margin: 0
  });
  s.addText("创新创业教学智能体", {
    x: 0.35, y: 2.15, w: 3.3, h: 0.5,
    fontSize: 16, bold: true, color: C.white, margin: 0
  });
  s.addText("基于知识图谱与超图的双创 AI 教育平台", {
    x: 0.35, y: 2.72, w: 3.3, h: 0.35,
    fontSize: 10, color: C.muted, italic: true, margin: 0
  });

  // 右侧功能一览（8个模块列）
  const items = [
    "01  完整场景演示",
    "02  全量 Prompt 体系",
    "03  知识图谱 & 评估",
    "04  超图 & 评估",
    "05  引用正确性验证",
    "06  用户·角色·权限",
    "07  界面美观与易用性",
    "08  个人画像 & 班级画像",
  ];
  items.forEach((txt, i) => {
    const y = 0.55 + i * 0.6;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 4.3, y, w: 5.3, h: 0.46,
      fill: { color: C.panel, transparency: 20 }, line: { color: C.panel }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 4.3, y, w: 0.07, h: 0.46,
      fill: { color: C.accent }, line: { color: C.accent }
    });
    s.addText(txt, {
      x: 4.45, y: y + 0.04, w: 5.1, h: 0.38,
      fontSize: 11, color: C.offwhite, valign: "middle", margin: 0
    });
  });

  s.addText("大数据特色课程  ·  2026", {
    x: 0.35, y: 5.1, w: 3.3, h: 0.25,
    fontSize: 8, color: C.muted, margin: 0
  });
})();

// ─── SLIDE 2：完整场景演示 ────────────────────────────────────
(function () {
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "01  完整场景");
  mainTitle(s, "一个完整的教学场景", "从学生入学到拿到竞赛评分的全链路体验");
  addFooter(s, "完整场景演示");

  // 流程步骤：横向5步
  const steps = [
    { icon: "①", title: "登录系统", desc: "学生/教师\n双端入口", color: C.blue },
    { icon: "②", title: "创建项目", desc: "填写创业想法\n选择行业领域", color: C.purple },
    { icon: "③", title: "AI教练对话", desc: "苏格拉底式\n三轮诊断法", color: C.accent },
    { icon: "④", title: "实时评分", desc: "五维雷达图\n隐性评分解析", color: C.orange },
    { icon: "⑤", title: "竞赛顾问", desc: "9项Rubric\n修复建议输出", color: C.red },
  ];
  steps.forEach((st, i) => {
    const x = 0.3 + i * 1.88;
    // 卡片
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.6, w: 1.7, h: 2.1,
      fill: { color: C.panel }, line: { color: C.panel },
      shadow: makeShadow()
    });
    // 顶部色条
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.6, w: 1.7, h: 0.1,
      fill: { color: st.color }, line: { color: st.color }
    });
    // 图标
    s.addText(st.icon, {
      x: x + 0.5, y: 1.75, w: 0.7, h: 0.5,
      fontSize: 24, bold: true, color: st.color, align: "center", margin: 0
    });
    // 标题
    s.addText(st.title, {
      x, y: 2.35, w: 1.7, h: 0.35,
      fontSize: 12, bold: true, color: C.white, align: "center", margin: 0
    });
    // 描述
    s.addText(st.desc, {
      x, y: 2.75, w: 1.7, h: 0.7,
      fontSize: 9.5, color: C.muted, align: "center", margin: 0
    });
    // 箭头（非最后一步）
    if (i < 4) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: x + 1.71, y: 2.6, w: 0.17, h: 0.04,
        fill: { color: C.accent }, line: { color: C.accent }
      });
    }
  });

  // 底部数据流说明
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 3.85, w: 9.4, h: 0.7,
    fill: { color: C.panel2 }, line: { color: C.panel2 }
  });
  s.addText("数据流：学生对话 → AI隐性评分（JSON嵌入）→ 后端解析 → 雷达图更新 → 汇总至教师Mission Control看板", {
    x: 0.5, y: 3.9, w: 9.0, h: 0.55,
    fontSize: 10.5, color: C.offwhite, valign: "middle", margin: 0
  });

  // 左右端标签
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 4.65, w: 4.5, h: 0.38,
    fill: { color: C.blue, transparency: 70 }, line: { color: C.blue, transparency: 50 }
  });
  s.addText("学生端  ·  Coach / Tutor / Competition / Project", {
    x: 0.4, y: 4.65, w: 4.3, h: 0.38,
    fontSize: 9.5, color: C.blue, valign: "middle", margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 4.65, w: 4.5, h: 0.38,
    fill: { color: C.accent, transparency: 70 }, line: { color: C.accent, transparency: 50 }
  });
  s.addText("教师端  ·  Mission Control / Rubric 审阅", {
    x: 5.3, y: 4.65, w: 4.3, h: 0.38,
    fontSize: 9.5, color: C.accent, valign: "middle", margin: 0
  });
})();

// ─── SLIDE 3：所有 Prompt ─────────────────────────────────────
(function () {
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "02  Prompt 体系", C.blue);
  mainTitle(s, "系统全量 Prompt 架构", "四类 Agent 各司其职，约束清晰、风格分明");
  addFooter(s, "Prompt 体系");

  const agents = [
    {
      name: "Coach Agent\n项目教练",
      color: C.accent,
      points: ["苏格拉底式追问，不直接给答案", "三轮诊断：Discovery→Stress Test→Feasibility", "结尾嵌入隐性评分 JSON 标记", "VC视角·冷幽默·引导性强"],
    },
    {
      name: "Tutor Agent\n学习辅导",
      color: C.blue,
      points: ["6步标准回答：定义→案例→错误→任务→产出→评标", "耐心温和，用类比讲抽象概念", "每次只聚焦一个概念讲透", "覆盖 PMF/AARRR/Canvas 等 20+ 概念"],
    },
    {
      name: "Competition Agent\n竞赛顾问",
      color: C.orange,
      points: ["对标互联网+/挑战杯等赛事评委视角", "9项Rubric逐项打分", "输出缺失证据清单", "24h/72h 分级修复方案"],
    },
    {
      name: "Teacher Agent\n教师智能体",
      color: C.purple,
      points: ["汇总全班对话生成教学建议", "识别班级共性错误Top 5", "高风险项目自动预警", "生成干预建议可直接在课堂执行"],
    },
  ];

  agents.forEach((ag, i) => {
    const x = 0.3 + i * 2.38;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.55, w: 2.18, h: 3.1,
      fill: { color: C.panel }, line: { color: C.panel },
      shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.55, w: 2.18, h: 0.08,
      fill: { color: ag.color }, line: { color: ag.color }
    });
    s.addText(ag.name, {
      x, y: 1.68, w: 2.18, h: 0.7,
      fontSize: 11, bold: true, color: ag.color, align: "center", margin: 0
    });
    // 分割线
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.2, y: 2.42, w: 1.78, h: 0.03,
      fill: { color: ag.color, transparency: 50 }, line: { color: ag.color, transparency: 50 }
    });
    // 要点
    ag.points.forEach((pt, j) => {
      s.addText("▸  " + pt, {
        x: x + 0.12, y: 2.52 + j * 0.5, w: 2.0, h: 0.45,
        fontSize: 9, color: C.offwhite, valign: "top", margin: 0
      });
    });
  });

  // 底部约束提示
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 4.78, w: 9.4, h: 0.38,
    fill: { color: C.panel2 }, line: { color: C.panel2 }
  });
  s.addText("硬性约束：严禁代写商业计划书  ·  每次回复只聚焦1-2个核心问题  ·  引用2025-2026行业趋势背景", {
    x: 0.5, y: 4.78, w: 9.0, h: 0.38,
    fontSize: 9, color: C.muted, valign: "middle", align: "center", margin: 0
  });
})();

// ─── SLIDE 4：知识图谱 ────────────────────────────────────────
(function () {
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "03  知识图谱", C.purple);
  mainTitle(s, "知识图谱 Schema & 评估机制", "结构化创业知识，支撑 AI 推理与证据追溯");
  addFooter(s, "知识图谱 & 评估");

  // 左侧：节点类型表
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 1.55, w: 3.5, h: 3.4,
    fill: { color: C.panel }, line: { color: C.panel }, shadow: makeShadow()
  });
  s.addText("节点类型  (6 种)", {
    x: 0.4, y: 1.62, w: 3.3, h: 0.34,
    fontSize: 11, bold: true, color: C.purple, margin: 0
  });

  const nodeTypes = [
    { type: "Concept", ex: "PMF / TAM / Moat", color: C.accent },
    { type: "Method",  ex: "Lean Canvas / AARRR", color: C.blue },
    { type: "Task",    ex: "用户访谈 / MVP设计", color: C.orange },
    { type: "Artifact",ex: "商业计划书 / 路演PPT", color: C.purple },
    { type: "Metric",  ex: "CAC / LTV / 转化率", color: C.gold },
    { type: "Case",    ex: "获奖项目 / 失败案例", color: C.red },
  ];
  nodeTypes.forEach((nt, i) => {
    const y = 2.05 + i * 0.47;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y, w: 0.85, h: 0.3,
      fill: { color: nt.color, transparency: 20 }, line: { color: nt.color }
    });
    s.addText(nt.type, {
      x: 0.4, y, w: 0.85, h: 0.3,
      fontSize: 9, bold: true, color: nt.color, align: "center", valign: "middle", margin: 0
    });
    s.addText(nt.ex, {
      x: 1.32, y: y + 0.02, w: 2.35, h: 0.28,
      fontSize: 9, color: C.offwhite, valign: "middle", margin: 0
    });
  });

  // 中间：关系类型
  s.addShape(pres.shapes.RECTANGLE, {
    x: 4.05, y: 1.55, w: 2.8, h: 3.4,
    fill: { color: C.panel }, line: { color: C.panel }, shadow: makeShadow()
  });
  s.addText("关系类型  (7 种)", {
    x: 4.15, y: 1.62, w: 2.6, h: 0.34,
    fontSize: 11, bold: true, color: C.blue, margin: 0
  });
  const rels = [
    "PREREQ       前置依赖",
    "USES            使用方法",
    "PRODUCES   产出关系",
    "MEASURED_BY  度量关系",
    "EVIDENCED_BY  证据支撑",
    "COMMON_MISTAKE  常见错误",
    "FIX_STRATEGY    修复策略",
  ];
  rels.forEach((r, i) => {
    s.addText("→  " + r, {
      x: 4.18, y: 2.08 + i * 0.42, w: 2.55, h: 0.36,
      fontSize: 9, color: C.offwhite, margin: 0
    });
  });

  // 右侧：评估说明
  s.addShape(pres.shapes.RECTANGLE, {
    x: 7.05, y: 1.55, w: 2.65, h: 3.4,
    fill: { color: C.panel }, line: { color: C.panel }, shadow: makeShadow()
  });
  s.addText("评估作用", {
    x: 7.15, y: 1.62, w: 2.45, h: 0.34,
    fontSize: 11, bold: true, color: C.accent, margin: 0
  });

  const evalPts = [
    { h: "知识组织", d: "PMF、AARRR等双创核心概念结构化入库", color: C.accent },
    { h: "前置推理", d: "PREREQ链保证教学顺序合理", color: C.blue },
    { h: "证据追溯", d: "EVIDENCED_BY确保每条评分有来源", color: C.orange },
    { h: "错误诊断", d: "COMMON_MISTAKE自动匹配已知陷阱", color: C.red },
    { h: "可复用性", d: "历届案例结构化入库，支持迁移推理", color: C.purple },
  ];
  evalPts.forEach((ep, i) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: 7.1, y: 2.08 + i * 0.6, w: 0.07, h: 0.38,
      fill: { color: ep.color }, line: { color: ep.color }
    });
    s.addText(ep.h, {
      x: 7.24, y: 2.08 + i * 0.6, w: 2.35, h: 0.22,
      fontSize: 9.5, bold: true, color: ep.color, margin: 0
    });
    s.addText(ep.d, {
      x: 7.24, y: 2.27 + i * 0.6, w: 2.35, h: 0.22,
      fontSize: 8.5, color: C.muted, margin: 0
    });
  });
})();

// ─── SLIDE 5：超图 ────────────────────────────────────────────
(function () {
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "04  超图约束", C.orange);
  mainTitle(s, "15 条超图约束规则 & 评估", "自动检测逻辑不一致，给出分级修复任务");
  addFooter(s, "超图 & 评估");

  // 高危（4条）
  const highRules = [
    { id: "H1", name: "客户–价值主张错位", trigger: "客户群体与价值主张不匹配" },
    { id: "H2", name: "渠道不可达", trigger: "选定渠道无法触达目标客户" },
    { id: "H5", name: "需求证据不足", trigger: "用户痛点缺乏一手数据支撑" },
    { id: "H8", name: "单位经济不成立", trigger: "LTV < CAC 或假设不合理" },
    { id: "H11", name: "合规/伦理缺口", trigger: "数据隐私/行业准入等合规风险" },
    { id: "H12", name: "技术路线与资源不匹配", trigger: "技术方案超出团队能力和资源" },
  ];
  const midRules = [
    { id: "H3", name: "定价无支付意愿证据", trigger: "缺乏支付意愿验证数据" },
    { id: "H4", name: "TAM/SAM/SOM 口径混乱", trigger: "市场规模计算逻辑不一致" },
    { id: "H6", name: "竞品对比不可比", trigger: "竞品维度不对等或遗漏" },
    { id: "H7", name: "创新点不可验证", trigger: "创新点缺乏数据或实验支撑" },
    { id: "H9", name: "增长逻辑跳跃", trigger: "用户增长策略缺阶段逻辑" },
    { id: "H10", name: "里程碑不可交付", trigger: "里程碑过于模糊不可量化" },
    { id: "H13", name: "实验设计不合格", trigger: "缺乏对照组或样本量不足" },
    { id: "H15", name: "评分证据覆盖不足", trigger: "多个评分维度缺乏支撑证据" },
  ];

  // 左列：高危规则
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 1.55, w: 0.7, h: 0.28,
    fill: { color: C.red, transparency: 30 }, line: { color: C.red }
  });
  s.addText("高危  ×6", {
    x: 0.3, y: 1.55, w: 0.7, h: 0.28,
    fontSize: 8.5, bold: true, color: C.red, align: "center", valign: "middle", margin: 0
  });

  highRules.forEach((r, i) => {
    const y = 1.92 + i * 0.54;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.3, y, w: 4.5, h: 0.44,
      fill: { color: C.panel }, line: { color: C.red, transparency: 60 }
    });
    s.addText(r.id, {
      x: 0.35, y: y + 0.04, w: 0.4, h: 0.36,
      fontSize: 9, bold: true, color: C.red, valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.78, y: y + 0.08, w: 0.03, h: 0.28,
      fill: { color: C.red, transparency: 40 }, line: { color: C.red, transparency: 40 }
    });
    s.addText(r.name, {
      x: 0.88, y: y + 0.02, w: 2.3, h: 0.22,
      fontSize: 9.5, bold: true, color: C.offwhite, margin: 0
    });
    s.addText(r.trigger, {
      x: 0.88, y: y + 0.22, w: 3.8, h: 0.2,
      fontSize: 8, color: C.muted, margin: 0
    });
  });

  // 右列：中等规则（2列布局）
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.0, y: 1.55, w: 0.75, h: 0.28,
    fill: { color: C.orange, transparency: 30 }, line: { color: C.orange }
  });
  s.addText("中等  ×8", {
    x: 5.0, y: 1.55, w: 0.75, h: 0.28,
    fontSize: 8.5, bold: true, color: C.orange, align: "center", valign: "middle", margin: 0
  });

  midRules.forEach((r, i) => {
    const col = i < 4 ? 0 : 1;
    const row = i % 4;
    const x = 5.0 + col * 2.45;
    const y = 1.92 + row * 0.81;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 2.3, h: 0.7,
      fill: { color: C.panel }, line: { color: C.orange, transparency: 65 }
    });
    s.addText(r.id, {
      x: x + 0.07, y: y + 0.04, w: 0.38, h: 0.28,
      fontSize: 9.5, bold: true, color: C.orange, margin: 0
    });
    s.addText(r.name, {
      x: x + 0.07, y: y + 0.3, w: 2.15, h: 0.22,
      fontSize: 8, color: C.offwhite, margin: 0
    });
    s.addText(r.trigger, {
      x: x + 0.07, y: y + 0.48, w: 2.15, h: 0.18,
      fontSize: 7, color: C.muted, margin: 0
    });
  });

  // H14 低危
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.0, y: 5.08, w: 4.75, h: 0.28,
    fill: { color: C.panel2 }, line: { color: C.muted, transparency: 60 }
  });
  s.addText("H14（低）路演叙事断裂  ·  路演材料故事线不连贯  →  按 问题→方案→市场→模式→团队 重构叙事", {
    x: 5.1, y: 5.08, w: 4.6, h: 0.28,
    fontSize: 7.5, color: C.muted, valign: "middle", margin: 0
  });
})();

// ─── SLIDE 6：引用正确性 ───────────────────────────────────────
(function () {
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "05  引用正确性", C.gold);
  mainTitle(s, "知识图谱与超图的引用正确性验证", "每条评分有证据链，评价不是 AI 拍脑袋");
  addFooter(s, "引用正确性验证");

  // 流程图（竖向三阶段）
  const stages = [
    {
      title: "① 评分触发阶段",
      color: C.blue,
      items: ["AI Coach / Competition Agent 输出对话", "结尾嵌入 <!--SCORES:{...}--> 隐性标记", "后端正则提取 → 解析 JSON"],
    },
    {
      title: "② 知识图谱查询阶段",
      color: C.accent,
      items: ["根据评分维度检索对应 Concept/Task 节点", "验证 PREREQ 链：前置任务是否已完成", "触发 COMMON_MISTAKE 自动匹配已知错误模式"],
    },
    {
      title: "③ 超图规则检验阶段",
      color: C.orange,
      items: ["逐条扫描 H1–H15 约束规则", "触发规则记录 Evidence Trace（引用来源）", "证据不足时标注 ⚠️ 不得凭感觉给高分"],
    },
  ];

  stages.forEach((st, i) => {
    const y = 1.55 + i * 1.22;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.3, y, w: 5.8, h: 1.05,
      fill: { color: C.panel }, line: { color: C.panel }, shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.3, y, w: 0.08, h: 1.05,
      fill: { color: st.color }, line: { color: st.color }
    });
    s.addText(st.title, {
      x: 0.52, y: y + 0.06, w: 5.5, h: 0.28,
      fontSize: 11, bold: true, color: st.color, margin: 0
    });
    st.items.forEach((item, j) => {
      s.addText("▸  " + item, {
        x: 0.52, y: y + 0.36 + j * 0.23, w: 5.5, h: 0.22,
        fontSize: 9, color: C.offwhite, margin: 0
      });
    });
    // 箭头
    if (i < 2) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.9, y: y + 1.05, w: 0.03, h: 0.12,
        fill: { color: st.color }, line: { color: st.color }
      });
    }
  });

  // 右侧：Evidence Trace 示例卡片
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.4, y: 1.55, w: 3.3, h: 3.7,
    fill: { color: C.panel }, line: { color: C.panel }, shadow: makeShadow()
  });
  s.addText("Evidence Trace 示例", {
    x: 6.5, y: 1.62, w: 3.1, h: 0.3,
    fontSize: 10.5, bold: true, color: C.gold, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.5, y: 1.95, w: 3.1, h: 0.03,
    fill: { color: C.gold, transparency: 60 }, line: { color: C.gold, transparency: 60 }
  });

  const evRows = [
    { rubric: "R1 痛点定义", src: "项目描述", quote: "针对大学生的二手课本需求" },
    { rubric: "R2 用户证据", src: "⚠️ 缺失", quote: "无用户访谈记录 → 3/10" },
    { rubric: "R3 方案可行性", src: "方案说明", quote: "基于AI的推荐算法匹配买卖双方" },
    { rubric: "H8 单位经济", src: "财务数据", quote: "LTV=$12 < CAC=$18 → 触发规则" },
    { rubric: "R5 市场竞争", src: "市场分析", quote: "TAM来源不明 → 触发H4" },
  ];
  evRows.forEach((ev, i) => {
    const y = 2.07 + i * 0.63;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 6.5, y, w: 3.1, h: 0.52,
      fill: { color: C.dark2 }, line: { color: C.panel2 }
    });
    s.addText(ev.rubric, {
      x: 6.58, y: y + 0.04, w: 1.3, h: 0.2,
      fontSize: 8.5, bold: true, color: C.gold, margin: 0
    });
    s.addText(ev.src, {
      x: 7.9, y: y + 0.04, w: 1.55, h: 0.2,
      fontSize: 8, color: C.muted, align: "right", margin: 0
    });
    s.addText("\"" + ev.quote + "\"", {
      x: 6.58, y: y + 0.27, w: 3.0, h: 0.2,
      fontSize: 8, color: C.offwhite, italic: true, margin: 0
    });
  });

  // 底部原则
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 5.05, w: 9.4, h: 0.28,
    fill: { color: C.panel2 }, line: { color: C.panel2 }
  });
  s.addText("原则：证据不足时明确标注  ·  不说[还不错]  ·  每条批评都伴随具体修复建议", {
    x: 0.5, y: 5.05, w: 9.0, h: 0.28,
    fontSize: 9, color: C.muted, valign: "middle", align: "center", margin: 0
  });
})();

// ─── SLIDE 7：用户角色权限 ────────────────────────────────────
(function () {
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "06  用户·角色·权限", C.purple);
  mainTitle(s, "用户、角色与权限管理", "双端架构，职能清晰，入口隔离");
  addFooter(s, "用户·角色·权限管理");

  // 两列：学生端 + 教师端
  const roles = [
    {
      title: "学生角色",
      subtitle: "Student",
      color: C.blue,
      icon: "🎓",
      features: [
        "登录入口：学生端独立入口",
        "AI 项目教练（Coach Agent）",
        "学习辅导（Tutor Agent）",
        "竞赛顾问（Competition Agent）",
        "个人项目管理（4个阶段追踪）",
        "查看自己的五维评分雷达图",
        "诊断问题列表（自查修复）",
      ],
      locked: [
        "❌ 不可见其他学生评分",
        "❌ 不可访问班级控制面板",
        "❌ 不可修改评分数据",
      ]
    },
    {
      title: "教师角色",
      subtitle: "Teacher",
      color: C.accent,
      icon: "📊",
      features: [
        "登录入口：教师端独立入口",
        "Mission Control 全班控制面板",
        "班级整体雷达图 & 共性错误Top5",
        "高风险项目预警（实时）",
        "Rubric 精细化项目审阅",
        "证据链追溯（Evidence Trace）",
        "AI 自动生成教学干预建议",
      ],
      locked: [
        "✅ 可查看所有学生项目",
        "✅ 查看对话评分数据汇总",
        "✅ 获取AI生成的课程优化建议",
      ]
    }
  ];

  roles.forEach((role, col) => {
    const x = 0.3 + col * 4.8;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.55, w: 4.55, h: 3.6,
      fill: { color: C.panel }, line: { color: C.panel }, shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.55, w: 4.55, h: 0.55,
      fill: { color: role.color, transparency: 20 }, line: { color: role.color, transparency: 20 }
    });
    s.addText(role.title, {
      x: x + 0.2, y: 1.62, w: 2.5, h: 0.38,
      fontSize: 13, bold: true, color: role.color, margin: 0
    });
    s.addText(role.subtitle, {
      x: x + 2.8, y: 1.68, w: 1.5, h: 0.3,
      fontSize: 10, color: C.muted, align: "right", margin: 0
    });

    role.features.forEach((f, i) => {
      s.addShape(pres.shapes.RECTANGLE, {
        x: x + 0.18, y: 2.18 + i * 0.36, w: 0.06, h: 0.22,
        fill: { color: role.color }, line: { color: role.color }
      });
      s.addText(f, {
        x: x + 0.32, y: 2.18 + i * 0.36, w: 4.1, h: 0.3,
        fontSize: 9.5, color: C.offwhite, valign: "middle", margin: 0
      });
    });

    // 权限标注
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.15, y: 4.58, w: 4.25, h: 0.06,
      fill: { color: role.color, transparency: 60 }, line: { color: role.color, transparency: 60 }
    });
    role.locked.forEach((l, i) => {
      s.addText(l, {
        x: x + 0.18, y: 4.68 + i * 0.22, w: 4.2, h: 0.2,
        fontSize: 8.5, color: i === 0 && col === 0 ? C.red : C.muted, margin: 0
      });
    });
  });

  // 认证接口提示
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 5.18, w: 9.4, h: 0.28,
    fill: { color: C.panel2 }, line: { color: C.panel2 }
  });
  s.addText("认证接口：POST /api/auth/login  ·  角色区分后跳转对应端  ·  会话数据内存存储（可扩展 Redis / PostgreSQL）", {
    x: 0.5, y: 5.18, w: 9.0, h: 0.28,
    fontSize: 8.5, color: C.muted, valign: "middle", align: "center", margin: 0
  });
})();

// ─── SLIDE 8：界面美观易用性 ──────────────────────────────────
(function () {
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "07  界面设计", C.accent);
  mainTitle(s, "界面的美观性与易用性", "Next.js 14 + Tailwind CSS · 响应式双端 Web 应用");
  addFooter(s, "界面美观与易用性");

  // 4个设计亮点卡片（2x2）
  const cards = [
    {
      title: "双端分离架构",
      color: C.blue,
      num: "2",
      unit: "独立端口",
      desc: "学生端与教师端完全独立界面，职能清晰互不干扰",
    },
    {
      title: "实时五维雷达图",
      color: C.accent,
      num: "5",
      unit: "维度实时更新",
      desc: "SVG 绘制雷达图，每次对话后自动刷新可视化评分",
    },
    {
      title: "颜色编码系统",
      color: C.orange,
      num: "3",
      unit: "色阶警示",
      desc: "绿(≥7)·黄(5-6)·红(<5) 直觉化评分状态呈现",
    },
    {
      title: "一屏掌握全班",
      color: C.purple,
      num: "5",
      unit: "Mission Control板块",
      desc: "概览数字+雷达图+共性错误+预警+教学建议一页呈现",
    },
  ];

  cards.forEach((c, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.3 + col * 4.8;
    const y = 1.65 + row * 1.95;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 4.55, h: 1.72,
      fill: { color: C.panel }, line: { color: C.panel }, shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 4.55, h: 0.08,
      fill: { color: c.color }, line: { color: c.color }
    });

    // 大数字
    s.addText(c.num, {
      x: x + 0.18, y: y + 0.15, w: 0.8, h: 0.8,
      fontSize: 40, bold: true, color: c.color, fontFace: "Arial Black", margin: 0
    });
    s.addText(c.unit, {
      x: x + 0.18, y: y + 0.98, w: 1.0, h: 0.24,
      fontSize: 8, color: c.color, margin: 0
    });

    // 分割线
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 1.22, y: y + 0.2, w: 0.04, h: 1.1,
      fill: { color: c.color, transparency: 50 }, line: { color: c.color, transparency: 50 }
    });

    s.addText(c.title, {
      x: x + 1.38, y: y + 0.2, w: 3.0, h: 0.3,
      fontSize: 12, bold: true, color: c.color, margin: 0
    });
    s.addText(c.desc, {
      x: x + 1.38, y: y + 0.56, w: 3.0, h: 0.8,
      fontSize: 9.5, color: C.offwhite, margin: 0
    });
  });

  // 底部技术标签
  const techTags = ["Next.js 14", "TypeScript", "Tailwind CSS", "SVG 雷达图", "RESTful API", "响应式设计"];
  techTags.forEach((tag, i) => {
    const x = 0.3 + i * 1.58;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 5.1, w: 1.45, h: 0.28,
      fill: { color: C.panel2 }, line: { color: C.accent, transparency: 50 }
    });
    s.addText(tag, {
      x, y: 5.1, w: 1.45, h: 0.28,
      fontSize: 8.5, color: C.accent, align: "center", valign: "middle", margin: 0
    });
  });
})();

// ─── SLIDE 9：个人画像 & 班级画像 ────────────────────────────
(function () {
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "08  画像系统", C.gold);
  mainTitle(s, "个人画像 & 班级画像", "从个体到群体，AI驱动的学情分析闭环");
  addFooter(s, "个人画像 & 班级画像");

  // 左侧：个人画像
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 1.55, w: 4.5, h: 3.65,
    fill: { color: C.panel }, line: { color: C.panel }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 1.55, w: 4.5, h: 0.08,
    fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText("👤  个人画像", {
    x: 0.42, y: 1.68, w: 4.2, h: 0.36,
    fontSize: 13, bold: true, color: C.gold, margin: 0
  });

  const personalItems = [
    { label: "五维能力雷达图", desc: "痛点发现·方案策划·商业建模·资源杠杆·路演表达", color: C.accent },
    { label: "项目阶段追踪", desc: "Discovery→Ideation→Modeling→Execution→Pitching", color: C.blue },
    { label: "AI诊断问题列表", desc: "实时更新待解决的逻辑漏洞与知识盲区", color: C.orange },
    { label: "对话历史记录", desc: "完整保存每次与 AI Agent 的对话内容", color: C.purple },
    { label: "竞赛 Rubric 评分", desc: "R1-R9 详细评分 + 证据链 + 修复建议", color: C.red },
  ];
  personalItems.forEach((item, i) => {
    const y = 2.15 + i * 0.62;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.42, y, w: 0.1, h: 0.38,
      fill: { color: item.color }, line: { color: item.color }
    });
    s.addText(item.label, {
      x: 0.6, y: y + 0.01, w: 4.05, h: 0.22,
      fontSize: 10, bold: true, color: item.color, margin: 0
    });
    s.addText(item.desc, {
      x: 0.6, y: y + 0.22, w: 4.05, h: 0.2,
      fontSize: 8.5, color: C.muted, margin: 0
    });
  });

  // 右侧：班级画像
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.55, w: 4.5, h: 3.65,
    fill: { color: C.panel }, line: { color: C.panel }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.55, w: 4.5, h: 0.08,
    fill: { color: C.accent }, line: { color: C.accent }
  });
  s.addText("📊  班级画像", {
    x: 5.32, y: 1.68, w: 4.2, h: 0.36,
    fontSize: 13, bold: true, color: C.accent, margin: 0
  });

  const classItems = [
    { label: "学生总数 / 项目总数 / 高风险数", desc: "三个核心指标大数字卡片，一屏概览班级动态", color: C.accent },
    { label: "班级平均五维雷达图", desc: "全班评分均值可视化，定位整体薄弱环节", color: C.blue },
    { label: "Top 5 共性错误榜", desc: "自动统计频率，优先级标色（红>黄>灰）", color: C.orange },
    { label: "高风险项目预警列表", desc: "自动识别低分/逻辑缺陷项目，标注风险原因", color: C.red },
    { label: "AI 教学干预建议", desc: "基于班级数据自动生成，下一节课可直接落地", color: C.purple },
  ];
  classItems.forEach((item, i) => {
    const y = 2.15 + i * 0.62;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.32, y, w: 0.1, h: 0.38,
      fill: { color: item.color }, line: { color: item.color }
    });
    s.addText(item.label, {
      x: 5.5, y: y + 0.01, w: 4.05, h: 0.22,
      fontSize: 10, bold: true, color: item.color, margin: 0
    });
    s.addText(item.desc, {
      x: 5.5, y: y + 0.22, w: 4.05, h: 0.2,
      fontSize: 8.5, color: C.muted, margin: 0
    });
  });

  // 底部：双向箭头说明
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 5.28, w: 9.4, h: 0.28,
    fill: { color: C.panel2 }, line: { color: C.panel2 }
  });
  s.addText("数据流：学生对话 → 个人评分更新 → 汇总至班级画像 → 教师获得全局洞察 → 生成干预建议反哺教学", {
    x: 0.5, y: 5.28, w: 9.0, h: 0.28,
    fontSize: 8.5, color: C.offwhite, valign: "middle", align: "center", margin: 0
  });
})();

// ─── SLIDE 10：总结页 ─────────────────────────────────────────
(function () {
  const s = pres.addSlide();
  s.background = { color: C.dark };

  // 左侧装饰
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 3.5, h: 5.625,
    fill: { color: C.panel }, line: { color: C.panel }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.accent }, line: { color: C.accent }
  });

  s.addText("VentureAI", {
    x: 0.3, y: 0.6, w: 3.1, h: 0.7,
    fontSize: 30, bold: true, color: C.accent, fontFace: "Arial Black", margin: 0
  });
  s.addText("创新创业教学智能体", {
    x: 0.3, y: 1.38, w: 3.1, h: 0.4,
    fontSize: 14, bold: true, color: C.white, margin: 0
  });
  s.addText("八大核心能力，已就绪", {
    x: 0.3, y: 1.85, w: 3.1, h: 0.3,
    fontSize: 10, color: C.muted, italic: true, margin: 0
  });

  const summaryItems = [
    { num: "01", txt: "完整场景演示", color: C.blue },
    { num: "02", txt: "全量 Prompt 体系", color: C.accent },
    { num: "03", txt: "知识图谱 & 评估", color: C.purple },
    { num: "04", txt: "超图约束 & 评估", color: C.orange },
    { num: "05", txt: "引用正确性验证", color: C.gold },
    { num: "06", txt: "用户·角色·权限", color: C.red },
    { num: "07", txt: "界面美观易用性", color: C.blue },
    { num: "08", txt: "个人·班级画像", color: C.accent },
  ];
  summaryItems.forEach((item, i) => {
    const col = Math.floor(i / 4);
    const row = i % 4;
    const x = 3.85 + col * 3.05;
    const y = 1.0 + row * 1.1;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 2.8, h: 0.88,
      fill: { color: C.panel }, line: { color: C.panel }, shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.08, h: 0.88,
      fill: { color: item.color }, line: { color: item.color }
    });
    s.addText(item.num, {
      x: x + 0.15, y: y + 0.04, w: 0.5, h: 0.4,
      fontSize: 22, bold: true, color: item.color, fontFace: "Arial Black", margin: 0
    });
    s.addText(item.txt, {
      x: x + 0.15, y: y + 0.48, w: 2.5, h: 0.28,
      fontSize: 10, color: C.offwhite, margin: 0
    });
  });

  // 底部
  s.addText("基于知识图谱与超图的双创 AI 教育平台  ·  大数据特色课程  ·  2026", {
    x: 0.3, y: 5.3, w: 9.4, h: 0.22,
    fontSize: 8, color: C.muted, align: "center", margin: 0
  });
})();

// ─── 输出 ─────────────────────────────────────────────────────
pres.writeFile({ fileName: "/Users/yaphowchien/Downloads/大数据特色课程/大数据/venture-ai/VentureAI_演示.pptx" })
  .then(() => console.log("✅ PPT 生成成功：VentureAI_演示.pptx"))
  .catch(err => console.error("❌ 生成失败：", err));
