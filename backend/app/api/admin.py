"""
管理员接口 — 高频 FAQ 管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.core.database import get_db
from app.core.auth import get_current_admin
from app.models.user import User
from app.services.faq_stats_service import (
    get_stats_list,
    add_to_cache,
    remove_from_cache,
    add_manual_entry,
    delete_stats_entry,
    update_answer_admin,
)

router = APIRouter(prefix="/api/admin", tags=["管理员"])


class ManualEntryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    answer: str = Field(..., min_length=1, max_length=3000)


class UpdateAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=3000)


@router.get("/faq-stats")
def list_faq_stats(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("hit_count", pattern=r"^(hit_count|last_hit_at|created_at)$"),
    cached_only: bool = Query(False),
    window: str = Query("week", pattern=r"^(week|month)$"),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """获取高频 FAQ 统计列表（仅管理员）"""
    items, total = get_stats_list(db, page, page_size, sort_by, cached_only, window)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("/faq-stats/{stats_id}/cache")
def cache_faq_stats(
    stats_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """将指定高频 FAQ 加入 Redis 缓存"""
    try:
        add_to_cache(db, stats_id)
        return {"message": "已加入缓存"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/faq-stats/{stats_id}/cache")
def uncache_faq_stats(
    stats_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """将指定高频 FAQ 从 Redis 缓存移除"""
    try:
        remove_from_cache(db, stats_id)
        return {"message": "已从缓存移除"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/faq-stats/{stats_id}")
def delete_faq_stats(
    stats_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """删除指定高频 FAQ 记录"""
    try:
        delete_stats_entry(db, stats_id)
        return {"message": "已删除"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/faq-stats/{stats_id}/answer")
def update_faq_answer(
    stats_id: int,
    req: UpdateAnswerRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """管理员编辑指定 FAQ 的答案（自动同步 Redis 缓存）"""
    try:
        result = update_answer_admin(db, stats_id, req.answer)
        return {"message": "答案已更新", "id": result["id"], "question": result["question"]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/faq-stats/manual")
def create_manual_entry(
    req: ManualEntryRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """管理员手动录入 FAQ（直接进 Redis 缓存）"""
    result = add_manual_entry(db, req.question, req.answer)
    return {"message": "已录入并加入缓存", "id": result["id"]}
