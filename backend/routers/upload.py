"""File upload router for multi-modal input (F3-adv) + hypergraph ingestion."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from pathlib import Path
import uuid
import re
import logging

from services.database import save_uploaded_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".png", ".jpg", ".jpeg", ".md", ".csv"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    project_id: str = Form(""),
    session_id: str = Form(""),
):
    """Upload PDF, image, or text file. Extract text and store."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过 10MB 限制")

    file_id = f"file_{uuid.uuid4().hex[:8]}"
    file_path = UPLOAD_DIR / f"{file_id}{ext}"
    file_path.write_bytes(content)

    # Determine file type and extract text
    if ext == ".pdf":
        file_type = "pdf"
        extracted_text = _extract_pdf_text(file_path)
    elif ext in (".txt", ".md", ".csv"):
        file_type = "text"
        extracted_text = _extract_text_file(file_path)
    else:
        file_type = "image"
        extracted_text = f"[图片文件: {file.filename}]"

    save_uploaded_file(
        file_id=file_id,
        project_id=project_id,
        session_id=session_id,
        filename=file.filename,
        file_type=file_type,
        extracted_text=extracted_text,
        file_size=len(content),
    )

    return {
        "file_id": file_id,
        "filename": file.filename,
        "file_type": file_type,
        "size": len(content),
        "extracted_text_preview": extracted_text[:500] if extracted_text else "",
    }


def _extract_pdf_text(file_path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(file_path))
        pages = []
        for page in reader.pages[:20]:  # limit to 20 pages
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except ImportError:
        return "[PyPDF2 未安装，无法提取 PDF 文本]"
    except Exception as e:
        return f"[PDF 解析失败: {str(e)}]"


def _extract_text_file(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8", errors="ignore")[:50000]
    except Exception:
        return "[文本读取失败]"


# ── Hypergraph ingestion ─────────────────────────────────────

# Tech keyword patterns for extraction
_TECH_PATTERNS = [
    "深度学习", "机器学习", "自然语言处理", "NLP", "计算机视觉", "CV",
    "大数据", "区块链", "物联网", "IoT", "云计算", "边缘计算",
    "强化学习", "知识图谱", "数字孪生", "AR", "VR", "5G",
    "YOLO", "BERT", "GPT", "Transformer", "CNN", "RNN", "LSTM",
    "GAN", "联邦学习", "迁移学习", "图神经网络", "GNN",
    "无人机", "机器人", "传感器", "光谱", "雷达", "卫星",
    "微流控", "生物信息", "基因", "蛋白质",
]

_INDUSTRY_PATTERNS = {
    "农业": ["农业", "种植", "养殖", "作物", "农产品", "智慧农业"],
    "医疗健康": ["医疗", "健康", "诊断", "药物", "临床", "康复", "病理"],
    "环保": ["环保", "碳", "污染", "废弃物", "生态", "环境监测"],
    "教育": ["教育", "学习", "教学", "课堂", "学生"],
    "智能制造": ["制造", "工业", "产线", "质检", "缺陷检测"],
    "安全": ["安全", "检测", "监控", "预警", "消防", "无人机"],
    "文化旅游": ["文化", "旅游", "文创", "非遗", "景区"],
    "交通": ["交通", "自动驾驶", "车辆", "道路"],
    "能源": ["能源", "电池", "光伏", "储能", "新能源"],
}


def _extract_entities_from_text(text: str) -> dict:
    """Extract project entities (tech, industry, problem, etc.) from raw text."""
    # Extract project name (usually in title or first line)
    lines = text.strip().split("\n")
    project_name = ""
    for line in lines[:10]:
        line = line.strip()
        if len(line) > 2 and len(line) < 50 and not line.startswith("["):
            project_name = line
            break
    if not project_name:
        project_name = "未命名项目"

    # Extract technologies
    technologies = []
    text_lower = text.lower()
    for tech in _TECH_PATTERNS:
        if tech.lower() in text_lower:
            technologies.append(tech)

    # Extract industry
    industry = "其他"
    max_hits = 0
    for ind, keywords in _INDUSTRY_PATTERNS.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > max_hits:
            max_hits = hits
            industry = ind

    # Extract problem (look for pain point section)
    problem = ""
    for pattern in ["痛点", "问题", "背景", "现状", "挑战"]:
        idx = text.find(pattern)
        if idx >= 0:
            problem = text[idx:idx + 300].split("\n")[0]
            break

    # Extract solution
    solution = ""
    for pattern in ["方案", "解决", "产品", "系统", "平台"]:
        idx = text.find(pattern)
        if idx >= 0:
            solution = text[idx:idx + 300].split("\n")[0]
            break

    # Extract business model keywords
    biz_models = []
    for kw in ["SaaS", "B2B", "B2C", "订阅", "广告", "佣金", "平台", "授权", "定制"]:
        if kw in text:
            biz_models.append(kw)

    # Extract moat keywords
    moat = []
    for kw in ["专利", "壁垒", "独家", "核心技术", "先发优势", "网络效应"]:
        if kw in text:
            moat.append(kw)

    return {
        "project_name": project_name,
        "industry": industry,
        "technologies": technologies[:10],
        "problem": problem,
        "solution": solution,
        "biz_models": biz_models,
        "moat": moat,
    }


@router.post("/ingest")
async def ingest_to_hypergraph(
    file: UploadFile = File(...),
):
    """
    Upload a competition project document (PDF/TXT),
    auto-extract entities, and add to the hypergraph.
    """
    from hypergraph.engine import add_project_to_hypergraph

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail=f"仅支持 PDF/TXT/MD 文件，收到: {ext}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过 10MB 限制")

    # Save temp file
    tmp_id = f"ingest_{uuid.uuid4().hex[:8]}"
    tmp_path = UPLOAD_DIR / f"{tmp_id}{ext}"
    tmp_path.write_bytes(content)

    # Extract text
    if ext == ".pdf":
        text = _extract_pdf_text(tmp_path)
    else:
        text = _extract_text_file(tmp_path)

    if not text or len(text) < 50:
        raise HTTPException(status_code=400, detail="无法从文件中提取足够的文本内容")

    # Extract entities
    entities = _extract_entities_from_text(text)

    # Add to hypergraph
    result = add_project_to_hypergraph(
        project_name=entities["project_name"],
        industry=entities["industry"],
        technologies=entities["technologies"],
        problem=entities["problem"],
        solution=entities["solution"],
        biz_models=entities["biz_models"],
        moat=entities["moat"],
        source=f"ingest:{file.filename}",
    )

    # Clean up temp file
    tmp_path.unlink(missing_ok=True)

    return {
        "status": "ok",
        "message": f"项目「{entities['project_name']}」已添加到超图",
        "extracted": entities,
        "hypergraph": result,
    }


class ManualIngestRequest(BaseModel):
    project_name: str
    industry: str
    technologies: list[str]
    problem: str = ""
    solution: str = ""
    market_size: str = ""
    biz_models: list[str] = []
    moat: list[str] = []


@router.post("/ingest/manual")
async def ingest_manual(req: ManualIngestRequest):
    """Manually add a project to the hypergraph without file upload."""
    from hypergraph.engine import add_project_to_hypergraph

    result = add_project_to_hypergraph(
        project_name=req.project_name,
        industry=req.industry,
        technologies=req.technologies,
        problem=req.problem,
        solution=req.solution,
        market_size=req.market_size,
        biz_models=req.biz_models,
        moat=req.moat,
        source="manual",
    )
    return {
        "status": "ok",
        "message": f"项目「{req.project_name}」已添加到超图",
        "hypergraph": result,
    }
