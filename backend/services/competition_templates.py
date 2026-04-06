"""
services/competition_templates.py
────────────────────────────────────────────────────────────────
动态赛事模板服务 — 根据目标赛事切换 Rubric 权重与评价侧重

支持 A5-2：Competition-Specific Rubric Shift
"""
from __future__ import annotations

import json
from pathlib import Path

_TEMPLATES_PATH = Path(__file__).parent.parent / "data" / "rubric" / "competition_templates.json"

_templates: list[dict] = []


def _load():
    global _templates
    if not _templates:
        with open(_TEMPLATES_PATH, encoding="utf-8") as f:
            _templates = json.load(f)


def get_all_templates() -> list[dict]:
    _load()
    return _templates


def match_template(user_input: str) -> dict | None:
    """根据用户输入匹配最佳赛事模板。"""
    _load()
    user_lower = user_input.lower()
    for tpl in _templates:
        for alias in tpl["aliases"]:
            if alias.lower() in user_lower:
                return tpl
    return None


def get_template_by_id(template_id: str) -> dict | None:
    _load()
    for tpl in _templates:
        if tpl["template_id"] == template_id:
            return tpl
    return None


def format_template_for_prompt(template: dict) -> str:
    """将赛事模板格式化为注入 prompt 的文本块。"""
    lines = [
        f"[动态赛事评估模板 — {template['name']}]",
        f"赛事特点：{template['description']}",
        "",
        "评分权重分配（按重要性排序）：",
    ]
    sorted_weights = sorted(
        template["rubric_weights"].items(),
        key=lambda x: x[1],
        reverse=True,
    )
    for rubric_id, weight in sorted_weights:
        lines.append(f"  {rubric_id}: {weight:.0%}")

    lines.append("")
    lines.append("本赛事重点关注领域：")
    for area in template["focus_areas"]:
        lines.append(f"  - {area}")

    lines.append("")
    lines.append("评审侧重说明：")
    lines.append(template["evaluation_emphasis"])

    lines.append("")
    lines.append("重点扣分规则（本赛事高权重触发）：")
    lines.append(f"  {', '.join(template['key_deduction_rules'])}")

    return "\n".join(lines)
