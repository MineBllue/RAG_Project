import { ref } from 'vue'
import type { ChunkMethod } from '../types'
import { uploadDocument } from '../api'

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
    loading.value = true; progress.value = 0; progStatus.value = ''
    const fd = new FormData()
    uploadFiles.value.forEach(f => fd.append('files', f))
    fd.append('chunk_size', String(chunkSize.value))
    fd.append('overlap', String(overlap.value))
    fd.append('chunk_method', chunkMethod.value)
    try {
      await uploadDocument(kbId, fd)
      uploadFiles.value = []
      onSuccess()
    } catch (e: any) {
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
