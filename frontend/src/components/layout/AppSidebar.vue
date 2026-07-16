<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useAvatar } from '../../composables/useAvatar'
import { useDarkMode } from '../../composables/useDarkMode'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { avatar, setAvatar } = useAvatar()
const { isDark, toggle: toggleDark } = useDarkMode()

const showMenu = ref(false)
const avatarInput = ref<HTMLInputElement | null>(null)

function toggleMenu() {
  showMenu.value = !showMenu.value
}

function closeMenu(e: MouseEvent) {
  const t = e.target as HTMLElement
  if (!t.closest('.avatar-wrap')) showMenu.value = false
}

function triggerUpload() {
  avatarInput.value?.click()
}

function onAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => setAvatar(reader.result as string)
  reader.readAsDataURL(file)
}

function doLogout() {
  auth.logout()
  router.push('/login')
}
onMounted(() => document.addEventListener('click', closeMenu))
onUnmounted(() => document.removeEventListener('click', closeMenu))
</script>

<template>
  <nav class="sidebar">
    <div class="sidebar-top">
      <div class="s-logo" @click="router.push('/chat')">
        <img src="@/icon/avatar_anime.jpg" alt="Logo" />
      </div>
      <div :class="['s-item', route.path === '/chat' ? 'active' : '']" @click="router.push('/chat')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
        <span>对话</span>
      </div>
      <div :class="['s-item', route.path === '/knowledge' ? 'active' : '']" @click="router.push('/knowledge')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
        </svg>
        <span>知识库</span>
      </div>
    </div>
      <div class="s-item" @click="toggleDark" :title="isDark ? '切换亮色' : '切换暗色'">
        <svg v-if="isDark" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
        <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
        </svg>
      </div>
    <div class="avatar-wrap">
      <div class="s-avatar" @click="toggleMenu">
        <img v-if="avatar" :src="avatar" />
        <div v-else class="s-avatar-fb">{{ (auth.user?.username || 'U')[0] }}</div>
      </div>
      <div v-if="showMenu" class="avatar-menu">
        <div class="menu-item" @click="triggerUpload">修改头像</div>
        <input ref="avatarInput" type="file" accept="image/*" hidden @change="onAvatarChange" />
        <div class="menu-item">个人设置</div>
        <div class="menu-divider"></div>
        <div class="menu-item danger" @click="doLogout">退出登录</div>
      </div>
    </div>
  </nav>
</template>
