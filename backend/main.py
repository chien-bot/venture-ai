from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, chat, projects, teacher
from routers import graph as graph_router
from routers import tools as tools_router
from routers import upload as upload_router
from routers import peer_review as peer_review_router
from services.database import init_db
from graph_db.neo4j_client import sync_knowledge_graph, is_available
import logging

logger = logging.getLogger(__name__)

# Initialize SQLite database on startup
init_db()

# Attempt Neo4j sync on startup (best-effort, non-blocking)
try:
    if is_available():
        sync_knowledge_graph()
        logger.info("Neo4j knowledge graph synced on startup.")
    else:
        logger.info("Neo4j not configured — running in SQLite-only mode.")
except Exception as e:
    logger.warning(f"Neo4j startup sync failed (non-fatal): {e}")

app = FastAPI(
    title="VentureAI - 创新创业教学智能体",
    description="基于知识图谱与超图的双创教育AI系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(projects.router)
app.include_router(teacher.router)
app.include_router(graph_router.router)
app.include_router(tools_router.router)
app.include_router(upload_router.router)
app.include_router(peer_review_router.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "VentureAI"}
