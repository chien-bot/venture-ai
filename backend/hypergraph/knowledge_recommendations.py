"""
hypergraph/knowledge_recommendations.py
────────────────────────────────────────────────────────────────
学习路径推荐 — 超图规则触发 → 推荐对应知识概念

当 critic_node 检测到 H1-H15 规则触发时，
系统可推荐学生主动学习对应概念，并自动跳转到 Tutor 节点。
"""
from __future__ import annotations

# H规则 → 推荐概念映射
H_RULE_TO_CONCEPT: dict[str, dict] = {
    "H1":  {"concept": "价值主张画布",    "query": "什么是价值主张画布，如何用它对齐客户需求和产品功能？"},
    "H2":  {"concept": "渠道策略与GTM",   "query": "如何选择和验证用户获取渠道？什么是Go-To-Market策略？"},
    "H3":  {"concept": "支付意愿测试",    "query": "如何通过预售和访谈验证用户真实的支付意愿？"},
    "H4":  {"concept": "TAM/SAM/SOM",    "query": "如何自下而上估算市场规模TAM、SAM、SOM？"},
    "H5":  {"concept": "用户访谈方法",    "query": "如何设计和执行高质量的用户访谈？有哪些常见错误？"},
    "H6":  {"concept": "竞品分析矩阵",    "query": "如何系统做竞品对比分析？竞品分析矩阵怎么建？"},
    "H7":  {"concept": "护城河理论",      "query": "什么是护城河？创业公司如何建立和量化差异化优势？"},
    "H8":  {"concept": "单位经济模型",    "query": "如何计算LTV、CAC，单位经济模型怎么验证？"},
    "H9":  {"concept": "增长黑客框架",    "query": "什么是AARRR增长漏斗？如何设计增长策略？"},
    "H10": {"concept": "SMART里程碑",     "query": "如何制定SMART里程碑计划？项目阶段如何划分？"},
    "H11": {"concept": "合规与伦理风险",  "query": "数据隐私和行业合规如何评估？哪些行业有特殊监管？"},
    "H12": {"concept": "技术可行性评估",  "query": "如何评估技术路线与团队能力的匹配度？"},
    "H13": {"concept": "实验设计方法",    "query": "如何设计有效的A/B测试和最小化验证实验？"},
    "H14": {"concept": "路演叙事结构",    "query": "如何构建完整的路演故事线？7幕叙事结构是什么？"},
    "H15": {"concept": "证据链构建",      "query": "如何为每个评分维度构建完整的证据材料？"},
}


def get_recommendations(triggered_rule_ids: list[str]) -> list[dict]:
    """
    Given a list of triggered H-rule IDs, return up to 3 concept recommendations.
    Each recommendation: {rule_id, concept, query}
    """
    recs = []
    seen: set[str] = set()
    for rid in triggered_rule_ids:
        if rid in H_RULE_TO_CONCEPT and rid not in seen:
            recs.append({"rule_id": rid, **H_RULE_TO_CONCEPT[rid]})
            seen.add(rid)
        if len(recs) >= 3:
            break
    return recs
