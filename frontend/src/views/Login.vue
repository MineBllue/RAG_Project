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
@import '../styles/auth.css';
</style>
