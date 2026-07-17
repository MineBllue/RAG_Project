"""
RAG 评估服务
评估指标:
  1. Context Relevance   — 检索结果是否与问题相关
  2. Context Recall      — 检索是否覆盖回答所需的全部信息
  3. Faithfulness        — 回答是否基于检索内容而非编造
  4. Answer Relevancy    — 回答是否真正回应了问题

混合策略: 关键词快速初评（同步 0ms）+ Ragas 精评（异步后台）
"""
from typing import List, Optional
import jieba


# ============================================================
# 快速关键词评估（同步，用于即时展示）
# ============================================================

def _keyword_context_relevance(query: str, contexts: List[str]) -> float:
    """基于 jieba 分词的上下文相关性评估"""
    if not contexts:
        return 0.0
    q_tokens = set(jieba.lcut(query))
    scores = []
    for ctx in contexts:
        ctx_tokens = set(jieba.lcut(ctx))
        overlap = len(q_tokens & ctx_tokens) / max(len(q_tokens), 1)
        scores.append(min(overlap * 2, 1.0))
    return round(sum(scores) / len(scores), 4)


def _keyword_context_recall(answer: str, contexts: List[str]) -> float:
    """关键词法评估上下文召回率：答案关键词有多少被上下文覆盖"""
    if not contexts or not answer:
        return 0.0
    a_tokens = set(jieba.lcut(answer))
    ctx_text = " ".join(contexts)
    ctx_tokens = set(jieba.lcut(ctx_text))
    recall = len(a_tokens & ctx_tokens) / max(len(a_tokens), 1)
    return round(min(recall, 1.0), 4)


def _keyword_faithfulness(answer: str, contexts: List[str]) -> float:
    """基于 jieba 分词的忠实度评估"""
    if not contexts or not answer:
        return 0.0
    context_text = " ".join(contexts)
    ctx_tokens = set(jieba.lcut(context_text))
    sentences = [s.strip() for s in answer.replace("。", "。\n").replace("！", "！\n").split("\n")
                 if len(s.strip()) > 5]
    if not sentences:
        return 0.0
    supported = 0
    for sent in sentences:
        sent_tokens = set(jieba.lcut(sent))
        if len(sent_tokens & ctx_tokens) / max(len(sent_tokens), 1) > 0.2:
            supported += 1
    return round(supported / len(sentences), 4)


def _keyword_answer_relevance(query: str, answer: str) -> float:
    """关键词法评估答案相关性：回答的关键词有多少与问题重叠"""
    if not query or not answer:
        return 0.0
    q_tokens = set(jieba.lcut(query))
    a_tokens = set(jieba.lcut(answer))
    overlap = len(q_tokens & a_tokens) / max(len(q_tokens), 1)
    return round(min(overlap * 2, 1.0), 4)


# ============================================================
# 关键词评估入口
# ============================================================

def run_evaluation(query: str, answer: str, contexts: List[str]) -> dict:
    """运行关键词快速评估（同步，~0ms）"""
    kw_cr = _keyword_context_relevance(query, contexts)
    kw_c_recall = _keyword_context_recall(answer, contexts)
    kw_ff = _keyword_faithfulness(answer, contexts)
    kw_ar = _keyword_answer_relevance(query, answer)

    return {
        "context_relevance": kw_cr,
        "context_recall": kw_c_recall,
        "context_precision": kw_cr,
        "faithfulness": kw_ff,
        "answer_relevance": kw_ar,
        "avg_score": round((kw_cr + kw_c_recall + kw_ff + kw_ar) / 4, 4),
        "method": "keyword",
    }


# ============================================================
# Ragas 结果合并
# ============================================================

def merge_ragas_result(keyword: dict, ragas_scores: Optional[dict]) -> dict:
    """合并关键词和 Ragas 结果，Ragas 优先"""
    if not ragas_scores:
        return keyword

    return {
        "context_relevance": ragas_scores.get("context_precision", keyword["context_relevance"]),
        "context_recall": ragas_scores.get("context_recall", keyword["context_recall"]),
        "context_precision": ragas_scores.get("context_precision", keyword["context_precision"]),
        "faithfulness": ragas_scores.get("faithfulness", keyword["faithfulness"]),
        "answer_relevance": ragas_scores.get("answer_relevancy", keyword["answer_relevance"]),
        "avg_score": round(sum(ragas_scores.values()) / max(len(ragas_scores), 1), 4),
        "method": "ragas",
    }


# 兼容旧接口
def apply_ragas_result(result: dict, ragas_scores: dict) -> dict:
    return merge_ragas_result(result, ragas_scores)


def evaluate_context_relevance(query: str, contexts: List[str]) -> dict:
    score = _keyword_context_relevance(query, contexts)
    return {"score": score, "relevant_count": 0, "total": len(contexts)}


def evaluate_faithfulness(answer: str, contexts: List[str]) -> dict:
    score = _keyword_faithfulness(answer, contexts)
    return {"score": score, "supported_claims": 0, "total_claims": 0}
