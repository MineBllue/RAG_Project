"""
Query 改写服务 - 4 种策略
1. 简化问题：去除冗余，提取核心
2. 假设问题：将陈述转为疑问
3. 子问题拆分：复杂问题拆为多个
4. 回溯改写：用关键词组合搜索
"""
from app.services.llm_service import chat_stream
from app.core.config import get_settings

settings = get_settings()

REWRITE_PROMPTS = {
    "simplify": "请将以下问题简化，提取核心关键词，只返回简化后的问题（不超过20字）：\n{question}",
    "hypothetical": "请将以下陈述转化为一个直接的疑问句，便于搜索知识库：\n{question}",
    "split": "请将以下复杂问题拆分为2-3个子问题，每行一个，只返回子问题列表：\n{question}",
    "retrospect": "以下问题可能表述不够精确，请用更专业的关键词重新表述（15字以内）：\n{question}",
}

async def _call_llm(prompt: str) -> str:
    """调用 LLM 获取简短回复"""
    messages = [{"role": "user", "content": prompt}]
    result = ""
    async for chunk in chat_stream(messages, temperature=0.1, max_tokens=80):
        result += chunk
    return result.strip()

async def rewrite_query(question: str) -> list[str]:
    """返回改写后的 3-4 个查询变体用于并行检索"""
    variants = [question]
    try:
        simplified = await _call_llm(REWRITE_PROMPTS["simplify"].format(question=question))
        if simplified and simplified != question:
            variants.append(simplified)

        hypothetical = await _call_llm(REWRITE_PROMPTS["hypothetical"].format(question=question))
        if hypothetical and hypothetical != question and hypothetical not in variants:
            variants.append(hypothetical)

        split_text = await _call_llm(REWRITE_PROMPTS["split"].format(question=question))
        for line in split_text.split("\n"):
            line = line.strip().lstrip("0123456789.、- ")
            if line and len(line) > 3 and line not in variants:
                variants.append(line)

        retro = await _call_llm(REWRITE_PROMPTS["retrospect"].format(question=question))
        if retro and retro != question and retro not in variants:
            variants.append(retro)
    except Exception:
        pass
    return variants[:5]
