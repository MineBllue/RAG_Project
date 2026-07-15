import json
import os
import io
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase, Document, DocumentChunk, DocumentStatus
from app.services.document_parser import process_document
from app.services.deep_parser import deep_parse
from app.services.image_rag_qa import image_qa_query
from app.services.deep_parser import ocr_image
from app.services.vector_store import insert_vectors, delete_collection
from app.services.sparse_embedding import encode_sparse
from app.services.llm_service import get_embeddings
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


class KBCreate(BaseModel):
    name: str
    description: str = ""


class KBUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


@router.get("/list")
def list_kb(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    kbs = db.query(KnowledgeBase).order_by(KnowledgeBase.updated_at.desc()).all()
    return [
        {"id": kb.id, "name": kb.name, "description": kb.description,
         "doc_count": db.query(Document).filter(Document.knowledge_base_id == kb.id).count(),
         "created_at": kb.created_at.isoformat(), "updated_at": kb.updated_at.isoformat()}
        for kb in kbs
    ]


@router.post("/create")
def create_kb(req: KBCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    kb = KnowledgeBase(name=req.name, description=req.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return {"id": kb.id, "name": kb.name, "message": "知识库创建成功"}


@router.delete("/{kb_id}")
def delete_kb(kb_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    try:
        delete_collection(kb_id)
    except Exception:
        pass
    db.delete(kb)
    db.commit()
    return {"message": "知识库已删除"}


@router.get("/{kb_id}/documents")
def list_documents(kb_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    docs = db.query(Document).filter(Document.knowledge_base_id == kb_id).order_by(Document.created_at.desc()).all()
    return [
        {"id": d.id, "filename": d.filename, "file_type": d.file_type,
         "file_size": d.file_size, "status": d.status, "chunk_count": d.chunk_count,
         "created_at": d.created_at.isoformat()}
        for d in docs
    ]


@router.get("/{kb_id}/documents/{doc_id}/chunks")
def list_chunks(kb_id: int, doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.knowledge_base_id == kb_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.chunk_index).all()
    return [
        {"id": c.id, "chunk_index": c.chunk_index, "content": c.content, "chunk_hash": c.chunk_hash}
        for c in chunks
    ]
@router.delete("/{kb_id}/documents/{doc_id}")
def delete_document(kb_id: int, doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.knowledge_base_id == kb_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
    db.delete(doc)
    db.commit()
    import os
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    return {"message": "文档已删除"}




@router.delete("/{kb_id}/documents/{doc_id}/chunks/{chunk_id}")
def delete_chunk(kb_id: int, doc_id: int, chunk_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id, DocumentChunk.document_id == doc_id).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="分块不存在")
    db.delete(chunk)
    db.commit()
    return {"message": "分块已删除"}


@router.put("/{kb_id}/documents/{doc_id}/chunks/{chunk_id}")
def update_chunk(kb_id: int, doc_id: int, chunk_id: int, content: str = Form(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id, DocumentChunk.document_id == doc_id).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="分块不存在")
    chunk.content = content
    db.commit()
    return {"message": "分块已更新", "content": content}


@router.post("/{kb_id}/upload")
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    chunk_size: int = Form(None),
    chunk_overlap: int = Form(None),
    chunk_method: str = Form("default"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    import re, shutil
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    ext = os.path.splitext(file.filename)[1].lower()
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(settings.upload_dir, str(kb_id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_filename)

    content = await file.read()

    # 先创建 Document 记录拿 doc.id（后续 OCR/MinIO 上传需要）
    doc = Document(
        knowledge_base_id=kb_id,
        filename=file.filename,
        file_type=ext,
        file_size=len(content),
        file_path=file_path,
        status=DocumentStatus.PARSING.value,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    doc.chunk_method = chunk_method
    db.commit()

    # ZIP 包支持：解压后找 .md + .assets 文件夹
    if ext == ".zip":
        from app.services.markdown_image_processor import process_zip
        try:
            processed_md, images, md_filename = process_zip(content, file.filename, kb_id, doc.id)
            # 保存改写后的 MD 到 upload_dir
            processed_md_path = os.path.join(upload_dir, safe_filename.replace(".zip", ".processed.md"))
            with open(processed_md_path, "w", encoding="utf-8") as f:
                f.write(processed_md)
            text_for_parsing = processed_md_path
            md_content = None  # 图片已处理完毕，不再走 md 图片处理
        except Exception as e:
            doc.status = DocumentStatus.FAILED.value
            db.commit()
            raise HTTPException(status_code=500, detail=f"ZIP 处理失败: {str(e)}")

    # 普通 .md 文件（无 assets 目录，无图片处理）
    elif ext in (".md", ".markdown"):
        with open(file_path, "wb") as f:
            f.write(content)
        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        md_base = os.path.dirname(file_path)
        md_path = file_path
    else:
        # 非 md 文件正常写入
        with open(file_path, "wb") as f:
            f.write(content)
        md_content = None

    # 处理 Markdown 中的图片引用
    text_for_parsing = file_path
    if md_content is not None:
        try:
            img_dir = os.path.join(upload_dir, "images")
            os.makedirs(img_dir, exist_ok=True)
            processed_lines = []
            img_idx = 0
            for line in md_content.split("\n"):
                m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
                if m:
                    # 图片行 → OCR + MinIO 替换（不保留原始行）
                    alt, img_ref = m.group(1), m.group(2)
                    if not img_ref.startswith("http"):
                        src_path = os.path.join(md_base, img_ref) if not os.path.isabs(img_ref) else img_ref
                        if os.path.exists(src_path):
                            ext2 = os.path.splitext(src_path)[1]
                            ocr_text = ocr_image(src_path)
                            minio_url = None
                            try:
                                from app.services.minio_store import upload_image
                                object_name = f"{kb_id}/{doc.id}/{img_idx:04d}{ext2}"
                                minio_url = upload_image(src_path, object_name, kb_id, doc.id)
                            except Exception:
                                pass
                            parts = []
                            if ocr_text:
                                parts.append(f"[图片OCR: {ocr_text[:500]}]")
                            if minio_url:
                                parts.append(f"[图片链接: {minio_url}]")
                            if not parts:
                                parts.append(f"[图片: {alt} ({img_ref})]")
                            if parts:
                                processed_lines.append(" ".join(parts))  # 替换原图行
                            img_idx += 1
                        else:
                            processed_lines.append(line)  # 图片文件不存在，保留原文
                    else:
                        processed_lines.append(line)  # 外部链接保留原文
                else:
                    processed_lines.append(line)  # 普通文本行保留
            processed_md = "\n".join(processed_lines)
            # ZIP 解压或直接上传 .md：保存处理后的文本
            if ext == ".zip":
                processed_path = os.path.join(upload_dir, safe_filename.replace(".zip", ".processed.md"))
            else:
                processed_path = file_path + ".processed.md"
            with open(processed_path, "w", encoding="utf-8") as f:
                f.write(processed_md)
            text_for_parsing = processed_path
        except Exception:
            pass

    try:
        # 深度解析：PDF/DOCX 先提取表格和 OCR
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in (".pdf", ".docx", ".doc"):
            try:
                deep_result = deep_parse(text_for_parsing)
                deep_text_path = text_for_parsing + ".deep.txt"
                with open(deep_text_path, "w", encoding="utf-8") as f:
                    f.write(deep_result["text"])
                text_for_parsing = deep_text_path
            except Exception:
                pass

        # overlap 按 chunk_size 的 20%
        cs = chunk_size or settings.chunk_size
        co = chunk_overlap if chunk_overlap is not None else int(cs * 0.2)
        result = process_document(text_for_parsing, cs, co, chunk_method)
        chunks = result["chunks"]
        if not chunks:
            raise ValueError("文档解析后无有效内容块，请检查文档是否为空")
        doc.chunk_count = len(chunks)
        doc.status = DocumentStatus.COMPLETED.value
        db.commit()

        db_chunks = []
        for c in chunks:
            db_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=c["chunk_index"],
                content=c["content"],
                chunk_hash=c["chunk_hash"],
           )
            db_chunk.chunk_type = c.get("chunk_type", "child")
            db_chunk.parent_chunk_id = c.get("parent_chunk_id")
            db_chunk.metadata_json = c.get("metadata", "{}")
            db.add(db_chunk)
            db_chunks.append(db_chunk)
        db.commit()

        texts = [c["content"] for c in chunks]
        embeddings = await get_embeddings(texts)
        if not embeddings or len(embeddings) != len(texts):
            raise ValueError(f"向量化失败：期望 {len(texts)} 个向量，实际获取 {len(embeddings) if embeddings else 0} 个。请检查 DASHSCOPE_API_KEY 是否正确")
        # 生成稀疏向量
        sparse_vecs = encode_sparse(texts)

        records = []
        for i, (db_chunk, emb) in enumerate(zip(db_chunks, embeddings)):
            vid = str(uuid.uuid4())
            db_chunk.milvus_id = vid
            sv = sparse_vecs[i] if i < len(sparse_vecs) else {0: 1e-6}
            record = {"id": vid, "text": db_chunk.content, "vector": emb, "sparse_vector": sv, "doc_id": doc.id, "kb_id": kb_id, "chunk_id": db_chunk.id, "content_type": "text", "chunk_type": db_chunk.chunk_type, "parent_chunk_id": db_chunk.parent_chunk_id or 0}
            records.append(record)
        db.commit()
        try:
            insert_vectors(kb_id, records)
        except Exception as milvus_err:
            raise ValueError(f"向量存储失败（Milvus 可能未启动）: {milvus_err}")

    except Exception as e:
        doc.status = DocumentStatus.FAILED.value
        db.commit()
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")

    return {"id": doc.id, "filename": doc.filename, "status": doc.status, "chunk_count": doc.chunk_count}
from concurrent.futures import ThreadPoolExecutor, as_completed


@router.post("/{kb_id}/upload-batch")
async def upload_documents_batch(
    kb_id: int,
    files: List[UploadFile] = File(...),
    chunk_size: int = Form(None),
    chunk_overlap: int = Form(None),
    chunk_method: str = Form("default"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量上传文档"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    upload_dir = os.path.join(settings.upload_dir, str(kb_id))
    os.makedirs(upload_dir, exist_ok=True)

    async def process_one(file: UploadFile) -> dict:
        import re, shutil, uuid
        ext = os.path.splitext(file.filename)[1].lower()
        safe_filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, safe_filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        doc = Document(knowledge_base_id=kb_id, filename=file.filename, file_type=ext, file_size=len(content), file_path=file_path, status=DocumentStatus.PARSING.value)
        db.add(doc); db.commit(); db.refresh(doc)

        try:
            text_for_parsing = file_path
            if ext == ".zip":
                from app.services.markdown_image_processor import process_zip
                processed_md, images, md_filename = process_zip(content, file.filename, kb_id, doc.id)
                processed_md_path = os.path.join(upload_dir, safe_filename.replace(".zip", ".processed.md"))
                with open(processed_md_path, "w", encoding="utf-8") as f:
                    f.write(processed_md)
                text_for_parsing = processed_md_path
            elif ext in (".md", ".markdown"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f: md_content = f.read()
                    img_dir = os.path.join(upload_dir, "images"); os.makedirs(img_dir, exist_ok=True)
                    md_base = os.path.dirname(file_path)
                    processed_lines = []
                    for line in md_content.split("\n"):
                        processed_lines.append(line)
                        m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
                        if m:
                            alt, img_ref = m.group(1), m.group(2)
                            if not img_ref.startswith("http"):
                                src_path = os.path.join(md_base, img_ref) if not os.path.isabs(img_ref) else img_ref
                                if os.path.exists(src_path):
                                    dest_name = f"img_{kb_id}_{doc.id}_0{os.path.splitext(src_path)[1]}"
                                    shutil.copy2(src_path, os.path.join(img_dir, dest_name))
                    processed_file = file_path + ".processed.md"
                    with open(processed_file, "w", encoding="utf-8") as f: f.write("\n".join(processed_lines))
                    text_for_parsing = processed_file
                except: pass

            if ext in (".pdf", ".docx", ".doc"):
                try:
                    from app.services.deep_parser import deep_parse
                    dr = deep_parse(text_for_parsing)
                    deep_path = text_for_parsing + ".deep.txt"
                    with open(deep_path, "w", encoding="utf-8") as f: f.write(dr["text"])
                    text_for_parsing = deep_path
                except: pass

            from app.services.document_parser import process_document
            cs = chunk_size or settings.chunk_size
            co = chunk_overlap if chunk_overlap is not None else int(cs * 0.2)
            result = process_document(text_for_parsing, cs, co, chunk_method)
            chunks = result["chunks"]
            if not chunks: raise ValueError("文档无有效内容")

            doc.chunk_count = len(chunks); doc.status = DocumentStatus.COMPLETED.value; db.commit()

            db_chunks = []
            for c in chunks:
                dc = DocumentChunk(document_id=doc.id, chunk_index=c["chunk_index"], content=c["content"], chunk_hash=c["chunk_hash"], chunk_type=c.get("chunk_type", "child"), parent_chunk_id=c.get("parent_chunk_id"), metadata_json=c.get("metadata", "{}"))
                db.add(dc); db_chunks.append(dc)
            db.commit()

            texts = [c["content"] for c in chunks]
            from app.services.llm_service import get_embeddings
            embeddings = await get_embeddings(texts)
            from app.services.sparse_embedding import encode_sparse
            sparse_vecs = encode_sparse(texts)

            records = []
            for i, (dc, emb) in enumerate(zip(db_chunks, embeddings)):
                vid = str(uuid.uuid4()); dc.milvus_id = vid
                sv = sparse_vecs[i] if i < len(sparse_vecs) else {0: 1e-6}
                records.append({"id": vid, "text": dc.content, "vector": emb, "sparse_vector": sv, "doc_id": doc.id, "kb_id": kb_id, "chunk_id": dc.id, "content_type": "text", "chunk_type": dc.chunk_type, "parent_chunk_id": dc.parent_chunk_id or 0})
            db.commit()

            from app.services.vector_store import insert_vectors
            insert_vectors(kb_id, records)
            return {"filename": file.filename, "status": "completed", "chunks": len(chunks)}
        except Exception as e:
            doc.status = DocumentStatus.FAILED.value; db.commit()
            return {"filename": file.filename, "status": "failed", "error": str(e)}

    results = []
    for file in files:
        r = await process_one(file)
        results.append(r)

    return {"kb_id": kb_id, "total": len(results), "succeeded": sum(1 for r in results if r["status"] == "completed"), "failed": sum(1 for r in results if r["status"] == "failed"), "results": results}


# ==================== 图片 RAG 问答 ====================

class ImageQARequest(BaseModel):
    question: str
    kb_ids: List[int]
    top_k: int = 8
    temperature: float = 0.3
    max_tokens: int = 2048


@router.post("/image-qa")
async def image_qa(
    req: ImageQARequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """多模态图片 RAG 问答（流式）"""
    from fastapi.responses import StreamingResponse

    async def generate():
        full = ""
        sources_data = {}
        try:
            async for chunk in image_qa_query(
                question=req.question,
                kb_ids=req.kb_ids,
                top_k=req.top_k,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            ):
                if "\n---SOURCES---\n" in chunk:
                    parts = chunk.split("\n---SOURCES---\n", 1)
                    if parts[0]:
                        full += parts[0]
                        yield f"data: {json.dumps({'content': parts[0], 'done': False})}\n\n"
                    try:
                        sources_data = json.loads(parts[1].strip())
                    except Exception:
                        pass
                else:
                    full += chunk
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'content': '', 'done': True, 'error': str(e)})}\n\n"
            return
        yield f"data: {json.dumps({'content': '', 'done': True, 'sources': sources_data})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
