<script setup lang="ts">
import { ref } from 'vue'

const chunkSize = defineModel<number>('chunkSize', { default: 500 })
const overlap = defineModel<number>('overlap', { default: 50 })
const chunkMethod = defineModel<string>('chunkMethod', { default: 'default' })
const fInp = ref<HTMLInputElement | null>(null)

defineProps<{
  uploadFiles: File[]
  loading: boolean
  progress: number
  progStatus: string
}>()

const emit = defineEmits<{
  'file-change': [files: FileList]
  'upload': []
  'cancel': []
}>()

</script>

<template>
  <section class="sec">
    <h3>上传文档</h3>
    <div class="fmts">支持: PDF / Word / PPT / Markdown / TXT / CSV</div>
    <div
      class="upload-zone"
      :class="{ has: uploadFiles.length > 0 }"
      @click="fInp?.click()"
    >
      <input
        ref="fInp"
        type="file"
        accept=".pdf,.docx,.doc,.pptx,.ppt,.md,.markdown,.txt,.csv,.zip"
        multiple
        hidden
        @change="emit('file-change', ($event.target as HTMLInputElement).files!)"
      />
      <svg v-if="uploadFiles.length === 0" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      <span v-if="uploadFiles.length === 0">点击选择文件（支持多选）</span>
      <span v-else class="f-name">{{ uploadFiles.length }} 个文件已选择</span>
    </div>
    <div v-if="uploadFiles.length" class="up-params">
      <div class="msel">
        <label class="prm-lbl">分块</label>
        <select v-model="chunkMethod">
          <option value="default">默认</option>
          <option value="semantic">语义</option>
          <option value="markdown">Markdown 结构</option>
          <option value="parent_child">父子切块</option>
        </select>
      </div>
      <div class="msel">
        <label class="prm-lbl">大小</label>
        <input type="number" v-model.number="chunkSize" min="100" max="5000" />
      </div>
      <div class="msel">
        <label class="prm-lbl">重叠</label>
        <input type="number" v-model.number="overlap" min="0" max="500" />
      </div>
      <button class="btn-up" :disabled="loading" @click="emit('upload')">
        {{ loading ? '处理中...' : '上传并处理' }}
      </button>
      <button class="btn-cl" :disabled="loading" @click="emit('cancel')">取消</button>
    </div>
    <div v-if="loading" class="prog-wrap">
      <div class="prog-bar"><div class="prog-fill" :style="{ width: progress + '%' }"></div></div>
      <div class="prog-pct">{{ progress }}% {{ progStatus }}</div>
    </div>
  </section>
</template>

<style scoped>
.sec { margin-bottom: 28px }
.sec h3 { font-size: 12px; font-weight: 600; margin-bottom: 8px; color: var(--text-secondary) }
.fmts { font-size: 10px; color: var(--text-muted); margin-bottom: 8px }
.upload-zone { border: 2px dashed var(--border-card); border-radius: 12px; padding: 28px; text-align: center; cursor: pointer; transition: all .25s; color: var(--text-tertiary); font-size: 13px; display: flex; flex-direction: column; align-items: center; gap: 8px }
.upload-zone:hover { border-color: var(--accent); background: var(--accent-soft); color: var(--text-secondary) }
.upload-zone.has { border-color: var(--accent); border-style: solid; background: var(--accent-soft) }
.f-name { color: var(--accent); font-weight: 500 }
.up-params { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 12px }
.msel { display: flex; align-items: center; gap: 4px }
.prm-lbl { font-size: 10px; color: var(--text-tertiary); white-space: nowrap }
.msel select, .msel input { padding: 3px 6px; background: var(--bg-card); border: 1px solid var(--border-card); border-radius: 4px; color: var(--text-primary); font-size: 11px; font-family: inherit; outline: none }
.msel input { width: 60px }
.btn-up { padding: 5px 12px; background: var(--accent); color: #fff; border: none; border-radius: 5px; font-size: 11px; cursor: pointer; font-family: inherit }
.btn-up:disabled { opacity: .5; cursor: not-allowed }
.btn-cl { padding: 5px 10px; background: var(--bg-hover); color: var(--text-secondary); border: none; border-radius: 5px; font-size: 11px; cursor: pointer; font-family: inherit }
.btn-cl:disabled { opacity: .5; cursor: not-allowed }
.prog-wrap { margin-top: 10px }
.prog-bar { height: 4px; background: var(--border-card); border-radius: 2px; overflow: hidden }
.prog-fill { height: 100%; background: var(--accent); transition: width .3s ease }
.prog-pct { font-size: 10px; color: var(--text-tertiary); margin-top: 4px; text-align: right }
</style>
