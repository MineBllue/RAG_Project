
"""
MinIO 对象存储服务 — 文档图片上传与 URL 管理
"""
import io
from datetime import timedelta
from pathlib import Path
from typing import Optional
from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings

settings = get_settings()

MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET = "rag-images"
MINIO_SECURE = False

_client: Optional[Minio] = None


def _get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        if not _client.bucket_exists(MINIO_BUCKET):
            _client.make_bucket(MINIO_BUCKET)
        # 每次都确保公开读
        import json
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}/*"],
            }]
        }
        try:
            _client.set_bucket_policy(MINIO_BUCKET, json.dumps(policy))
        except Exception:
            pass
    return _client


def upload_image(file_path: str, object_name: str = None, kb_id: int = 0, doc_id: int = 0) -> Optional[str]:
    """
    上传图片到 MinIO

    返回: 图片的持久化 URL
    """
    try:
        client = _get_client()
        if object_name is None:
            ext = Path(file_path).suffix.lower()
            object_name = f"{kb_id}/{doc_id}/{Path(file_path).name}"
        with open(file_path, "rb") as f:
            data = f.read()
        client.put_object(
            MINIO_BUCKET,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=_content_type(Path(file_path).suffix),
        )
        # 生成预签名 URL（有效期 7 天）
        url = client.presigned_get_object(
            MINIO_BUCKET, object_name, expires=timedelta(days=7)
        )
        return url
    except S3Error:
        return None


def upload_bytes(data: bytes, object_name: str, content_type: str = "image/png") -> Optional[str]:
    """上传字节数据到 MinIO"""
    try:
        client = _get_client()
        client.put_object(
            MINIO_BUCKET,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        url = client.presigned_get_object(
            MINIO_BUCKET, object_name, expires=timedelta(days=7)
        )
        return url
    except S3Error:
        return None


def _content_type(ext: str) -> str:
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
    }
    return mapping.get(ext.lower(), "application/octet-stream")
