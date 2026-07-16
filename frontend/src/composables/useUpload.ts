import { ref } from 'vue'
import type { ChunkMethod } from '../types'

export function useUpload() {
  const uploadFiles = ref<File[]>([])
  const chunkSize = ref(500)
  const overlap = ref(50)
  const chunkMethod = ref<ChunkMethod>('default')
  const loading = ref(false)
  const progress = ref(0)
  const progStatus = ref('')

  function onFileChange(files: FileList) {
    uploadFiles.value = Array.from(files)
  }

  async function doUpload(kbId: number, errorFn: (msg: string) => void, onSuccess: () => void) {
    if (!uploadFiles.value.length) return
    loading.value = true
    progress.value = 10; progStatus.value = '准备上传...'
    await new Promise(r => setTimeout(r, 300))
    progress.value = 25; progStatus.value = '上传中...'
    const fd = new FormData()
    uploadFiles.value.forEach(f => fd.append('files', f))
    fd.append('chunk_size', String(chunkSize.value))
    fd.append('chunk_overlap', String(overlap.value))
    fd.append('chunk_method', chunkMethod.value)
    progress.value = 40; progStatus.value = '解析文档...'
    await new Promise(r => setTimeout(r, 200))
    progress.value = 60; progStatus.value = '向量化中...'
    try {
      const token = localStorage.getItem('access_token')
      const resp = await fetch('/api/knowledge/' + kbId + '/upload-batch', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + token },
        body: fd,
      })
      await resp.json()
      progress.value = 85; progStatus.value = '存储中...'
      await new Promise(r => setTimeout(r, 200))
      progress.value = 100; progStatus.value = '完成'
      setTimeout(() => { progress.value = 0; progStatus.value = '' }, 1500)
      uploadFiles.value = []
      onSuccess()
    } catch (e: any) {
      progress.value = 0; progStatus.value = '失败'
      errorFn('上传失败: ' + (e.message || ''))
    } finally { loading.value = false }
  }

  function cancelUpload() {
    uploadFiles.value = []
    loading.value = false
  }

  return {
    uploadFiles, chunkSize, overlap, chunkMethod, loading, progress, progStatus,
    onFileChange, doUpload, cancelUpload,
  }
}
