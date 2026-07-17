/** 会话 */
export interface Conversation {
  id: number
  title: string
}

/** 评估结果 */
export interface Evaluation {
  context_relevance: number
  context_recall?: number
  context_precision?: number
  faithfulness: number
  answer_relevance?: number
  method?: string
}

/** 引用来源 */
export interface Source {
  kb_name: string
  doc_name: string
  score: number
}

/** 消息 */
export interface Message {
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
  _sources?: Source[]
  _evaluation?: Evaluation | null
  _expanded?: boolean
}

/** SSE 流式数据块 */
export interface StreamChunk {
  content?: string
  done?: boolean
  error?: string
  sources?: {
    sources?: Source[]
    evaluation?: Evaluation
  }
}
