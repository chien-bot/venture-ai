"""
hypergraph/semantic_retriever.py
────────────────────────────────────────────────────────────────
语义检索引擎 — 基于 TF-IDF 向量索引

替代 retriever.py 中的硬编码关键词匹配，实现：
1. 对超图 Project 节点建立 TF-IDF 向量索引
2. 给定用户输入文本，用余弦相似度检索最相关的项目/案例
3. 支持按行业、技术过滤

优势：
- 不依赖固定关键词表，能匹配同义词和近义表述
- "帮老人看病的APP" 可以匹配到 "医疗健康" 行业的项目
- 无需额外安装 embedding 模型，用 sklearn 即可
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import NamedTuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

# ── Data path ────────────────────────────────────────────────
_DATA_PATH = Path(__file__).parent.parent / "data" / "hypergraph_data.json"

# ── Index state ──────────────────────────────────────────────
_vectorizer: TfidfVectorizer | None = None
_tfidf_matrix = None
_project_docs: list[dict] = []       # [{id, label, industry, text, ...}]
_all_node_docs: list[dict] = []      # [{id, type, label, text}]
_node_vectorizer: TfidfVectorizer | None = None
_node_tfidf_matrix = None


# ── Chinese tokenization helper ──────────────────────────────
def _simple_tokenize(text: str) -> str:
    """
    简单中文分词：按字符 bigram + 保留英文单词。
    不依赖 jieba，对关键词检索已够用。
    """
    tokens = []
    # 提取英文单词和数字
    eng_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_\-]+", text)
    tokens.extend(t.lower() for t in eng_tokens)

    # 中文 bigram
    chinese = re.sub(r"[A-Za-z0-9_\-\s]+", "", text)
    for i in range(len(chinese) - 1):
        tokens.append(chinese[i : i + 2])
    # 也保留单字（unigram）用于短词匹配
    for ch in chinese:
        if ch.strip():
            tokens.append(ch)

    return " ".join(tokens)


def _build_project_text(node: dict) -> str:
    """将 Project 节点的所有信息拼成一段可检索的文本。"""
    props = node.get("properties", {})
    parts = [
        node.get("label", ""),
        props.get("industry", ""),
        " ".join(props.get("technologies", [])),
        props.get("problem", ""),
        props.get("solution", ""),
        " ".join(props.get("biz_model", [])),
        " ".join(props.get("moat", [])),
        " ".join(props.get("success_factors", [])),
        " ".join(props.get("failure_risks", [])),
        props.get("market_size", ""),
        props.get("biz_detail", ""),
    ]
    return " ".join(p for p in parts if p)


def _build_node_text(node: dict) -> str:
    """将任意节点拼成可检索文本。"""
    props = node.get("properties", {})
    parts = [
        node.get("label", ""),
        node.get("type", ""),
        props.get("en", ""),
        props.get("industry", ""),
    ]
    # 对 Technology/Concept 等节点，label 本身就是核心信息
    return " ".join(p for p in parts if p)


# ── Build index ──────────────────────────────────────────────

def build_index():
    """从超图数据构建 TF-IDF 索引。启动时调用一次。"""
    global _vectorizer, _tfidf_matrix, _project_docs
    global _node_vectorizer, _node_tfidf_matrix, _all_node_docs

    if not _DATA_PATH.exists():
        logger.warning(f"Hypergraph data not found: {_DATA_PATH}")
        return

    with open(_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # ── Project index ──
    _project_docs.clear()
    project_texts = []
    for node in data["nodes"]:
        if node["type"] != "Project":
            continue
        text = _build_project_text(node)
        tokenized = _simple_tokenize(text)
        _project_docs.append({
            "id": node["id"],
            "label": node["label"],
            "industry": node.get("properties", {}).get("industry", ""),
            "technologies": node.get("properties", {}).get("technologies", []),
            "text": text,
        })
        project_texts.append(tokenized)

    if project_texts:
        _vectorizer = TfidfVectorizer(
            max_features=5000,
            sublinear_tf=True,
            min_df=1,
            max_df=0.95,
        )
        _tfidf_matrix = _vectorizer.fit_transform(project_texts)
        logger.info(f"Semantic index built: {len(_project_docs)} projects, "
                    f"{_tfidf_matrix.shape[1]} features")

    # ── All-node index (for industry/concept matching) ──
    _all_node_docs.clear()
    node_texts = []
    for node in data["nodes"]:
        text = _build_node_text(node)
        tokenized = _simple_tokenize(text)
        _all_node_docs.append({
            "id": node["id"],
            "type": node["type"],
            "label": node["label"],
            "text": text,
        })
        node_texts.append(tokenized)

    if node_texts:
        _node_vectorizer = TfidfVectorizer(
            max_features=3000,
            sublinear_tf=True,
            min_df=1,
            max_df=0.95,
        )
        _node_tfidf_matrix = _node_vectorizer.fit_transform(node_texts)


# Auto-build on import
build_index()


# ── Search functions ─────────────────────────────────────────

class SearchResult(NamedTuple):
    project_id: str
    label: str
    industry: str
    technologies: list
    score: float


def search_projects(
    query: str,
    top_k: int = 8,
    min_score: float = 0.05,
    industry_filter: str = "",
) -> list[SearchResult]:
    """
    语义搜索：给定查询文本，返回最相关的项目列表。

    Parameters
    ----------
    query : 用户输入（自然语言）
    top_k : 最多返回项目数
    min_score : 最低相似度阈值
    industry_filter : 可选行业过滤

    Returns
    -------
    按相似度降序排列的 SearchResult 列表
    """
    if _vectorizer is None or _tfidf_matrix is None or not _project_docs:
        return []

    tokenized = _simple_tokenize(query)
    query_vec = _vectorizer.transform([tokenized])
    scores = cosine_similarity(query_vec, _tfidf_matrix).flatten()

    # 按分数排序
    ranked = np.argsort(scores)[::-1]

    results = []
    for idx in ranked:
        score = float(scores[idx])
        if score < min_score:
            break
        doc = _project_docs[idx]
        # 行业过滤
        if industry_filter and doc["industry"] != industry_filter:
            continue
        results.append(SearchResult(
            project_id=doc["id"],
            label=doc["label"],
            industry=doc["industry"],
            technologies=doc["technologies"],
            score=round(score, 4),
        ))
        if len(results) >= top_k:
            break

    return results


def detect_industry(query: str, top_n: int = 1) -> list[str]:
    """
    语义检测用户输入对应的行业。

    使用同义词扩展 + TF-IDF 双重匹配：
    - "帮老人看病" → "医疗健康"
    - "田里种菜" → "农业发展"
    - "教小朋友编程" → "教育教学"
    """
    # 策略1: 同义词扩展匹配（覆盖常见自然语言表述）
    _INDUSTRY_SYNONYMS = {
        "医疗健康": [
            "医疗", "健康", "医学", "诊断", "手术", "药物", "医院", "病人",
            "看病", "挂号", "体检", "护理", "康复", "疾病", "患者", "临床",
            "中医", "脉诊", "眼底", "脑瘤", "CT", "MRI", "超声", "内窥",
            "老人", "养老", "残疾", "心理", "基因", "细胞",
        ],
        "工业制造": [
            "工业", "制造", "工厂", "产线", "巡检", "焊接", "天线", "脱硫",
            "质检", "缺陷检测", "产品质量", "车间", "自动化", "流水线",
            "钢铁", "化工", "零件", "装配",
        ],
        "交通运输": [
            "交通", "运输", "驾驶", "飞行", "航行", "低空", "充电桩",
            "出行", "打车", "物流", "快递", "送货", "配送", "货运",
            "公交", "地铁", "高铁", "航空", "港口", "停车",
        ],
        "农业发展": [
            "农业", "种植", "养殖", "除草", "农药", "灌溉", "农村",
            "种菜", "水果", "畜牧", "渔业", "害虫", "施肥", "土壤",
            "温室", "大棚", "田", "地", "庄稼", "粮食", "牧场",
        ],
        "环境保护": [
            "环保", "碳", "CO2", "生态", "湿地", "水质", "污染", "火灾",
            "垃圾", "回收", "分类", "废物", "排放", "节能", "新能源",
            "太阳能", "风能", "光伏", "清洁", "绿色",
        ],
        "教育教学": [
            "教育", "教学", "学生", "课堂", "实验", "学习", "培训",
            "编程", "学校", "老师", "考试", "作业", "辅导", "教材",
            "在线教育", "网课", "题库", "评估", "幼儿", "小朋友",
        ],
        "政务管理": [
            "政务", "新闻", "舆情", "风控", "安全", "防控",
            "政府", "社区", "城市", "管理", "监管", "公共",
        ],
        "文化旅游": [
            "文化", "旅游", "非遗", "入境游", "文旅",
            "景区", "酒店", "民宿", "导游", "博物馆", "展览",
        ],
    }
    query_lower = query.lower()
    synonym_scores = {}
    for industry, synonyms in _INDUSTRY_SYNONYMS.items():
        score = sum(1 for s in synonyms if s in query_lower)
        if score > 0:
            synonym_scores[industry] = score

    if synonym_scores:
        sorted_industries = sorted(synonym_scores, key=synonym_scores.get, reverse=True)
        return sorted_industries[:top_n]

    # 策略2: TF-IDF 向量匹配（fallback）
    if _node_vectorizer is None or _node_tfidf_matrix is None:
        return []

    tokenized = _simple_tokenize(query)
    query_vec = _node_vectorizer.transform([tokenized])
    scores = cosine_similarity(query_vec, _node_tfidf_matrix).flatten()

    market_scores = []
    for i, doc in enumerate(_all_node_docs):
        if doc["type"] == "Market":
            market_scores.append((doc["label"], float(scores[i])))

    market_scores.sort(key=lambda x: -x[1])
    return [label for label, score in market_scores[:top_n] if score > 0.01]


def detect_concepts(query: str, top_n: int = 3) -> list[str]:
    """
    语义检测用户提到的创业概念。

    比硬编码更灵活：
    - "怎么知道产品有没有市场" → "PMF"
    - "获取用户的成本" → "CAC"
    """
    if _node_vectorizer is None or _node_tfidf_matrix is None:
        return []

    tokenized = _simple_tokenize(query)
    query_vec = _node_vectorizer.transform([tokenized])
    scores = cosine_similarity(query_vec, _node_tfidf_matrix).flatten()

    concept_scores = []
    for i, doc in enumerate(_all_node_docs):
        if doc["type"] == "Concept":
            concept_scores.append((doc["label"], float(scores[i])))

    concept_scores.sort(key=lambda x: -x[1])
    return [label for label, score in concept_scores[:top_n] if score > 0.02]


def detect_technologies(query: str, top_n: int = 5) -> list[str]:
    """
    语义检测用户提到的技术关键词。

    比硬编码更灵活：
    - "用摄像头识别人脸" → ["计算机视觉", "人脸识别", "目标检测"]
    - "训练一个聊天机器人" → ["NLP", "LLM", "大模型"]
    """
    if _node_vectorizer is None or _node_tfidf_matrix is None:
        return []

    tokenized = _simple_tokenize(query)
    query_vec = _node_vectorizer.transform([tokenized])
    scores = cosine_similarity(query_vec, _node_tfidf_matrix).flatten()

    tech_scores = []
    for i, doc in enumerate(_all_node_docs):
        if doc["type"] in ("Technology", "SubTechnology"):
            tech_scores.append((doc["label"], float(scores[i])))

    tech_scores.sort(key=lambda x: -x[1])
    return [label for label, score in tech_scores[:top_n] if score > 0.02]
