"""
检索服务 — 直接混合检索 + Corrective RAG 按需重查

流程:
  1. 直接 Dense+Sparse 混合检索 → Reranker 精排
  2. LLM 生成回答时自我评估
  3. 如果回答不够好 → LLM 改写 query → 再检索一轮 → 合并
"""
from typing import List
import logging

from app.services.llm_service import chat_stream
from app.services.hybrid_retrieval import hybrid_search

logger = logging.getLogger(__name__)


async def retrieve(query: str, kb_ids: List[int], top_k: int = 5) -> List[dict]:
    """直接混合检索（Dense+Sparse），多 query 去重合并"""
    all_items = {}
    r_list = await hybrid_search(query, kb_ids, dense_weight=0.7, top_k=top_k)
    for r in r_list:
        k = r["text"][:120]
        r.setdefault("doc_id", 0)
        r.setdefault("kb_id", 0)
        if k not in all_items or r["final_score"] > all_items[k].get("final_score", 0):
            all_items[k] = r
    items = sorted(all_items.values(), key=lambda x: x.get("final_score", 0), reverse=True)
    return items[:top_k]


REQUERY_PROMPT = """你是一个检索优化助手。当前的检索结果可能不足以回答用户问题。
请将用户问题改写为一个更精准的检索查询（20字以内），以便从知识库中找到需要的信息。
只返回改写后的查询，不要解释。

用户问题: {question}

改写查询:"""


async def requery_if_needed(question: str, kb_ids: List[int], existing_results: List[dict], top_k: int = 5) -> List[dict]:
    """
    Corrective RAG 重查：让 LLM 改写 query，再用新 query 检索一轮。
    返回新检索到的结果（与已有结果合并后去重）。
    """
    try:
        msgs = [{"role": "user", "content": REQUERY_PROMPT.format(question=question)}]
        new_query = ""
        async for chunk in chat_stream(msgs, temperature=0.1, max_tokens=40):
            new_query += chunk
        new_query = new_query.strip()

        if not new_query or new_query == question or len(new_query) < 3:
            logger.debug("Requery: no valid rewrite, skipping")
            return []

        logger.info("Requery: '%s' → '%s'", question[:40], new_query[:40])
        new_results = await retrieve(new_query, kb_ids, top_k=top_k)

        # 去重合并（用 text 前 120 字做 key）
        seen = {r["text"][:120] for r in existing_results}
        added = [r for r in new_results if r["text"][:120] not in seen]
        logger.info("Requery: added %d new results", len(added))
        return added
    except Exception:
        logger.exception("Requery failed")
        return []
