"""
services/playbook_engine.py
────────────────────────────────────────────────────────────────
创业范式库 (Playbooks) — 从案例碎片到可复用套路

核心思路（方向4）：
把 85 个竞赛案例拆解为若干"创业范式"（Playbook），
每个范式对应：适用条件、关键假设、典型指标、常见坑、最小证据包。

范式类型（从数据聚类得出）：
  platform     — 平台型（双边市场/API平台）
  saas_sub     — SaaS订阅型
  b2b_solution — ToB解决方案（项目制→产品化）
  hardware     — 硬件+服务（设备销售+增值服务）
  gov_policy   — 政府/政策驱动（补贴+采购）
  campus       — 校园场景创业（渠道与用户密度优势）
  ai_tool      — AI工具型（技术API+SaaS）

工作流：
  1. 从超图聚类出范式（规则匹配，非 ML）
  2. 每个范式输出：说明、适用条件、关键指标、最小证据包
  3. 给学生匹配范式 → 推荐 BP 结构 + 补充证据
  4. 教练/评分时引用范式解释"为什么此维度缺 X 证据"
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

_PLAYBOOKS_PATH = Path(__file__).parent.parent / "data" / "playbooks.json"


# ── 范式定义 ──────────────────────────────────────────────────

@dataclass
class Playbook:
    playbook_id: str
    name: str                    # 范式名称
    subtitle: str                # 一句话描述
    description: str             # 详细说明（markdown）
    # 适用条件 (if-then)
    conditions: list[str]        # 满足哪些条件适用此范式
    match_keywords: list[str]    # 用于自动匹配的关键词
    match_biz_models: list[str]  # 匹配的商业模式标签
    match_industries: list[str]  # 偏好行业（空=通用）
    # 关键指标
    key_metrics: list[dict]      # [{name, formula, benchmark, why}]
    # 最小证据包
    min_evidence: list[dict]     # [{rubric, evidence, why}]
    # 常见坑
    common_pitfalls: list[str]
    # BP 模板建议
    bp_structure: list[str]      # 推荐的 BP 章节顺序
    # 案例引用
    example_projects: list[str]  # 超图中属于此范式的项目名
    # 元数据
    project_count: int = 0       # 聚类后属于此范式的项目数

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Playbook":
        return Playbook(**{k: v for k, v in d.items() if k in Playbook.__dataclass_fields__})


# ── 7 个创业范式（内置 + 从数据验证） ─────────────────────

PLAYBOOKS: dict[str, Playbook] = {

    "platform": Playbook(
        playbook_id="platform",
        name="平台型（双边市场）",
        subtitle="连接供需双方，靠交易量/佣金/增值服务盈利",
        description=(
            "**核心逻辑：** 你不是内容/服务的生产者，而是连接供给方和需求方的撮合平台。\n\n"
            "**关键挑战：** 鸡生蛋问题——先有供给还是先有需求？\n\n"
            "**典型路径：** 单边切入（先做工具吸引供给方）→ 引入需求方 → 双边飞轮\n\n"
            "**护城河来源：** 网络效应——用户越多价值越大，越难被替代"
        ),
        conditions=[
            "你的产品/服务连接两类不同的用户群体",
            "价值来自撮合/匹配而非自己提供服务",
            "用户越多，平台对双方的价值越大",
        ],
        match_keywords=["平台", "撮合", "匹配", "双边", "交易", "连接", "marketplace"],
        match_biz_models=["平台", "佣金", "广告"],
        match_industries=[],
        key_metrics=[
            {"name": "GMV/交易额", "formula": "平台上的总交易金额", "benchmark": "月环比增长>20%", "why": "衡量平台规模"},
            {"name": "Take Rate", "formula": "平台收入/GMV", "benchmark": "5%-20%", "why": "衡量变现能力"},
            {"name": "供给方密度", "formula": "每个需求者可选的供给方数", "benchmark": ">5", "why": "确保匹配效率"},
            {"name": "匹配效率", "formula": "成功交易/总请求", "benchmark": ">30%", "why": "核心体验指标"},
        ],
        min_evidence=[
            {"rubric": "R1", "evidence": "两端用户的痛点各是什么，访谈了多少人", "why": "双边各自的需求必须验证"},
            {"rubric": "R2", "evidence": "供给方和需求方各至少 3 人的访谈记录", "why": "两端都需要一手数据"},
            {"rubric": "R4", "evidence": "鸡生蛋策略：先从哪端切入，怎么冷启动", "why": "平台最大的生死问题"},
            {"rubric": "R5", "evidence": "同类平台的 Take Rate 和 GMV 对标", "why": "验证市场容量"},
            {"rubric": "R7", "evidence": "网络效应如何形成，为什么竞品无法复制", "why": "平台的护城河核心"},
        ],
        common_pitfalls=[
            "没有解决冷启动问题就开始烧钱补贴",
            "只关注需求端忽略供给端体验",
            "Take Rate 定太高导致供给方流失",
            "高估网络效应——本地化服务的网络效应比全国弱",
        ],
        bp_structure=[
            "双边痛点与市场机会",
            "平台架构与匹配机制",
            "冷启动策略（先攻哪端）",
            "单位经济（Take Rate + CAC/LTV）",
            "网络效应与增长飞轮",
            "竞品对比与差异化",
            "团队与执行路径",
        ],
        example_projects=[],
    ),

    "saas_sub": Playbook(
        playbook_id="saas_sub",
        name="SaaS 订阅型",
        subtitle="软件即服务，按月/年收费，靠留存和扩展收入增长",
        description=(
            "**核心逻辑：** 提供云端软件服务，客户按订阅付费，收入可预测。\n\n"
            "**关键挑战：** 获客成本高，需要靠留存回收。LTV/CAC > 3 是生命线。\n\n"
            "**典型路径：** 免费试用/Freemium → 付费转化 → 客户成功 → 扩展收入\n\n"
            "**护城河来源：** 转换成本——用户的数据和工作流都在你的系统里"
        ),
        conditions=[
            "你提供的是线上软件/工具服务",
            "客户需要持续使用（非一次性购买）",
            "可以按功能/用量分级定价",
        ],
        match_keywords=["SaaS", "订阅", "月费", "年费", "软件", "云", "工具", "Freemium"],
        match_biz_models=["SaaS", "订阅", "会员", "增值服务"],
        match_industries=[],
        key_metrics=[
            {"name": "MRR/ARR", "formula": "月/年经常性收入", "benchmark": "月增长>10%", "why": "SaaS的核心收入指标"},
            {"name": "Churn Rate", "formula": "月流失客户/总客户", "benchmark": "<5%", "why": "留存是SaaS生命线"},
            {"name": "LTV/CAC", "formula": "用户终身价值/获客成本", "benchmark": ">3", "why": "商业模式是否可持续"},
            {"name": "NRR", "formula": "净收入留存率", "benchmark": ">100%", "why": "衡量扩展收入能力"},
        ],
        min_evidence=[
            {"rubric": "R2", "evidence": "目标客户的工作流痛点和现有工具不满", "why": "SaaS 必须解决真实工作流问题"},
            {"rubric": "R4", "evidence": "定价阶梯（免费/基础/专业）和付费转化率预估", "why": "SaaS 的核心是定价策略"},
            {"rubric": "R6", "evidence": "CAC、LTV、Payback Period 的计算", "why": "SaaS 的财务逻辑必须成立"},
            {"rubric": "R7", "evidence": "与 3+ 竞品的功能对比矩阵", "why": "SaaS 赛道竞争激烈"},
        ],
        common_pitfalls=[
            "Freemium 用户不转化——免费版功能太多",
            "只看新增不看流失——月流失 5% 年损失 46%",
            "定价太低不敢涨——早期客户应该为价值付费",
            "功能堆砌而非解决核心问题",
        ],
        bp_structure=[
            "目标客户的工作流痛点",
            "产品功能与核心价值",
            "定价策略与付费层级",
            "单位经济模型（CAC/LTV/Payback）",
            "增长策略（PLG vs Sales-led）",
            "竞品对比与转换成本",
            "发展路线图",
        ],
        example_projects=[],
    ),

    "b2b_solution": Playbook(
        playbook_id="b2b_solution",
        name="ToB 解决方案型",
        subtitle="为企业/机构提供定制化解决方案，项目制起步走向产品化",
        description=(
            "**核心逻辑：** 针对企业客户的具体问题提供技术解决方案，先做项目积累能力，再抽象为标准产品。\n\n"
            "**关键挑战：** 从「做项目」到「卖产品」的转型——项目制不可规模化。\n\n"
            "**典型路径：** 标杆客户 → 行业方案 → 标准产品 → 渠道分发\n\n"
            "**护城河来源：** 行业 know-how + 客户数据积累 + 实施案例"
        ),
        conditions=[
            "你的客户是企业/政府/机构，不是个人消费者",
            "解决方案需要一定程度的定制",
            "客单价高（>万元），决策链长",
        ],
        match_keywords=["B2B", "企业", "解决方案", "项目", "定制", "实施", "部署", "技术服务"],
        match_biz_models=["B2B", "技术服务", "授权", "代理"],
        match_industries=["工业制造", "政务管理"],
        key_metrics=[
            {"name": "客单价", "formula": "合同总额/客户数", "benchmark": "视行业而定", "why": "ToB 靠大单"},
            {"name": "销售周期", "formula": "从首次接触到签约的天数", "benchmark": "<90天", "why": "周期太长现金流会断"},
            {"name": "产品化率", "formula": "标准功能/总交付功能", "benchmark": ">60%", "why": "衡量可复制程度"},
            {"name": "续约率", "formula": "续约客户/到期客户", "benchmark": ">80%", "why": "ToB 的核心是客户成功"},
        ],
        min_evidence=[
            {"rubric": "R1", "evidence": "与 3+ 企业决策者的深度访谈", "why": "ToB 必须理解决策链"},
            {"rubric": "R3", "evidence": "技术方案的可交付性验证（PoC 或标杆项目）", "why": "企业要看到实际效果"},
            {"rubric": "R4", "evidence": "项目制 vs 产品化的转型路线", "why": "这是 ToB 创业的核心战略"},
            {"rubric": "R8", "evidence": "团队有行业经验或客户资源", "why": "ToB 很依赖行业人脉"},
        ],
        common_pitfalls=[
            "沉迷做项目不做产品——收入增长靠堆人",
            "客户需求无限膨胀——不懂说'不'",
            "标杆客户选错——不具备行业代表性",
            "低估销售周期和决策链复杂度",
        ],
        bp_structure=[
            "行业痛点与客户画像",
            "解决方案架构",
            "标杆客户与交付案例",
            "产品化路线（项目→产品）",
            "定价与销售策略",
            "竞争格局与差异化",
            "团队行业背景",
        ],
        example_projects=[],
    ),

    "hardware": Playbook(
        playbook_id="hardware",
        name="硬件+服务型",
        subtitle="卖设备/硬件 + 增值服务/耗材，剃须刀模式",
        description=(
            "**核心逻辑：** 通过硬件设备获客，靠耗材/服务/数据持续收费。\n\n"
            "**关键挑战：** 硬件的库存、供应链、售后成本远超软件。\n\n"
            "**典型路径：** 原型验证 → 小批量 → 找代工/供应链 → 渠道铺货\n\n"
            "**护城河来源：** 硬件专利 + 耗材锁定 + 数据壁垒"
        ),
        conditions=[
            "你的产品包含实体硬件/设备",
            "有后续耗材/服务/数据的持续收入",
            "需要供应链和生产制造能力",
        ],
        match_keywords=["硬件", "设备", "传感器", "IoT", "机器人", "无人机", "芯片", "耗材"],
        match_biz_models=["设备销售", "直销"],
        match_industries=["工业制造", "农业发展"],
        key_metrics=[
            {"name": "BOM 成本", "formula": "物料清单总成本", "benchmark": "售价的30%-50%", "why": "硬件毛利空间"},
            {"name": "设备毛利率", "formula": "(售价-BOM-组装)/售价", "benchmark": ">40%", "why": "覆盖渠道和售后"},
            {"name": "耗材/服务收入占比", "formula": "后续收入/总收入", "benchmark": ">30%", "why": "剃须刀模式的关键"},
            {"name": "退货率", "formula": "退货/发货", "benchmark": "<5%", "why": "产品质量指标"},
        ],
        min_evidence=[
            {"rubric": "R3", "evidence": "原型/样品的实际测试数据", "why": "硬件必须有实物验证"},
            {"rubric": "R6", "evidence": "BOM 成本清单和供应商报价", "why": "硬件的财务逻辑从成本开始"},
            {"rubric": "R8", "evidence": "供应链和生产制造的可行性方案", "why": "能设计不等于能量产"},
        ],
        common_pitfalls=[
            "原型到量产的鸿沟——实验室能做不代表能量产",
            "低估售后和退货成本",
            "库存积压导致现金流断裂",
            "专利保护不充分被快速山寨",
        ],
        bp_structure=[
            "产品定义与技术方案",
            "原型验证与测试数据",
            "BOM 成本与定价",
            "供应链与量产方案",
            "渠道策略（直销/经销/线上）",
            "售后与增值服务",
            "知识产权保护",
        ],
        example_projects=[],
    ),

    "gov_policy": Playbook(
        playbook_id="gov_policy",
        name="政策驱动型",
        subtitle="依托政策红利、政府采购或补贴，为公共部门提供服务",
        description=(
            "**核心逻辑：** 借政策东风，为政府/事业单位提供合规/高效的解决方案。\n\n"
            "**关键挑战：** 政策有时效性，必须在窗口期建立独立竞争力。\n\n"
            "**典型路径：** 政策洞察 → 试点项目 → 标杆案例 → 全国推广\n\n"
            "**护城河来源：** 政策理解深度 + 标杆案例 + 合规能力"
        ),
        conditions=[
            "项目受益于特定政策（补贴、合规要求、政府采购）",
            "主要客户是政府/事业单位/国企",
            "政策变化会显著影响项目可行性",
        ],
        match_keywords=["政策", "政府", "补贴", "采购", "合规", "监管", "公共", "国标"],
        match_biz_models=["B2B", "技术服务"],
        match_industries=["政务管理", "环境保护"],
        key_metrics=[
            {"name": "政策依赖度", "formula": "政策相关收入/总收入", "benchmark": "<70%", "why": "不能完全依赖政策"},
            {"name": "中标率", "formula": "中标项目/投标项目", "benchmark": ">20%", "why": "衡量竞争力"},
            {"name": "标杆项目数", "formula": "已完成的政府标杆案例", "benchmark": ">2", "why": "政府客户看先例"},
            {"name": "政策窗口期", "formula": "政策剩余有效期", "benchmark": ">2年", "why": "要在窗口期内建立壁垒"},
        ],
        min_evidence=[
            {"rubric": "R1", "evidence": "具体引用政策文件编号和条款", "why": "政策驱动必须有政策依据"},
            {"rubric": "R4", "evidence": "如果政策取消，收入会下降多少", "why": "必须评估政策依赖风险"},
            {"rubric": "R5", "evidence": "同赛道其他供应商的竞争格局", "why": "政府赛道也有竞争"},
            {"rubric": "R8", "evidence": "团队的政策解读和政府资源能力", "why": "政策型创业靠人脉和理解力"},
        ],
        common_pitfalls=[
            "政策依赖度过高——政策变了项目就死了",
            "低估政府采购的流程和周期",
            "标杆项目选错——不同省市政策差异大",
            "没有建立政策之外的独立竞争力",
        ],
        bp_structure=[
            "政策背景与市场机会",
            "解决方案与合规能力",
            "标杆案例与政府资源",
            "政策依赖度分析与风险对冲",
            "竞争格局（同类供应商）",
            "独立竞争力建设路线",
            "团队政府经验",
        ],
        example_projects=[],
    ),

    "campus": Playbook(
        playbook_id="campus",
        name="校园场景创业",
        subtitle="利用校园渠道密度和学生群体特征快速验证",
        description=(
            "**核心逻辑：** 校园是天然的用户聚集地，获客成本极低，适合快速验证。\n\n"
            "**关键挑战：** 校园市场天花板低，必须有向外扩展的路径。\n\n"
            "**典型路径：** 本校验证 → 周边高校 → 社区/城市 → 全国\n\n"
            "**护城河来源：** 先发优势（本地网络效应）+ 学生口碑传播速度"
        ),
        conditions=[
            "核心用户群是学生或校园场景",
            "可以利用校园渠道低成本获客",
            "产品/服务在校园场景有天然使用频率",
        ],
        match_keywords=["校园", "学生", "大学", "高校", "社团", "宿舍", "食堂", "课程"],
        match_biz_models=["平台", "广告", "会员"],
        match_industries=["教育教学"],
        key_metrics=[
            {"name": "校内渗透率", "formula": "活跃用户/全校人数", "benchmark": ">10%", "why": "验证产品在校园的接受度"},
            {"name": "CAC", "formula": "获客成本", "benchmark": "<10元", "why": "校园获客应该很便宜"},
            {"name": "校外可复制性", "formula": "其他高校的适用度评估", "benchmark": ">70%", "why": "必须能走出校园"},
            {"name": "口碑系数", "formula": "用户推荐带来的新增/总新增", "benchmark": ">40%", "why": "校园靠口碑"},
        ],
        min_evidence=[
            {"rubric": "R2", "evidence": "本校学生的实际使用数据和反馈", "why": "校园创业最大优势就是近距离验证"},
            {"rubric": "R5", "evidence": "校园外的市场有多大，扩展路径", "why": "投资人最担心天花板"},
            {"rubric": "R8", "evidence": "团队在校园的渠道资源（社团/学生会）", "why": "校园获客靠关系"},
        ],
        common_pitfalls=[
            "只在本校做不出去——校园市场天花板低",
            "功能太学生化不适合社会用户",
            "毕业了团队就散了——执行力断档",
            "低估校外获客成本——校园外贵 10 倍",
        ],
        bp_structure=[
            "校园痛点与验证数据",
            "产品方案与用户体验",
            "校内增长策略",
            "校外扩展路径（从校园到社会）",
            "竞品分析与差异化",
            "团队与校园资源",
            "财务模型",
        ],
        example_projects=[],
    ),

    "ai_tool": Playbook(
        playbook_id="ai_tool",
        name="AI 工具型",
        subtitle="将 AI 能力封装为 API/SaaS 工具，按调用量或订阅收费",
        description=(
            "**核心逻辑：** 用 AI/ML 技术解决特定问题，将模型能力封装为可调用的工具。\n\n"
            "**关键挑战：** 技术壁垒 ≠ 商业壁垒——模型会被追平，数据和场景才是护城河。\n\n"
            "**典型路径：** 论文/模型 → 行业场景验证 → API/产品 → 数据飞轮\n\n"
            "**护城河来源：** 场景数据积累 + 行业 know-how + 部署成本（不是模型本身）"
        ),
        conditions=[
            "核心能力是 AI/ML 模型或算法",
            "解决的问题有明确的行业场景",
            "可以按 API 调用量或功能收费",
        ],
        match_keywords=["AI", "深度学习", "机器学习", "模型", "算法", "神经网络", "YOLO",
                         "目标检测", "自然语言", "大模型", "GPT", "智能"],
        match_biz_models=["API", "SaaS", "技术服务", "授权"],
        match_industries=[],
        key_metrics=[
            {"name": "模型准确率", "formula": "任务指标（精度/召回/F1）", "benchmark": "比现有方案提升>10%", "why": "AI 必须有可量化优势"},
            {"name": "推理成本", "formula": "每次 API 调用的成本", "benchmark": "客户付费>成本×3", "why": "AI 的边际成本决定可持续性"},
            {"name": "数据飞轮效果", "formula": "数据量增长→模型精度提升幅度", "benchmark": "对数增长", "why": "数据护城河的关键"},
            {"name": "场景覆盖度", "formula": "可服务的行业/场景数", "benchmark": ">3", "why": "AI 工具要有通用性"},
        ],
        min_evidence=[
            {"rubric": "R3", "evidence": "模型在真实数据上的测试结果（非实验室数据）", "why": "实验室性能≠生产环境"},
            {"rubric": "R6", "evidence": "推理成本 vs 客户付费意愿的计算", "why": "AI 的经济模型必须算清"},
            {"rubric": "R7", "evidence": "你的数据/场景优势是什么，为什么大厂不做", "why": "模型会被追平，场景不会"},
            {"rubric": "R8", "evidence": "团队的 AI 研发能力（论文/竞赛/项目经验）", "why": "AI 团队的技术底蕴"},
        ],
        common_pitfalls=[
            "只有模型没有场景——技术找不到买家",
            "把技术壁垒当商业壁垒——大厂随时可以做",
            "实验室数据好看但真实场景翻车",
            "推理成本太高客户付不起",
        ],
        bp_structure=[
            "行业问题与 AI 解决方案",
            "技术方案与模型性能",
            "真实场景验证结果",
            "数据飞轮与护城河",
            "商业模式（API/SaaS/授权）",
            "推理成本与财务模型",
            "竞争分析（vs 大厂 vs 同行）",
            "团队技术背景",
        ],
        example_projects=[],
    ),
}


# ── 从超图数据聚类：给每个范式匹配案例 ────────────────────

def cluster_projects_to_playbooks() -> dict:
    """
    将超图中的 85 个项目按规则匹配到 7 个范式中。
    返回统计结果并更新 PLAYBOOKS 的 example_projects。
    """
    from hypergraph.engine import _nodes, _hyperedges

    # 收集每个项目的特征
    project_features: list[dict] = []
    for he in _hyperedges.values():
        if he["type"] != "Product_Market_Fit":
            continue
        props = he["properties"]
        proj_nodes = [_nodes[nid] for nid in he["nodes"]
                      if nid in _nodes and _nodes[nid]["type"] == "Project"]
        if not proj_nodes:
            continue
        proj = proj_nodes[0]
        project_features.append({
            "name": proj["label"],
            "industry": props.get("industry", ""),
            "biz_models": props.get("biz_models") or proj.get("properties", {}).get("biz_model", []),
            "techs": props.get("techs", []),
            "moat": proj.get("properties", {}).get("moat", []),
        })

    # 规则匹配
    stats = {pid: 0 for pid in PLAYBOOKS}
    for proj in project_features:
        best_match = _match_project_to_playbook(proj)
        if best_match:
            pb = PLAYBOOKS[best_match]
            if proj["name"] not in pb.example_projects:
                pb.example_projects.append(proj["name"])
            stats[best_match] += 1

    # 更新 project_count
    for pid, pb in PLAYBOOKS.items():
        pb.project_count = len(pb.example_projects)

    # 保存
    _save_playbooks()

    return {
        "total_projects": len(project_features),
        "matched": sum(stats.values()),
        "unmatched": len(project_features) - sum(stats.values()),
        "by_playbook": {pid: {"count": c, "examples": PLAYBOOKS[pid].example_projects[:3]}
                        for pid, c in stats.items()},
    }


def _match_project_to_playbook(proj: dict) -> str | None:
    """规则匹配：根据项目特征返回最匹配的 playbook_id。"""
    scores: dict[str, float] = {}

    name = proj["name"].lower()
    industry = proj["industry"]
    biz_models = [b.lower() for b in proj.get("biz_models", [])]
    techs = [t.lower() for t in proj.get("techs", [])]
    all_text = f"{name} {industry} {' '.join(biz_models)} {' '.join(techs)}"

    for pid, pb in PLAYBOOKS.items():
        score = 0.0

        # 关键词匹配
        for kw in pb.match_keywords:
            if kw.lower() in all_text:
                score += 2.0

        # 商业模式匹配
        for bm in pb.match_biz_models:
            if bm.lower() in biz_models or any(bm.lower() in b for b in biz_models):
                score += 3.0

        # 行业匹配
        if pb.match_industries:
            if industry in pb.match_industries:
                score += 2.0

        if score > 0:
            scores[pid] = score

    if not scores:
        return None

    # 返回得分最高的
    return max(scores, key=scores.get)


# ── 给学生匹配范式 ───────────────────────────────────────────

def match_playbook(
    description: str = "",
    industry: str = "",
    biz_model: str = "",
    techs: list[str] | None = None,
) -> list[dict]:
    """
    根据学生的项目描述，匹配最适合的 1-2 个范式。
    返回排序后的匹配结果。
    """
    proj = {
        "name": description,
        "industry": industry,
        "biz_models": [biz_model] if biz_model else [],
        "techs": techs or [],
    }

    all_text = f"{description} {industry} {biz_model} {' '.join(techs or [])}".lower()

    results: list[tuple[float, str]] = []
    for pid, pb in PLAYBOOKS.items():
        score = 0.0
        for kw in pb.match_keywords:
            if kw.lower() in all_text:
                score += 2.0
        for bm in pb.match_biz_models:
            if bm.lower() in all_text:
                score += 3.0
        if pb.match_industries and industry in pb.match_industries:
            score += 2.0
        # 条件语义匹配（粗略）
        for cond in pb.conditions:
            cond_chars = set(cond)
            desc_chars = set(description)
            overlap = len(cond_chars & desc_chars)
            if overlap > 5:
                score += 0.5

        if score > 0:
            results.append((score, pid))

    results.sort(key=lambda x: -x[0])

    return [
        {
            "playbook_id": pid,
            "match_score": round(score, 1),
            **PLAYBOOKS[pid].to_dict(),
        }
        for score, pid in results[:2]
    ]


# ── 格式化范式为 prompt 注入 ─────────────────────────────────

def format_playbook_for_prompt(playbook_id: str) -> str:
    """格式化单个范式为 LLM prompt 注入块。"""
    pb = PLAYBOOKS.get(playbook_id)
    if not pb:
        return ""

    lines = [f"[推荐创业范式：{pb.name}]"]
    lines.append(f"简介：{pb.subtitle}\n")

    lines.append("适用条件：")
    for c in pb.conditions:
        lines.append(f"  - {c}")

    lines.append(f"\n关键指标：")
    for m in pb.key_metrics[:3]:
        lines.append(f"  - {m['name']}（{m['formula']}）→ 健康标准：{m['benchmark']}")

    lines.append(f"\n最小证据包（此范式下必须提供的证据）：")
    for e in pb.min_evidence:
        lines.append(f"  - [{e['rubric']}] {e['evidence']}（{e['why']}）")

    lines.append(f"\n常见坑：")
    for p in pb.common_pitfalls[:3]:
        lines.append(f"  - {p}")

    if pb.example_projects:
        lines.append(f"\n超图案例库中属于此范式的项目：{'、'.join(pb.example_projects[:5])}")

    lines.append(f"\n请基于此范式框架评估学生项目，指出最缺的证据。")
    return "\n".join(lines)


def format_playbook_for_student(playbook_id: str) -> str:
    """生成面向学生的范式说明（用于前端展示或 AI 回复）。"""
    pb = PLAYBOOKS.get(playbook_id)
    if not pb:
        return ""

    lines = [f"## {pb.name}\n"]
    lines.append(f"**{pb.subtitle}**\n")
    lines.append(pb.description)

    lines.append(f"\n### 关键指标")
    for m in pb.key_metrics:
        lines.append(f"- **{m['name']}** = {m['formula']}（目标：{m['benchmark']}）")

    lines.append(f"\n### 你需要准备的证据")
    for e in pb.min_evidence:
        lines.append(f"- **[{e['rubric']}]** {e['evidence']}")

    lines.append(f"\n### 常见坑，务必避免")
    for p in pb.common_pitfalls:
        lines.append(f"- {p}")

    lines.append(f"\n### 推荐 BP 结构")
    for i, s in enumerate(pb.bp_structure, 1):
        lines.append(f"{i}. {s}")

    if pb.example_projects:
        lines.append(f"\n### 参考案例\n{'、'.join(pb.example_projects[:5])}")

    return "\n".join(lines)


# ── 持久化 ───────────────────────────────────────────────────

def _save_playbooks():
    data = [pb.to_dict() for pb in PLAYBOOKS.values()]
    with open(_PLAYBOOKS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_playbooks():
    """加载已持久化的 example_projects 等动态数据。"""
    if not _PLAYBOOKS_PATH.exists():
        return
    with open(_PLAYBOOKS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for d in data:
        pid = d.get("playbook_id", "")
        if pid in PLAYBOOKS:
            PLAYBOOKS[pid].example_projects = d.get("example_projects", [])
            PLAYBOOKS[pid].project_count = d.get("project_count", 0)


# 启动时加载
_load_playbooks()


def get_all_playbooks() -> list[dict]:
    return [pb.to_dict() for pb in PLAYBOOKS.values()]


def get_playbook(playbook_id: str) -> dict | None:
    pb = PLAYBOOKS.get(playbook_id)
    return pb.to_dict() if pb else None
