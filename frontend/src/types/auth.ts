/** 用户信息 */
export interface User {
  id: number
  username: string
}

/** 登录请求参数 */
export interface LoginParams {
  username: string
  password: string
  captcha_key: string
  captcha_code: string
}

/** 注册请求参数 */
export interface RegisterParams {
  username: string
  password: string
  captcha_key: string
  captcha_code: string
}

/** 登录/注册响应 */
export interface AuthResponse {
  access_token: string
  refresh_token: string
  user_id: number
  username: string
}

/** 验证码响应 */
export interface CaptchaResponse {
  captcha_key: string
  captcha_image: string
}
