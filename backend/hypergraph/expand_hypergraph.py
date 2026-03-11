"""
expand_hypergraph.py
────────────────────────────────────────────────────────────────
从现有 82 个竞赛项目中深度挖掘，将超图从 ~196 节点扩展到 800+。

用法：
    cd backend && python3 hypergraph/expand_hypergraph.py

数据源：
    1. data/hypergraph_data.json         — 现有超图
    2. /private/tmp/venture-data/extracted_entities.json
    3. /private/tmp/venture-data/enriched_top15.json
    4. /private/tmp/venture-data/all_texts.json
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────
_BACKEND = Path(__file__).parent.parent
_HG_PATH = _BACKEND / "data" / "hypergraph_data.json"
_VENTURE = Path("/private/tmp/venture-data")
_ENTITIES_PATH = _VENTURE / "extracted_entities.json"
_ENRICHED_PATH = _VENTURE / "enriched_top15.json"
_TEXTS_PATH = _VENTURE / "all_texts.json"

# ── Constants ────────────────────────────────────────────────────────

TECH_HIERARCHY: dict[str, list[str]] = {
    "深度学习": ["CNN", "RNN", "LSTM", "GAN", "ResNet", "UNet", "VAE", "AutoEncoder", "DenseNet", "MobileNet",
                "EfficientNet", "VGG", "AlexNet", "Inception", "SqueezeNet", "ShuffleNet"],
    "计算机视觉": ["YOLO", "Faster R-CNN", "SSD", "ViT", "目标检测", "图像分割", "语义分割", "实例分割", "OCR",
                 "全景分割", "光流", "深度估计", "人脸识别", "人体姿态", "RetinaNet", "Mask R-CNN", "DeepLab"],
    "自然语言处理": ["BERT", "GPT", "Transformer", "Word2Vec", "TF-IDF", "命名实体识别", "情感分析", "文本分类",
                  "seq2seq", "attention", "词向量", "预训练", "微调", "RoBERTa", "ERNIE", "T5"],
    "强化学习": ["DQN", "PPO", "SAC", "DDPG", "A3C", "Q-Learning", "MCTS", "Actor-Critic", "TD3"],
    "大模型": ["LLM", "ChatGPT", "LLaMA", "通义千问", "文心一言", "LoRA", "RAG", "Fine-tuning", "Prompt Engineering",
             "RLHF", "InstructGPT", "Chain-of-Thought", "Agent"],
    "机器学习": ["SVM", "随机森林", "XGBoost", "LightGBM", "决策树", "KNN", "聚类", "K-Means", "PCA", "降维",
              "逻辑回归", "朴素贝叶斯", "梯度提升", "DBSCAN", "GMM", "t-SNE", "UMAP", "交叉验证"],
    "知识图谱": ["Neo4j", "图数据库", "实体关系抽取", "知识推理", "本体", "RDF", "SPARQL", "知识融合"],
    "大数据": ["Hadoop", "Spark", "Flink", "MapReduce", "Hive", "数据仓库", "ETL", "数据湖", "Kafka", "Storm"],
    "云计算": ["Docker", "Kubernetes", "微服务", "云原生", "Serverless", "容器", "负载均衡", "API网关"],
    "区块链": ["智能合约", "去中心化", "共识机制", "DApp", "NFT", "以太坊", "联盟链", "跨链"],
    "IoT": ["MQTT", "边缘计算", "传感器网络", "LoRa", "ZigBee", "5G", "NB-IoT", "数字孪生"],
    "信号处理": ["FFT", "小波变换", "滤波", "卷积", "频谱", "噪声抑制", "信号增强"],
    "优化算法": ["梯度下降", "Adam", "SGD", "牛顿法", "拉格朗日", "线性规划", "整数规划", "凸优化"],
    "数据库": ["MySQL", "PostgreSQL", "MongoDB", "Redis", "SQLite", "ElasticSearch", "向量数据库", "Milvus"],
}

FRAMEWORK_PATTERNS: list[str] = [
    "PyTorch", "TensorFlow", "Keras", "OpenCV", "ROS", "Spark",
    "Hadoop", "Flink", "Docker", "Kubernetes", "LangChain",
    "HuggingFace", "Scikit-learn", "Pandas", "Unity", "Unreal",
    "Flask", "FastAPI", "Spring", "Vue", "React", "WeChat",
]

DOMAIN_PATTERNS: dict[str, str] = {
    "眼科":       r"眼[底科]|视网膜|青光眼|白内障|眼部",
    "脑科学":     r"脑[瘤肿]|脑部|神经影像|脑机接口|EEG|脑电",
    "心血管":     r"心[脏血电]|心律|ECG|心电",
    "呼吸系统":   r"呼吸|肺[部炎]|呼吸道",
    "医学影像":   r"CT|MRI|X射线|超声[波检]|内窥镜|医学影像",
    "智能农业":   r"智[慧能]农|精准农业|作物|农田|植[保物]|除草|灌溉",
    "水产养殖":   r"水产|养殖|渔业|鱼[类塘]",
    "无人驾驶":   r"无人驾驶|自动驾驶|车路协同|V2X|智能[网驾]",
    "低空经济":   r"低空|无人机|UAV|飞行器|空域",
    "卫星遥感":   r"卫星|遥感|SAR|高光谱|地球观测",
    "水下探测":   r"水下|深海|海洋[探监]|AUV|ROV|潜航",
    "新能源":     r"新能源|光伏|风[电力]|储能|充电[桩站]|锂电",
    "半导体":     r"半导体|芯片|集成电路|FPGA|SoC|光刻",
    "3D打印":     r"3D打印|增材制造|激光烧结",
    "数字孪生":   r"数字孪生|仿真|虚拟[现仿]|数字化模型",
    "元宇宙":     r"元宇宙|虚拟现实|VR|AR|XR|混合现实|MR",
    "智慧城市":   r"智慧城市|城市[大治]|市政|交通管[理控]",
    "智慧教育":   r"智慧教育|在线[教学]|教育[大技]|自适应学习",
    "网络安全":   r"网络安全|信息安全|加密|隐私[计保]|安全[检防]",
    "文物保护":   r"文物|非遗|非物质文化|文化遗产|古建筑",
    "环境监测":   r"环[境保]|污[染水气]|碳[排中]|生态监测|空气质量",
    "供应链":     r"供应链|物流|仓储|冷链|配送",
    "金融科技":   r"金融[科大]|风控|信贷|征信|反欺诈|量化",
    "政务服务":   r"政务|电子政务|一网通办|政[府策]",
}

SOLUTION_PATTERNS: list[str] = [
    "目标检测", "图像识别", "语音识别", "路径规划", "数据融合",
    "特征提取", "模型压缩", "迁移学习", "联邦学习", "数据增强",
    "异常检测", "预测模型", "推荐系统", "自动标注", "知识蒸馏",
    "多模态融合", "对比学习", "自监督学习", "注意力机制", "图神经网络",
    "点云处理", "三维重建", "SLAM", "姿态估计", "光流估计",
    "信号处理", "频谱分析", "边缘检测", "风格迁移", "超分辨率",
    "文本生成", "机器翻译", "对话系统", "问答系统", "信息抽取",
    "时序预测", "回归分析", "分类模型", "概率图模型", "贝叶斯",
    "遗传算法", "粒子群优化", "模拟退火", "蚁群算法", "多目标优化",
    "强化学习策略", "模仿学习", "逆强化学习",
]

MODALITY_PATTERNS: list[str] = [
    "图像", "文本", "语音", "视频", "点云", "时序数据",
    "多模态", "3D", "光谱", "雷达信号", "红外", "深度图",
    "遥感影像", "医学影像", "卫星图像", "热成像",
]

EXTRA_CONCEPTS: list[dict] = [
    {"label": "精益创业", "en": "Lean Startup"},
    {"label": "最小可行产品", "en": "MVP"},
    {"label": "客户开发", "en": "Customer Development"},
    {"label": "增长黑客", "en": "Growth Hacking"},
    {"label": "单位经济学", "en": "Unit Economics"},
    {"label": "客户获取成本", "en": "CAC"},
    {"label": "客户终身价值", "en": "LTV"},
    {"label": "总可寻址市场", "en": "TAM"},
    {"label": "可服务市场", "en": "SAM"},
    {"label": "可获得市场", "en": "SOM"},
    {"label": "竞争分析", "en": "Competitive Analysis"},
    {"label": "差异化策略", "en": "Differentiation"},
    {"label": "网络效应", "en": "Network Effect"},
    {"label": "飞轮效应", "en": "Flywheel Effect"},
    {"label": "规模效应", "en": "Economies of Scale"},
    {"label": "平台战略", "en": "Platform Strategy"},
    {"label": "用户画像", "en": "User Persona"},
    {"label": "用户体验", "en": "UX"},
    {"label": "商业画布", "en": "Business Model Canvas"},
    {"label": "价值链分析", "en": "Value Chain Analysis"},
    {"label": "设计思维", "en": "Design Thinking"},
    {"label": "敏捷开发", "en": "Agile Development"},
    {"label": "技术路线图", "en": "Technology Roadmap"},
    {"label": "风险评估矩阵", "en": "Risk Matrix"},
    {"label": "退出策略", "en": "Exit Strategy"},
    {"label": "股权结构", "en": "Cap Table"},
    {"label": "融资策略", "en": "Fundraising"},
    {"label": "知识产权", "en": "IP Strategy"},
    {"label": "供应链管理", "en": "Supply Chain"},
    {"label": "品牌定位", "en": "Brand Positioning"},
    {"label": "定价策略", "en": "Pricing Strategy"},
    {"label": "渠道策略", "en": "Channel Strategy"},
    {"label": "数据驱动", "en": "Data-Driven"},
    {"label": "A/B测试", "en": "A/B Testing"},
    {"label": "转化漏斗", "en": "Conversion Funnel"},
    {"label": "留存分析", "en": "Retention Analysis"},
    {"label": "产品迭代", "en": "Product Iteration"},
    {"label": "需求分析", "en": "Requirements Analysis"},
    {"label": "可行性分析", "en": "Feasibility Study"},
    {"label": "盈利模式", "en": "Revenue Model"},
    {"label": "成本结构", "en": "Cost Structure"},
    {"label": "用户反馈", "en": "User Feedback"},
    {"label": "市场调研", "en": "Market Research"},
    {"label": "商业策略", "en": "Business Strategy"},
    {"label": "技术壁垒", "en": "Technical Barrier"},
    {"label": "专利布局", "en": "Patent Portfolio"},
    {"label": "产业链", "en": "Industry Chain"},
    {"label": "场景化", "en": "Scenario-based"},
    {"label": "落地应用", "en": "Deployment"},
    {"label": "技术创新", "en": "Tech Innovation"},
    {"label": "社会价值", "en": "Social Value"},
    {"label": "可持续发展", "en": "Sustainability"},
    {"label": "数据安全", "en": "Data Security"},
    {"label": "隐私保护", "en": "Privacy Protection"},
    {"label": "合规性", "en": "Compliance"},
    {"label": "标准化", "en": "Standardization"},
    {"label": "产学研", "en": "Industry-Academia"},
    {"label": "成果转化", "en": "Tech Transfer"},
    {"label": "原型设计", "en": "Prototyping"},
    {"label": "用户增长", "en": "User Growth"},
    {"label": "商业闭环", "en": "Business Loop"},
    {"label": "核心竞争力", "en": "Core Competence"},
    {"label": "战略合作", "en": "Strategic Partnership"},
    {"label": "市场验证", "en": "Market Validation"},
    {"label": "技术验证", "en": "Technical Validation"},
    {"label": "产品定位", "en": "Product Positioning"},
    {"label": "团队建设", "en": "Team Building"},
    {"label": "迭代优化", "en": "Iterative Optimization"},
    {"label": "用户调研", "en": "User Research"},
    {"label": "行业报告", "en": "Industry Report"},
    {"label": "财务预测", "en": "Financial Projection"},
]

EXTRA_RISK_PATTERNS: list[dict] = [
    {"label": "技术路线不清晰", "dimension": "技术", "severity": "medium"},
    {"label": "团队技术能力不足", "dimension": "团队", "severity": "high"},
    {"label": "市场窗口期过短", "dimension": "市场", "severity": "medium"},
    {"label": "数据获取困难", "dimension": "技术", "severity": "medium"},
    {"label": "用户粘性不足", "dimension": "产品", "severity": "high"},
    {"label": "政策监管风险", "dimension": "外部", "severity": "high"},
    {"label": "同质化竞争严重", "dimension": "市场", "severity": "medium"},
    {"label": "供应链依赖风险", "dimension": "运营", "severity": "medium"},
    {"label": "变现路径不明确", "dimension": "商业建模", "severity": "high"},
    {"label": "核心人才流失", "dimension": "团队", "severity": "high"},
    {"label": "知识产权纠纷", "dimension": "法务", "severity": "medium"},
    {"label": "技术债务累积", "dimension": "技术", "severity": "medium"},
    {"label": "融资节奏失控", "dimension": "财务", "severity": "high"},
    {"label": "产品体验差", "dimension": "产品", "severity": "medium"},
    {"label": "国际化障碍", "dimension": "市场", "severity": "low"},
]

HARDWARE_PATTERNS: list[str] = [
    "FPGA", "嵌入式", "SoC", "单片机", "树莓派", "Jetson",
    "传感器", "激光雷达", "LiDAR", "摄像头", "IMU",
    "GPU", "TPU", "NPU", "ASIC",
]

# ── Helpers ──────────────────────────────────────────────────────────

def _md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()[:8]


def _make_node(nid: str, ntype: str, label: str, props: dict | None = None) -> dict:
    return {"id": nid, "type": ntype, "label": label, "properties": props or {}}


def _make_edge(eid: str, etype: str, nodes: list[str], props: dict | None = None) -> dict:
    return {"id": eid, "type": etype, "nodes": nodes, "properties": props or {}}


# ── Load Data ────────────────────────────────────────────────────────

def load_sources():
    with open(_HG_PATH, encoding="utf-8") as f:
        hg = json.load(f)
    with open(_ENTITIES_PATH, encoding="utf-8") as f:
        entities = json.load(f)
    with open(_ENRICHED_PATH, encoding="utf-8") as f:
        enriched = json.load(f)
    with open(_TEXTS_PATH, encoding="utf-8") as f:
        texts = json.load(f)
    return hg, entities, enriched, texts


# ── Project ID Mapping ───────────────────────────────────────────────

def build_project_name_to_id(hg: dict) -> dict[str, str]:
    """Map project label -> node id in existing hypergraph."""
    m = {}
    for n in hg["nodes"]:
        if n["type"] == "Project":
            m[n["label"]] = n["id"]
    return m


def find_project_id(name: str, proj_map: dict[str, str]) -> str | None:
    """Fuzzy match entity project_name to existing hypergraph project node."""
    if name in proj_map:
        return proj_map[name]
    for label, pid in proj_map.items():
        if name in label or label in name:
            return pid
    return None


# ── TIER 1: Structured Extraction ────────────────────────────────────

def mine_structured_nodes(entities: list[dict], enriched: list[dict], texts: list[dict],
                          proj_map: dict[str, str]):
    nodes: dict[str, dict] = {}
    proj_links: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    # BusinessModel
    for ent in entities:
        pid = find_project_id(ent["project_name"], proj_map)
        if not pid:
            continue
        for bm in ent.get("biz_model", []):
            bm = bm.strip()
            if not bm or len(bm) < 2:
                continue
            nid = f"biz_{_md5(bm)}"
            if nid not in nodes:
                nodes[nid] = _make_node(nid, "BusinessModel", bm, {"usage_count": 0})
            nodes[nid]["properties"]["usage_count"] += 1
            proj_links[pid]["BusinessModel"].append(nid)

    # MoatType
    for ent in entities:
        pid = find_project_id(ent["project_name"], proj_map)
        if not pid:
            continue
        for mt in ent.get("moat", []):
            mt = mt.strip()
            if not mt or len(mt) < 2:
                continue
            nid = f"moat_{_md5(mt)}"
            if nid not in nodes:
                nodes[nid] = _make_node(nid, "MoatType", mt, {"usage_count": 0})
            nodes[nid]["properties"]["usage_count"] += 1
            proj_links[pid]["MoatType"].append(nid)

    # PainPoint
    for ent in entities:
        pid = find_project_id(ent["project_name"], proj_map)
        if not pid:
            continue
        for pp in ent.get("pain_points", []):
            pp = pp.strip()
            if not pp or len(pp) < 2:
                continue
            nid = f"pain_{_md5(pp)}"
            if nid not in nodes:
                nodes[nid] = _make_node(nid, "PainPoint", pp, {"usage_count": 0})
            nodes[nid]["properties"]["usage_count"] += 1
            proj_links[pid]["PainPoint"].append(nid)

    # RiskCategory (from risks[])
    for ent in entities:
        pid = find_project_id(ent["project_name"], proj_map)
        if not pid:
            continue
        for rk in ent.get("risks", []):
            rk = rk.strip()
            if not rk or len(rk) < 2:
                continue
            nid = f"riskcat_{_md5(rk)}"
            if nid not in nodes:
                nodes[nid] = _make_node(nid, "RiskCategory", rk, {"usage_count": 0})
            nodes[nid]["properties"]["usage_count"] += 1
            proj_links[pid]["RiskCategory"].append(nid)

    # CompetitionTrack
    tracks_seen: dict[str, list[str]] = defaultdict(list)
    for ent in entities:
        pid = find_project_id(ent["project_name"], proj_map)
        if not pid:
            continue
        src = ent.get("source", "").strip()
        if src:
            nid = f"track_{_md5(src)}"
            if nid not in nodes:
                nodes[nid] = _make_node(nid, "CompetitionTrack", src, {"project_count": 0})
            nodes[nid]["properties"]["project_count"] += 1
            proj_links[pid]["CompetitionTrack"].append(nid)
            tracks_seen[nid].append(pid)

    # AwardLevel (from all_texts path: .../本科/... .../硕士/... .../博士/...)
    level_map: dict[str, list[str]] = defaultdict(list)
    for txt in texts:
        path = txt.get("path", "")
        pid_name = txt.get("filename", "").replace(".pdf", "").replace(".docx", "").replace(".pptx", "")
        pid = None
        for ent in entities:
            if ent["project_name"] in pid_name or pid_name in ent["project_name"]:
                pid = find_project_id(ent["project_name"], proj_map)
                break
        if not pid:
            continue
        for level in ["本科", "硕士", "博士"]:
            if f"/{level}/" in path:
                nid = f"level_{_md5(level)}"
                if nid not in nodes:
                    nodes[nid] = _make_node(nid, "AwardLevel", level, {"project_count": 0})
                nodes[nid]["properties"]["project_count"] += 1
                proj_links[pid]["AwardLevel"].append(nid)
                level_map[nid].append(pid)

    # TeamRole (from enriched)
    for enr in enriched:
        pid = find_project_id(enr["project_name"], proj_map)
        if not pid:
            continue
        for role in enr.get("team_backgrounds", []):
            role = role.strip()
            if not role or len(role) < 2:
                continue
            nid = f"role_{_md5(role)}"
            if nid not in nodes:
                nodes[nid] = _make_node(nid, "TeamRole", role, {"usage_count": 0})
            nodes[nid]["properties"]["usage_count"] += 1
            proj_links[pid]["TeamRole"].append(nid)

    return nodes, proj_links


# ── TIER 2: Text-Mined Nodes ────────────────────────────────────────

def mine_text_nodes(texts: list[dict], entities: list[dict], proj_map: dict[str, str]):
    nodes: dict[str, dict] = {}
    proj_links: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    # Build text -> project_id mapping
    text_to_pid: dict[int, str | None] = {}
    for i, txt in enumerate(texts):
        fname = txt.get("filename", "")
        pid = None
        for ent in entities:
            pn = ent["project_name"]
            if pn in fname or fname.replace(".pdf", "").replace(".docx", "") in pn or pn in fname:
                pid = find_project_id(pn, proj_map)
                break
        text_to_pid[i] = pid

    for i, txt in enumerate(texts):
        content = txt.get("text", "")
        if not content:
            continue
        pid = text_to_pid[i]

        # SubTechnology
        for parent, children in TECH_HIERARCHY.items():
            for child in children:
                pattern = re.escape(child)
                if re.search(pattern, content, re.IGNORECASE):
                    nid = f"subtech_{_md5(child)}"
                    if nid not in nodes:
                        nodes[nid] = _make_node(nid, "SubTechnology", child,
                                                {"parent_tech": parent, "usage_count": 0})
                    nodes[nid]["properties"]["usage_count"] += 1
                    if pid:
                        proj_links[pid]["SubTechnology"].append(nid)

        # Framework
        for fw in FRAMEWORK_PATTERNS:
            if re.search(re.escape(fw), content, re.IGNORECASE):
                nid = f"fw_{_md5(fw)}"
                if nid not in nodes:
                    nodes[nid] = _make_node(nid, "Framework", fw, {"usage_count": 0})
                nodes[nid]["properties"]["usage_count"] += 1
                if pid:
                    proj_links[pid]["Framework"].append(nid)

        # ApplicationDomain
        for domain, pattern in DOMAIN_PATTERNS.items():
            if re.search(pattern, content):
                nid = f"domain_{_md5(domain)}"
                if nid not in nodes:
                    nodes[nid] = _make_node(nid, "ApplicationDomain", domain, {"usage_count": 0})
                nodes[nid]["properties"]["usage_count"] += 1
                if pid:
                    proj_links[pid]["ApplicationDomain"].append(nid)

        # SolutionApproach
        for sol in SOLUTION_PATTERNS:
            if sol in content:
                nid = f"sol_{_md5(sol)}"
                if nid not in nodes:
                    nodes[nid] = _make_node(nid, "SolutionApproach", sol, {"usage_count": 0})
                nodes[nid]["properties"]["usage_count"] += 1
                if pid:
                    proj_links[pid]["SolutionApproach"].append(nid)

        # DataModality
        for mod in MODALITY_PATTERNS:
            if mod in content:
                nid = f"modality_{_md5(mod)}"
                if nid not in nodes:
                    nodes[nid] = _make_node(nid, "DataModality", mod, {"usage_count": 0})
                nodes[nid]["properties"]["usage_count"] += 1
                if pid:
                    proj_links[pid]["DataModality"].append(nid)

        # HardwarePlatform
        for hw in HARDWARE_PATTERNS:
            if re.search(re.escape(hw), content, re.IGNORECASE):
                nid = f"hw_{_md5(hw)}"
                if nid not in nodes:
                    nodes[nid] = _make_node(nid, "HardwarePlatform", hw, {"usage_count": 0})
                nodes[nid]["properties"]["usage_count"] += 1
                if pid:
                    proj_links[pid]["HardwarePlatform"].append(nid)

        # Extra RiskPattern nodes
        for rp in EXTRA_RISK_PATTERNS:
            label = rp["label"]
            keywords = [label[j:j+3] for j in range(0, len(label)-2, 2)]
            if any(kw in content for kw in keywords[:3]):
                nid = f"risk_{_md5(label)}"
                if nid not in nodes:
                    nodes[nid] = _make_node(nid, "RiskPattern", label, {
                        "dimension": rp["dimension"],
                        "severity": rp["severity"],
                        "usage_count": 0,
                    })
                nodes[nid]["properties"]["usage_count"] += 1
                if pid:
                    proj_links[pid]["RiskPattern"].append(nid)

    return nodes, proj_links


# ── TIER 3: Enriched-Only Nodes ──────────────────────────────────────

def mine_enriched_nodes(enriched: list[dict], proj_map: dict[str, str]):
    nodes: dict[str, dict] = {}
    proj_links: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for enr in enriched:
        pid = find_project_id(enr["project_name"], proj_map)
        if not pid:
            continue

        for sf in enr.get("success_factors", []):
            sf = sf.strip()
            if not sf or len(sf) < 3:
                continue
            nid = f"sf_{_md5(sf)}"
            if nid not in nodes:
                nodes[nid] = _make_node(nid, "SuccessFactor", sf, {"usage_count": 0})
            nodes[nid]["properties"]["usage_count"] += 1
            proj_links[pid]["SuccessFactor"].append(nid)

        for fr in enr.get("failure_risks", []):
            fr = fr.strip()
            if not fr or len(fr) < 3:
                continue
            nid = f"fr_{_md5(fr)}"
            if nid not in nodes:
                nodes[nid] = _make_node(nid, "FailureRisk", fr, {"usage_count": 0})
            nodes[nid]["properties"]["usage_count"] += 1
            proj_links[pid]["FailureRisk"].append(nid)

    return nodes, proj_links


# ── TIER 3b: Extra Concept Nodes ─────────────────────────────────────

def mine_concept_nodes(texts: list[dict], entities: list[dict], proj_map: dict[str, str],
                       existing_concept_labels: set[str]):
    nodes: dict[str, dict] = {}
    proj_links: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    text_to_pid: dict[int, str | None] = {}
    for i, txt in enumerate(texts):
        fname = txt.get("filename", "")
        pid = None
        for ent in entities:
            pn = ent["project_name"]
            if pn in fname or fname.replace(".pdf", "") in pn:
                pid = find_project_id(pn, proj_map)
                break
        text_to_pid[i] = pid

    for concept in EXTRA_CONCEPTS:
        label = concept["label"]
        en = concept["en"]
        if label in existing_concept_labels:
            continue
        nid = f"concept_{en.replace(' ', '_')}"
        # Check if this concept appears in any text
        found = False
        for i, txt in enumerate(texts):
            content = txt.get("text", "")
            if label in content or en.lower() in content.lower():
                found = True
                pid = text_to_pid.get(i)
                if pid:
                    proj_links[pid]["Concept"].append(nid)
        if found:
            nodes[nid] = _make_node(nid, "Concept", label, {"en": en, "usage_count": 0})
            # Count usages
            for pid, links in proj_links.items():
                nodes[nid]["properties"]["usage_count"] = sum(
                    1 for pid2, l2 in proj_links.items() if nid in l2.get("Concept", []))
                break

    return nodes, proj_links


# ── TIER 4: TF-IDF Keywords ─────────────────────────────────────────

def mine_keyword_nodes(texts: list[dict], entities: list[dict], proj_map: dict[str, str],
                       existing_labels: set[str], max_keywords: int = 600):
    import jieba
    from sklearn.feature_extraction.text import TfidfVectorizer

    nodes: dict[str, dict] = {}
    proj_links: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    # Map text index -> pid
    text_to_pid: dict[int, str | None] = {}
    for i, txt in enumerate(texts):
        fname = txt.get("filename", "")
        pid = None
        for ent in entities:
            pn = ent["project_name"]
            if pn in fname or fname.replace(".pdf", "") in pn:
                pid = find_project_id(pn, proj_map)
                break
        text_to_pid[i] = pid

    corpus = []
    for txt in texts:
        raw = txt.get("text", "")
        corpus.append(" ".join(jieba.lcut(raw)))

    vectorizer = TfidfVectorizer(
        max_features=5000,
        min_df=1,
        max_df=0.7,
        token_pattern=r"(?u)\b[\u4e00-\u9fff]{2,6}\b|[A-Za-z]{3,}",
    )
    tfidf_matrix = vectorizer.fit_transform(corpus)
    feature_names = vectorizer.get_feature_names_out()

    # Collect global document frequency
    doc_freq: Counter = Counter()
    doc_keywords: dict[int, list[str]] = {}
    for i in range(tfidf_matrix.shape[0]):
        row = tfidf_matrix[i].toarray().flatten()
        top_indices = row.argsort()[-20:][::-1]
        kws = []
        for idx in top_indices:
            if row[idx] > 0.01:
                kw = feature_names[idx]
                kws.append(kw)
                doc_freq[kw] += 1
        doc_keywords[i] = kws

    # Filter: skip words already captured as other node types, skip too short/common
    stopwords = {"项目", "系统", "研究", "方法", "基于", "通过", "实现", "进行",
                 "结果", "过程", "目前", "工作", "相关", "具有", "其中", "能够",
                 "以及", "由于", "同时", "不同", "主要", "需要", "可以", "使用",
                 "采用", "包括", "利用", "提高", "提出", "问题", "方案", "发展"}
    existing_lower = {l.lower() for l in existing_labels}

    selected = []
    for kw, freq in doc_freq.most_common():
        if len(selected) >= max_keywords:
            break
        if kw in stopwords or kw.lower() in existing_lower:
            continue
        if len(kw) < 2 or freq < 2:
            continue
        selected.append(kw)

    # Create nodes and link to projects
    for kw in selected:
        nid = f"kw_{_md5(kw)}"
        nodes[nid] = _make_node(nid, "Keyword", kw, {
            "doc_frequency": doc_freq[kw],
        })

    for i, kws in doc_keywords.items():
        pid = text_to_pid.get(i)
        if not pid:
            continue
        for kw in kws:
            if kw in selected:
                nid = f"kw_{_md5(kw)}"
                proj_links[pid]["Keyword"].append(nid)

    return nodes, proj_links


# ── Build Hyperedges ─────────────────────────────────────────────────

def build_hyperedges(all_proj_links: dict[str, dict[str, list[str]]],
                     new_nodes: dict[str, dict],
                     hg: dict) -> list[dict]:
    edges: list[dict] = []
    existing_node_map = {n["id"]: n for n in hg["nodes"]}

    # --- Technology_Hierarchy ---
    parent_to_subtechs: dict[str, list[str]] = defaultdict(list)
    for nid, node in new_nodes.items():
        if node["type"] == "SubTechnology":
            parent = node["properties"].get("parent_tech", "")
            if parent:
                parent_to_subtechs[parent].append(nid)

    # Find existing tech node ids for parents
    for parent_name, subtech_ids in parent_to_subtechs.items():
        parent_nid = None
        for n in hg["nodes"]:
            if n["type"] == "Technology" and n["label"] == parent_name:
                parent_nid = n["id"]
                break
        if parent_nid and subtech_ids:
            eid = f"he_techhier_{_md5(parent_name)}"
            child_labels = [new_nodes[sid]["label"] for sid in subtech_ids]
            edges.append(_make_edge(eid, "Technology_Hierarchy",
                                    [parent_nid] + list(set(subtech_ids)),
                                    {"parent_tech": parent_name,
                                     "child_count": len(set(subtech_ids)),
                                     "teaching_note": f"{parent_name}下包含{', '.join(child_labels[:5])}等具体技术"}))

    # --- Business_Strategy ---
    for pid, links in all_proj_links.items():
        biz_ids = list(set(links.get("BusinessModel", [])))
        moat_ids = list(set(links.get("MoatType", [])))
        if biz_ids or moat_ids:
            proj_label = existing_node_map.get(pid, {}).get("label", pid)
            eid = f"he_bizstrat_{_md5(pid)}"
            all_nids = [pid] + biz_ids + moat_ids
            biz_labels = [new_nodes.get(b, {}).get("label", "") for b in biz_ids]
            moat_labels = [new_nodes.get(m, {}).get("label", "") for m in moat_ids]
            edges.append(_make_edge(eid, "Business_Strategy", all_nids, {
                "project": proj_label,
                "biz_models": biz_labels,
                "moat_types": moat_labels,
                "teaching_note": f"{proj_label}采用{'、'.join(biz_labels[:3])}模式，{'、'.join(moat_labels[:3])}为壁垒"
            }))

    # --- Pain_Solution_Fit ---
    for pid, links in all_proj_links.items():
        pain_ids = list(set(links.get("PainPoint", [])))
        sol_ids = list(set(links.get("SolutionApproach", [])))
        if pain_ids or sol_ids:
            proj_label = existing_node_map.get(pid, {}).get("label", pid)
            eid = f"he_psf_{_md5(pid)}"
            all_nids = [pid] + pain_ids + sol_ids
            pain_labels = [new_nodes.get(p, {}).get("label", "") for p in pain_ids[:3]]
            sol_labels = [new_nodes.get(s, {}).get("label", "") for s in sol_ids[:3]]
            edges.append(_make_edge(eid, "Pain_Solution_Fit", all_nids, {
                "project": proj_label,
                "pain_points": pain_labels,
                "solutions": sol_labels,
                "teaching_note": f"{proj_label}解决{'、'.join(pain_labels)}等痛点，采用{'、'.join(sol_labels)}等方案"
            }))

    # --- Team_Composition ---
    for pid, links in all_proj_links.items():
        role_ids = list(set(links.get("TeamRole", [])))
        if role_ids:
            proj_label = existing_node_map.get(pid, {}).get("label", pid)
            eid = f"he_team_{_md5(pid)}"
            role_labels = [new_nodes.get(r, {}).get("label", "") for r in role_ids]
            edges.append(_make_edge(eid, "Team_Composition", [pid] + role_ids, {
                "project": proj_label,
                "roles": role_labels,
                "teaching_note": f"{proj_label}团队包含{'、'.join(role_labels)}"
            }))

    # --- Competition_Track ---
    track_projects: dict[str, list[str]] = defaultdict(list)
    for pid, links in all_proj_links.items():
        for tid in set(links.get("CompetitionTrack", [])):
            track_projects[tid].append(pid)
    for tid, pids in track_projects.items():
        track_label = new_nodes.get(tid, {}).get("label", tid)
        eid = f"he_comptrack_{_md5(tid)}"
        edges.append(_make_edge(eid, "Competition_Track_Group", [tid] + list(set(pids)), {
            "track": track_label,
            "project_count": len(set(pids)),
            "teaching_note": f"赛道'{track_label}'共有{len(set(pids))}个项目"
        }))

    # --- Cross_Industry_Tech ---
    # Find technologies appearing in 3+ industries
    tech_industries: dict[str, set[str]] = defaultdict(set)
    for n in hg["nodes"]:
        if n["type"] == "Project":
            industry = n.get("properties", {}).get("industry", "")
            techs = n.get("properties", {}).get("technologies", [])
            for tech in techs:
                if industry:
                    tech_industries[tech].add(industry)

    for tech_name, industries in tech_industries.items():
        if len(industries) >= 3:
            tech_nid = None
            for n in hg["nodes"]:
                if n["type"] == "Technology" and n["label"] == tech_name:
                    tech_nid = n["id"]
                    break
            if not tech_nid:
                continue
            mkt_nids = []
            for n in hg["nodes"]:
                if n["type"] == "Market" and n["label"] in industries:
                    mkt_nids.append(n["id"])
            if mkt_nids:
                eid = f"he_crossind_{_md5(tech_name)}"
                edges.append(_make_edge(eid, "Cross_Industry_Tech",
                                        [tech_nid] + mkt_nids, {
                                            "technology": tech_name,
                                            "industry_count": len(mkt_nids),
                                            "industries": list(industries),
                                            "teaching_note": f"{tech_name}横跨{len(industries)}个行业：{'、'.join(list(industries)[:4])}"
                                        }))

    # --- Application_Domain_Map ---
    domain_projects: dict[str, list[str]] = defaultdict(list)
    for pid, links in all_proj_links.items():
        for did in set(links.get("ApplicationDomain", [])):
            domain_projects[did].append(pid)
    for did, pids in domain_projects.items():
        if len(pids) < 1:
            continue
        domain_label = new_nodes.get(did, {}).get("label", did)
        eid = f"he_domainmap_{_md5(did)}"
        edges.append(_make_edge(eid, "Application_Domain_Map", [did] + list(set(pids)), {
            "domain": domain_label,
            "project_count": len(set(pids)),
            "teaching_note": f"应用领域'{domain_label}'涉及{len(set(pids))}个项目"
        }))

    # --- Project_Profile: connect each project to ALL its new node types ---
    # This ensures no orphan nodes: every new node is in at least one edge
    all_profile_types = [
        "SubTechnology", "Framework", "ApplicationDomain", "SolutionApproach",
        "DataModality", "HardwarePlatform", "RiskCategory", "RiskPattern", "SuccessFactor",
        "FailureRisk", "AwardLevel", "Keyword", "Concept",
    ]
    for pid, links in all_proj_links.items():
        profile_nids = []
        for ntype in all_profile_types:
            profile_nids.extend(set(links.get(ntype, [])))
        if not profile_nids:
            continue
        proj_label = existing_node_map.get(pid, {}).get("label", pid)
        eid = f"he_profile_{_md5(pid)}"
        edges.append(_make_edge(eid, "Project_Profile", [pid] + list(set(profile_nids)), {
            "project": proj_label,
            "attribute_count": len(set(profile_nids)),
            "teaching_note": f"{proj_label}的详细属性画像，包含{len(set(profile_nids))}个属性节点"
        }))

    # --- Keyword_Cluster (co-occurrence based) ---
    kw_cooccur: Counter = Counter()
    pid_keywords: dict[str, set[str]] = defaultdict(set)
    for pid, links in all_proj_links.items():
        kw_ids = set(links.get("Keyword", []))
        pid_keywords[pid] = kw_ids

    for pid, kw_ids in pid_keywords.items():
        kw_list = sorted(kw_ids)
        for i in range(len(kw_list)):
            for j in range(i + 1, min(i + 5, len(kw_list))):
                kw_cooccur[(kw_list[i], kw_list[j])] += 1

    cluster_count = 0
    used_kws: set[str] = set()
    for (kw1, kw2), freq in kw_cooccur.most_common(80):
        if freq < 2 or kw1 in used_kws or kw2 in used_kws:
            continue
        pids_with_both = [pid for pid, kws in pid_keywords.items() if kw1 in kws and kw2 in kws]
        if len(pids_with_both) < 2:
            continue
        label1 = new_nodes.get(kw1, {}).get("label", "")
        label2 = new_nodes.get(kw2, {}).get("label", "")
        eid = f"he_kwcluster_{cluster_count}"
        edges.append(_make_edge(eid, "Keyword_Cluster",
                                [kw1, kw2] + pids_with_both[:5], {
                                    "keywords": [label1, label2],
                                    "project_count": len(pids_with_both),
                                    "teaching_note": f"关键词'{label1}'和'{label2}'在{len(pids_with_both)}个项目中共现"
                                }))
        used_kws.add(kw1)
        used_kws.add(kw2)
        cluster_count += 1
        if cluster_count >= 40:
            break

    return edges


# ── Validate & Merge ─────────────────────────────────────────────────

def validate_and_merge(hg: dict, new_nodes: dict[str, dict], new_edges: list[dict]):
    existing_ids = {n["id"] for n in hg["nodes"]}
    all_node_ids = existing_ids | set(new_nodes.keys())

    # Remove edges referencing non-existent nodes
    valid_edges = []
    for e in new_edges:
        if all(nid in all_node_ids for nid in e["nodes"]):
            valid_edges.append(e)
        else:
            missing = [nid for nid in e["nodes"] if nid not in all_node_ids]
            log.warning(f"  Skipping edge {e['id']}: missing nodes {missing}")

    # Remove orphan new nodes (not in any edge)
    nodes_in_edges = set()
    for e in hg["hyperedges"]:
        nodes_in_edges.update(e["nodes"])
    for e in valid_edges:
        nodes_in_edges.update(e["nodes"])

    final_new_nodes = {nid: n for nid, n in new_nodes.items() if nid in nodes_in_edges}
    orphans = len(new_nodes) - len(final_new_nodes)
    if orphans:
        log.info(f"  Removed {orphans} orphan nodes")

    # Merge
    merged = {
        "nodes": hg["nodes"] + list(final_new_nodes.values()),
        "hyperedges": hg["hyperedges"] + valid_edges,
    }
    return merged


# ── Main ─────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("超图扩充脚本 — 从现有数据深度挖掘")
    log.info("=" * 60)

    # Load
    log.info("\n[1/6] 加载数据源...")
    hg, entities, enriched, texts = load_sources()
    proj_map = build_project_name_to_id(hg)
    log.info(f"  现有超图: {len(hg['nodes'])} 节点, {len(hg['hyperedges'])} 超边")
    log.info(f"  实体数据: {len(entities)} 项目")
    log.info(f"  详细数据: {len(enriched)} 项目")
    log.info(f"  文本数据: {len(texts)} 文档")

    all_new_nodes: dict[str, dict] = {}
    all_proj_links: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    # Tier 1
    log.info("\n[2/6] Tier 1: 结构化数据提取...")
    t1_nodes, t1_links = mine_structured_nodes(entities, enriched, texts, proj_map)
    all_new_nodes.update(t1_nodes)
    for pid, links in t1_links.items():
        for k, v in links.items():
            all_proj_links[pid][k].extend(v)
    type_counts = Counter(n["type"] for n in t1_nodes.values())
    log.info(f"  提取 {len(t1_nodes)} 个新节点: {dict(type_counts)}")

    # Tier 2
    log.info("\n[3/6] Tier 2: 文本正则挖掘...")
    t2_nodes, t2_links = mine_text_nodes(texts, entities, proj_map)
    all_new_nodes.update(t2_nodes)
    for pid, links in t2_links.items():
        for k, v in links.items():
            all_proj_links[pid][k].extend(v)
    type_counts = Counter(n["type"] for n in t2_nodes.values())
    log.info(f"  提取 {len(t2_nodes)} 个新节点: {dict(type_counts)}")

    # Tier 3
    log.info("\n[4/6] Tier 3: 详细案例深度提取...")
    t3_nodes, t3_links = mine_enriched_nodes(enriched, proj_map)
    all_new_nodes.update(t3_nodes)
    for pid, links in t3_links.items():
        for k, v in links.items():
            all_proj_links[pid][k].extend(v)
    type_counts = Counter(n["type"] for n in t3_nodes.values())
    log.info(f"  提取 {len(t3_nodes)} 个新节点: {dict(type_counts)}")

    # Tier 3b: Extra Concepts
    log.info("\n[4b/7] Tier 3b: 创业教育概念节点...")
    existing_concept_labels = {n["label"] for n in hg["nodes"] if n["type"] == "Concept"}
    t3b_nodes, t3b_links = mine_concept_nodes(texts, entities, proj_map, existing_concept_labels)
    all_new_nodes.update(t3b_nodes)
    for pid, links in t3b_links.items():
        for k, v in links.items():
            all_proj_links[pid][k].extend(v)
    log.info(f"  提取 {len(t3b_nodes)} 个新概念节点")

    # Tier 4
    log.info("\n[5/7] Tier 4: TF-IDF 关键词挖掘...")
    existing_labels = {n["label"] for n in hg["nodes"]} | {n["label"] for n in all_new_nodes.values()}
    t4_nodes, t4_links = mine_keyword_nodes(texts, entities, proj_map, existing_labels)
    all_new_nodes.update(t4_nodes)
    for pid, links in t4_links.items():
        for k, v in links.items():
            all_proj_links[pid][k].extend(v)
    log.info(f"  提取 {len(t4_nodes)} 个关键词节点")

    # Build edges
    log.info("\n[6/6] 构建新超边...")
    new_edges = build_hyperedges(all_proj_links, all_new_nodes, hg)
    edge_counts = Counter(e["type"] for e in new_edges)
    log.info(f"  构建 {len(new_edges)} 条新超边: {dict(edge_counts)}")

    # Validate & Merge
    log.info("\n验证与合并...")
    merged = validate_and_merge(hg, all_new_nodes, new_edges)

    # Stats
    final_node_counts = Counter(n["type"] for n in merged["nodes"])
    final_edge_counts = Counter(e["type"] for e in merged["hyperedges"])

    log.info("\n" + "=" * 60)
    log.info("扩充结果")
    log.info("=" * 60)
    log.info(f"\n总节点数: {len(merged['nodes'])} (原 {len(hg['nodes'])})")
    for t, c in sorted(final_node_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {t}: {c}")
    log.info(f"\n总超边数: {len(merged['hyperedges'])} (原 {len(hg['hyperedges'])})")
    for t, c in sorted(final_edge_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {t}: {c}")

    # Backup & Save
    bak_path = _HG_PATH.with_suffix(".json.bak")
    shutil.copy2(_HG_PATH, bak_path)
    log.info(f"\n已备份原文件: {bak_path}")

    with open(_HG_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    log.info(f"已写入扩充后超图: {_HG_PATH}")
    log.info(f"文件大小: {_HG_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
