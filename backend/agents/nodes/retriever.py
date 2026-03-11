"""
agents/nodes/retriever.py
────────────────────────────────────────────────────────────────
超图检索节点 (Retriever Node)

在 LangGraph 流程中，这个节点在 router 之后、coach/tutor/competition 之前运行。
它的职责是：
1. 从学生的对话中提取关键词（技术、行业、概念）
2. 用这些关键词查询超图引擎
3. 将检索结果注入 AgentState，供后续节点使用

这实现了 RAG（检索增强生成）的 "R" 部分：
  学生输入 → 关键词提取 → 超图检索 → 上下文注入 → LLM 生成
"""
from __future__ import annotations

import re
from agents.state import AgentState
from hypergraph.engine import query_hypergraph, format_context_for_prompt

# ── 技术关键词词表（用于从学生消息中提取） ──────────────────
_TECH_KEYWORDS = [
    # 一级技术
    "AI", "人工智能", "深度学习", "机器学习", "神经网络", "计算机视觉", "NLP",
    "自然语言处理", "大模型", "知识图谱", "数字孪生", "物联网", "IoT", "5G",
    "边缘计算", "云计算", "区块链", "强化学习", "大数据", "信号处理",
    # 子技术 — 深度学习
    "CNN", "RNN", "LSTM", "GAN", "ResNet", "UNet", "VAE", "DenseNet", "MobileNet",
    "EfficientNet", "VGG", "Inception", "AutoEncoder",
    # 子技术 — 视觉
    "YOLO", "Faster R-CNN", "SSD", "ViT", "Mask R-CNN", "DeepLab", "RetinaNet",
    "目标检测", "图像识别", "图像分割", "语义分割", "实例分割", "OCR", "人脸识别",
    # 子技术 — NLP
    "Transformer", "BERT", "GPT", "RoBERTa", "ERNIE", "T5", "Word2Vec",
    "命名实体识别", "情感分析", "文本分类", "seq2seq",
    # 子技术 — RL
    "DQN", "PPO", "SAC", "DDPG", "A3C", "Q-Learning", "Actor-Critic",
    # 子技术 — 大模型
    "LLM", "ChatGPT", "LLaMA", "LoRA", "RAG", "Fine-tuning", "RLHF",
    "Prompt Engineering", "Chain-of-Thought",
    # 子技术 — 传统ML
    "SVM", "随机森林", "XGBoost", "LightGBM", "决策树", "KNN", "K-Means", "PCA",
    "DBSCAN", "t-SNE",
    # 方法
    "SLAM", "三维重建", "多模态", "数据融合", "迁移学习", "联邦学习",
    "知识蒸馏", "模型压缩", "对比学习", "图神经网络", "点云处理", "AIGC",
    "数据挖掘", "数据湖", "图计算", "GNN", "语音识别", "扩散模型",
    # 硬件
    "激光雷达", "LiDAR", "机器人", "无人机", "传感器", "芯片", "FPGA", "嵌入式",
    "Jetson", "GPU", "TPU",
    # 框架
    "PyTorch", "TensorFlow", "OpenCV", "Spark", "Hadoop", "Docker", "Kubernetes",
    "LangChain", "HuggingFace",
    # 其他
    "AR", "VR", "MR", "元宇宙", "3D打印", "碳中和", "新能源", "氢能", "光伏",
    "超声", "红外", "光纤", "拉曼", "内窥镜", "光学", "自动驾驶",
]

_INDUSTRY_KEYWORDS = {
    "医疗健康": ["医疗", "健康", "医学", "诊断", "手术", "药物", "医院", "病人",
                "CT", "MRI", "超声", "内窥", "脉诊", "眼底", "脑瘤"],
    "工业制造": ["工业", "制造", "工厂", "产线", "巡检", "焊接", "天线", "脱硫"],
    "交通运输": ["交通", "运输", "驾驶", "飞行", "航行", "低空", "充电桩"],
    "农业发展": ["农业", "种植", "养殖", "除草", "农药", "灌溉", "农村"],
    "环境保护": ["环保", "碳", "CO2", "生态", "湿地", "水质", "污染", "火灾"],
    "教育教学": ["教育", "教学", "学生", "课堂", "实验", "学习", "培训"],
    "政务管理": ["政务", "新闻", "舆情", "风控", "安全", "防控"],
    "文化旅游": ["文化", "旅游", "非遗", "入境游", "文旅"],
}

_CONCEPT_KEYWORDS = {
    "PMF": ["PMF", "产品市场契合", "市场匹配"],
    "TAM": ["TAM", "SAM", "SOM", "市场规模", "总市场"],
    "价值主张": ["价值主张", "价值", "用户价值"],
    "护城河": ["护城河", "壁垒", "竞争优势", "门槛"],
    "精益画布": ["精益画布", "Lean Canvas", "画布"],
    "JTBD": ["JTBD", "待办任务", "待完成的工作"],
    "SWOT": ["SWOT", "优势劣势"],
    "CAC": ["CAC", "获客成本"],
    "LTV": ["LTV", "终身价值", "用户价值"],
    "BEP": ["BEP", "盈亏平衡", "收支平衡"],
    "MVP": ["MVP", "最小可行", "原型"],
    "定价": ["定价", "价格", "收费"],
    "AARRR": ["AARRR", "海盗指标", "增长漏斗"],
}


def _extract_tech_keywords(text: str) -> list[str]:
    """Extract technology keywords from text."""
    found = []
    text_lower = text.lower()
    for kw in _TECH_KEYWORDS:
        if kw.lower() in text_lower:
            found.append(kw)
    return list(set(found))


def _extract_industry(text: str) -> str:
    """Detect industry from text."""
    text_lower = text.lower()
    scores = {}
    for industry, keywords in _INDUSTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[industry] = score
    if scores:
        return max(scores, key=scores.get)
    return ""


def _extract_concept(text: str) -> str:
    """Detect which entrepreneurship concept is being discussed."""
    text_lower = text.lower()
    for concept, keywords in _CONCEPT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return concept
    return ""


def retriever_node(state: AgentState) -> AgentState:
    """
    超图检索节点。

    从对话历史中提取关键词，查询超图，将结果存入 state。
    后续的 coach/tutor/competition 节点可以直接使用 state["hypergraph_context"]。
    """
    messages = state.get("messages", [])
    current = state.get("current_message", "")

    # 合并最近的用户消息（最近5条 + 当前消息）
    recent_user_text = current
    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    recent_user_text += " " + " ".join(user_msgs[-5:])

    # 提取关键词
    tech_kws = _extract_tech_keywords(recent_user_text)
    industry = _extract_industry(recent_user_text)
    concept = _extract_concept(recent_user_text)

    # 查询超图
    ctx = query_hypergraph(
        tech_keywords=tech_kws if tech_kws else None,
        industry=industry,
        concept=concept,
    )

    # 格式化为可注入 prompt 的文本
    context_text = format_context_for_prompt(ctx)

    return {
        **state,
        "hypergraph_context": context_text,
        "extracted_techs": tech_kws,
        "extracted_industry": industry,
        "extracted_concept": concept,
    }
