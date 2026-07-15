/** 知识库 */
export interface KnowledgeBase {
  id: number
  name: string
  description: string
  doc_count: number
}

/** 创建知识库参数 */
export interface CreateKBParams {
  name: string
  description: string
}

/** 文档 */
export interface Document {
  id: number
  filename: string
  status: 'pending' | 'parsing' | 'completed' | 'failed'
  chunk_count: number
}

/** 文档分块 */
export interface Chunk {
  id: number
  chunk_index: number
  content: string
}

/** 分块方法 */
export type ChunkMethod = 'default' | 'semantic' | 'fixed'
