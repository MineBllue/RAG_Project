import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.knowledge_base import KnowledgeBase
from app.services.rag_service import rag_query

router = APIRouter(prefix="/api/chat", tags=["对话"])


class ChatRequest(BaseModel):
    question: str
    kb_ids: List[int] = []
    conversation_id: Optional[int] = None
    temperature: float = 0.3
    top_p: float = 0.85
    max_tokens: int = 2048
    history_rounds: int = 5


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    convs = db.query(Conversation).filter(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat()} for c in convs]


@router.post("/conversations")
def create_conversation(title: str = "新对话", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = Conversation(user_id=user.id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"id": conv.id, "title": conv.title}


@router.put("/conversations/{conv_id}")
def update_conversation(conv_id: int, title: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    conv.title = title
    db.commit()
    return {"id": conv.id, "title": conv.title}


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.query(Message).filter(Message.conversation_id == conv_id).delete()
    db.delete(conv)
    db.commit()
    return {"message": "会话已删除"}


@router.get("/conversations/{conv_id}/messages")
def get_messages(conv_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at.asc()).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "sources": m.sources, "created_at": m.created_at.isoformat()} for m in msgs]


@router.post("/query")
async def chat_query(req: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = None
    if req.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == req.conversation_id, Conversation.user_id == user.id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        conv = Conversation(user_id=user.id, title=req.question[:30])
        db.add(conv)
        db.commit()
        db.refresh(conv)

    user_msg = Message(conversation_id=conv.id, role="user", content=req.question)
    db.add(user_msg)
    db.commit()

    history_msgs = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at.asc()).all()
    history = []
    for m in history_msgs[:-1]:
        history.append({"role": m.role, "content": m.content})

    async def generate():
        full_answer = ""
        sources_data = []
        try:
            async for chunk in rag_query(question=req.question, kb_ids=req.kb_ids, db=db, history_messages=history, temperature=req.temperature, top_p=req.top_p, max_tokens=req.max_tokens, history_rounds=req.history_rounds):
                if "\n---SOURCES---\n" in chunk:
                    parts = chunk.split("\n---SOURCES---\n", 1)
                    if parts[0]: full_answer += parts[0]; yield f"data: {json.dumps({'content': parts[0], 'done': False})}\n\n"
                    try: sources_data = json.loads(parts[1].strip())
                    except: pass
                else:
                    full_answer += chunk
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'content': '', 'done': True, 'error': str(e)})}\n\n"
            return

        assistant_msg = Message(conversation_id=conv.id, role="assistant", content=full_answer, sources=json.dumps(sources_data, ensure_ascii=False) if sources_data else None)
        db.add(assistant_msg)
        db.commit()
        yield f"data: {json.dumps({'content': '', 'done': True, 'sources': sources_data})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
