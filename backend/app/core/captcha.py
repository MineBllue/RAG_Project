import random
import string
import io
import base64
import uuid
from PIL import Image, ImageDraw, ImageFont
from app.core.config import get_settings

settings = get_settings()

# 内存存储作为 Redis 不可用时的降级方案
_captcha_store: dict[str, str] = {}
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        from redis import Redis
        _redis_client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password or None,
            socket_connect_timeout=2,
            decode_responses=True,
        )
        _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_client = False
        return None


def _set_captcha(key: str, code: str, ttl: int = 300):
    r = _get_redis()
    if r:
        r.setex(f"captcha:{key}", ttl, code)
    else:
        _captcha_store[key] = code


def _get_captcha(key: str) -> str | None:
    r = _get_redis()
    if r:
        return r.get(f"captcha:{key}")
    return _captcha_store.get(key)


def _del_captcha(key: str):
    r = _get_redis()
    if r:
        r.delete(f"captcha:{key}")
    else:
        _captcha_store.pop(key, None)


def generate_captcha() -> tuple[str, str, str]:
    code = "".join(random.choices(string.digits, k=4))
    key = str(uuid.uuid4())

    width, height = 120, 45
    image = Image.new("RGB", (width, height), color=(240, 240, 245))
    draw = ImageDraw.Draw(image)

    for i in range(30):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = x1 + random.randint(-10, 10)
        y2 = y1 + random.randint(-10, 10)
        draw.line([(x1, y1), (x2, y2)], fill=(180, 180, 200), width=1)

    for i, char in enumerate(code):
        x = 15 + i * 24 + random.randint(-3, 3)
        y = random.randint(5, 12)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        except (IOError, OSError):
            font = ImageFont.load_default()
        draw.text((x, y), char, font=font, fill=(50, 50, 80))

    for _ in range(100):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(150, 150, 180))

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    _set_captcha(key, code.lower())
    return key, code, img_base64


def verify_captcha(key: str, code: str) -> bool:
    stored = _get_captcha(key)
    if stored and stored == code.lower().strip():
        _del_captcha(key)
        return True
    return False
