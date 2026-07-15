"""
混合检索 - Dense + Sparse (Milvus Hybrid Search)
"""
from typing import List
from app.services.vector_store import hybrid_search_vectors, search_vectors, search_with_parent_context
from app.services.llm_service import get_embeddings
from app.services.sparse_embedding import encode_sparse


async def hybrid_search(query: str, kb_ids: List[int], dense_weight: float = 0.6, top_k: int = 10) -> List[dict]:
    dense_vecs = await get_embeddings([query])
    if not dense_vecs:
        return []
    dense_q = dense_vecs[0]
    sparse_vecs = encode_sparse([query])
    sparse_q = sparse_vecs[0] if sparse_vecs else {0: 1e-6}

    all_results = {}
    for kb_id in kb_ids:
        if sparse_q and len(sparse_q) > 1:
            results = hybrid_search_vectors(kb_id, dense_q, sparse_q, top_k=top_k, dense_weight=dense_weight)
        else:
            results = search_vectors(kb_id, dense_q, top_k=top_k)

        for r in results:
            k = r["text"][:120]
            score = r.get("final_score", r.get("score", 0))
            # 统一归一化：确保所有结果都有 final_score
            if "final_score" not in r:
                r["final_score"] = r.get("score", 0)
            if k not in all_results or score > all_results[k].get("final_score", all_results[k].get("score", 0)):
                r["dense_score"] = r.get("score", score)
                all_results[k] = r

    items = sorted(all_results.values(), key=lambda x: x.get("final_score", x.get("score", 0)), reverse=True)
    return items[:top_k]


async def hybrid_search_parent_child(query: str, kb_ids: List[int], dense_weight: float = 0.6, top_k: int = 10) -> List[dict]:
    """
    父子检索：先匹配子块，再返回父块上下文
    适用场景：文档使用 parent_child 策略切块时
    """
    dense_vecs = await get_embeddings([query])
    if not dense_vecs:
        return []
    dense_q = dense_vecs[0]
    sparse_vecs = encode_sparse([query])
    sparse_q = sparse_vecs[0] if sparse_vecs else {0: 1e-6}

    all_results = {}
    for kb_id in kb_ids:
        if sparse_q and len(sparse_q) > 1:
            results = search_with_parent_context(kb_id, dense_q, sparse_q, top_k=top_k, dense_weight=dense_weight)
        else:
            results = search_vectors(kb_id, dense_q, top_k=top_k)

        for r in results:
            k = r["text"][:120]
            score = r.get("final_score", r.get("score", 0))
            if "final_score" not in r:
                r["final_score"] = r.get("score", 0)
            if k not in all_results or score > all_results[k].get("final_score", all_results[k].get("score", 0)):
                all_results[k] = r

    items = sorted(all_results.values(), key=lambda x: x.get("final_score", x.get("score", 0)), reverse=True)
    return items[:top_k]
