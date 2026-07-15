import { ref } from 'vue'

export const toastMsg = ref('')
export const toastVisible = ref(false)

let timer: ReturnType<typeof setTimeout> | null = null

export function showToast(msg: string, duration = 3000) {
  toastMsg.value = msg
  toastVisible.value = true
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    toastVisible.value = false
  }, duration)
}
