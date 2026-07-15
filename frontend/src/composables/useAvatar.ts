import { ref, watch } from 'vue'

const avatar = ref<string | null>(localStorage.getItem('user_avatar'))

export function useAvatar() {
  function setAvatar(dataUrl: string) {
    localStorage.setItem('user_avatar', dataUrl)
    avatar.value = dataUrl
  }
  return { avatar, setAvatar }
}
