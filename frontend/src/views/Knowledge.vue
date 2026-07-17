<script setup lang="ts">
import {ref, onMounted} from 'vue'
import {useRouter} from 'vue-router'
import {useAuthStore} from '../stores/auth'
import {useKnowledge} from '../composables/useKnowledge'
import {useUpload} from '../composables/useUpload'
import {listChunks, deleteChunk, updateChunk} from '../api'
import type {Chunk} from '../types'
import AppSidebar from '../components/layout/AppSidebar.vue'
import KbListPanel from '../components/knowledge/KbListPanel.vue'
import UploadZone from '../components/knowledge/UploadZone.vue'
import DocumentList from '../components/knowledge/DocumentList.vue'
import ChunkPanel from '../components/knowledge/ChunkPanel.vue'
import WelcomeScreen from '../components/shared/WelcomeScreen.vue'

const router = useRouter()
const auth = useAuthStore()
const {
  kbList, activeKbId, newKbName, newKbDesc, showCreateKb, creatingKb,
  documents, activeDocId,
  loadKBs, selectKB, doCreateKB, doDeleteKB, doDeleteDoc,
} = useKnowledge()
const {
  uploadFiles, chunkSize, overlap, chunkMethod, loading, progress, progStatus,
  onFileChange, doUpload, cancelUpload,
} = useUpload()

const chunks = ref<Chunk[]>([])
const editingChunk = ref<{id: number; content: string} | null>(null)
const chunkJump = ref<number | null>(null)
const errorMsg = ref('')

function showError(msg: string) { errorMsg.value = msg; setTimeout(() => errorMsg.value = '', 3000) }

async function onSelectKB(id: number) {
  await selectKB(id)
  chunks.value = []
}

async function onUpload() {
  await doUpload(activeKbId.value!, showError, () => {
    selectKB(activeKbId.value!)
    loadKBs()
  })
}

async function selectDoc(id: number) {
  activeDocId.value = id
  try { const r = await listChunks(activeKbId.value!, id); chunks.value = r.data } catch {}
}

function startEdit(chunk: Chunk) { editingChunk.value = {id: chunk.id, content: chunk.content} }

async function saveEdit(content: string) {
  if (!editingChunk.value) return
  try {
    await updateChunk(activeKbId.value!, activeDocId.value!, editingChunk.value.id, content)
    editingChunk.value = null
    await selectDoc(activeDocId.value!)
  } catch { showError('保存失败') }
}

async function doDeleteChunk(chunkId: number) {
  if (!confirm('确认删除该分块？')) return
  try {
    await deleteChunk(activeKbId.value!, activeDocId.value!, chunkId)
    await selectDoc(activeDocId.value!)
  } catch {}
}

function doJump() {
  if (chunkJump.value !== null && chunkJump.value >= 1) {
    const idx = chunkJump.value - 1
    const el = document.getElementById('chunk-' + idx)
    el ? el.scrollIntoView({behavior: 'smooth', block: 'center'}) : showError('找不到 #' + chunkJump.value)
    chunkJump.value = null
  }
}

onMounted(loadKBs)
</script>

<template>
  <div class="app-layout">
    <AppSidebar/>
    <KbListPanel
      v-model:new-kb-name="newKbName"
      v-model:new-kb-desc="newKbDesc"
      v-model:show-create-kb="showCreateKb"
      :kb-list="kbList"
      :active-kb-id="activeKbId"
      :creating-kb="creatingKb"
      @select-kb="onSelectKB"
      @delete-kb="doDeleteKB"
      @create-kb="doCreateKB(showError)"
    />
    <main v-if="activeKbId" class="main">
      <header class="main-hd">
        <div class="main-title">{{ kbList.find(k => k.id === activeKbId)?.name }}</div>
      </header>
      <div class="content">
        <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
        <UploadZone
          v-model:chunk-size="chunkSize"
          v-model:overlap="overlap"
          v-model:chunk-method="chunkMethod"
          :upload-files="uploadFiles"
          :loading="loading"
          :progress="progress"
          :prog-status="progStatus"
          @file-change="onFileChange"
          @upload="onUpload"
          @cancel="cancelUpload"
        />
        <DocumentList
          :documents="documents"
          :active-doc-id="activeDocId"
          @select-doc="selectDoc"
          @delete-doc="doDeleteDoc"
        />
        <ChunkPanel
          v-if="activeDocId"
          v-model:chunk-jump="chunkJump"
          :chunks="chunks"
          :editing-chunk="editingChunk"
          @start-edit="startEdit"
          @delete-chunk="doDeleteChunk"
          @save-edit="saveEdit"
          @cancel-edit="editingChunk = null"
          @jump="doJump"
        />
      </div>
    </main>
    <div v-else class="main">
      <WelcomeScreen title="知识库管理" subtitle="选择或创建知识库"/>
    </div>
  </div>
</template>

<style scoped>
.toast { position: fixed; top: 16px; left: 50%; transform: translateX(-50%); background: #ef4444; color: #fff; padding: 10px 20px; border-radius: 8px; font-size: 13px; z-index: 1000; cursor: pointer; box-shadow: 0 4px 12px rgba(239,68,68,.3); animation: tIn .3s cubic-bezier(.4,0,.2,1); max-width: 500px; text-align: center }
@keyframes tIn { from { opacity: 0; transform: translateX(-50%) translateY(-10px) } to { opacity: 1; transform: translateX(-50%) translateY(0) } }
.error-bar { color: var(--red); font-size: 12px; margin-bottom: 12px; padding: 8px 12px; background: var(--red-soft); border-radius: 6px }
.content { flex: 1; overflow-y: auto; padding: 20px 24px; background: transparent }
</style>
