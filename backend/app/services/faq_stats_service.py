"""
FAQ 高频统计服务
- 每次 RAG 问答后，将用户 query 做 BM25 + 词级重叠 聚合
- 窗口内 hit_count >= 阈值 → 自动写 Redis
- 管理员可手动管理缓存、编辑答案
"""
import json
import math
import hashlib
import jieba
import logging
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

import redis
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.models.faq_stats import FAQStats
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

from app.services.qa_stopwords import normalize_query as _normalize_query, get_content_tokens


# ============================================================
# Redis 连接池（模块级单例，避免每次调用创建新连接）
# ============================================================

_redis_pool: Optional[redis.Redis] = None


def _get_redis() -> redis.Redis:
    """获取 Redis 连接（惰性初始化 + 连接健康检查）"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password or None,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_keepalive=True,
            health_check_interval=30,
        )
    return _redis_pool


# ============================================================
# 工具函数
# ============================================================

def _tokenize(text: str) -> List[str]:
    return [w.strip() for w in jieba.cut(text) if len(w.strip()) > 0]


def _build_bm25_index(questions: List[str]) -> BM25Okapi:
    """构建 BM25 索引"""
    tokenized = [jieba.lcut(q) for q in questions]
    return BM25Okapi(tokenized)


def _minmax_normalize(scores: List[float]) -> List[float]:
    """Min-Max 归一化到 0-1（比 softmax 更适合 BM25 分数）"""
    if not scores:
        return []
    min_s = min(scores)
    max_s = max(scores)
    if max_s == min_s:
        return [1.0] * len(scores)
    return [(s - min_s) / (max_s - min_s) for s in scores]


def _compute_word_overlap(tokens_a: set, tokens_b: set) -> float:
    """计算词级重叠率"""
    shared = tokens_a & tokens_b
    return len(shared) / max(min(len(tokens_a), len(tokens_b)), 1)


# ============================================================
# FAQ 统计聚合
# ============================================================

def record_query(db: Session, question: str, answer: str = ""):
    """
    记录一次用户查询，自动做 BM25 + 词级重叠 聚合。
    
    注意：此函数在 async 上下文中调用，内部只有同步 DB I/O。
    如果高并发场景需要，可在上层用 run_in_executor 包装。
    """
    cutoff = datetime.utcnow() - timedelta(days=settings.faq_stats_window_days)
    existing = db.query(FAQStats).filter(FAQStats.last_hit_at >= cutoff).all()

    if not existing:
        _create_cluster(db, question, question, answer)
        logger.info("[FAQ Stats] NEW cluster: '%s' (first query in window)", question[:40])
        return

    # 第一轮：归一化后精确匹配（最快，跳过 BM25）
    norm_q = _normalize_query(question)
    for fs in existing:
        if _normalize_query(fs.question_cluster) == norm_q:
            _increment_cluster(db, fs, question, answer)
            return

    # 第二轮：BM25(min-max) + 词级重叠 双重匹配
    cluster_questions = [_normalize_query(fs.question_cluster) for fs in existing]
    bm25 = _build_bm25_index(cluster_questions)
    tokenized_q = jieba.lcut(norm_q)
    raw_scores = bm25.get_scores(tokenized_q)
    norm_scores = _minmax_normalize(list(raw_scores))

    max_idx = max(range(len(norm_scores)), key=lambda i: norm_scores[i])
    bm25_score = norm_scores[max_idx]

    best_q = _normalize_query(existing[max_idx].question_cluster)
    q_tokens = set(get_content_tokens(norm_q))
    best_tokens = set(get_content_tokens(best_q))
    word_overlap = _compute_word_overlap(q_tokens, best_tokens)
    shared_count = len(q_tokens & best_tokens)

    # 三重判定
    exact = norm_q == best_q
    high_overlap = word_overlap >= 0.7 and shared_count >= 1
    matched = exact or high_overlap or (bm25_score * 0.6 + word_overlap * 0.4) > settings.faq_stats_similarity_threshold

    if matched:
        fs = existing[max_idx]
        logger.info(
            "[FAQ Stats] MATCH: '%s' -> cluster '%s' (hit=%d, overlap=%.3f, bm25=%.3f)",
            question[:30], fs.question_cluster[:30], fs.hit_count + 1, word_overlap, bm25_score,
        )
        _increment_cluster(db, fs, question, answer)
    else:
        logger.info(
            "[FAQ Stats] NO MATCH: '%s' (best overlap=%.3f, bm25=%.3f) -> new cluster",
            question[:30], word_overlap, bm25_score,
        )
        _create_cluster(db, question, question, answer)


def _increment_cluster(db: Session, fs: FAQStats, question: str, answer: str = ""):
    """更新已有 cluster 的命中计数和 raw_queries"""
    fs.hit_count += 1
    fs.last_hit_at = datetime.utcnow()
    raw_list = json.loads(fs.raw_queries or "[]")
    if question not in raw_list:
        raw_list.append(question)
    fs.raw_queries = json.dumps(raw_list, ensure_ascii=False)
    if answer:
        fs.answer = answer
    db.commit()

    # 达到阈值 → 写 Redis
    if fs.hit_count >= settings.faq_stats_cache_threshold and not fs.is_cached:
        _write_redis_cache(fs)
        fs.is_cached = True
        db.commit()


def _create_cluster(db: Session, question: str, representative: str, answer: str = ""):
    """创建新的 FAQ cluster"""
    fs = FAQStats(
        question_cluster=representative,
        raw_queries=json.dumps([question], ensure_ascii=False),
        answer=answer or "",
        hit_count=1,
        is_cached=False,
        last_hit_at=datetime.utcnow(),
    )
    db.add(fs)
    db.commit()


# ============================================================
# Redis 缓存查询与写入
# ============================================================

async def check_stats_cache(question: str) -> Optional[str]:
    """检查 stats-based FAQ 是否在 Redis 缓存中（BM25 模糊匹配，用 SCAN 替代 KEYS）"""
    try:
        r = _get_redis()
        # 用 SCAN 替代 KEYS，避免阻塞 Redis
        keys: List[str] = []
        cursor = 0
        while True:
            cursor, batch = r.scan(cursor, match="faq_stats:*", count=50)
            keys.extend(batch)
            if cursor == 0:
                break

        if not keys:
            return None

        # 取出所有缓存的 question
        cached_items: List[Tuple[str, str, str]] = []
        for k in keys:
            try:
                val = r.get(k)
                if val:
                    data = json.loads(val)
                    cached_items.append((k, data.get("question", ""), data.get("answer", "")))
            except Exception:
                continue

        if not cached_items:
            return None

        # 第一轮：归一化后精确匹配
        norm_q = _normalize_query(question)
        for item in cached_items:
            if _normalize_query(item[1]) == norm_q:
                logger.info("[FAQ Cache HIT exact] question='%s'", question[:50])
                return item[2]

        # 第二轮：BM25(min-max) + 词级重叠 模糊匹配
        cache_questions = [_normalize_query(item[1]) for item in cached_items]
        bm25 = _build_bm25_index(cache_questions)
        tokenized = jieba.lcut(norm_q)
        raw_scores = bm25.get_scores(tokenized)
        if len(raw_scores) == 0:
            return None
        norm_scores = _minmax_normalize(list(raw_scores))

        max_idx = max(range(len(norm_scores)), key=lambda i: norm_scores[i])
        best_q = cache_questions[max_idx]
        q_tokens = set(get_content_tokens(norm_q))
        b_tokens = set(get_content_tokens(best_q))
        word_overlap = _compute_word_overlap(q_tokens, b_tokens)
        shared_count = len(q_tokens & b_tokens)

        exact = norm_q == best_q
        high_overlap = word_overlap >= 0.7 and shared_count >= 1
        if exact or high_overlap or (norm_scores[max_idx] * 0.6 + word_overlap * 0.4) > settings.faq_stats_similarity_threshold:
            logger.info(
                "[FAQ Cache HIT] question='%s' matched cluster='%s' overlap=%.3f",
                question[:50], best_q[:50], word_overlap,
            )
            return cached_items[max_idx][2]
        else:
            logger.debug(
                "[FAQ Cache MISS] question='%s' best='%s' overlap=%.3f",
                question[:50], best_q[:50], word_overlap,
            )
    except Exception:
        logger.exception("[FAQ Cache ERROR]")
    return None


def _write_redis_cache(fs: FAQStats):
    """将 FAQStats 写入 Redis 缓存"""
    try:
        r = _get_redis()
        key = f"faq_stats:{hashlib.md5(fs.question_cluster.strip().lower().encode()).hexdigest()}"
        value = json.dumps({"question": fs.question_cluster, "answer": fs.answer}, ensure_ascii=False)
        r.setex(key, settings.faq_stats_redis_ttl, value)
        logger.info("[FAQ Cache WRITE] key=%s q='%s'", key, fs.question_cluster[:40])
    except Exception:
        logger.exception("[FAQ Cache WRITE ERROR]")


def _remove_redis_cache(question_cluster: str):
    """从 Redis 移除缓存"""
    try:
        r = _get_redis()
        key = f"faq_stats:{hashlib.md5(question_cluster.strip().lower().encode()).hexdigest()}"
        r.delete(key)
        logger.info("[FAQ Cache REMOVE] key=%s", key)
    except Exception:
        logger.exception("[FAQ Cache REMOVE ERROR]")


# ============================================================
# 查询列表
# ============================================================

def get_stats_list(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "hit_count",
    cached_only: bool = False,
    window: str = "week",
) -> Tuple[List[dict], int]:
    """
    获取高频问题列表（分页）
    window: "week" | "month"
    """
    if window == "month":
        cutoff = datetime.utcnow() - timedelta(days=30)
    else:
        now = datetime.utcnow()
        cutoff = now - timedelta(days=now.weekday())
        cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)

    q = db.query(FAQStats).filter(FAQStats.last_hit_at >= cutoff)
    if cached_only:
        q = q.filter(FAQStats.is_cached == True)

    total = q.count()
    items = q.order_by(getattr(FAQStats, sort_by).desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for fs in items:
        raw_list = json.loads(fs.raw_queries or "[]")
        result.append({
            "id": fs.id,
            "question": fs.question_cluster,
            "raw_queries": raw_list[:10],
            "raw_query_count": len(raw_list),
            "answer": fs.answer,
            "hit_count": fs.hit_count,
            "is_cached": fs.is_cached,
            "last_hit_at": fs.last_hit_at.isoformat() if fs.last_hit_at else None,
            "created_at": fs.created_at.isoformat() if fs.created_at else None,
        })

    return result, total


# ============================================================
# 答案更新（内部用 + 管理员用）
# ============================================================

def update_answer(db: Session, question: str, answer: str):
    """RAG 生成答案后，自动更新匹配 cluster 的 answer 字段。
    
    优先 BM25 + 词级重叠匹配；如果匹配失败但窗口内只有一个 cluster
    且归一化后精确匹配，则直接更新（兜底新创建的 cluster）。
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=settings.faq_stats_window_days)
        existing = db.query(FAQStats).filter(FAQStats.last_hit_at >= cutoff).all()
        if not existing:
            return
        norm_q = _normalize_query(question)

        # 如果窗口内只有一个 cluster 且归一化后精确匹配 → 直接更新
        if len(existing) == 1 and norm_q == _normalize_query(existing[0].question_cluster):
            existing[0].answer = answer
            db.commit()
            if existing[0].is_cached:
                _write_redis_cache(existing[0])
            return

        cluster_questions = [_normalize_query(fs.question_cluster) for fs in existing]
        bm25 = _build_bm25_index(cluster_questions)
        tokenized_q = jieba.lcut(norm_q)
        raw_scores = bm25.get_scores(tokenized_q)
        if len(raw_scores) == 0:
            return
        norm_scores = _minmax_normalize(list(raw_scores))
        max_idx = max(range(len(norm_scores)), key=lambda i: norm_scores[i])
        bm25_score = norm_scores[max_idx]
        best_fs = existing[max_idx]
        q_set = set(get_content_tokens(norm_q))
        b_set = set(get_content_tokens(_normalize_query(best_fs.question_cluster)))
        word_overlap = _compute_word_overlap(q_set, b_set)
        shared_count = len(q_set & b_set)
        exact = norm_q == _normalize_query(best_fs.question_cluster)
        high_overlap = word_overlap >= 0.7 and shared_count >= 1
        if exact or high_overlap or (bm25_score * 0.6 + word_overlap * 0.4) > settings.faq_stats_similarity_threshold:
            best_fs.answer = answer
            db.commit()
            if best_fs.is_cached:
                _write_redis_cache(best_fs)
    except Exception:
        logger.exception("[FAQ Update Answer ERROR]")


def update_answer_admin(db: Session, stats_id: int, answer: str):
    """管理员编辑指定 FAQ 的答案并同步更新 Redis 缓存"""
    fs = db.query(FAQStats).filter(FAQStats.id == stats_id).first()
    if not fs:
        raise ValueError(f"FAQStats id={stats_id} 不存在")
    fs.answer = answer
    db.commit()
    if fs.is_cached:
        _write_redis_cache(fs)
    return {"id": fs.id, "question": fs.question_cluster}


# ============================================================
# 管理员手动管理
# ============================================================

def add_to_cache(db: Session, stats_id: int):
    """管理员手动将指定 FAQ 加入 Redis 缓存"""
    fs = db.query(FAQStats).filter(FAQStats.id == stats_id).first()
    if not fs:
        raise ValueError(f"FAQStats id={stats_id} 不存在")
    _write_redis_cache(fs)
    fs.is_cached = True
    db.commit()
    return True


def remove_from_cache(db: Session, stats_id: int):
    """管理员从 Redis 缓存中移除"""
    fs = db.query(FAQStats).filter(FAQStats.id == stats_id).first()
    if not fs:
        raise ValueError(f"FAQStats id={stats_id} 不存在")
    _remove_redis_cache(fs.question_cluster)
    fs.is_cached = False
    db.commit()
    return True


def delete_stats_entry(db: Session, stats_id: int):
    """管理员删除指定 FAQ 统计记录（同时移除 Redis 缓存）"""
    fs = db.query(FAQStats).filter(FAQStats.id == stats_id).first()
    if not fs:
        raise ValueError(f"FAQStats id={stats_id} 不存在")
    if fs.is_cached:
        _remove_redis_cache(fs.question_cluster)
    db.delete(fs)
    db.commit()
    return True


def add_manual_entry(db: Session, question: str, answer: str):
    """管理员手动录入 FAQ 并直接加入缓存"""
    fs = FAQStats(
        question_cluster=question,
        raw_queries=json.dumps([question], ensure_ascii=False),
        answer=answer,
        hit_count=settings.faq_stats_cache_threshold,
        is_cached=True,
        last_hit_at=datetime.utcnow(),
    )
    db.add(fs)
    db.commit()
    _write_redis_cache(fs)
    return {"id": fs.id, "question": fs.question_cluster}
