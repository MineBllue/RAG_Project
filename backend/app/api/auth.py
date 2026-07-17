import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import logging
from app.core.database import get_db
from app.core.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, get_current_user
from app.core.captcha import generate_captcha, verify_captcha
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, CaptchaResponse
from app.core.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["认证"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.get("/captcha", response_model=CaptchaResponse)
def get_captcha():
    key, code, img_base64 = generate_captcha()
    return CaptchaResponse(captcha_key=key, captcha_image=img_base64)


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if req.password != req.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="两次输入的密码不一致")

    if not verify_captcha(req.captcha_key, req.captcha_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    user = User(username=req.username, password_hash=hash_password(req.password), is_admin=req.is_admin)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User registered: '%s' (id=%d, admin=%s)", user.username, user.id, user.is_admin)

    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id, user.username)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        avatar_url=user.avatar_url,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    if not verify_captcha(req.captcha_key, req.captcha_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    logger.info("User login: '%s' (id=%d)", user.username, user.id)
    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id, user.username)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        avatar_url=user.avatar_url,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_token_str: str, db: Session = Depends(get_db)):
    payload = decode_token(refresh_token_str)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌类型")
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        refresh_token=create_refresh_token(user.id, user.username),
        user_id=user.id,
        username=user.username,
        avatar_url=user.avatar_url,
    )


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """上传用户头像"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片格式")
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="头像不能超过 2MB")

    ext = os.path.splitext(file.filename or "avatar.png")[1] or ".png"
    filename = f"avatar_{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    avatar_dir = os.path.join(settings.upload_dir, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    filepath = os.path.join(avatar_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    avatar_url = f"/api/files/avatars/{filename}"
    user.avatar_url = avatar_url
    db.commit()
    logger.info("Avatar uploaded for user '%s': %s", user.username, avatar_url)
    return {"avatar_url": avatar_url}
