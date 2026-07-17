import {defineStore} from 'pinia'
import {ref} from 'vue'
import {login as apiLogin, register as apiRegister} from '../api'
import {useAvatar} from '../composables/useAvatar'
import type {LoginParams, RegisterParams, User} from '../types'

export const useAuthStore = defineStore('auth', () => {
  const savedUser = localStorage.getItem('user_info')
const user = ref<User | null>(savedUser ? JSON.parse(savedUser) : null)
  const token = ref(localStorage.getItem('access_token') || '')

  async function doLogin(data: LoginParams) {
    const res = await apiLogin(data)
    const { access_token, refresh_token, user_id, username, is_admin, avatar_url } = res.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    token.value = access_token
    user.value = { id: user_id, username, is_admin: is_admin || false }
    localStorage.setItem('user_info', JSON.stringify(user.value))
    const { loadFromUserInfo } = useAvatar()
    loadFromUserInfo(avatar_url)
  }

  async function doRegister(data: RegisterParams) {
    const res = await apiRegister(data)
    const { access_token, refresh_token, user_id, username, is_admin, avatar_url } = res.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    token.value = access_token
    user.value = { id: user_id, username, is_admin: is_admin || false }
    localStorage.setItem('user_info', JSON.stringify(user.value))
    const { loadFromUserInfo } = useAvatar()
    loadFromUserInfo(avatar_url)
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_info')
    const { clearAvatar } = useAvatar()
    clearAvatar()
    token.value = ''
    user.value = null
  }

  return { user, token, doLogin, doRegister, logout }
})
