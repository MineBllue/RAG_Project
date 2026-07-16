import axios from 'axios'
import { showToast } from '../stores/toast'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken && !error.config._retry) {
        error.config._retry = true
        try {
          const res = await axios.post('/api/auth/refresh', null, {
            params: { refresh_token_str: refreshToken },
          })
          const { access_token, refresh_token } = res.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)
          error.config.headers.Authorization = `Bearer ${access_token}`
          return api(error.config)
        } catch {
          localStorage.clear()
          showToast('登录已过期，请重新登录')
          setTimeout(() => { window.location.href = '/login' }, 1500)
        }
      } else {
        localStorage.clear()
        showToast('登录已过期，请重新登录')
        setTimeout(() => { window.location.href = '/login' }, 1500)
      }
    }
    return Promise.reject(error)
  }
)

export default api

// Auth
export const getCaptcha = () => api.get('/auth/captcha')
export const login = (data: any) => api.post('/auth/login', data)
export const register = (data: any) => api.post('/auth/register', data)

// Knowledge
export const listKBs = () => api.get('/knowledge/list')
export const createKB = (data: any) => api.post('/knowledge/create', data)
export const deleteKB = (id: number) => api.delete(`/knowledge/${id}`)
export const listDocuments = (kbId: number) => api.get(`/knowledge/${kbId}/documents`)
export const deleteDocument = (kbId: number, docId: number) => api.delete(`/knowledge/${kbId}/documents/${docId}`)
export const uploadDocument = (kbId: number, formData: FormData) =>
  api.post(`/knowledge/${kbId}/upload-batch`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const listChunks = (kbId: number, docId: number) => api.get(`/knowledge/${kbId}/documents/${docId}/chunks`)
export const deleteChunk = (kbId: number, docId: number, chunkId: number) =>
  api.delete(`/knowledge/${kbId}/documents/${docId}/chunks/${chunkId}`)
export const updateChunk = (kbId: number, docId: number, chunkId: number, content: string) =>
  api.put(`/knowledge/${kbId}/documents/${docId}/chunks/${chunkId}`, new URLSearchParams({ content }))

// Chat
export const listConversations = () => api.get('/chat/conversations')
export const createConversation = (title: string) => api.post('/chat/conversations', null, { params: { title } })
export const deleteConversation = (id: number) => api.delete(`/chat/conversations/${id}`)
export const updateConversation = (id: number, title: string) =>
  api.put(`/chat/conversations/${id}`, null, { params: { title } })
export const getMessages = (convId: number) => api.get(`/chat/conversations/${convId}/messages`)
