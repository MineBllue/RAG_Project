<script setup lang="ts">
import type {KnowledgeBase} from '../../types'

const newKbName = defineModel<string>('newKbName', { default: '' })
const newKbDesc = defineModel<string>('newKbDesc', { default: '' })
const showCreateKb = defineModel<boolean>('showCreateKb', { default: false })

defineProps<{
  kbList: KnowledgeBase[]
  activeKbId: number | null
  creatingKb: boolean
}>()

const emit = defineEmits<{
  'select-kb': [id: number]
  'delete-kb': [id: number]
  'create-kb': []
}>()
</script>

<template>
  <div class="panel-l">
    <div class="pl-hd">
      知识库
      <button class="pl-btn" @click="showCreateKb = !showCreateKb">+</button>
    </div>
    <div v-if="showCreateKb" class="create-form">
      <input v-model="newKbName" placeholder="名称" class="inp" />
      <input v-model="newKbDesc" placeholder="描述" class="inp" />
      <button class="btn-s" :disabled="creatingKb" @click="emit('create-kb')">
        {{ creatingKb ? '创建中...' : '创建' }}
      </button>
    </div>
    <div class="kb-list-f">
      <div
        v-for="kb in kbList"
        :key="kb.id"
        :class="['kb-row', { active: kb.id === activeKbId }]"
        @click="emit('select-kb', kb.id)"
      >
        <div class="kb-row-i">
          <div class="kb-row-n">{{ kb.name }}</div>
          <div class="kb-row-m">{{ kb.doc_count }} 文档</div>
        </div>
        <button class="kb-del" @click.stop="emit('delete-kb', kb.id)">&times;</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-form { padding: 8px 12px; display: flex; flex-direction: column; gap: 6px; border-bottom: 1px solid var(--border-subtle); animation: slideDownIn .3s cubic-bezier(.4, 0, .2, 1) }
@keyframes slideDownIn { from { opacity: 0; transform: translateY(-10px) } to { opacity: 1; transform: translateY(0) } }
.inp { padding: 7px 10px; background: var(--bg-card); border: 1px solid var(--border-card); border-radius: 6px; color: var(--text-primary); font-size: 12px; font-family: inherit; outline: none }
.inp:focus { border-color: var(--accent) }
.btn-s { padding: 6px 12px; background: var(--accent); color: #fff; border: none; border-radius: 6px; font-size: 12px; cursor: pointer; font-family: inherit }
.btn-s:disabled { opacity: .5; cursor: not-allowed }
.kb-list-f { flex: 1; overflow-y: auto; padding: 4px 6px }
.kb-row { display: flex; align-items: center; justify-content: space-between; padding: 7px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 1px; transition: all .2s }
.kb-row:hover { background: var(--bg-hover) }
.kb-row.active { background: var(--accent-soft) }
.kb-row-i { flex: 1; min-width: 0 }
.kb-row-n { font-size: 12px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.kb-row-m { font-size: 10px; color: var(--text-tertiary) }
.kb-del { width: 22px; height: 22px; border-radius: 4px; background: transparent; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 14px; opacity: 0; transition: all .15s }
.kb-row:hover .kb-del { opacity: 1 }
.kb-del:hover { background: rgba(239, 68, 68, .12); color: var(--red) }
</style>
