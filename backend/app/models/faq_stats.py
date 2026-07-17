"""
FAQ 高频统计表
- 存储每个归一化问题的命中次数
- 支持按时间窗口（本周/本月）统计
- BM25 聚合后的问题存 question_cluster 字段
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, func
from app.core.database import Base


class FAQStats(Base):
    __tablename__ = "faq_stats"
    __table_args__ = (
        Index("idx_faq_stats_last_hit", "last_hit_at"),
        Index("idx_faq_stats_cached_hit", "is_cached", "last_hit_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 聚合后的代表性问题（频次最高的那条 query）
    question_cluster = Column(String(500), nullable=False, index=True)
    # JSON: 所有归入此 cluster 的原始 query 列表 ["退款怎么操作", "怎么退款", ...]
    raw_queries = Column(String(5000), nullable=False, default="[]")
    # 标准化答案（由最近一次 RAG 回答自动填充，或管理员手动填写）
    answer = Column(String(3000), nullable=False, default="")
    # 统计周期内命中次数
    hit_count = Column(Integer, default=0)
    # 是否已加入 Redis 缓存
    is_cached = Column(Boolean, default=False)
    # 最近一次命中时间
    last_hit_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FAQStats(id={self.id}, q='{self.question_cluster[:30]}', hits={self.hit_count})>"
