from fastapi.staticfiles import StaticFiles
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.core.database import init_db
from app.api import auth, chat, knowledge, eval

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    try:
        init_db()
    except Exception as e:
        print(f"[WARN] 数据库初始化失败 (MySQL 可能未启动): {e}")
    yield


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



# 静态文件：上传的图片
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/api/files/images", StaticFiles(directory=settings.upload_dir), name="uploaded_images")

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
