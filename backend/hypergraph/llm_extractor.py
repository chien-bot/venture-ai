"""
hypergraph/llm_extractor.py
────────────────────────────────────────────────────────────────
LLM 语义提取器 — 用轻量模型从学生消息中提取结构化信息

替代 retriever.py 中的硬编码关键词表，能理解自然语言：
  - "帮老人看病的APP" → industry="医疗健康", techs=["移动应用"]
  - "用摄像头识别垃圾分类" → techs=["计算机视觉","目标检测"], industry="环境保护"
  - "我不太懂什么叫产品市场匹配" → concept="PMF"

使用 MODEL_LIGHT（Qwen 7B）做提取，单次调用 ~0.5s，不会明显增加延迟。
"""
from __future__ import annotations

import json
import logging
from config import USE_MOCK_API

logger = logging.getLogger(__name__)

_EXTRACT_SYSTEM_PROMPT = """你是一个信息提取器。从用户的创业讨论消息中提取以下结构化信息。

只输出 JSON，不要有任何其他内容。格式：
{"techs": ["技术1", "技术2"], "industry": "行业名", "concept": "概念名", "project_desc": "一句话项目描述"}

规则：
- techs: 提取提到的技术/方法（如 AI、深度学习、YOLO、区块链、物联网、大数据等）。如果没有明确提到，推断可能用到的技术。最多5个。
- industry: 从以下行业中选一个最匹配的：医疗健康、工业制造、交通运输、农业发展、环境保护、教育教学、政务管理、文化旅游、通用。如果不明确，输出"通用"。
- concept: 如果用户在询问创业概念，提取概念名（如 PMF、TAM、LTV、CAC、护城河、精益画布等）。如果没有，输出空字符串。
- project_desc: 用一句话概括用户的项目/想法。如果用户不是在讨论项目，输出空字符串。

示例输入："我想做一个帮助社区老人预约挂号的小程序"
示例输出：{"techs": ["移动应用", "小程序"], "industry": "医疗健康", "concept": "", "project_desc": "社区老人预约挂号小程序"}

示例输入："我不太懂什么叫产品市场契合"
示例输出：{"techs": [], "industry": "通用", "concept": "PMF", "project_desc": ""}

示例输入："我们用YOLO做农田里的害虫识别"
示例输出：{"techs": ["YOLO", "目标检测", "计算机视觉", "深度学习"], "industry": "农业发展", "concept": "", "project_desc": "基于YOLO的农田害虫识别系统"}
"""


def extract_from_message(message: str) -> dict:
    """
    用 LLM 从学生消息中提取技术/行业/概念信息。

    Returns
    -------
    {
        "techs": list[str],
        "industry": str,
        "concept": str,
        "project_desc": str,
    }
    """
    if USE_MOCK_API:
        return _fallback_extract(message)

    try:
        from services.claude_client import chat_completion
        from config import MODEL_LIGHT

        response = chat_completion(
            _EXTRACT_SYSTEM_PROMPT,
            [{"role": "user", "content": message}],
            model=MODEL_LIGHT,
            max_tokens=256,
        )

        # 尝试解析 JSON
        response = response.strip()
        # 处理可能的 markdown 代码块包裹
        if response.startswith("```"):
            response = response.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        result = json.loads(response)
        # 确保字段存在
        return {
            "techs": result.get("techs", []),
            "industry": result.get("industry", "通用"),
            "concept": result.get("concept", ""),
            "project_desc": result.get("project_desc", ""),
        }
    except Exception as e:
        logger.warning(f"LLM extraction failed, falling back to keyword: {e}")
        return _fallback_extract(message)


def _fallback_extract(message: str) -> dict:
    """
    当 LLM 不可用时的 fallback，使用 semantic_retriever 的检测功能。
    """
    from hypergraph.semantic_retriever import (
        detect_technologies,
        detect_industry,
        detect_concepts,
    )

    techs = detect_technologies(message, top_n=5)
    industries = detect_industry(message, top_n=1)
    concepts = detect_concepts(message, top_n=1)

    return {
        "techs": techs,
        "industry": industries[0] if industries else "通用",
        "concept": concepts[0] if concepts else "",
        "project_desc": "",
    }


def extract_from_conversation(
    messages: list[dict],
    current_message: str,
    window: int = 5,
) -> dict:
    """
    从对话上下文中提取信息。合并最近 N 轮用户消息 + 当前消息。

    两层策略：
    1. 对当前消息做 LLM 提取（精确）
    2. 对历史消息做 TF-IDF 语义检测（快速，无 LLM 调用）
    3. 合并去重

    Returns
    -------
    同 extract_from_message 的格式，但信息更全面
    """
    # 1. LLM 提取当前消息
    current_result = extract_from_message(current_message)

    # 2. TF-IDF 提取历史上下文
    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    recent = user_msgs[-window:]
    history_text = " ".join(recent) if recent else ""

    if history_text:
        history_result = _fallback_extract(history_text)

        # 合并 techs（去重，当前消息优先，大小写不敏感）
        seen = set()
        all_techs = []
        for t in list(current_result["techs"]) + history_result["techs"]:
            key = t.lower().strip()
            if key and key not in seen:
                seen.add(key)
                all_techs.append(t)
        current_result["techs"] = all_techs[:8]  # 最多 8 个

        # industry: 如果当前消息没检测到，用历史的
        if current_result["industry"] == "通用" and history_result["industry"] != "通用":
            current_result["industry"] = history_result["industry"]

        # concept: 当前消息优先
        if not current_result["concept"] and history_result["concept"]:
            current_result["concept"] = history_result["concept"]

    return current_result
