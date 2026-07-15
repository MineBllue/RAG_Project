
"""
处理带图片引用的 Markdown 文件，完整流程：
1. 解析 Markdown 中的 ![alt](path) 图片引用
2. 将本地图片上传到 MinIO，获取对象 URL
3. 替换本地路径为 MinIO URL，并在文中嵌入可见的关联图片信息
4. 加载处理后的 Markdown
5. 父子块切分
6. 存入 Milvus 向量数据库（图片 URL 存储在 metadata 中）
"""
import os
import re
import base64
import io
import json
import uuid
import hashlib
import tempfile
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import timedelta

from minio import Minio
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownTextSplitter

from app.services.minio_store import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
    MINIO_BUCKET, MINIO_SECURE,
)
from app.services.llm_service import get_embeddings
from app.services.sparse_embedding import encode_sparse


# ============================================================
# MinIO 客户端
# ============================================================

_minio_client: Optional[Minio] = None

def _get_minio() -> Minio:
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        if not _minio_client.bucket_exists(MINIO_BUCKET):
            _minio_client.make_bucket(MINIO_BUCKET)
            import json
            try:
                _minio_client.set_bucket_policy(MINIO_BUCKET, json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{"Effect": "Allow", "Principal": {"AWS": ["*"]},
                                   "Action": ["s3:GetObject"],
                                   "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}/*"]}]
                }))
            except Exception:
                pass
    return _minio_client


def upload_to_minio(file_path: str, object_name: str) -> Optional[str]:
    """上传文件到 MinIO，返回直接访问 URL"""
    try:
        client = _get_minio()
        content_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                         ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}
        ext = os.path.splitext(file_path)[1].lower()
        client.fput_object(MINIO_BUCKET, object_name, file_path,
                           content_type=content_types.get(ext, "application/octet-stream"))
        return f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}"
    except Exception as e:
        return None


def download_image_to_base64(url: str) -> Optional[str]:
    """下载图片并转为 base64（用于多模态模型）"""
    try:
        import requests
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            ext = os.path.splitext(url.split("?")[0])[1].lower()
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "gif": "image/gif", "webp": "image/webp"}.get(ext.lstrip("."), "image/png")
            b64 = base64.b64encode(resp.content).decode("utf-8")
            return f"data:{mime};base64,{b64}"
    except Exception:
        pass
    return None


# ============================================================
# Markdown 图片处理
# ============================================================

def process_markdown_images(
    md_content: str,
    md_base_dir: str,
    kb_id: int,
    doc_id: int,
) -> Tuple[str, List[Dict[str, str]]]:
    """
    处理 Markdown 中的图片引用

    对每个本地图片：
    1. 上传到 MinIO
    2. 替换路径为 MinIO URL
    3. 追加 [关联图片: alt | 图片链接: URL]

    返回: (处理后的 markdown 文本, 图片信息列表)
    """
    img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    all_images = []  # 全局图片列表（所有 chunk 共用）

    def _replace_image(match):
        alt = match.group(1)
        img_ref = match.group(2)

        # 跳过网络图片
        if img_ref.startswith("http://") or img_ref.startswith("https://"):
            return match.group(0)

        # 解析本地路径
        src_path = os.path.join(md_base_dir, img_ref) if not os.path.isabs(img_ref) else img_ref
        if not os.path.exists(src_path):
            print(f"[process_md] 图片不存在: {src_path} (ref={img_ref}, base={md_base_dir})")
            return match.group(0)

        # 上传 MinIO
        ext = os.path.splitext(src_path)[1]
        object_name = os.path.basename(src_path)
        minio_url = upload_to_minio(src_path, object_name)

        if not minio_url:
            print(f"[process_md] MinIO 上传失败: {src_path}")
            return match.group(0)

        # 记录图片信息
        all_images.append({"alt": alt, "url": minio_url, "object_name": object_name})
        print(f"[process_md] 图片已处理: {alt} → {minio_url[:60]}...")

        # 替换本地路径为 MinIO URL + 追加关联图片信息
        replaced = f"![{alt}]({minio_url})"
        info_line = f"\n\n[关联图片: {alt} | 图片链接: {minio_url}]"
        return replaced + info_line

    processed = img_pattern.sub(_replace_image, md_content)
    return processed, all_images


# ============================================================
# 父子切块 + 存入 Milvus（独立使用）
# ============================================================

def parent_child_split(
    text: str,
    images: List[Dict[str, str]],
    parent_size: int = 1200,
    child_size: int = 400,
) -> Tuple[List[Document], List[Document]]:
    """
    父子切块：
    - 父块：大粒度，保留完整章节上下文
    - 子块：小粒度，用于精确匹配，继承父块图片 URL
    """
    parent_splitter = MarkdownTextSplitter(chunk_size=parent_size, chunk_overlap=100)
    child_splitter = MarkdownTextSplitter(chunk_size=child_size, chunk_overlap=50)

    parent_docs = parent_splitter.create_documents([text])

    # 全局图片 URL 列表（JSON）
    all_image_urls = [img["url"] for img in images]

    child_docs = []
    for p_doc in parent_docs:
        # 父块 ID
        parent_id = str(uuid.uuid4())
        p_doc.metadata["id"] = parent_id
        p_doc.metadata["chunk_type"] = "parent"
        p_doc.metadata["images"] = json.dumps(all_image_urls, ensure_ascii=False)

        # 子块切分
        sub_docs = child_splitter.create_documents([p_doc.page_content])
        for sub in sub_docs:
            sub.metadata["id"] = str(uuid.uuid4())
            sub.metadata["chunk_type"] = "child"
            sub.metadata["parent_id"] = parent_id
            sub.metadata["images"] = json.dumps(all_image_urls, ensure_ascii=False)
            child_docs.append(sub)

    return parent_docs, child_docs


# ============================================================
# 存入 Milvus
# ============================================================

async def store_to_milvus(
    child_docs: List[Document],
    kb_id: int,
    doc_id: int,
    collection_name: str = None,
):
    """将子块存入 Milvus 向量数据库"""
    if not child_docs:
        return 0
    from app.services.vector_store import insert_vectors, ensure_collection, get_collection_name as _gc

    texts = [doc.page_content for doc in child_docs]
    embeddings = await get_embeddings(texts)
    sparse_vecs = encode_sparse(texts)

    records = []
    for i, (doc, emb) in enumerate(zip(child_docs, embeddings)):
        vid = str(uuid.uuid4())
        sv = sparse_vecs[i] if i < len(sparse_vecs) else {0: 1e-6}
        records.append({
            "id": vid,
            "text": doc.page_content,
            "vector": emb,
            "sparse_vector": sv,
            "doc_id": doc_id,
            "kb_id": kb_id,
            "chunk_id": 0,
            "content_type": "text",
            "chunk_type": doc.metadata.get("chunk_type", "child"),
            "parent_chunk_id": 0,
        })

    ensure_collection(kb_id)
    insert_vectors(kb_id, records)

    return len(records)


# ============================================================
# 完整处理入口：ZIP → Markdown 改写
# ============================================================

def process_zip(
    file_content: bytes,
    filename: str,
    kb_id: int,
    doc_id: int,
) -> Tuple[str, List[Dict[str, str]], str]:
    """
    ZIP 解压 → 找 .md → 图片上传 MinIO → Markdown 改写

    返回: (处理后的 markdown 文本, 图片信息列表, md 文件名)
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".zip":
        tmpdir = tempfile.mkdtemp()
        with zipfile.ZipFile(io.BytesIO(file_content)) as zf:
            print(f"[process_zip] ZIP files: {zf.namelist()}")
            # 修复 macOS 中文编码：逐文件提取并用 utf-8 解码文件名
            for member in zf.infolist():
                if "__MACOSX" in member.filename or member.is_dir():
                    continue
                try:
                    real_name = member.filename.encode("cp437").decode("utf-8")
                except (UnicodeDecodeError, UnicodeEncodeError):
                    real_name = member.filename
                dest = os.path.join(tmpdir, real_name)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with zf.open(member) as src, open(dest, "wb") as dst:
                    dst.write(src.read())
        md_files = list(Path(tmpdir).rglob("*.md"))
        if not md_files:
            raise ValueError("ZIP 包中未找到 .md 文件")
        md_path = str(md_files[0])
        md_base_dir = os.path.dirname(md_path)
        md_filename = os.path.basename(md_path)
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
    else:
        raise ValueError(f"不支持的文件类型: {ext}")

    # 解析图片 → MinIO → 改写
    processed_md, images = process_markdown_images(md_content, md_base_dir, kb_id, doc_id)
    print(f"[process_zip] 处理完成: md_base={md_base_dir}, 图片数={len(images)}, md前300字={processed_md[:300]}")
    return processed_md, images, md_filename


async def process_and_store(
    file_content: bytes,
    filename: str,
    kb_id: int,
    doc_id: int,
) -> dict:
    """
    完整处理流程（独立使用）：
    ZIP 解压 → Markdown 改写 → 父子切块 → Milvus 入库
    """
    processed_md, images, _ = process_zip(file_content, filename, kb_id, doc_id)
    parent_docs, child_docs = parent_child_split(processed_md, images)

    count = await store_to_milvus(child_docs, kb_id, doc_id)

    return {
        "status": "completed",
        "chunk_count": count,
        "parent_count": len(parent_docs),
        "child_count": len(child_docs),
        "image_count": len(images),
        "images": images,
    }
