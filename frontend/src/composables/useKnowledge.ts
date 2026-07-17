import { ref } from 'vue'
import type { KnowledgeBase, Document, Chunk } from '../types'
import { listKBs, createKB, deleteKB, listDocuments, deleteDocument } from '../api'

export function useKnowledge() {
  const kbList = ref<KnowledgeBase[]>([])
  const activeKbId = ref<number | null>(null)
  const newKbName = ref('')
  const newKbDesc = ref('')
  const showCreateKb = ref(false)
  const creatingKb = ref(false)
  const documents = ref<Document[]>([])
  const activeDocId = ref<number | null>(null)

  async function loadKBs() {
    try { const r = await listKBs(); kbList.value = r.data } catch {}
  }

  async function selectKB(id: number) {
    activeKbId.value = id
    activeDocId.value = null
    try { const r = await listDocuments(id); documents.value = r.data } catch {}
  }

  async function doCreateKB(errorFn: (msg: string) => void) {
    if (!newKbName.value) return errorFn('请输入名称')
    creatingKb.value = true
    try {
      await createKB({ name: newKbName.value, description: newKbDesc.value })
      newKbName.value = ''; newKbDesc.value = ''; showCreateKb.value = false
      await loadKBs()
    } catch (e: any) {
      errorFn(e.response?.data?.detail || '创建失败')
    } finally { creatingKb.value = false }
  }

  async function doDeleteKB(id: number) {
    if (!confirm('删除知识库？所有数据将被清空。')) return
    try {
      await deleteKB(id)
      await loadKBs()
      if (activeKbId.value === id) { activeKbId.value = null; documents.value = [] }
    } catch {}
  }

  async function doDeleteDoc(docId: number) {
    if (!confirm('确认删除该文档？')) return
    if (!activeKbId.value) return
    try {
      await deleteDocument(activeKbId.value, docId)
      if (activeDocId.value === docId) activeDocId.value = null
      await selectKB(activeKbId.value)
      await loadKBs()
    } catch {}
  }

  return {
    kbList, activeKbId, newKbName, newKbDesc, showCreateKb, creatingKb,
    documents, activeDocId,
    loadKBs, selectKB, doCreateKB, doDeleteKB, doDeleteDoc, refreshDocs: selectKB,
  }
}
