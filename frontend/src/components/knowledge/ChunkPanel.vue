<script setup lang="ts">
import {ref, watch} from 'vue'
import type {Chunk} from '../../types'

const chunkJump = defineModel<number | null>('chunkJump', { default: null })

const props = defineProps<{
  chunks: Chunk[]
  editingChunk: { id: number; content: string } | null
}>()

const emit = defineEmits<{
  'start-edit': [chunk: Chunk]
  'delete-chunk': [id: number]
  'save-edit': [content: string]
  'cancel-edit': []
  'jump': []
}>()

const editContent = ref('')

watch(() => props.editingChunk, (val) => {
  if (val) editContent.value = val.content
})

function handleSave() {
  emit('save-edit', editContent.value)
}
</script>

<template>
  <section class="sec">
    <div class="chunk-hd-bar">
      <h3>分块 ({{ chunks.length }})</h3>
      <div class="chunk-nav">
        <input
          type="number"
          class="jump-inp"
          v-model.number="chunkJump"
          placeholder="#"
          min="1"
          :max="chunks.length"
          @keydown.enter="emit('jump')"
        />
        <button class="jump-btn" @click="emit('jump')">跳转</button>
      </div>
    </div>
    <div class="chunk-list" v-if="chunks.length">
      <div
        v-for="chunk in chunks"
        :key="chunk.id"
        :id="'chunk-' + chunk.chunk_index"
        class="chunk-card"
      >
        <div class="chunk-hd">
          <span>Chunk #{{ chunk.chunk_index + 1 }}</span>
          <div class="chunk-act">
            <button @click="emit('start-edit', chunk)">编辑</button>
            <button class="dng" @click="emit('delete-chunk', chunk.id)">删除</button>
          </div>
        </div>
        <div v-if="editingChunk?.id === chunk.id" class="chunk-edit">
          <textarea v-model="editContent" rows="4"></textarea>
          <div class="edit-act">
            <button @click="handleSave">保存</button>
            <button class="sec" @click="emit('cancel-edit')">取消</button>
          </div>
        </div>
        <div v-else class="chunk-content">{{ chunk.content }}</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.sec { margin-bottom: 28px }
.chunk-hd-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px }
.chunk-hd-bar h3 { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 0 }
.chunk-nav { display: flex; gap: 4px }
.jump-inp { width: 48px; padding: 3px 6px; background: var(--bg-card); border: 1px solid var(--border-card); border-radius: 4px; color: var(--text-primary); font-size: 11px; font-family: inherit; outline: none; text-align: center }
.jump-btn { padding: 3px 8px; background: var(--accent); color: #fff; border: none; border-radius: 4px; font-size: 10px; cursor: pointer; font-family: inherit }
.chunk-list { display: flex; flex-direction: column; gap: 6px }
.chunk-card { background: rgba(255,255,255,0.4); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); border: 1px solid rgba(0,0,0,0.04); border-radius: 10px; overflow: hidden; transition: all .2s }
.chunk-card:hover { border-color: rgba(0,0,0,0.1); background: rgba(255,255,255,0.6) }
.chunk-hd { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: var(--bg-hover); font-size: 10px; color: var(--text-tertiary); font-weight: 600 }
.chunk-act { display: flex; gap: 4px }
.chunk-act button { padding: 2px 8px; border-radius: 4px; border: none; font-size: 10px; cursor: pointer; background: var(--bg-card); color: var(--text-secondary); font-family: inherit }
.chunk-act button.dng { color: var(--red) }
.chunk-act button.dng:hover { background: var(--red-soft) }
.chunk-content { padding: 10px 12px; font-size: 12px; line-height: 1.6; color: var(--text-secondary); white-space: pre-wrap }
.chunk-edit { padding: 10px 12px }
.chunk-edit textarea { width: 100%; background: var(--bg-root); border: 1px solid var(--border-card); border-radius: 6px; color: var(--text-primary); font-size: 12px; font-family: inherit; padding: 8px; resize: vertical; outline: none }
.chunk-edit textarea:focus { border-color: var(--accent) }
.edit-act { display: flex; gap: 6px; margin-top: 6px; height: 40px }
.edit-act button { padding: 5px 14px; border-radius: 5px; border: none; font-size: 11px; cursor: pointer; background: var(--accent); color: #fff; font-family: inherit; height: 26px }
.edit-act button.sec { background: var(--bg-hover); color: var(--text-secondary) }
</style>
