"""
services/knowledge_cards.py
────────────────────────────────────────────────────────────────
知识卡片系统 — 结构化知识单元 (Knowledge Cards)

核心思路（方向3）：
每条知识不是一段长文本，而是一张"卡片"，带字段、标签、
适用场景和可引用证据。检索时先按字段过滤，再按相关度排序。

卡片类型：
  concept   — 概念卡（PMF、TAM、护城河等）
  method    — 方法卡（精益画布、JTBD、用户访谈技巧等）
  case      — 案例卡（从超图 85 个竞赛项目提取）
  mistake   — 常见错误卡（从 Rubric common_mistakes + H 规则提取）
  template  — 模板卡（BP 模板、路演结构、财务模型模板）

检索策略：先按字段过滤 → 再 TF-IDF 相关度排序
"""
from __future__ import annotations

import json
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CARDS_PATH = Path(__file__).parent.parent / "data" / "knowledge_cards.json"


# ── 卡片 Schema ──────────────────────────────────────────────

@dataclass
class KnowledgeCard:
    card_id: str
    card_type: str           # concept | method | case | mistake | template
    title: str               # 卡片标题
    summary: str             # 一句话摘要
    content: str             # 详细内容（markdown）
    # 分类标签
    stage: list[str]         # 适用阶段 ["discovery", "ideation", "modeling", "execution", "pitching"]
    dimensions: list[str]    # 关联维度 ["empathy", "ideation", "business", "execution", "pitching"]
    rubrics: list[str]       # 关联 Rubric ["R1", "R2", ...]
    industry: str = ""       # 适用行业（空=通用）
    tags: list[str] = field(default_factory=list)   # 自由标签
    # 结构化字段（按 card_type 不同填充）
    fields: dict = field(default_factory=dict)
    # 可引用证据
    evidence_refs: list[dict] = field(default_factory=list)  # [{source, text, type}]
    # 元数据
    source: str = ""         # 来源标识
    related_cards: list[str] = field(default_factory=list)  # 关联卡片 ID

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "KnowledgeCard":
        return KnowledgeCard(**{k: v for k, v in d.items() if k in KnowledgeCard.__dataclass_fields__})


# ── 卡片存储 ──────────────────────────────────────────────────

_cards: dict[str, KnowledgeCard] = {}
_cards_loaded = False


def _load_cards():
    global _cards, _cards_loaded
    if _cards_loaded:
        return
    if _CARDS_PATH.exists():
        with open(_CARDS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _cards = {d["card_id"]: KnowledgeCard.from_dict(d) for d in data}
        logger.info(f"Loaded {len(_cards)} knowledge cards")
    _cards_loaded = True


def _save_cards():
    data = [c.to_dict() for c in _cards.values()]
    with open(_CARDS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_cards() -> list[KnowledgeCard]:
    _load_cards()
    return list(_cards.values())


def get_card(card_id: str) -> Optional[KnowledgeCard]:
    _load_cards()
    return _cards.get(card_id)


def add_card(card: KnowledgeCard) -> KnowledgeCard:
    _load_cards()
    _cards[card.card_id] = card
    _save_cards()
    return card


# ── 从超图 + Rubric 生成知识卡片库 ──────────────────────────

def generate_cards_from_hypergraph() -> dict:
    """
    一次性从现有超图数据 + Rubric 定义生成完整卡片库。

    来源：
    1. 超图 Project 节点 → case 卡片
    2. 超图 Concept 节点 → concept 卡片
    3. Rubric common_mistakes → mistake 卡片
    4. H1-H15 规则 → method 卡片（修复策略）
    5. 内置模板 → template 卡片

    幂等：同 card_id 的卡片会被覆盖。
    """
    _load_cards()
    stats = {"case": 0, "concept": 0, "mistake": 0, "method": 0, "template": 0}

    # ── 1. Case cards from hypergraph projects ──
    _generate_case_cards(stats)

    # ── 2. Concept cards from ontology + hypergraph ──
    _generate_concept_cards(stats)

    # ── 3. Mistake cards from rubric ──
    _generate_mistake_cards(stats)

    # ── 4. Method cards from H-rules ──
    _generate_method_cards(stats)

    # ── 5. Template cards (built-in) ──
    _generate_template_cards(stats)

    _save_cards()
    logger.info(f"Generated knowledge cards: {stats}")
    return {"total": len(_cards), **stats}


def _make_id(prefix: str, text: str) -> str:
    return f"{prefix}_{hashlib.md5(text.encode()).hexdigest()[:8]}"


# ── Rubric→维度映射 ──
_RUBRIC_TO_DIM = {
    "R1": "empathy", "R2": "empathy",
    "R3": "ideation", "R7": "ideation",
    "R4": "business", "R5": "business", "R6": "business",
    "R8": "execution", "R9": "pitching",
}

_RUBRIC_TO_STAGE = {
    "R1": ["discovery"], "R2": ["discovery"],
    "R3": ["ideation"], "R7": ["ideation"],
    "R4": ["modeling"], "R5": ["modeling"], "R6": ["modeling"],
    "R8": ["execution"], "R9": ["pitching"],
}


def _generate_case_cards(stats: dict):
    """从超图的 detailed Case_Study 超边生成案例卡片。"""
    from hypergraph.engine import _hyperedges, _nodes

    for he in _hyperedges.values():
        if he["type"] != "Case_Study" or not he["properties"].get("is_detailed"):
            continue
        props = he["properties"]
        name = props.get("project", "")
        if not name:
            continue

        card_id = _make_id("case", name)
        industry = props.get("industry", "")

        # 提取技术标签
        techs = [_nodes[nid]["label"] for nid in he["nodes"]
                 if nid in _nodes and _nodes[nid]["type"] == "Technology"]

        # 构建内容
        content_parts = []
        if props.get("problem"):
            content_parts.append(f"**痛点：** {props['problem']}")
        if props.get("solution"):
            content_parts.append(f"**方案：** {props['solution']}")
        if props.get("market_size"):
            content_parts.append(f"**市场规模：** {props['market_size']}")
        if props.get("biz_models"):
            content_parts.append(f"**商业模式：** {'、'.join(props['biz_models'])}")
        if props.get("moat"):
            content_parts.append(f"**壁垒/护城河：** {'、'.join(props['moat'][:3])}")
        if props.get("success_factors"):
            content_parts.append(f"**成功要素：** {'；'.join(props['success_factors'][:3])}")
        if props.get("failure_risks"):
            content_parts.append(f"**风险警示：** {'；'.join(props['failure_risks'][:3])}")

        # 确定适用阶段（案例卡适用于所有阶段）
        stages = ["discovery", "ideation", "modeling", "execution", "pitching"]
        dims = ["empathy", "ideation", "business", "execution", "pitching"]

        card = KnowledgeCard(
            card_id=card_id,
            card_type="case",
            title=name,
            summary=f"{industry}行业竞赛案例，技术：{'、'.join(techs[:3]) or '未知'}",
            content="\n\n".join(content_parts),
            stage=stages,
            dimensions=dims,
            rubrics=[],
            industry=industry,
            tags=techs[:5] + ([industry] if industry else []),
            fields={
                "problem": props.get("problem", "")[:200],
                "solution": props.get("solution", "")[:200],
                "market_size": props.get("market_size", ""),
                "biz_models": props.get("biz_models", []),
                "moat": props.get("moat", []),
                "technologies": techs,
                "success_factors": props.get("success_factors", []),
                "failure_risks": props.get("failure_risks", []),
            },
            source="hypergraph_case_study",
        )
        _cards[card_id] = card
        stats["case"] += 1


def _generate_concept_cards(stats: dict):
    """从超图 Concept 节点 + 本体定义生成概念卡片。"""
    from hypergraph.engine import _nodes, get_concept_prerequisites, get_neighbors

    # 内置概念详解
    _CONCEPT_DETAILS: dict[str, dict] = {
        "PMF": {
            "summary": "产品-市场匹配：验证你的产品是否满足真实市场需求",
            "content": "**PMF (Product-Market Fit)** 是指产品与市场需求之间的匹配程度。\n\n"
                       "**判断标准：**\n"
                       "- 用户自发推荐给朋友（NPS > 40）\n"
                       "- 没有产品用户会感到失望（>40%的用户）\n"
                       "- 用户增长超过团队获客能力\n\n"
                       "**验证方法：** Sean Ellis测试、用户留存曲线、有机增长率",
            "stages": ["discovery", "ideation"],
            "dims": ["empathy", "ideation"],
            "rubrics": ["R1", "R2", "R3"],
        },
        "TAM": {
            "summary": "总可寻址市场（Total Addressable Market）：自上而下+自下而上估算",
            "content": "**TAM/SAM/SOM 三级市场估算：**\n\n"
                       "- **TAM（总市场）：** 如果你100%垄断，最大的收入\n"
                       "- **SAM（可服务市场）：** 你的产品能覆盖的那部分\n"
                       "- **SOM（可获得市场）：** 短期内你能拿下的份额\n\n"
                       "**正确方法：** 自下而上估算 = 单客户价值 × 可触达客户数\n"
                       "**常见错误：** '中国有14亿人，只要1%...'（自上而下陷阱）",
            "stages": ["modeling"],
            "dims": ["business"],
            "rubrics": ["R5"],
        },
        "LTV": {
            "summary": "用户终身价值（Lifetime Value）：一个客户在整个生命周期的总贡献",
            "content": "**LTV = ARPU × 平均留存时间**\n\n"
                       "**关键规则：** LTV/CAC > 3 才是健康的商业模式\n"
                       "**提升路径：** 提高客单价、增加购买频次、延长留存时间",
            "stages": ["modeling"],
            "dims": ["business"],
            "rubrics": ["R6"],
        },
        "CAC": {
            "summary": "客户获取成本（Customer Acquisition Cost）：获取一个付费用户的成本",
            "content": "**CAC = 总获客支出 / 新增付费用户数**\n\n"
                       "**优化思路：**\n"
                       "- 渠道优化：选择 CAC 最低的渠道\n"
                       "- 转化率提升：优化落地页、试用体验\n"
                       "- 口碑增长：让用户自发推荐（CAC≈0）",
            "stages": ["modeling"],
            "dims": ["business"],
            "rubrics": ["R6"],
        },
        "护城河": {
            "summary": "竞争壁垒：阻止竞争对手复制你的差异化优势",
            "content": "**四大护城河类型：**\n\n"
                       "1. **网络效应：** 用户越多越好用（如微信）\n"
                       "2. **转换成本：** 迁移到竞品的成本很高\n"
                       "3. **规模经济：** 规模越大边际成本越低\n"
                       "4. **品牌/IP：** 用户认知和信任壁垒\n\n"
                       "**创业公司常犯错误：** 把「先发优势」当护城河（它不是）",
            "stages": ["ideation", "modeling"],
            "dims": ["ideation"],
            "rubrics": ["R7"],
        },
        "精益画布": {
            "summary": "Lean Canvas：一页纸快速梳理商业模式的核心假设",
            "content": "**精益画布 9 个模块：**\n\n"
                       "1. 问题（Top 3 痛点）\n"
                       "2. 客户细分（目标用户）\n"
                       "3. 独特价值主张\n"
                       "4. 解决方案\n"
                       "5. 渠道（如何触达用户）\n"
                       "6. 收入来源\n"
                       "7. 成本结构\n"
                       "8. 关键指标\n"
                       "9. 门槛优势（护城河）\n\n"
                       "**使用场景：** 项目早期快速验证假设，比写50页商业计划书更有效",
            "stages": ["discovery", "ideation", "modeling"],
            "dims": ["empathy", "ideation", "business"],
            "rubrics": ["R1", "R3", "R4"],
        },
        "用户访谈": {
            "summary": "与潜在用户面对面交流，验证需求假设的核心方法",
            "content": ("**访谈原则（The Mom Test）：**\n\n"
                       "1. 问他们的**行为**而非**意见**（「你上次怎么解决的？」而非「你觉得好不好？」）\n"
                       "2. 问**过去**而非**未来**（「你昨天怎么做的？」而非「你会不会用？」）\n"
                       "3. 少说多听，追问具体细节\n\n"
                       "**最低标准：** 至少访谈 5 个人，3 个陌生人\n"
                       "**黄金问题：** 「你上次遇到这个问题时做了什么？花了多少时间/钱？」"),
            "stages": ["discovery"],
            "dims": ["empathy"],
            "rubrics": ["R1", "R2"],
        },
        "商业模式画布": {
            "summary": "Business Model Canvas：系统化描述商业模式的 9 大要素",
            "content": "**9 大要素：** 客户细分、价值主张、渠道、客户关系、"
                       "收入来源、核心资源、关键活动、关键合作、成本结构\n\n"
                       "**与精益画布的区别：** 精益画布更关注问题和风险，BMC 更关注运营和资源",
            "stages": ["modeling"],
            "dims": ["business"],
            "rubrics": ["R4"],
        },
        "JTBD": {
            "summary": "Jobs To Be Done：用户「雇佣」产品来完成的任务",
            "content": "**核心思想：** 用户不是在买产品，而是在雇佣产品完成某个任务。\n\n"
                       "**公式：** 当我[在某个场景]时，我想要[完成某个任务]，这样我就能[获得某个结果]。\n\n"
                       "**应用：** 帮助发现真需求而非表面需求。例如：用户买钻头，真正的 Job 是「在墙上打洞」。",
            "stages": ["discovery", "ideation"],
            "dims": ["empathy", "ideation"],
            "rubrics": ["R1", "R3"],
        },
        "AARRR": {
            "summary": "海盗指标/增长漏斗：Acquisition → Activation → Retention → Revenue → Referral",
            "content": "**五个阶段：**\n"
                       "1. **获取(A)：** 用户从哪里来？\n"
                       "2. **激活(A)：** 用户是否体验到「啊哈时刻」？\n"
                       "3. **留存(R)：** 用户是否持续回来？\n"
                       "4. **收入(R)：** 用户是否付费？\n"
                       "5. **推荐(R)：** 用户是否推荐给别人？\n\n"
                       "**核心：** 先做留存，再做获客。留存不好的情况下大量获客 = 漏桶灌水",
            "stages": ["execution"],
            "dims": ["execution"],
            "rubrics": ["R8"],
        },
    }

    # 从超图中生成 + 内置详解合并
    for nid, node in _nodes.items():
        if node["type"] != "Concept":
            continue
        label = node["label"]
        card_id = _make_id("concept", label)

        # 获取前置依赖
        prereqs = get_concept_prerequisites(label)
        neighbors = get_neighbors(nid)
        related_concepts = [n["label"] for n in neighbors if n["type"] == "Concept"][:5]

        # 检查是否有内置详解
        detail = _CONCEPT_DETAILS.get(label, {})

        card = KnowledgeCard(
            card_id=card_id,
            card_type="concept",
            title=label,
            summary=detail.get("summary", f"创业核心概念：{label}"),
            content=detail.get("content", f"**{label}** — 创新创业领域的核心概念。"),
            stage=detail.get("stages", ["discovery", "ideation", "modeling"]),
            dimensions=detail.get("dims", ["empathy", "ideation", "business"]),
            rubrics=detail.get("rubrics", []),
            tags=[label] + related_concepts[:3],
            fields={
                "prerequisites": prereqs.get("prerequisites", []),
                "learning_order": prereqs.get("learning_order", []),
                "related_concepts": related_concepts,
            },
            source="hypergraph_concept",
            related_cards=[_make_id("concept", c) for c in related_concepts[:3]],
        )
        _cards[card_id] = card
        stats["concept"] += 1


def _generate_mistake_cards(stats: dict):
    """从 Rubric common_mistakes 生成常见错误卡片。"""
    rubric_path = Path(__file__).parent.parent / "data" / "rubric" / "rubric_items.json"
    if not rubric_path.exists():
        return

    with open(rubric_path, encoding="utf-8") as f:
        rubrics = json.load(f)

    _MISTAKE_DETAILS: dict[str, str] = {
        "痛点模糊": "学生描述的痛点过于笼统（如「不方便」「体验不好」），缺少具体场景和量化描述。\n\n"
                    "**修复方法：** 用 JTBD 框架重新定义：「在[场景]下，[用户]想要[完成任务]，但因为[具体障碍]，导致[可量化的损失]」",
        "假设性需求": "学生只是「觉得」用户需要，但没有实际访谈或数据支撑。\n\n"
                      "**修复方法：** 至少做 5 次用户访谈，遵循 The Mom Test 原则。",
        "主观验证": "只调研了身边朋友/同学，或只收集正面反馈。\n\n"
                    "**修复方法：** 样本中至少包含 3 个陌生人，记录拒绝/负面反馈占比。",
        "过度工程化": "方案过于复杂，一上来就要做全平台/全功能系统。\n\n"
                      "**修复方法：** 先做 MVP（最小可行产品），只保留核心功能验证核心假设。",
        "渠道-用户不匹配": "选择的渠道无法有效触达目标用户。\n\n"
                           "**修复方法：** 列出用户花时间的 Top 3 场所/平台，从中选渠道。",
        "市场规模虚高": "用「中国有14亿人，只需要1%」式的自上而下估算。\n\n"
                        "**修复方法：** 改用自下而上估算：单客价值 × 可触达客户数 = SOM。",
        "LTV < CAC": "获客成本超过用户终身价值，商业模式不可持续。\n\n"
                     "**修复方法：** 1) 降低 CAC（优化渠道）；2) 提高 LTV（提价/提频/提留存）；目标 LTV/CAC > 3。",
        "伪创新": "差异化仅是「我们用了AI」但核心价值没变。\n\n"
                  "**修复方法：** 做竞品对比矩阵，在 3 个以上维度标注与竞品的实质差异。",
        "技能不匹配": "团队能力与项目技术需求不匹配。\n\n"
                      "**修复方法：** 列出项目所需的 Top 3 技能，标注团队覆盖情况，缺口写招聘/合作计划。",
        "叙事断裂": "路演材料逻辑不连贯，痛点-方案-市场-盈利之间缺乏因果链。\n\n"
                    "**修复方法：** 用 7 幕结构：① 现状 → ② 痛点 → ③ 方案 → ④ 市场 → ⑤ 商业模式 → ⑥ 团队 → ⑦ 愿景",
    }

    for rubric in rubrics:
        rid = rubric["id"]
        dim = _RUBRIC_TO_DIM.get(rid, "empathy")
        stages = _RUBRIC_TO_STAGE.get(rid, ["discovery"])

        for mistake in rubric.get("common_mistakes", []):
            card_id = _make_id("mistake", f"{rid}_{mistake}")
            detail = _MISTAKE_DETAILS.get(mistake, f"**{mistake}** — 在{rubric['name']}维度常见的问题。")

            card = KnowledgeCard(
                card_id=card_id,
                card_type="mistake",
                title=f"常见错误：{mistake}",
                summary=f"{rubric['name']}维度的常见问题",
                content=detail,
                stage=stages,
                dimensions=[dim],
                rubrics=[rid],
                tags=[mistake, rubric["name"]],
                fields={
                    "rubric_id": rid,
                    "rubric_name": rubric["name"],
                    "severity": "high" if rubric.get("weight", 0) >= 0.1 else "medium",
                },
                source="rubric_common_mistakes",
            )
            _cards[card_id] = card
            stats["mistake"] += 1


def _generate_method_cards(stats: dict):
    """从 H1-H15 规则生成方法/修复策略卡片。"""
    from hypergraph.knowledge_recommendations import H_RULE_TO_CONCEPT

    rules_path = Path(__file__).parent.parent / "data" / "rubric" / "constraint_rules.json"
    if not rules_path.exists():
        return

    with open(rules_path, encoding="utf-8") as f:
        rules = json.load(f)

    rule_map = {r["rule_id"]: r for r in rules}

    for rid, concept_info in H_RULE_TO_CONCEPT.items():
        rule = rule_map.get(rid, {})
        concept = concept_info["concept"]
        query = concept_info["query"]

        card_id = _make_id("method", f"{rid}_{concept}")

        # 从规则提取维度
        dim = rule.get("dimension", "empathy")
        fix_task = rule.get("fix_task", "")
        severity = rule.get("severity", "medium")

        card = KnowledgeCard(
            card_id=card_id,
            card_type="method",
            title=f"修复策略：{concept}",
            summary=f"当{rule.get('name', rid)}问题触发时的修复方法",
            content=f"**触发条件：** {rule.get('description', rid)}\n\n"
                    f"**修复任务：** {fix_task}\n\n"
                    f"**学习问题：** {query}",
            stage=_RUBRIC_TO_STAGE.get(rule.get("rubric", "R1"), ["discovery"]),
            dimensions=[dim] if dim else ["empathy"],
            rubrics=[rule.get("rubric", "")],
            tags=[concept, rid],
            fields={
                "rule_id": rid,
                "concept": concept,
                "severity": severity,
                "fix_task": fix_task,
                "learning_query": query,
            },
            source="h_rules",
        )
        _cards[card_id] = card
        stats["method"] += 1


def _generate_template_cards(stats: dict):
    """内置模板卡片。"""
    templates = [
        {
            "title": "路演PPT七幕结构",
            "summary": "投资人/竞赛评委期待的路演叙事结构",
            "content": "**七幕结构：**\n\n"
                       "1. **开场Hook：** 一个吸引注意的故事或数据\n"
                       "2. **痛点：** 谁，在什么场景下，遇到什么问题\n"
                       "3. **方案：** 你怎么解决，核心差异化\n"
                       "4. **市场：** TAM/SAM/SOM，为什么是现在\n"
                       "5. **商业模式：** 谁付钱，怎么赚钱\n"
                       "6. **团队：** 为什么是你们\n"
                       "7. **Ask：** 你需要什么资源/想达到什么目标\n\n"
                       "**时间分配：** 每幕1-2分钟，总计不超过10分钟",
            "stage": ["pitching"],
            "dims": ["pitching"],
            "rubrics": ["R9"],
            "tags": ["路演", "PPT", "叙事结构"],
        },
        {
            "title": "单位经济模型模板",
            "summary": "验证商业模式可持续性的核心计算模板",
            "content": "**关键指标：**\n\n"
                       "| 指标 | 公式 | 健康标准 |\n"
                       "|------|------|----------|\n"
                       "| CAC | 总获客成本/新客数 | 越低越好 |\n"
                       "| LTV | ARPU × 平均留存月数 | LTV/CAC > 3 |\n"
                       "| 毛利率 | (收入-直接成本)/收入 | > 50% |\n"
                       "| 回收期 | CAC/月均收入 | < 12个月 |\n\n"
                       "**验证顺序：** 先验证有人付费(PMF) → 再算单位经济 → 最后做增长",
            "stage": ["modeling"],
            "dims": ["business"],
            "rubrics": ["R6"],
            "tags": ["财务", "单位经济", "LTV", "CAC"],
        },
        {
            "title": "竞品对比矩阵模板",
            "summary": "系统化的竞品分析框架",
            "content": "**对比维度建议：**\n\n"
                       "| 维度 | 我们 | 竞品A | 竞品B | 替代方案 |\n"
                       "|------|------|-------|-------|----------|\n"
                       "| 核心功能 | | | | |\n"
                       "| 价格 | | | | |\n"
                       "| 目标用户 | | | | |\n"
                       "| 技术方案 | | | | |\n"
                       "| 获客渠道 | | | | |\n\n"
                       "**注意：** '替代方案'列很重要——用户在你出现之前怎么解决的？"
                       "Excel、微信群、线下方式都是你的竞争对手。",
            "stage": ["ideation", "modeling"],
            "dims": ["ideation", "business"],
            "rubrics": ["R5", "R7"],
            "tags": ["竞品分析", "对比矩阵", "差异化"],
        },
        {
            "title": "用户访谈记录模板",
            "summary": "结构化的用户访谈记录框架",
            "content": "**访谈记录表：**\n\n"
                       "- **受访者：** [姓名/编号] | [年龄/职业] | [是否陌生人]\n"
                       "- **场景：** [在什么场景下遇到问题]\n"
                       "- **痛点描述：** [用户原话]\n"
                       "- **现有解决方案：** [用户目前怎么解决]\n"
                       "- **付费意愿：** [是否愿意付费/付多少]\n"
                       "- **关键引用：** [最有价值的一句话]\n\n"
                       "**黄金规则：** 问行为不问意见，问过去不问未来",
            "stage": ["discovery"],
            "dims": ["empathy"],
            "rubrics": ["R1", "R2"],
            "tags": ["用户访谈", "调研", "The Mom Test"],
        },
    ]

    for t in templates:
        card_id = _make_id("template", t["title"])
        card = KnowledgeCard(
            card_id=card_id,
            card_type="template",
            title=t["title"],
            summary=t["summary"],
            content=t["content"],
            stage=t["stage"],
            dimensions=t["dims"],
            rubrics=t["rubrics"],
            tags=t.get("tags", []),
            fields={},
            source="built_in_template",
        )
        _cards[card_id] = card
        stats["template"] += 1


# ── 检索引擎 ──────────────────────────────────────────────────

def search_cards(
    query: str = "",
    card_type: str = "",
    stage: str = "",
    dimension: str = "",
    rubric: str = "",
    industry: str = "",
    max_results: int = 10,
) -> list[dict]:
    """
    两层检索：先按字段过滤 → 再 TF-IDF 相关度排序。

    参数可组合，空字符串表示不过滤。
    """
    _load_cards()
    candidates = list(_cards.values())

    # Layer 1: 字段过滤
    if card_type:
        candidates = [c for c in candidates if c.card_type == card_type]
    if stage:
        candidates = [c for c in candidates if stage in c.stage]
    if dimension:
        candidates = [c for c in candidates if dimension in c.dimensions]
    if rubric:
        candidates = [c for c in candidates if rubric in c.rubrics]
    if industry:
        candidates = [c for c in candidates
                      if c.industry == industry or not c.industry]

    if not query:
        return [c.to_dict() for c in candidates[:max_results]]

    # Layer 2: 关键词相关度排序
    scored: list[tuple[float, KnowledgeCard]] = []
    query_lower = query.lower()
    query_chars = set(query_lower)

    for card in candidates:
        score = 0.0
        text = f"{card.title} {card.summary} {' '.join(card.tags)}".lower()

        # 完整匹配
        if query_lower in text:
            score += 3.0
        # 标题匹配
        if query_lower in card.title.lower():
            score += 5.0
        # 标签匹配
        for tag in card.tags:
            if query_lower in tag.lower() or tag.lower() in query_lower:
                score += 2.0
        # 字符重叠（中文 bigram 粗略匹配）
        text_chars = set(text)
        overlap = len(query_chars & text_chars) / max(len(query_chars), 1)
        score += overlap * 1.5
        # 内容匹配（低权重）
        if query_lower in card.content.lower():
            score += 1.0

        if score > 0:
            scored.append((score, card))

    scored.sort(key=lambda x: -x[0])
    return [c.to_dict() for _, c in scored[:max_results]]


def get_cards_for_rubric_gap(rubric_id: str, dimension: str = "") -> list[dict]:
    """
    为特定 Rubric 缺口推荐卡片：
    1. 该 Rubric 的 mistake 卡片（常见错误）
    2. 该 Rubric 的 method 卡片（修复策略）
    3. 该 Rubric 的 concept 卡片（相关概念）
    4. 该 Rubric 的 template 卡片（可用模板）
    """
    _load_cards()
    results = []
    for card in _cards.values():
        if rubric_id in card.rubrics:
            results.append(card.to_dict())
        elif dimension and dimension in card.dimensions:
            results.append(card.to_dict())

    # 按类型排序：mistake → method → concept → template → case
    type_order = {"mistake": 0, "method": 1, "concept": 2, "template": 3, "case": 4}
    results.sort(key=lambda c: type_order.get(c["card_type"], 5))
    return results[:8]


def format_cards_for_prompt(cards: list[dict], max_cards: int = 3) -> str:
    """将卡片格式化为 LLM prompt 注入块。"""
    if not cards:
        return ""

    lines = ["[知识卡片参考 — 结构化知识单元]"]
    for i, card in enumerate(cards[:max_cards], 1):
        card_type_label = {
            "concept": "概念", "method": "方法", "case": "案例",
            "mistake": "常见错误", "template": "模板",
        }.get(card["card_type"], "知识")

        lines.append(f"\n📋 卡片{i}【{card_type_label}】{card['title']}")
        lines.append(f"   {card['summary']}")
        # 内容精简
        content_preview = card["content"][:200]
        if len(card["content"]) > 200:
            content_preview += "..."
        lines.append(f"   {content_preview}")
        if card.get("tags"):
            lines.append(f"   标签：{'、'.join(card['tags'][:5])}")

    lines.append("\n请在回复中自然引用上述知识卡片的内容，帮助学生理解和应用。")
    return "\n".join(lines)
