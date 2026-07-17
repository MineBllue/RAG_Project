
"""
意图识别 — LLM 判断用户问题是否需要查知识库

不需要 RAG 的场景: 问候、闲聊、自我介绍、通用常识
需要 RAG 的场景: 技术问题、项目相关、需要检索文档
"""
import logging
from app.services.llm_service import chat_stream

logger = logging.getLogger(__name__)

INTENT_PROMPT = """你是一个意图分类器。判断用户问题是否需要查询企业知识库（RAG）。

不需要查知识库（返回 NO）:
- 问候语: 你好、谢谢、再见、早上好
- 纯闲聊: 你是谁、今天天气怎么样、讲个笑话
- 纯常识/计算: 1+1等于几、今天星期几
- 无意义输入: 单个字、乱码

需要查知识库（返回 YES）:
- 任何需要查找信息的问题: 退款规则、优惠券折扣、上架流程、定价策略
- 业务名词查询: 下午茶折扣、新人券、CP003、星巴克
- 数据查询: 退款率多少、销量排名、客单价
- 规则/流程: 怎么操作、有什么要求、如何配置

用户问题: {question}

只返回 YES 或 NO:"""


async def recognize_intent(question: str) -> bool:
    """
    LLM 意图识别
    返回 True = 需要 RAG, False = 直接 LLM 回答
    """
    try:
        msgs = [{"role": "user", "content": INTENT_PROMPT.format(question=question)}]
        result = ""
        async for chunk in chat_stream(msgs, temperature=0.0, max_tokens=5):
            result += chunk
        is_rag = "YES" in result.upper()
        logger.debug("Intent: '%s' → %s", question[:40], "RAG" if is_rag else "NO-RAG")
        return is_rag
    except Exception:
        return True  # 异常时默认走 RAG


"""同步版本 — 兼容旧代码"""

GREETINGS = {"你好", "谢谢", "再见", "拜拜", "早上好", "晚上好", "下午好", "你是谁", "你好吗", "你是谁呀"}


async def async_recognize_intent(question: str) -> bool:
    """问候语快速检查（兜底：只有明确的短问候才跳过 RAG）"""
    q = question.strip().replace("？", "").replace("?", "").replace("！", "").replace(" ", "")
    if q in GREETINGS:
        return False
    return True
