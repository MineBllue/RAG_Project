import { ref } from 'vue'

const avatar = ref<string | null>(localStorage.getItem('user_avatar'))

export function useAvatar() {
  function setAvatar(dataUrl: string) {
    localStorage.setItem('user_avatar', dataUrl)
    avatar.value = dataUrl
  }

  async function uploadAvatar(file: File): Promise<string | null> {
    const form = new FormData()
    form.append('file', file)
    const token = localStorage.getItem('access_token')
    try {
      const resp = await fetch('/api/auth/avatar', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      if (!resp.ok) return null
      const data = await resp.json()
      return data.avatar_url
    } catch {
      return null
    }
  }

  function loadFromUserInfo(avatarUrl: string | null | undefined) {
    if (avatarUrl) {
      // 后端返回的是相对路径，浏览器会用当前 origin 拼接
      avatar.value = avatarUrl
      localStorage.setItem('user_avatar', avatarUrl)
    }
  }

  function clearAvatar() {
    localStorage.removeItem('user_avatar')
    avatar.value = null
  }

  return { avatar, setAvatar, uploadAvatar, loadFromUserInfo, clearAvatar }
}
