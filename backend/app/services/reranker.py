"""
重排序服务 - 使用 bge-reranker 对混合检索结果精排
"""
import sys
import math
import os
from typing import List
import logging
from FlagEmbedding import FlagReranker

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
_reranker_loading = False
_reranker = None
_warmed_up = False


def _get_reranker() -> FlagReranker:
    global _reranker, _reranker_loading
    if _reranker is None:
        # 避免并发重复加载
        if _reranker_loading:
            import time
            for _ in range(300):
                if _reranker is not None:
                    return _reranker
                time.sleep(0.1)
        _reranker_loading = True
        # 临时抑制 FlagEmbedding 的 "Loading weights" 进度条
        _old_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        try:
            _reranker = FlagReranker(RERANKER_MODEL, use_fp16=True)
        except Exception:
            _reranker = FlagReranker(RERANKER_MODEL, use_fp16=False)
        finally:
            sys.stderr.close()
            sys.stderr = _old_stderr
        _reranker_loading = False
        logging.getLogger(__name__).info("Reranker model loaded successfully")
    return _reranker


def warmup_reranker():
    """预热 reranker 模型（在 lifespan 启动时调用，避免首次请求阻塞）"""
    global _warmed_up
    if _warmed_up:
        return
    _warmed_up = True
    logger = logging.getLogger(__name__)
    logger.info("Reranker warmup: loading model (this may take a few seconds)...")
    try:
        _get_reranker()
        logger.info("Reranker warmup: model loaded successfully")
    except Exception:
        logger.warning("Reranker warmup: failed to load model, will retry on first request")


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
