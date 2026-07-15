"""
重排序服务 - 使用 bge-reranker 对混合检索结果精排
"""
import math
import os
from typing import List
from FlagEmbedding import FlagReranker

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        try:
            _reranker = FlagReranker(RERANKER_MODEL, use_fp16=True)
        except Exception:
            _reranker = FlagReranker(RERANKER_MODEL, use_fp16=False)
    return _reranker


def rerank(query: str, documents: List[str], top_k: int = 5) -> List[dict]:
    """对文档列表重排序（sigmoid 校准到 0-1）"""
    if not documents:
        return []
    try:
        reranker = _get_reranker()
        pairs = [[query, doc] for doc in documents]
        raw_scores = reranker.compute_score(pairs)
        if isinstance(raw_scores, float):
            raw_scores = [raw_scores]
        # sigmoid 校准 logits -> 0-1
        calibrated = [1.0 / (1.0 + math.exp(-s)) for s in raw_scores]
        ranked = sorted(zip(documents, calibrated), key=lambda x: x[1], reverse=True)
        return [{"text": doc, "rerank_score": round(score, 4)} for doc, score in ranked[:top_k]]
    except Exception:
        pass
    return []
