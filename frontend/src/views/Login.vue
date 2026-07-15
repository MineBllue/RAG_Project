<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getCaptcha } from '../api'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const captchaCode = ref('')
const captchaKey = ref('')
const captchaImage = ref('')
const errorMsg = ref('')
const loading = ref(false)

async function refreshCaptcha() {
  try {
    const res = await getCaptcha()
    captchaKey.value = res.data.captcha_key
    captchaImage.value = res.data.captcha_image
  } catch {
    errorMsg.value = '获取验证码失败'
  }
}

onMounted(refreshCaptcha)

async function handleLogin() {
  errorMsg.value = ''
  if (!username.value || !password.value || !captchaCode.value) {
    errorMsg.value = '请填写所有字段'
    return
  }
  loading.value = true
  try {
    await auth.doLogin({
      username: username.value,
      password: password.value,
      captcha_key: captchaKey.value,
      captcha_code: captchaCode.value,
    })
    router.push('/chat')
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || '登录失败'
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <img src="@/icon/avatar_anime.jpg" class="auth-logo" alt="Logo" />
        <h1>InnerQA</h1>
        <p>企业知识库智能问答系统</p>
      </div>
      <form @submit.prevent="handleLogin" class="auth-form">
        <div class="field">
          <label>账号</label>
          <input v-model="username" type="text" placeholder="请输入账号" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="请输入密码" />
        </div>
        <div class="field captcha-field">
          <label>验证码</label>
          <div class="captcha-row">
            <input v-model="captchaCode" type="text" placeholder="验证码" maxlength="4" />
            <img
              v-if="captchaImage"
              :src="'data:image/png;base64,' + captchaImage"
              @click="refreshCaptcha"
              class="captcha-img"
              alt="验证码"
            />
          </div>
        </div>
        <div v-if="errorMsg" class="error">{{ errorMsg }}</div>
        <button type="submit" :disabled="loading" class="btn-primary">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
      <div class="auth-footer">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(ellipse at 30% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 70% 30%, rgba(245, 158, 11, 0.06) 0%, transparent 50%),
    var(--bg-root);
}
.auth-card {
  width: 380px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 40px 36px;
}
.auth-header { text-align: center; margin-bottom: 32px; }
.auth-logo {
  width: 48px; height: 48px; border-radius: var(--radius-sm);
  object-fit: cover; display: block; margin: 0 auto 12px;
}
.auth-header h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.auth-header p { font-size: 13px; color: var(--text-tertiary); }
.field { margin-bottom: 18px; }
.field label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.field input {
  width: 100%; padding: 10px 12px; background: var(--bg-card); border: 1px solid var(--border-card);
  border-radius: var(--radius-sm); color: var(--text-primary); font-size: 14px; font-family: inherit;
  outline: none; transition: border-color .15s;
}
.field input:focus { border-color: var(--accent); }
.captcha-row { display: flex; gap: 10px; }
.captcha-row input { flex: 1; }
.captcha-img { height: 42px; border-radius: var(--radius-sm); cursor: pointer; border: 1px solid var(--border-card); }
.error { color: var(--red); font-size: 13px; margin-bottom: 12px; }
.btn-primary {
  width: 100%; padding: 11px; background: var(--accent); color: #fff; border: none;
  border-radius: var(--radius-sm); font-size: 14px; font-weight: 500; cursor: pointer; font-family: inherit;
  transition: opacity .15s;
}
.btn-primary:hover { opacity: .9; }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.auth-footer { text-align: center; margin-top: 20px; font-size: 13px; color: var(--text-tertiary); }
.auth-footer a { color: var(--accent); text-decoration: none; }
.auth-footer a:hover { text-decoration: underline; }
</style>
