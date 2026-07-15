<script setup lang="ts">
import { toastVisible, toastMsg } from './stores/toast'
</script>

<template>
  <Transition name="toast">
    <div v-if="toastVisible" class="toast-bar">{{ toastMsg }}</div>
  </Transition>
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --bg-root: #f3f4f6;
  --bg-surface: #ffffff;
  --bg-sidebar: #f8f9fb;
  --bg-card: #ffffff;
  --bg-hover: #f0f1f3;
  --border-subtle: #e5e7eb;
  --border-card: #d1d5db;
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --text-tertiary: #9ca3af;
  --text-muted: #d1d5db;
  --accent: #3b82f6;
  --accent-soft: rgba(59, 130, 246, 0.08);
  --gold: #f59e0b;
  --gold-soft: rgba(245, 158, 11, 0.08);
  --green: #10b981;
  --green-soft: rgba(16, 185, 129, 0.08);
  --red: #ef4444;
  --red-soft: rgba(239, 68, 68, 0.08);
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,.06);
  --shadow-md: 0 4px 12px rgba(0,0,0,.08);
}

.page-enter-active { transition: all .3s cubic-bezier(.4,0,.2,1); }
.page-leave-active { transition: all .2s cubic-bezier(.4,0,.2,1); }
.page-enter-from { opacity: 0; transform: translateY(8px); }
.page-leave-to { opacity: 0; transform: translateY(-8px); }

* { -webkit-tap-highlight-color: transparent; }
::selection { background: rgba(59,130,246,.2); color: #111827; }

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg-root);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-card); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-tertiary); }

.toast-bar {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  background: var(--red);
  color: #fff;
  padding: 12px 28px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 8px 24px rgba(239,68,68,.35);
  white-space: nowrap;
}

.toast-enter-active { transition: all .3s cubic-bezier(.4,0,.2,1); }
.toast-leave-active { transition: all .25s ease-in; }
.toast-enter-from { opacity: 0; transform: translateX(-50%) translateY(-12px); }
.toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(-12px); }
</style>
