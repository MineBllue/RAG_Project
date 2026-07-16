import json
from typing import List, AsyncGenerator, Optional
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.knowledge_base import KnowledgeBase, Document, DocumentStatus
from app.services.llm_service import chat_stream
from app.services.query_rewriter import rewrite_query
from app.services.reranker import rerank
from app.services.evaluator import run_evaluation, _llm_evaluate, apply_llm_result
from app.services.faq_service import search_faq, save_faq
from app.services.retrieval_strategies import select_strategy, execute_strategy

settings = get_settings()

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
            cached = await search_faq(db, question, threshold=0.9)
            if cached:
                yield cached
                return
        except: pass

    # 意图识别
    if use_intent:
        try:
            from app.services.intent_recognizer import recognize_intent as llm_intent
            need_rag = await llm_intent(question)
            if not need_rag:
                yield "您好！我是企业知识库助手，请问有什么技术问题需要我帮您检索？"
                return
        except: pass

    # 策略选择: 直接 / HyDE / 子问题 / 回溯
    strategy = "direct"
    if use_rewrite and kb_ids:
        try:
            strategy = await select_strategy(question)
        except:
            pass

    # Query 改写（直接检索策略下使用）
    queries = [question]
    if use_rewrite and kb_ids and strategy == "direct":
        try:
            queries = await rewrite_query(question)
        except:
            pass

    # 执行检索策略
    items = await execute_strategy(strategy, question, kb_ids, top_k=8)

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
        except: pass

    all_contexts = [it["text"] for it in items]

    sources = [{
        "text": it["text"][:150],
        "score": round(max(
            it.get("final_score", 0) or 0,
            it.get("dense_score", 0) or 0,
            it.get("score", 0) or 0,
        ), 3),
        "kb_id": it.get("kb_id") or (kb_ids[0] if kb_ids else 0),
        "doc_id": it.get("doc_id", 0),
    } for it in items]
    print(f"[rag_query] 原始检索分数: {[(it.get('final_score'), it.get('dense_score'), it.get('score')) for it in items]}")

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
                    doc_map[s["doc_id"]] = d.filename if d else "未知"
            seen = set()
            for s in sources:
                k2 = (s.get("kb_id", 0), s.get("doc_id", 0))
                if k2 not in seen and s.get("kb_id"):
                    seen.add(k2)
                    source_info.append({
                        "kb_name": kb_map.get(s["kb_id"], f"知识库{s['kb_id']}"),
                        "doc_name": doc_map.get(s.get("doc_id", 0)) if s.get("doc_id") and s["doc_id"] in doc_map else "文档片段",
                        "score": s["score"],
                    })
        finally:
            if not db: _db.close()

    # 上下文
    if source_info:
        parts = [f"[{i+1}] {si['kb_name']} / {si['doc_name']}:\n{all_contexts[i] if i<len(all_contexts) else ''}" for i, si in enumerate(source_info[:5])]
        ctx = "\n\n".join(parts)
    else:
        ctx = "\n\n---\n\n".join(all_contexts[:8]) if all_contexts else "暂无相关内容。"

    # 消息
    msgs = (history_messages[-(history_rounds * 2):] if history_messages else []) + [{"role": "user", "content": build_rag_prompt(question, [ctx])}]

    # 流式
    full = ""
    async for chunk in chat_stream(msgs, temperature=temperature, top_p=top_p, max_tokens=max_tokens):

        full += chunk; yield chunk


    # 评估 + 来源
    eval_result = None
    try:

        eval_result = run_evaluation(question, full, all_contexts, use_llm=False)

        # LLM 精评

        llm_scores = await _llm_evaluate(question, full, all_contexts)

        if llm_scores:

           eval_result = apply_llm_result(eval_result, llm_scores)
    except:

        pass


    payload = {"sources": source_info, "evaluation": None}
    if eval_result:
        payload["evaluation"] = {

            "context_relevance": eval_result["context_relevance"],
            "faithfulness": eval_result["faithfulness"],
            "answer_relevance": eval_result.get("answer_relevance", 0),
            "avg": eval_result["avg_score"],
            "method": eval_result.get("method", "keyword"),
            "reason": eval_result.get("reason", ""),
        }
    yield "\n\n---SOURCES---\n" + json.dumps(payload, ensure_ascii=False)


    # 保存到 FAQ
    if db and full:
        try: await save_faq(db, question, full)
        except: pass
