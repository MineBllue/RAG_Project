
"""
FAQ 高频问答服务 — Redis 缓存 + BM25 检索 + MySQL 持久化

流程:
  1. Redis 缓存命中 → 直接返回
  2. 未命中 → BM25 检索 FAQ 问题库 → softmax 归一化
  3. 最高分 > 0.85 → 从 MySQL 取答案 → 写入 Redis → 返回
  4. 最高分 ≤ 0.85 → 返回 None（需要完整 RAG）
"""
import math
import json
import jieba
import hashlib
from typing import List, Optional
from collections import defaultdict

import redis
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.models.faq import FAQ
from app.core.config import get_settings

settings = get_settings()


# ============================================================
# Redis 缓存
# ============================================================

_redis: Optional[redis.Redis] = None

def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password or None,
            decode_responses=True,
            socket_connect_timeout=2,
        )
    return _redis


def _cache_key(question: str) -> str:
    h = hashlib.md5(question.strip().lower().encode()).hexdigest()
    return f"faq:{h}"


def _get_cached_answer(question: str) -> Optional[str]:
    """从 Redis 获取缓存答案（文本哈希 + 语义相似度双重匹配）"""
    try:
        r = _get_redis()
        exact = r.get(_cache_key(question))
        if exact:
            return exact
        # 语义缓存：通过 embedding 相似度查找
        return _semantic_cache_lookup(question, r)
    except Exception:
        return None


def _semantic_cache_lookup(question: str, r) -> Optional[str]:
    """语义相似度匹配缓存"""
    try:
        import json, asyncio
        from app.services.llm_service import get_embeddings
        emb = asyncio.run(get_embeddings([question]))
        if not emb:
            return None
        q_vec = emb[0]
        # 扫描 faq:emb:* 键（最多 100 个）
        keys = list(r.scan_iter("faq:emb:*", count=100))
        if not keys:
            return None
        best_key, best_sim = None, 0.0
        for key in keys:
            cached_vec = r.get(key)
            if not cached_vec:
                continue
            try:
                vec = json.loads(cached_vec)
            except Exception:
                continue
            dot = sum(a * b for a, b in zip(q_vec, vec))
            na = sum(a * a for a in q_vec) ** 0.5
            nb = sum(b * b for b in vec) ** 0.5
            sim = dot / (na * nb) if na > 0 and nb > 0 else 0
            if sim > best_sim:
                best_sim = sim
                best_key = key
        if best_sim > 0.92 and best_key:
            answer_key = best_key.replace(b"faq:emb:", b"faq:")
            return r.get(answer_key)
    except Exception:
        pass
    return None


def _set_cached_answer(question: str, answer: str, ttl: int = 86400):
    """写入 Redis 缓存（默认 24h）"""
    try:
        r = _get_redis()
        r.setex(_cache_key(question), ttl, answer)
        # 同时缓存 embedding 向量用于语义匹配
        try:
            import json, asyncio
            from app.services.llm_service import get_embeddings
            emb = asyncio.run(get_embeddings([question]))
            if emb:
                r.setex(f"faq:emb:{_cache_key(question)}", ttl, json.dumps(emb[0]))
        except Exception:
            pass
    except Exception:
        pass


# ============================================================
# BM25 检索 FAQ 问题库
# ============================================================

_faq_bm25: Optional[BM25Okapi] = None
_faq_questions: List[str] = []
_faq_version: int = 0


def _tokenize(text: str) -> List[str]:
    return [w.strip() for w in jieba.cut(text) if w.strip() and len(w.strip()) > 1]


def _softmax(scores: List[float]) -> List[float]:
    """Softmax 归一化"""
    if not scores:
        return []
    max_s = max(scores)
    exp_scores = [math.exp(s - max_s) for s in scores]
    total = sum(exp_scores)
    return [e / total for e in exp_scores]


def _build_faq_index(db: Session):
    """从 MySQL 构建 FAQ BM25 索引"""
    global _faq_bm25, _faq_questions, _faq_version
    try:
        faqs = db.query(FAQ).all()
        if not faqs:
            _faq_bm25 = None
            _faq_questions = []
            return
        _faq_questions = [faq.question for faq in faqs]
        tokenized = [_tokenize(q) for q in _faq_questions]
        _faq_bm25 = BM25Okapi(tokenized)
        _faq_version = len(faqs)
    except Exception:
        pass


def _search_faq_bm25(query: str, db: Session, top_k: int = 5) -> Optional[str]:
    """
    BM25 检索 FAQ 问题库 + softmax 归一化
    最高分 > 0.85 → 返回答案；否则返回 None
    """
    global _faq_bm25, _faq_version

    # 检查是否需要重建索引
    try:
        count = db.query(FAQ).count()
    except Exception:
        count = 0
    if _faq_bm25 is None or count != _faq_version:
        _build_faq_index(db)

    if _faq_bm25 is None or not _faq_questions:
        return None

    tokens = _tokenize(query)
    scores = _faq_bm25.get_scores(tokens)

    if not scores.any():
        return None

    # Softmax 归一化
    softmax_scores = _softmax(list(scores))
    max_idx = max(range(len(softmax_scores)), key=lambda i: softmax_scores[i])
    max_score = softmax_scores[max_idx]

    if max_score <= 0.85:
        return None

    # 从 MySQL 获取答案
    matched_question = _faq_questions[max_idx]
    faq = db.query(FAQ).filter(FAQ.question == matched_question).first()
    if not faq:
        return None

    # 更新命中计数
    faq.hit_count = (faq.hit_count or 0) + 1
    faq.score = float(max_score)
    db.commit()

    return faq.answer


# ============================================================
# 统一 FAQ 查询入口
# ============================================================

def search_faq(db: Session, question: str, threshold: float = 0.85) -> Optional[str]:
    """
    FAQ 查询（Redis → BM25 + MySQL → 写 Redis）
    """
    # Step 1: Redis 缓存
    cached = _get_cached_answer(question)
    if cached:
        return cached

    # Step 2: BM25 + softmax + MySQL
    answer = _search_faq_bm25(question, db)
    if answer:
        # Step 3: 写入 Redis
        _set_cached_answer(question, answer)
        return answer

    return None


def save_faq(db: Session, question: str, answer: str):
    """保存 FAQ 到 MySQL + 更新 BM25 索引 + 写 Redis"""
    global _faq_version
    qh = hashlib.md5(question.strip().lower().encode()).hexdigest()
    existing = db.query(FAQ).filter(FAQ.question_hash == qh).first()
    if existing:
        existing.answer = answer
        existing.hit_count = (existing.hit_count or 0) + 1
    else:
        faq = FAQ(question=question, question_hash=qh, answer=answer, hit_count=1)
        db.add(faq)
    db.commit()

    # 写 Redis
    _set_cached_answer(question, answer)

    # 标记索引需要重建
    _faq_version = 0
