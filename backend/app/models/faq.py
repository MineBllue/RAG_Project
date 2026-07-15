from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.core.database import Base


class FAQ(Base):
    __tablename__ = "faq_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String(500), nullable=False, index=True)
    question_hash = Column(String(64), nullable=False, unique=True, index=True)
    answer = Column(String(2000), nullable=False)
    hit_count = Column(Integer, default=1)
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
