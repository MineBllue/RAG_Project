import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.rag_service import rag_query
from app.services.evaluator import run_evaluation

router = APIRouter(prefix="/api/eval", tags=["评估"])


@router.post("/test")
async def test_rag(question: str, kb_ids: list[int], db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """运行 RAG 并评估"""
    full_answer = ""
    async for chunk in rag_query(question, kb_ids, db=db):
        if chunk.startswith("\n\n---SOURCES---\n"):
            continue
        full_answer += chunk

    contexts = [question]
    result = run_evaluation(question, full_answer, contexts)
    return {"question": question, "answer": full_answer, "evaluation": result}
