<script setup lang="ts">
const modelValue = defineModel<string>('modelValue', { default: '' })
defineProps<{ selectedKbCount: number; sending: boolean }>()
const emit = defineEmits<{ send: [] }>()

function handleSend() {
  if (!modelValue.value.trim()) return
  emit('send')
}
</script>

<template>
  <div class="input-area">
    <div class="input-row">
      <div class="input-box">
        <input
          v-model="modelValue"
          type="text"
          placeholder="输入你的问题，Enter 发送..."
          :disabled="sending"
          @keydown.enter="handleSend"
        />
      </div>
      <button class="send-btn" :disabled="!modelValue.trim() || sending" @click="handleSend">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
      </button>
    </div>
    <div class="input-hint">
      <span v-if="selectedKbCount">已选 {{ selectedKbCount }} 个知识库</span>
      <span v-else class="warn">请选择知识库</span>
    </div>
  </div>
</template>

<style scoped>
.input-area { padding: 10px 20px 14px; border-top: 1px solid var(--border-subtle); background: var(--bg-surface); flex-shrink: 0 }
.input-row { max-width: 700px; margin: 0 auto; display: flex; gap: 8px }
.input-box { flex: 1; background: var(--bg-card); border: 1px solid var(--border-card); border-radius: 10px; padding: 0 10px 0 14px; transition: all .25s }
.input-box:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); transform: translateY(-1px) }
.input-box input { width: 100%; background: none; border: none; color: var(--text-primary); font-size: 13px; font-family: inherit; outline: none; line-height: 38px }
.input-box input::placeholder { color: var(--text-muted) }
.send-btn { width: 42px; height: 42px; border-radius: 10px; background: var(--accent); border: none; color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all .25s }
.send-btn:hover:not(:disabled) { transform: scale(1.05); box-shadow: 0 4px 16px rgba(59, 130, 246, .2) }
.send-btn:active:not(:disabled) { transform: scale(.95) }
.send-btn:disabled { opacity: .25; cursor: not-allowed }
.input-hint { display: flex; gap: 14px; margin-top: 6px; max-width: 700px; margin-left: auto; margin-right: auto; font-size: 10px; color: var(--text-muted) }
.warn { color: var(--red) }
</style>
