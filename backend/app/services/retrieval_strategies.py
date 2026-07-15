
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

STRATEGY_PROMPT = """你是一个检索策略路由器。根据用户问题的特征，选择最合适的检索策略。

可选策略:
- direct: 直接检索。适用于简单、明确的事实性问题。
- hyde: 假设文档检索。适用于需要综合理解的问题，或问题表述不够精确的场景。
- sub_question: 子问题拆分。适用于复合型、需要分步回答的复杂问题。
- step_back: 回溯检索。适用于具体细节问题，需要先理解更广泛的背景知识。

用户问题: {question}

请只返回一个策略名称: direct, hyde, sub_question, step_back"""


async def select_strategy(question: str) -> str:
    """LLM 选择检索策略"""
    try:
        msgs = [{"role": "user", "content": STRATEGY_PROMPT.format(question=question)}]
        result = ""
        async for chunk in chat_stream(msgs, temperature=0.0, max_tokens=20):
            result += chunk
        result = result.strip().lower()
        if "hyde" in result:
            return "hyde"
        elif "sub" in result:
            return "sub_question"
        elif "step" in result or "back" in result:
            return "step_back"
    except Exception:
        pass
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
