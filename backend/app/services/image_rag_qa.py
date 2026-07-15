
"""
RAG 图片问答系统 —— 多模态视觉语言模型

问答流程:
  用户 query
    → hybrid_search 混合检索
    → 从检索文本提取 [关联图片: ... | 图片链接: URL]
    → 有图片: 下载 base64 → qwen-vl-max 多模态理解
    → 无图片: 纯文本 LLM 回答
"""
import os
import re
import json
import base64
from typing import List, Optional, AsyncGenerator
from io import BytesIO

from app.services.hybrid_retrieval import hybrid_search
from app.services.reranker import rerank
from app.services.llm_service import chat_stream
from app.services.markdown_image_processor import download_image_to_base64
from app.core.config import get_settings

settings = get_settings()

VISION_MODEL = "qwen-vl-max"
TEXT_MODEL = settings.llm_model

# 从检索文本中提取图片链接的模式
IMG_PATTERN = re.compile(r'\[关联图片:.*?\|\s*图片链接:\s*(https?://[^\]]+)\]')


def extract_image_urls(text: str) -> List[str]:
    """从文本中提取所有关联图片的 URL"""
    return [m.group(1).strip() for m in IMG_PATTERN.finditer(text)]


async def image_qa_query(
    question: str,
    kb_ids: List[int],
    top_k: int = 8,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> AsyncGenerator[str, None]:
    """
    图片感知 RAG 问答（流式）

    1. 混合检索 + Reranker
    2. 提取图片 URL
    3. 有图 → qwen-vl-max 多模态
    4. 无图 → 纯文本 LLM
    """
    # Step 1: 混合检索
    results = await hybrid_search(question, kb_ids, dense_weight=0.7, top_k=top_k * 2)

    if not results:
        yield "知识库中没有相关内容。"
        return

    # Step 2: Reranker 精排
    texts = [r["text"] for r in results]
    try:
        ranked = rerank(question, texts, top_k=min(top_k, len(texts)))
        rm = {r["text"]: r["rerank_score"] for r in ranked}
        for r in results:
            if r["text"] in rm:
                r["final_score"] = rm[r["text"]]
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        results = results[:top_k]
    except Exception:
        results = results[:top_k]

    # 合并上下文
    contexts = [r["text"] for r in results]
    context_text = "\n\n---\n\n".join(contexts)

    # Step 3: 提取图片 URL
    image_urls = extract_image_urls(context_text)

    if image_urls:
        # --- 多模态路径 ---
        yield f"[检测到 {len(image_urls)} 张关联图片，使用多模态模型分析...]\n\n"

        # 下载图片 base64
        image_b64_list = []
        for url in image_urls[:3]:  # 最多 3 张
            b64 = download_image_to_base64(url)
            if b64:
                image_b64_list.append(b64)

        vision_prompt = f"""你是一个技术文档分析助手。请根据以下文档内容和关联图片，回答用户问题。

## 文档内容
{context_text[:4000]}

## 用户问题
{question}

## 要求
1. 结合图片中的流程/架构信息进行分析
2. 用中文回答，专业准确简洁
3. 如果图片中有流程图，请描述关键步骤"""

        if image_b64_list:
            # 构建多模态消息
            messages = [{"role": "user", "content": [{"type": "text", "text": vision_prompt}]}]
            for b64 in image_b64_list:
                messages[0]["content"].append({"type": "image_url", "image_url": {"url": b64}})

            full = ""
            async for chunk in chat_stream(
                messages,
                model=VISION_MODEL,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                full += chunk
                yield chunk
        else:
            # 图片下载失败，降级纯文本
            yield "（图片下载失败，切换纯文本模式）\n\n"
            full = ""
            async for chunk in chat_stream(
                [{"role": "user", "content": f"## 上下文\n{context_text[:4000]}\n\n## 问题\n{question}"}],
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                full += chunk
                yield chunk
    else:
        # --- 纯文本路径 ---
        text_prompt = f"""你是一个企业知识库智能助手。请根据以下知识库内容回答用户问题。

## 知识库内容
{context_text[:4000]}

## 用户问题
{question}

## 回答"""
        full = ""
        async for chunk in chat_stream(
            [{"role": "user", "content": text_prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            full += chunk
            yield chunk

    # 附加来源信息
    sources = []
    for r in results[:5]:
        urls = extract_image_urls(r["text"])
        sources.append({
            "text": r["text"][:150],
            "score": round(r.get("final_score", r.get("score", 0)), 3),
            "images": urls,
        })

    yield "\n\n---SOURCES---\n" + json.dumps({
        "sources": sources,
        "model_used": VISION_MODEL if image_urls else TEXT_MODEL,
        "image_count": len(image_urls),
    }, ensure_ascii=False)
