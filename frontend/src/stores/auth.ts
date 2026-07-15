import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as apiLogin, register as apiRegister } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<{ id: number; username: string } | null>(null)
  const token = ref(localStorage.getItem('access_token') || '')

  async function doLogin(data: { username: string; password: string; captcha_key: string; captcha_code: string }) {
    const res = await apiLogin(data)
    const { access_token, refresh_token, user_id, username } = res.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    token.value = access_token
    user.value = { id: user_id, username }
  }

  async function doRegister(data: any) {
    const res = await apiRegister(data)
    const { access_token, refresh_token, user_id, username } = res.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    token.value = access_token
    user.value = { id: user_id, username }
  }

  function logout() {
    localStorage.clear()
    token.value = ''
    user.value = null
  }

  return { user, token, doLogin, doRegister, logout }
})
