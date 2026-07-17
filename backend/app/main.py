import logging
from fastapi.staticfiles import StaticFiles
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging_config import setup_logging
from app.api import auth, chat, knowledge, eval, admin
from app.models import faq_stats  # 确保表在 init_db 时创建
from app.services.reranker import warmup_reranker
from app.services.vector_store import disconnect_milvus

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    setup_logging()
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning("数据库初始化失败 (MySQL 可能未启动): %s", e)
    # 后台预热 reranker 模型（不阻塞启动）
    import threading
    threading.Thread(target=warmup_reranker, daemon=True).start()
    yield
    disconnect_milvus()
    logger.info("Server shutdown complete")


app = FastAPI(title="InnerQA - 企业知识库问答系统", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(eval.router)
app.include_router(admin.router)



# 静态文件：上传的图片
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/api/files/images", StaticFiles(directory=settings.upload_dir), name="uploaded_images")
os.makedirs(os.path.join(settings.upload_dir, "avatars"), exist_ok=True)
app.mount("/api/files/avatars", StaticFiles(directory=os.path.join(settings.upload_dir, "avatars")), name="avatars")

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
