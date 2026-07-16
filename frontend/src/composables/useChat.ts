import { ref, nextTick } from 'vue'
import type { Message, Conversation, KnowledgeBase } from '../types'
import { listConversations, createConversation, deleteConversation, getMessages } from '../api'

export function useChat() {
  const conversations = ref<Conversation[]>([])
  const activeConvId = ref<number | null>(null)
  const messages = ref<Message[]>([])
  const inputText = ref('')
  const sending = ref(false)
  const chatArea = ref<HTMLElement | null>(null)

  function scrollBottom() {
    nextTick(() => {
      if (chatArea.value) chatArea.value.scrollTop = chatArea.value.scrollHeight
    })
  }

  async function loadConversations() {
    try { const r = await listConversations(); conversations.value = r.data } catch {}
  }

  async function selectConv(conv: Conversation) {
    activeConvId.value = conv.id
    try {
      const r = await getMessages(conv.id)
      messages.value = r.data.map((m: any) => {
        if (m.sources) try { m._sources = JSON.parse(m.sources) } catch {}
        return m
      })
    } catch { messages.value = [] }
    nextTick(scrollBottom)
  }

  function newConv() {
    activeConvId.value = null
    messages.value = []
  }

  async function delConv(id: number) {
    try {
      await deleteConversation(id)
      conversations.value = conversations.value.filter(c => c.id !== id)
      if (activeConvId.value === id) { activeConvId.value = null; messages.value = [] }
    } catch {}
  }

  async function sendMessage(kbIds: number[], params: {
    temperature: number; topP: number; maxTokens: number; historyRounds: number
  }) {
    const text = inputText.value.trim()
    if (!text || sending.value) return
    inputText.value = ''

    if (!activeConvId.value) {
      const title = text.length > 30 ? text.substring(0, 30) + '...' : text
      try {
        const r = await createConversation(title)
        activeConvId.value = r.data.id
        conversations.value.unshift(r.data)
      } catch { return }
    }

    messages.value.push({ role: 'user', content: text })
    scrollBottom()
    const last: Message = { role: 'assistant', content: '', streaming: true }
    messages.value.push(last)
    scrollBottom()
    sending.value = true

    const token = localStorage.getItem('access_token')
    try {
      const resp = await fetch('/api/chat/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          conversation_id: activeConvId.value,
          kb_ids: kbIds,
          question: text,
          temperature: params.temperature,
          top_p: params.topP,
          max_tokens: params.maxTokens,
          history_rounds: params.historyRounds,
        }),
      })
      const reader = resp.body?.getReader()
      if (!reader) { last.content = '响应为空'; last.streaming = false; sending.value = false; return }
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const t = decoder.decode(value, { stream: true })
        for (const line of t.split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const d = JSON.parse(line.slice(6))
            if (d.content) { last.content += d.content; scrollBottom() }
            if (d.done) {
              last.streaming = false
              if (d.sources) {
                last._sources = Array.isArray(d.sources) ? d.sources : (d.sources.sources || d.sources)
                last._evaluation = d.sources.evaluation || null
              }
            }
            if (d.error) { last.content = '错误: ' + d.error; last.streaming = false }
          } catch {}
        }
      }
      last.streaming = false
    } catch (e: any) {
      last.content = '请求失败: ' + (e.message || '网络错误')
      last.streaming = false
    } finally {
      sending.value = false
    }
  }

  return {
    conversations, activeConvId, messages, inputText, sending, chatArea,
    loadConversations, selectConv, newConv, delConv, sendMessage, scrollBottom,
  }
}
