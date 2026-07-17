from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    captcha_key: str = Field(..., description="图形验证码的 key")
    captcha_code: str = Field(..., description="图形验证码的输入值")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    confirm_password: str = Field(..., min_length=6, max_length=100)
    captcha_key: str = Field(...)
    captcha_code: str = Field(...)
    is_admin: bool = Field(False)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    is_admin: bool = False
    avatar_url: str | None = None


class CaptchaResponse(BaseModel):
    captcha_key: str
    captcha_image: str
