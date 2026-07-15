
"""
RAG 评估服务
评估指标:
  1. 上下文相关性 (Context Relevance) — 检索结果是否与问题相关
  2. 答案忠实度 (Faithfulness) — 回答是否基于检索内容而非编造
  3. 答案相关性 (Answer Relevance) — 回答是否真正回应了问题

混合策略: 快速关键词初筛 + LLM 精评
"""
from typing import List, Optional
import json
import re


# ============================================================
# 快速关键词评估（无 LLM 兜底）
# ============================================================

def _keyword_context_relevance(query: str, contexts: List[str]) -> float:
    """关键词重叠法评估上下文相关性"""
    if not contexts:
        return 0.0
    keywords = set(query)
    scores = []
    for ctx in contexts:
        overlap = len(keywords & set(ctx)) / max(len(keywords), 1)
        scores.append(min(overlap * 3, 1.0))
    return round(sum(scores) / len(scores), 4)


def _keyword_faithfulness(answer: str, contexts: List[str]) -> float:
    """关键词法评估忠实度"""
    if not contexts or not answer:
        return 0.0
    context_text = " ".join(contexts)
    sentences = [s.strip() for s in answer.replace("。", "。\n").replace("！", "！\n").split("\n")
                 if len(s.strip()) > 5]
    if not sentences:
        return 0.0
    supported = 0
    for sent in sentences:
        words = set(sent)
        if len(words & set(context_text)) / max(len(words), 1) > 0.2:
            supported += 1
    return round(supported / len(sentences), 4)


# ============================================================
# LLM 精评
# ============================================================

EVAL_PROMPT = """你是一个 RAG 系统评估专家。请根据以下信息，对检索和生成质量进行评分。

## 用户问题
{question}

## 检索到的上下文
{context}

## 生成的回答
{answer}

请从以下三个维度打分（0.0-1.0），并给出简短理由：

1. context_relevance: 检索到的上下文与问题的相关程度
   - 1.0: 完全相关，直接覆盖问题
   - 0.5: 部分相关
   - 0.0: 完全不相关

2. faithfulness: 回答是否忠实于检索到的上下文（而非编造）
   - 1.0: 完全基于上下文
   - 0.5: 部分基于上下文，有少量推断
   - 0.0: 完全编造或与上下文矛盾

3. answer_relevance: 回答是否真正回应了用户问题
   - 1.0: 完全回答了问题
   - 0.5: 部分回答了问题
   - 0.0: 答非所问

请严格按以下 JSON 格式输出，不要输出其他内容：
{{"context_relevance": <float>, "faithfulness": <float>, "answer_relevance": <float>, "reason": "<一句话理由>"}}"""


async def _llm_evaluate(query: str, answer: str, contexts: List[str]) -> Optional[dict]:
    """用 LLM 精评"""
    try:
        from app.services.llm_service import chat_stream
        ctx = "\n\n---\n\n".join(contexts[:5]) if contexts else "（无上下文）"
        prompt = EVAL_PROMPT.format(question=query, context=ctx[:3000], answer=answer[:2000])

        full = ""
        async for chunk in chat_stream(
            [{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=256,
        ):
            full += chunk

        # 提取 JSON
        m = re.search(r'\{[^}]+\}', full)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return None


# ============================================================
# 综合评估入口
# ============================================================

def run_evaluation(query: str, answer: str, contexts: List[str],
                   use_llm: bool = True) -> dict:
    """
    综合评估（支持 LLM 精评 + 关键词兜底）

    返回:
    {
        "query": str,
        "context_relevance": float,
        "faithfulness": float,
        "answer_relevance": float,
        "avg_score": float,
        "method": "llm" | "keyword",
        "reason": str,
    }
    """
    # 先用关键词快速打分
    kw_cr = _keyword_context_relevance(query, contexts)
    kw_ff = _keyword_faithfulness(answer, contexts)

    result = {
        "query": query,
        "context_relevance": kw_cr,
        "faithfulness": kw_ff,
        "answer_relevance": kw_cr,  # 默认用上下文相关性近似
        "avg_score": round((kw_cr + kw_ff + kw_cr) / 3, 4),
        "method": "keyword",
        "reason": "",
    }

    # LLM 精评（异步兼容：先尝试同步方式，允许失败降级）
    if use_llm and contexts and answer:
        # 在 rag_service 异步上下文中，这里会被 await
        # 在同步调用时，我们返回关键词结果
        result["_llm_pending"] = True
        result["_llm_contexts"] = contexts
        result["_llm_answer"] = answer

    return result


def apply_llm_result(result: dict, llm_scores: dict) -> dict:
    """将 LLM 评分合并到评估结果中"""
    if not llm_scores:
        return result
    result["context_relevance"] = llm_scores.get("context_relevance", result["context_relevance"])
    result["faithfulness"] = llm_scores.get("faithfulness", result["faithfulness"])
    result["answer_relevance"] = llm_scores.get("answer_relevance", result["answer_relevance"])
    result["avg_score"] = round(
        (result["context_relevance"] + result["faithfulness"] + result["answer_relevance"]) / 3, 4
    )
    result["method"] = "llm"
    result["reason"] = llm_scores.get("reason", "")
    result.pop("_llm_pending", None)
    result.pop("_llm_contexts", None)
    result.pop("_llm_answer", None)
    return result


# 同步包装（兼容旧接口）
def evaluate_context_relevance(query: str, contexts: List[str]) -> dict:
    score = _keyword_context_relevance(query, contexts)
    return {"score": score, "relevant_count": 0, "total": len(contexts)}


def evaluate_faithfulness(answer: str, contexts: List[str]) -> dict:
    score = _keyword_faithfulness(answer, contexts)
    return {"score": score, "supported_claims": 0, "total_claims": 0}
