<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useAvatar } from '../../composables/useAvatar'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { avatar, setAvatar, uploadAvatar } = useAvatar()

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

async function onAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  // 先本地预览
  const reader = new FileReader()
  reader.onload = () => setAvatar(reader.result as string)
  reader.readAsDataURL(file)
  // 再上传到后端持久化
  await uploadAvatar(file)
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
      <div v-if="auth.user?.is_admin" :class="['s-item', route.path === '/faq-management' ? 'active' : '']" @click="router.push('/faq-management')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 20V10M18 20V4M6 20v-4"/>
        </svg>
        <span>高频问答</span>
      </div>
    </div>
    <div class="avatar-wrap">
      <div class="s-avatar" @click="toggleMenu">
        <img v-if="avatar" :src="avatar" />
        <div v-else class="s-avatar-fb">{{ (auth.user?.username || 'U')[0] }}</div>
      </div>
      <div v-if="showMenu" class="avatar-menu">
        <div class="menu-item" @click="triggerUpload">修改头像</div>
        <input ref="avatarInput" type="file" accept="image/*" hidden @change="onAvatarChange" />
        <div class="menu-divider"></div>
        <div class="menu-item danger" @click="doLogout">退出登录</div>
      </div>
    </div>
  </nav>
</template>
