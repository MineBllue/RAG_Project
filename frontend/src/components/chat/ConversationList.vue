<script setup lang="ts">
import type {KnowledgeBase, Conversation} from '../../types'

defineProps<{
  kbList: KnowledgeBase[]
  selectedKbIds: number[]
  conversations: Conversation[]
  activeConvId: number | null
}>()

const emit = defineEmits<{
  'toggle-kb': [id: number]
  'select-conv': [conv: Conversation]
  'delete-conv': [id: number]
  'new-conv': []
  'go-knowledge': []
}>()
</script>

<template>
  <div class="panel-l">
    <div class="pl-hd">
      知识库
      <button class="pl-btn" @click="emit('go-knowledge')">+</button>
    </div>
    <div class="kb-list">
      <div
        v-for="kb in kbList"
        :key="kb.id"
        :class="['kb-card', { active: selectedKbIds.includes(kb.id) }]"
        @click="emit('toggle-kb', kb.id)"
      >
        <div class="kb-icon">K</div>
        <div class="kb-info">
          <div class="kb-name">{{ kb.name }}</div>
          <div class="kb-meta">{{ kb.doc_count }} 文档</div>
        </div>
        <div v-if="selectedKbIds.includes(kb.id)" class="kb-check">&check;</div>
      </div>
      <div v-if="kbList.length === 0" class="empty">暂无知识库</div>
    </div>
    <div class="pl-hd" style="border-top:1px solid var(--border-subtle)">
      会话
      <button class="pl-btn" @click="emit('new-conv')">+</button>
    </div>
    <div class="conv-list">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        :class="['conv-row', { active: conv.id === activeConvId }]"
        @click="emit('select-conv', conv)"
      >
        <span class="conv-dot"></span>
        <span class="conv-name">{{ conv.title }}</span>
        <button class="conv-del" @click.stop="emit('delete-conv', conv.id)">&times;</button>
      </div>
      <div v-if="conversations.length === 0" class="empty">暂无会话</div>
    </div>
  </div>
</template>

<style scoped>
.kb-list { padding: 0 6px 8px; max-height: 40%; overflow-y: auto }
.kb-card { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 1px; transition: all .2s }
.kb-card:hover { background: var(--bg-hover); transform: translateX(2px) }
.kb-card.active { background: var(--accent-soft) }
.kb-icon { width: 26px; height: 26px; border-radius: 6px; background: var(--accent-soft); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0 }
.kb-info { flex: 1; min-width: 0 }
.kb-name { font-size: 12px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.kb-meta { font-size: 10px; color: var(--text-tertiary) }
.kb-check { color: var(--accent); font-size: 13px; font-weight: 700 }
.conv-list { flex: 1; overflow-y: auto; padding: 0 6px 8px }
.conv-row { display: flex; align-items: center; gap: 7px; padding: 6px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 1px; font-size: 12px; color: var(--text-secondary); transition: all .2s }
.conv-row:hover { background: var(--bg-hover) }
.conv-row.active { background: var(--accent-soft); color: var(--accent) }
.conv-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--text-tertiary); flex-shrink: 0 }
.conv-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.conv-del { width: 20px; height: 20px; border-radius: 4px; background: transparent; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 13px; opacity: 0; transition: all .15s }
.conv-row:hover .conv-del { opacity: 1 }
.conv-del:hover { background: rgba(239, 68, 68, .12); color: var(--red) }
</style>
