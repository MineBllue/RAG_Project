<script setup lang="ts">
import {ref, onMounted} from 'vue'
import {useRouter} from 'vue-router'
import {useAuthStore} from '../stores/auth'
import {useAvatar} from '../composables/useAvatar'
import {useChat} from '../composables/useChat'
import {listKBs} from '../api'
import type {KnowledgeBase} from '../types'
import AppSidebar from '../components/layout/AppSidebar.vue'
import ConversationList from '../components/chat/ConversationList.vue'
import MessageBubble from '../components/chat/MessageBubble.vue'
import MessageInput from '../components/chat/MessageInput.vue'
import ParamPanel from '../components/chat/ParamPanel.vue'
import WelcomeScreen from '../components/shared/WelcomeScreen.vue'

const router = useRouter()
const auth = useAuthStore()
const {avatar} = useAvatar()
const {
  conversations, activeConvId, messages, inputText, sending, chatArea,
  loadConversations, selectConv, newConv, delConv, sendMessage,
} = useChat()

const kbList = ref<KnowledgeBase[]>([])
const selectedKbIds = ref<number[]>([])
const temperature = ref(0.3)
const topP = ref(0.85)
const maxTokens = ref(2048)
const historyRounds = ref(5)
const showParams = ref(false)

async function loadKBs() {
  try { const r = await listKBs(); kbList.value = r.data as KnowledgeBase[] } catch {}
}

function toggleKb(id: number) {
  const idx = selectedKbIds.value.indexOf(id)
  idx >= 0 ? selectedKbIds.value.splice(idx, 1) : selectedKbIds.value.push(id)
}

function handleSend() {
  sendMessage(selectedKbIds.value, {
    temperature: temperature.value,
    topP: topP.value,
    maxTokens: maxTokens.value,
    historyRounds: historyRounds.value,
  })
}

onMounted(() => { loadKBs(); loadConversations() })
</script>

<template>
  <div class="app-layout">
    <AppSidebar/>
    <ConversationList
      :kb-list="kbList"
      :selected-kb-ids="selectedKbIds"
      :conversations="conversations"
      :active-conv-id="activeConvId"
      @toggle-kb="toggleKb"
      @select-conv="selectConv"
      @delete-conv="delConv"
      @new-conv="newConv"
      @go-knowledge="router.push('/knowledge')"
    />
    <main class="main">
      <header class="main-hd">
        <div class="main-title">
          {{ activeConvId ? conversations.find(c => c.id === activeConvId)?.title || '对话' : '新对话' }}
        </div>
        <div class="hdr-model"><span class="m-dot"></span>Qwen-Max</div>
        <button class="hdr-btn" :class="{active:showParams}" @click="showParams=!showParams">参数</button>
      </header>
      <div class="chat-area" ref="chatArea">
        <WelcomeScreen v-if="messages.length===0" title="InnerQA" subtitle="选择知识库，开始检索问答"/>
        <MessageBubble
          v-for="(msg,i) in messages"
          :key="i"
          :msg="msg"
          :avatar="avatar"
          :username="auth.user?.username||'U'"
        />
      </div>
      <MessageInput v-model="inputText" :selected-kb-count="selectedKbIds.length" :sending="sending" @send="handleSend"/>
    </main>
    <ParamPanel v-model:show="showParams" v-model:temperature="temperature" v-model:top-p="topP" v-model:max-tokens="maxTokens" v-model:history-rounds="historyRounds"/>
  </div>
</template>

<style scoped>
@import '../styles/shared.css';

.hdr-model { font-size: 11px; color: var(--text-secondary); padding: 3px 10px; border-radius: 6px; background: var(--bg-card); border: 1px solid var(--border-subtle); display: flex; align-items: center; gap: 5px }
.m-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green) }
.hdr-btn { height: 30px; padding: 0 12px; border-radius: 6px; background: transparent; border: 1px solid var(--border-subtle); color: var(--text-secondary); cursor: pointer; font-size: 11px; font-family: inherit; transition: all .2s }
.hdr-btn:hover,.hdr-btn.active { background: var(--bg-hover); color: var(--text-primary) }
.chat-area { flex: 1; overflow-y: auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 16px }
</style>
