
"""
意图识别 — LLM 判断用户问题是否需要查知识库

不需要 RAG 的场景: 问候、闲聊、自我介绍、通用常识
需要 RAG 的场景: 技术问题、项目相关、需要检索文档
"""
from app.services.llm_service import chat_stream


INTENT_PROMPT = """你是一个意图分类器。判断用户问题是否需要查询知识库（RAG）。

不需要查知识库（返回 NO）:
- 问候语: 你好、谢谢、再见
- 闲聊: 你是谁、今天天气怎么样
- 自我介绍相关: 你会什么、介绍一下你自己
- 纯常识: 1+1等于几

需要查知识库（返回 YES）:
- 技术问题: FastAPI和Flask的区别、Bert模型架构
- 项目流程: MySQL问答系统流程
- 需要文档: 简述下项目背景

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
        return "YES" in result.upper()
    except Exception:
        return True  # 异常时默认走 RAG


"""同步版本 — 兼容旧代码"""

GREETINGS = {"你好", "谢谢", "再见", "拜拜", "早上好", "晚上好", "下午好", "你是谁", "你好吗", "你是谁呀"}


async def async_recognize_intent(question: str) -> bool:
    """问候语快速检查（兜底）"""
    q = question.strip().replace("？", "").replace("?", "").replace("！", "")
    if q in GREETINGS or (len(q) < 6 and any(g in q for g in GREETINGS)):
        return False
    return True
