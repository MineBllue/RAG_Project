from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "12345678"
    mysql_database: str = "innerQaSystem"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_database: str = "itcast"
    milvus_collection_name: str = "innerQA"

    # LLM
    dashscope_api_key: str = ""
    llm_model: str = "qwen-max"
    embedding_model: str = "text-embedding-v3"

    # Multimodal
    clip_model: str = "ViT-B/32"
    ocr_enabled: bool = True

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50

    # FAQ 高频统计
    faq_stats_window_days: int = 7          # 统计窗口（天）
    faq_stats_similarity_threshold: float = 0.88  # BM25+Softmax 相似度阈值
    faq_stats_cache_threshold: int = 10     # 自动写 Redis 的命中次数阈值
    faq_stats_redis_ttl: int = 86400 * 7    # Redis 缓存过期时间（秒，默认 7 天）

    # File storage
    upload_dir: str = "./data/uploads"
    data_dir: str = "../data"
    max_upload_size_mb: int = 50          # 单个文件最大上传大小（MB）

    @property
    def mysql_url(self) -> str:
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    @property
    def mysql_url_async(self) -> str:
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
