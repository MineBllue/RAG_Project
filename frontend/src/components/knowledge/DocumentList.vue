<script setup lang="ts">
import type {Document} from '../../types'

defineProps<{
  documents: Document[]
  activeDocId: number | null
}>()

const emit = defineEmits<{
  'select-doc': [id: number]
  'delete-doc': [id: number]
}>()
</script>

<template>
  <section class="sec">
    <h3>文档 ({{ documents.length }})</h3>
    <div class="doc-list">
      <div
        v-for="doc in documents"
        :key="doc.id"
        :class="['doc-row', { active: doc.id === activeDocId }]"
        @click="emit('select-doc', doc.id)"
      >
        <div class="doc-icon">D</div>
        <div class="doc-name">{{ doc.filename }}</div>
        <div class="doc-st">{{ doc.status }}</div>
        <div class="doc-ch">块: {{ doc.chunk_count || 0 }}</div>
        <button class="doc-del" @click.stop="emit('delete-doc', doc.id)">&times;</button>
      </div>
      <div v-if="documents.length === 0" class="empty-doc">暂无文档</div>
    </div>
  </section>
</template>

<style scoped>
.sec { margin-bottom: 28px }
.sec h3 { font-size: 12px; font-weight: 600; margin-bottom: 8px; color: var(--text-secondary) }
.doc-list { display: flex; flex-direction: column; gap: 2px }
.doc-row { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 8px; cursor: pointer; transition: all .2s }
.doc-row:hover { background: var(--bg-hover) }
.doc-row.active { background: var(--accent-soft) }
.doc-icon { width: 24px; height: 24px; border-radius: 5px; background: var(--gold-soft); color: var(--gold); display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; flex-shrink: 0 }
.doc-name { flex: 1; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.doc-st { font-size: 10px; padding: 2px 6px; border-radius: 3px; background: var(--bg-root); color: var(--text-tertiary) }
.doc-ch { font-size: 10px; color: var(--text-tertiary) }
.doc-del { width: 20px; height: 20px; border-radius: 4px; background: transparent; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 13px; opacity: 0; transition: all .15s }
.doc-row:hover .doc-del { opacity: 1 }
.doc-del:hover { background: rgba(239, 68, 68, .12); color: var(--red) }
.empty-doc { padding: 12px; text-align: center; color: var(--text-muted); font-size: 11px }
</style>
