"""
Ragas 异步评估服务（后台运行，不阻塞用户响应）

评估指标:
  1. Context Precision  — 检索到的上下文是否精准相关
  2. Context Recall     — 检索是否覆盖了回答问题所需的全部信息
  3. Faithfulness       — 回答是否忠实于检索到的上下文
  4. Answer Relevancy   — 回答是否真正回应了用户问题
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def run_ragas_evaluation(
    question: str,
    answer: str,
    contexts: list[str],
) -> Optional[dict]:
    """
    后台运行 Ragas 四项评估，返回 {metric: score, ...}
    失败返回 None（上游用关键词评估兜底）
    """
    try:
        # Ragas 0.4.x 有硬编码的 langchain_community 导入 bug，stub 绕过
        import sys, types
        if "langchain_community.chat_models.vertexai" not in sys.modules:
            stub = types.ModuleType("langchain_community.chat_models.vertexai")
            stub.ChatVertexAI = type("ChatVertexAI", (), {})
            sys.modules["langchain_community.chat_models.vertexai"] = stub

        from ragas import evaluate, EvaluationDataset, SingleTurnSample
        from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
        from ragas.llms import LangchainLLMWrapper
        from langchain_openai import ChatOpenAI
        from app.core.config import get_settings

        settings = get_settings()

        # 配置 Ragas 使用的 LLM（通义千问兼容 OpenAI 接口）
        eval_llm = LangchainLLMWrapper(ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.0,
            max_tokens=256,
        ))

        # 构建数据集
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
            reference=answer,  # ContextRecall 需要 reference，用 answer 近似
        )
        dataset = EvaluationDataset(samples=[sample])

        # 四项指标
        metrics = [
            ContextPrecision(),
            ContextRecall(),
            Faithfulness(),
            AnswerRelevancy(),
        ]

        # 在线程池中运行（ragas evaluate 是同步的）
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: evaluate(dataset=dataset, metrics=metrics, llm=eval_llm),
        )

        scores = {
            "context_precision": round(float(result["context_precision"]), 4),
            "context_recall": round(float(result["context_recall"]), 4),
            "faithfulness": round(float(result["faithfulness"]), 4),
            "answer_relevancy": round(float(result["answer_relevancy"]), 4),
        }
        logger.info("Ragas evaluation complete: %s", scores)
        return scores

    except Exception:
        logger.exception("Ragas evaluation failed")
        return None
