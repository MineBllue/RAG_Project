from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, default=0)
    file_path = Column(String(500), nullable=False)
    status = Column(String(20), default=DocumentStatus.PENDING.value)
    chunk_count = Column(Integer, default=0)
    chunk_method = Column(String(50), default="default")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    chunk_type = Column(String(20), default="child", nullable=False, index=True)
    parent_chunk_id = Column(Integer, ForeignKey("document_chunks.id"), nullable=True)
    chunk_hash = Column(String(64), nullable=False, index=True)
    milvus_id = Column(String(100), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    document = relationship("Document", back_populates="chunks")
    parent = relationship("DocumentChunk", remote_side=[id], foreign_keys=[parent_chunk_id], backref="children")
