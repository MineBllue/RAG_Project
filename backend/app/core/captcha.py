"""
图形验证码服务（无状态 HMAC 签名模式）

- 不依赖 Redis 或内存存储，天然支持多进程部署和服务重启
- 验证码有效期 5 分钟，key 内嵌 HMAC 签名防篡改
"""
import random
import string
import io
import base64
import json
import hmac
import hashlib
import time
import logging
from PIL import Image, ImageDraw, ImageFont
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

CAPTCHA_TTL = 300  # 5 分钟


def _sign(payload: str) -> str:
    """HMAC-SHA256 签名"""
    secret = settings.jwt_secret_key.encode()
    return hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()


def generate_captcha() -> tuple[str, str, str]:
    """生成图形验证码，返回 (key, code, base64_image)"""
    code = "".join(random.choices(string.digits, k=4))
    ts = int(time.time())

    # key 格式: base64({"c":"1234","t":1234567890}) + "." + hmac_signature
    payload = base64.urlsafe_b64encode(
        json.dumps({"c": code, "t": ts}).encode()
    ).decode().rstrip("=")
    key = f"{payload}.{_sign(payload)}"

    # 绘制图片
    width, height = 120, 45
    image = Image.new("RGB", (width, height), color=(240, 240, 245))
    draw = ImageDraw.Draw(image)

    for _ in range(30):
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

    logger.debug("Captcha generated: code=%s key_prefix=%s", code, key[:20])
    return key, code, img_base64


def verify_captcha(key: str, code: str) -> bool:
    """验证图形验证码（无状态，仅验证 HMAC 签名和时效性）"""
    try:
        if "." not in key:
            return False
        payload_b64, sig = key.rsplit(".", 1)

        # 验证 HMAC 签名
        if not hmac.compare_digest(sig, _sign(payload_b64)):
            logger.debug("Captcha verify FAIL: invalid signature")
            return False

        # 补齐 base64 padding 再解码
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        data = json.loads(base64.urlsafe_b64decode(payload_b64))

        stored_code = data.get("c", "")
        ts = data.get("t", 0)

        # 检查过期
        if time.time() - ts > CAPTCHA_TTL:
            logger.debug("Captcha verify FAIL: expired (age=%ds)", int(time.time() - ts))
            return False

        # 比较验证码（不区分大小写 + 去空格）
        match = stored_code == code.lower().strip()
        if match:
            logger.debug("Captcha verify OK")
        else:
            logger.debug("Captcha verify FAIL: code mismatch (expected=%s, got=%s)", stored_code, code.lower().strip())
        return match
    except Exception:
        logger.exception("Captcha verify ERROR")
        return False
