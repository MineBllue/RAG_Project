import {defineStore} from 'pinia'
import {ref} from 'vue'
import {login as apiLogin, register as apiRegister} from '../api'
import type {LoginParams, RegisterParams, User} from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref(localStorage.getItem('access_token') || '')

  async function doLogin(data: LoginParams) {
    const res = await apiLogin(data)
    const { access_token, refresh_token, user_id, username } = res.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    token.value = access_token
    user.value = { id: user_id, username }
  }

  async function doRegister(data: RegisterParams) {
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
