
"""
检索策略选择器 — 四种策略:
  1. 直接检索 (direct): 原始 query → 混合检索
  2. 假设问题检索 (hyde): LLM 生成假设文档 → 向量检索
  3. 子问题查询 (sub_question): 复杂问题拆分 → 并行检索 → 合并
  4. 回溯问题检索 (step_back): 抽象问题 → 回溯检索 → 用结果回答原问题
"""
from typing import List

from app.services.llm_service import chat_stream, get_embeddings
from app.services.hybrid_retrieval import hybrid_search
from app.services.sparse_embedding import encode_sparse
from app.services.vector_store import search_vectors


# ============================================================
# Strategy 1: 直接检索
# ============================================================

async def direct_retrieval(queries: List[str], kb_ids: List[int], top_k: int = 5) -> List[dict]:
    """原始查询直接检索"""
    all_items = {}
    for q in queries:
        r_list = await hybrid_search(q, kb_ids, dense_weight=0.7, top_k=top_k)
        for r in r_list:
            k = r["text"][:120]
            r.setdefault("doc_id", 0)
            r.setdefault("kb_id", 0)
            if k not in all_items or r["final_score"] > all_items[k].get("final_score", 0):
                all_items[k] = r
    items = sorted(all_items.values(), key=lambda x: x.get("final_score", 0), reverse=True)
    return items[:top_k]


# ============================================================
# Strategy 2: HyDE (假设文档检索)
# ============================================================

HYDE_PROMPT = """你是一个技术文档撰写助手。请根据用户问题，写一段假设性的文档内容（100-200字），
这段内容应该像一个真实的知识库文档，直接回答用户可能想问的问题。

用户问题: {question}

假设文档:"""


async def hyde_retrieval(query: str, kb_ids: List[int], top_k: int = 5) -> List[dict]:
    """HyDE: 生成假设文档 → 用假设文档做向量检索"""
    # Step 1: LLM 生成假设文档
    hyde_doc = ""
    try:
        msgs = [{"role": "user", "content": HYDE_PROMPT.format(question=query)}]
        async for chunk in chat_stream(msgs, temperature=0.3, max_tokens=300):
            hyde_doc += chunk
    except Exception:
        pass

    if not hyde_doc.strip():
        # 降级为直接检索
        return await direct_retrieval([query], kb_ids, top_k)

    # Step 2: 用假设文档做向量检索
    hyde_embedding = await get_embeddings([hyde_doc])
    if not hyde_embedding:
        return await direct_retrieval([query], kb_ids, top_k)

    all_results = {}
    for kb_id in kb_ids:
        results = search_vectors(kb_id, hyde_embedding[0], top_k=top_k)
        for r in results:
            k = r["text"][:120]
            score = r.get("score", 0)
            if k not in all_results or score > all_results[k].get("final_score", 0):
                r["final_score"] = score
                all_results[k] = r

    items = sorted(all_results.values(), key=lambda x: x.get("final_score", 0), reverse=True)
    return items[:top_k]


# ============================================================
# Strategy 3: 子问题查询
# ============================================================

DECOMPOSE_PROMPT = """请将以下复杂问题拆分为2-3个独立的子问题，每行一个，只返回子问题列表：

复杂问题: {question}

子问题:"""


async def sub_question_retrieval(query: str, kb_ids: List[int], top_k: int = 5) -> List[dict]:
    """子问题拆分 → 并行检索 → 合并去重"""
    # Step 1: LLM 拆分子问题
    sub_queries = [query]
    try:
        msgs = [{"role": "user", "content": DECOMPOSE_PROMPT.format(question=query)}]
        full = ""
        async for chunk in chat_stream(msgs, temperature=0.1, max_tokens=150):
            full += chunk
        for line in full.split("\n"):
            line = line.strip().lstrip("0123456789.、- ")
            if line and len(line) > 3 and line not in sub_queries:
                sub_queries.append(line)
    except Exception:
        pass

    # Step 2: 并行检索
    return await direct_retrieval(sub_queries[:4], kb_ids, top_k)


# ============================================================
# Strategy 4: 回溯问题检索
# ============================================================

STEP_BACK_PROMPT = """请将以下具体问题抽象为一个更通用、更高层次的问题（20字以内），便于从知识库中检索相关背景知识：

具体问题: {question}

抽象问题:"""


async def step_back_retrieval(query: str, kb_ids: List[int], top_k: int = 5) -> List[dict]:
    """回溯: 抽象问题 → 检索 → 取回上下文"""
    # Step 1: LLM 生成回溯问题
    step_back_q = ""
    try:
        msgs = [{"role": "user", "content": STEP_BACK_PROMPT.format(question=query)}]
        async for chunk in chat_stream(msgs, temperature=0.1, max_tokens=80):
            step_back_q += chunk
    except Exception:
        pass

    # Step 2: 用回溯问题检索
    queries = [query]
    if step_back_q.strip() and step_back_q.strip() != query:
        queries.insert(0, step_back_q.strip())

    return await direct_retrieval(queries, kb_ids, top_k)


# ============================================================
# 策略选择器
# ============================================================

import jieba
import logging
from app.services.qa_stopwords import _init_jieba

_init_jieba()
logger = logging.getLogger(__name__)

# 复杂问题特征词（通常需要子问题拆分）
_COMPLEX_KEYWORDS = {
    "比较", "对比", "区别", "异同", "优缺点", "利弊",
    "为什么", "原因", "因素", "影响", "后果",
    "如何", "怎么", "步骤", "流程", "方法", "方案",
    "分别", "各自", "同时", "以及", "并且", "还有",
}

# 概念性问题特征词（通常适合 HyDE）
_CONCEPT_KEYWORDS = {
    "什么是", "是什么", "定义", "概念", "含义", "解释",
    "概述", "总结", "归纳", "概括",
}

# 子问题拆分标记
_SUB_MARKERS = {"？", "?", "；", ";", "，", ","}


def select_strategy(question: str) -> str:
    """基于规则引擎选择检索策略（同步，零 LLM 调用）"""
    q = question.strip()
    q_len = len(q)

    if q_len < 6:
        return "direct"

    # 多个问号/分号 → 子问题拆分（优先于概念关键词检测）
    if sum(1 for c in q if c in _SUB_MARKERS) >= 2 and q_len > 15:
        return "sub_question"

    # 概念关键词 → HyDE（优先于长度判断，因为这些词明确表示概念性问题）
    for kw in _CONCEPT_KEYWORDS:
        if kw in q:
            return "hyde"

    words = set(jieba.lcut(q))

    # 包含复杂特征词 + 有一定长度 → 子问题拆分
    if q_len > 10 and words & _COMPLEX_KEYWORDS:
        return "sub_question"

    # 非短问题 → HyDE（扩大检索覆盖）
    if q_len >= 6:
        logger.debug("Strategy: medium length → hyde for '%s'", q[:50])
        return "hyde"

    logger.debug("Strategy: default direct for '%s'", q[:20])
    return "direct"


async def execute_strategy(strategy: str, query: str, kb_ids: List[int], top_k: int = 5) -> List[dict]:
    """执行指定策略"""
    if strategy == "hyde":
        return await hyde_retrieval(query, kb_ids, top_k)
    elif strategy == "sub_question":
        return await sub_question_retrieval(query, kb_ids, top_k)
    elif strategy == "step_back":
        return await step_back_retrieval(query, kb_ids, top_k)
    else:
        return await direct_retrieval([query], kb_ids, top_k)
