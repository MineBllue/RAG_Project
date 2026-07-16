<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getCaptcha } from '../api'
import AnimatedCharacters from '../components/auth/AnimatedCharacters.vue'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const captchaCode = ref('')
const captchaKey = ref('')
const captchaImage = ref('')
const errorMsg = ref('')
const loading = ref(false)
const showPassword = ref(false)
const isFocused = ref(false)

const isTyping = computed(() => isFocused.value && (username.value.length > 0 || password.value.length > 0))

function onFocus() { isFocused.value = true }
function onBlur() { isFocused.value = false }

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
  <div class="auth-page auth-page-split">
    <AnimatedCharacters :is-typing="isTyping" :show-password="showPassword" :password-length="password.length" />
    <div class="auth-card">
      <div class="auth-header">
        <img src="@/icon/avatar_anime.jpg" class="auth-logo" alt="Logo" />
        <h1>InnerQA</h1>
        <p>企业知识库智能问答系统</p>
      </div>
      <form @submit.prevent="handleLogin" class="auth-form">
        <div class="field">
          <label>账号</label>
          <input v-model="username" type="text" placeholder="请输入账号" @focus="onFocus" @blur="onBlur" />
        </div>
        <div class="field">
          <label>密码</label>
          <div class="pwd-wrap">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="请输入密码"
              @focus="onFocus"
              @blur="onBlur"
            />
            <button type="button" class="pwd-toggle" @click="showPassword = !showPassword">
              <svg v-if="!showPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
              <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
          </div>
        </div>
        <div class="field captcha-field">
          <label>验证码</label>
          <div class="captcha-row">
            <input v-model="captchaCode" type="text" placeholder="验证码" maxlength="4" @focus="onFocus" @blur="onBlur" />
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

<style>
.auth-header{
  margin-bottom: 10px;
}
</style>