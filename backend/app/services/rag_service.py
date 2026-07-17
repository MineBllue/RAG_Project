import json
import asyncio
import logging
from typing import List, AsyncGenerator, Optional
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.knowledge_base import KnowledgeBase, Document, DocumentStatus
from app.services.llm_service import chat_stream
from app.services.query_rewriter import rewrite_query
from app.services.reranker import rerank
from app.services.evaluator import run_evaluation
from app.services.retrieval_strategies import select_strategy, execute_strategy

settings = get_settings()
logger = logging.getLogger(__name__)

RAG_PROMPT = """你是一个企业知识库智能助手。请根据以下知识库内容回答用户问题。
要求：基于内容回答，专业准确简洁，使用中文。引用来源时在句末标注序号，如 [1]、[2]。

## 知识库内容
{context}

## 用户问题
{question}

## 回答（请在引用文档内容时标注来源序号，如 [1]）"""


def build_rag_prompt(question: str, contexts: List[str]) -> str:
    return RAG_PROMPT.format(context="\n\n---\n\n".join(contexts), question=question)


async def rag_query(
    question: str, kb_ids: List[int], db: Session = None,
    use_rewrite: bool = True, use_rerank: bool = True, use_intent: bool = True,
    history_messages: Optional[List[dict]] = None,
    temperature: float = 0.3, top_p: float = 0.85, max_tokens: int = 2048, history_rounds: int = 5,
) -> AsyncGenerator[str, None]:
    sources, queries = [], [question]

    # FAQ 缓存命中
    if db:
        try:
            import concurrent.futures
            from app.services.faq_stats_service import check_stats_cache, record_query
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                await loop.run_in_executor(pool, record_query, db, question)
            cached = await check_stats_cache(question)
            if cached:
                logger.info("FAQ cache HIT: '%s' → %d chars", question[:60], len(cached))
                yield cached
                return
        except Exception:
            pass

    # 意图识别
    if use_intent:
        try:
            from app.services.intent_recognizer import recognize_intent as llm_intent
            need_rag = await llm_intent(question)
            if not need_rag:
                logger.info("Intent: non-RAG '%s', returning greeting", question[:40])
                yield "您好！我是企业知识库助手，请问有什么技术问题需要我帮您检索？"
                return
        except:
            pass

    # 策略选择
    strategy = "direct"
    if use_rewrite and kb_ids:
        try:
            strategy = select_strategy(question)
            logger.info("Strategy '%s' for '%s'", strategy, question[:60])
        except:
            pass

    # Query 改写
    queries = [question]
    if use_rewrite and kb_ids and strategy == "direct":
        try:
            queries = await rewrite_query(question)
        except:
            pass

    # 执行检索
    items = await execute_strategy(strategy, question, kb_ids, top_k=8)
    logger.debug("Retrieved %d items via strategy '%s'", len(items), strategy)

    # Reranker 精排
    if use_rerank and len(items) > 1:
        try:
            ranked = rerank(question, [it["text"] for it in items], top_k=5)
            rm = {r["text"]: r.get("rerank_score", 0) for r in ranked}
            for it in items:
                if it["text"] in rm:
                    it["final_score"] = rm[it["text"]]
            items.sort(key=lambda x: x.get("final_score", 0), reverse=True)
            items = items[:5]
            logger.debug("Reranked: %d → %d items", len(items), len(ranked))
        except: pass

    all_contexts = [it["text"] for it in items]

    sources = [{
        "text": it["text"][:150],
        "score": round(max(filter(None, [
            it.get("final_score"), it.get("dense_score"),
            it.get("rerank_score"), it.get("score"),
        ])), 3) if any(it.get(k) for k in ["final_score","dense_score","rerank_score","score"]) else 0,
        "kb_id": it.get("kb_id") if it.get("kb_id") else (kb_ids[0] if kb_ids else 0),
        "doc_id": it.get("doc_id", 0),
    } for it in items]

    # 来源名称
    source_info = []
    if sources and kb_ids:
        _db = db or SessionLocal()
        try:
            kb_ids_in_sources = list({s["kb_id"] for s in sources if s.get("kb_id")})
            kb_map = {kb.id: kb.name for kb in _db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(kb_ids_in_sources or kb_ids)).all()} if kb_ids_in_sources else {k: f"知识库{k}" for k in kb_ids}
            doc_map = {}
            for s in sources:
                if s.get("doc_id") and s["doc_id"] not in doc_map:
                    d = _db.query(Document).filter(Document.id == s["doc_id"]).first()
                    doc_map[s["doc_id"]] = d.filename if d else f"文档#{s['doc_id']}"
            seen = set()
            for s in sources:
                k2 = (s.get("kb_id", 0), s.get("doc_id", 0))
                if k2 not in seen and (s.get("kb_id") or s.get("doc_id")):
                    seen.add(k2)
                    kb_name = kb_map.get(s["kb_id"], f"知识库{s['kb_id']}") if s.get("kb_id") else "未知知识库"
                    doc_name = doc_map.get(s.get("doc_id", 0), f"文档#{s.get('doc_id', 0)}")
                    source_info.append({"kb_name": kb_name, "doc_name": doc_name, "score": s["score"]})
        finally:
            if not db: _db.close()

    # 上下文
    if source_info:
        parts = [f"[{i+1}] {si['kb_name']} / {si['doc_name']}:\n{all_contexts[i] if i<len(all_contexts) else ''}" for i, si in enumerate(source_info[:5])]
        ctx = "\n\n".join(parts)
    else:
        ctx = "\n\n---\n\n".join(all_contexts[:8]) if all_contexts else "暂无相关内容。"

    # 消息 + 流式生成
    msgs = (history_messages[-(history_rounds * 2):] if history_messages else []) + [{"role": "user", "content": build_rag_prompt(question, [ctx])}]
    full = ""
    async for chunk in chat_stream(msgs, temperature=temperature, top_p=top_p, max_tokens=max_tokens):
        full += chunk; yield chunk
    logger.info("RAG answer generated: '%s' → %d chars", question[:60], len(full))

    # ---- 关键词快速评估（同步，即时展示） ----
    keyword_eval = run_evaluation(question, full, all_contexts)
    payload = {
        "sources": source_info,
        "evaluation": {
            "context_relevance": keyword_eval["context_relevance"],
            "context_recall": keyword_eval["context_recall"],
            "context_precision": keyword_eval["context_precision"],
            "faithfulness": keyword_eval["faithfulness"],
            "answer_relevance": keyword_eval["answer_relevance"],
            "avg": keyword_eval["avg_score"],
            "method": "keyword",
        },
    }
    yield "\n\n---SOURCES---\n" + json.dumps(payload, ensure_ascii=False)

    # 保存到 FAQ
    if db and full:
        try:
            from app.services.faq_stats_service import update_answer
            import concurrent.futures
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                await loop.run_in_executor(pool, update_answer, db, question, full)
        except Exception:
            pass
