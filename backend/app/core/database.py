from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import logging
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

engine = create_engine(settings.mysql_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)

    # 兼容旧表：补上缺失的列（SQLAlchemy create_all 不改已有表）
    _migrate_schema()


def _migrate_schema():
    """轻量 schema 迁移：补全缺失的列"""
    insp = inspect(engine)
    with engine.connect() as conn:
        if 'users' in insp.get_table_names():
            cols = {c['name'] for c in insp.get_columns('users')}
            if 'is_admin' not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
                conn.commit()
                logger.info("Schema migration: users.is_admin column added")
            if 'avatar_url' not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) DEFAULT NULL"))
                conn.commit()
                logger.info("Schema migration: users.avatar_url column added")
