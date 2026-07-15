import httpx
import json
from typing import AsyncGenerator, Optional
from app.core.config import get_settings

settings = get_settings()

DASHSCOPE_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"


async def chat_stream(
    messages: list[dict],
    temperature: float = 0.3,
    top_p: float = 0.85,
    max_tokens: int = 2048,
    model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """通义千问流式对话"""
    model_name = model or settings.llm_model
    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{DASHSCOPE_API_BASE}/chat/completions", headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """获取文本向量（最多10条/批次）"""
    all_embeddings = []
    BATCH = 10
    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        for start in range(0, len(texts), BATCH):
            batch = texts[start:start + BATCH]
            payload = {"model": settings.embedding_model, "input": {"texts": batch}}
            resp = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
                headers=headers,
                json=payload,
            )
            if resp.status_code != 200:
                raise ValueError(f"Embedding API 错误 ({resp.status_code}) batch[{start}:{start+BATCH}]: {resp.text[:300]}")
            data = resp.json()
            if "output" not in data:
                raise ValueError(f"Embedding 返回异常: {data.get('message', data)}")
            all_embeddings.extend(item["embedding"] for item in data["output"]["embeddings"])
    return all_embeddings
