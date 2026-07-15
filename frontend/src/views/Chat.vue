<script setup lang="ts">
import {ref, onMounted, nextTick} from 'vue'
import {useRouter} from 'vue-router'
import {useAuthStore} from '../stores/auth'
import {useAvatar} from '../composables/useAvatar'
import {listKBs, listConversations, createConversation, deleteConversation, getMessages} from '../api'

const router = useRouter()
const auth = useAuthStore()
const {avatar, setAvatar} = useAvatar()

const kbList = ref<any[]>([]);
const selectedKbIds = ref<number[]>([])
const conversations = ref<any[]>([]);
const activeConvId = ref<number | null>(null)
const messages = ref<any[]>([]);
const inputText = ref('');
const sending = ref(false)
const chatArea = ref<HTMLElement | null>(null)
const showAvatarMenu = ref(false);
const avatarInput = ref<HTMLInputElement | null>(null)
const temperature = ref(0.3);
const topP = ref(0.85);
const maxTokens = ref(2048);
const historyRounds = ref(5);
const showParams = ref(false)

async function loadKBs() {
  try {
    const r = await listKBs();
    kbList.value = r.data
  } catch (e) {
  }
}

async function loadConversations() {
  try {
    const r = await listConversations();
    conversations.value = r.data
  } catch (e) {
  }
}

async function loadMessages(convId: number) {
  try {
    const r = await getMessages(convId);
    messages.value = r.data.map((m: any) => {
      if (m.sources) try {
        m._sources = JSON.parse(m.sources)
      } catch (e) {
      }
      return m
    });
    scrollBottom()
  } catch (e) {
  }
}

function scrollBottom() {
  nextTick(() => {
    if (chatArea.value) chatArea.value.scrollTop = chatArea.value.scrollHeight
  })
}

function toggleKb(id: number) {
  const i = selectedKbIds.value.indexOf(id);
  i >= 0 ? selectedKbIds.value.splice(i, 1) : selectedKbIds.value.push(id)
}

async function selectConv(conv: any) {
  activeConvId.value = conv.id;
  await loadMessages(conv.id)
}

async function delConv(id: number) {
  try {
    await deleteConversation(id);
    conversations.value = conversations.value.filter(c => c.id !== id);
    if (activeConvId.value === id) {
      activeConvId.value = null;
      messages.value = []
    }
  } catch (e) {
  }
}

function toggleMenu() {
  showAvatarMenu.value = !showAvatarMenu.value
}

function triggerUpload() {
  showAvatarMenu.value = false;
  avatarInput.value?.click()
}

function onAvatarChange(e: Event) {
  const i = e.target as HTMLInputElement;
  if (i.files?.length) {
    const r = new FileReader();
    r.onload = ev => setAvatar(ev.target?.result as string);
    r.readAsDataURL(i.files[0])
  }
}

function doLogout() {
  showAvatarMenu.value = false;
  auth.logout();
  router.push('/login')
}

function closeMenu(e: MouseEvent) {
  const t = e.target as HTMLElement;
  if (!t.closest('.avatar-wrap')) showAvatarMenu.value = false
}

async function sendMessage() {
  const text = inputText.value.trim();
  if (!text || sending.value) return;
  inputText.value = ''
  const isNew = !activeConvId.value
  if (isNew) {
    const title = text.length > 30 ? text.substring(0, 30) + '...' : text;
    try {
      const r = await createConversation(title);
      conversations.value.unshift(r.data);
      activeConvId.value = r.data.id
    } catch (e) {
      return
    }
  }
  messages.value.push({role: 'user', content: text});
  scrollBottom()
  sending.value = true;
  messages.value.push({role: 'assistant', content: '', streaming: true, _sources: null});
  scrollBottom()
  const token = localStorage.getItem('access_token')
  try {
    const resp = await fetch('/api/chat/query', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', Authorization: `Bearer ${token}`},
      body: JSON.stringify({
        question: text,
        kb_ids: selectedKbIds.value,
        conversation_id: activeConvId.value,
        temperature: temperature.value,
        top_p: topP.value,
        max_tokens: maxTokens.value,
        history_rounds: historyRounds.value
      })
    })
    const reader = resp.body?.getReader();
    if (!reader) return
    const decoder = new TextDecoder();
    const last = messages.value[messages.value.length - 1]
    while (true) {
      const {done, value} = await reader.read();
      if (done) break
      const t = decoder.decode(value, {stream: true})
      for (const line of t.split('\n')) {
        if (!line.startsWith('data: ')) continue
        try {
          const d = JSON.parse(line.slice(6))
          if (d.content) {
            last.content += d.content;
            scrollBottom()
          }
          if (d.done) {
            last.streaming = false;
            if (d.sources) {
              const sd = Array.isArray(d.sources) ? d.sources : (d.sources.sources || d.sources);
              last._sources = sd;
              last._evaluation = d.sources.evaluation || null
            }
          }
          if (d.error) {
            last.content = '错误: ' + d.error;
            last.streaming = false
          }
        } catch (e) {
        }
      }
    }
    last.streaming = false
  } catch (e: any) {
    const lm = messages.value[messages.value.length - 1];
    lm.content = '请求失败: ' + (e.message || '网络错误');
    lm.streaming = false
  } finally {
    sending.value = false
  }
}

onMounted(() => {
  loadKBs();
  loadConversations();
  document.addEventListener('click', closeMenu)
})
</script>

<template>
  <div class="app-layout">
    <nav class="sidebar">
      <div class="sidebar-top">
        <div class="s-logo" @click="router.push('/chat')"><img src="@/icon/avatar_anime.jpg" alt="Logo"/></div>
        <div :class="['s-item',$route.path==='/chat'?'active':'']" @click="router.push('/chat')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
          <span>对话</span></div>
        <div :class="['s-item',$route.path==='/knowledge'?'active':'']" @click="router.push('/knowledge')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
          </svg>
          <span>知识库</span></div>
      </div>
      <div class="avatar-wrap">
        <div class="s-avatar" @click="toggleMenu"><img v-if="avatar" :src="avatar"/>
          <div v-else class="s-avatar-fb">{{ (auth.user?.username || 'U')[0] }}</div>
        </div>
        <div v-if="showAvatarMenu" class="avatar-menu">
          <div class="menu-item" @click="triggerUpload">更换头像</div>
          <div class="menu-divider"></div>
          <div class="menu-item danger" @click="doLogout">退出登录</div>
        </div>
        <input ref="avatarInput" type="file" accept="image/*" hidden @change="onAvatarChange"/></div>
    </nav>

    <div class="panel-l">
      <div class="pl-hd">知识库
        <button class="pl-btn" @click="router.push('/knowledge')">+</button>
      </div>
      <div class="kb-list">
        <div v-for="kb in kbList" :key="kb.id" :class="['kb-card',{active:selectedKbIds.includes(kb.id)}]"
             @click="toggleKb(kb.id)">
          <div class="kb-icon">K</div>
          <div class="kb-info">
            <div class="kb-name">{{ kb.name }}</div>
            <div class="kb-meta">{{ kb.doc_count }} 文档</div>
          </div>
          <div v-if="selectedKbIds.includes(kb.id)" class="kb-check">&check;</div>
        </div>
        <div v-if="kbList.length===0" class="empty">暂无知识库</div>
      </div>
      <div class="pl-hd" style="border-top:1px solid var(--border-subtle)">会话
        <button class="pl-btn" @click="activeConvId=null;messages=[]">+</button>
      </div>
      <div class="conv-list">
        <div v-for="conv in conversations" :key="conv.id" :class="['conv-row',{active:conv.id===activeConvId}]"
             @click="selectConv(conv)"><span class="conv-dot"></span><span class="conv-name">{{ conv.title }}</span>
          <button class="conv-del" @click.stop="delConv(conv.id)">&times;</button>
        </div>
        <div v-if="conversations.length===0" class="empty">暂无会话</div>
      </div>
    </div>

    <main class="main">
      <header class="main-hd">
        <div class="main-title">
          {{ activeConvId ? conversations.find(c => c.id === activeConvId)?.title || '对话' : '新对话' }}
        </div>
        <div class="hdr-model"><span class="m-dot"></span>Qwen-Max</div>
        <button class="hdr-btn" :class="{active:showParams}" @click="showParams=!showParams">参数</button>
      </header>
      <div class="chat-area" ref="chatArea">
        <div v-if="messages.length===0" class="welcome"><img src="@/icon/avatar_anime.jpg" class="welcome-img"
                                                             alt="Logo"/>
          <h2>InnerQA</h2>
          <p>选择知识库，开始检索问答</p></div>
        <div v-for="(msg,i) in messages" :key="i" :class="['msg',msg.role]">
          <div :class="['msg-av',msg.role]"><img v-if="msg.role==='assistant'" src="@/icon/avatar_anime.jpg"
                                                 class="msg-av-img"/><img v-else-if="avatar" :src="avatar"
                                                                          class="msg-av-img"/><span
              v-else>{{ (auth.user?.username || 'U')[0] }}</span></div>
          <div class="msg-body">
            <div :class="['msg-bub',msg.role]">
              <div v-if="msg.streaming&&!msg.content" class="thinking"><span class="t-dot"></span><span
                  class="t-dot"></span><span class="t-dot"></span></div>
              <div v-else class="msg-text">{{ msg.content }}</div>
              <div v-if="msg._evaluation&&!msg.streaming" class="eval-box">
                <span class="eval-badge">上下文相关性 {{ (msg._evaluation.context_relevance * 100).toFixed(0) }}%</span>
                <span class="eval-badge">答案忠实度 {{ (msg._evaluation.faithfulness * 100).toFixed(0) }}%</span>
              </div>
              <div v-if="msg._sources&&msg._sources.length&&!msg.streaming">
                <div class="src-bar-badge" @click="msg._expanded=!msg._expanded">
                  <span class="src-bar-label">{{ msg._sources.length }} 个引用来源</span>
                  <span class="src-bar-hint">点击{{ msg._expanded ? '收起' : '展开' }}</span>
                </div>
                <div v-if="msg._expanded" class="sources-box">
                  <div v-for="(s,j) in msg._sources.slice(0,3)" :key="j" class="src-item">
                    <div class="src-item-body"><span class="src-kb">{{ s.kb_name }}</span><span class="src-sep">/</span><span
                        class="src-doc">{{ s.doc_name }}</span></div>
                    <span class="src-score">相关度 {{ (s.score * 100).toFixed(0) }}%</span>
                  </div>
                  <div v-if="msg._sources.length>3" class="src-more">+{{ msg._sources.length - 3 }} 条更多</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="input-area">
        <div class="input-row">
          <div class="input-box"><input v-model="inputText" placeholder="输入问题..." @keydown.enter="sendMessage"
                                        :disabled="sending"/></div>
          <button class="send-btn" @click="sendMessage" :disabled="sending||!inputText.trim()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="19" x2="12" y2="5"/>
              <polyline points="5 12 12 5 19 12"/>
            </svg>
          </button>
        </div>
        <div class="input-hint"><span>Enter 发送</span><span v-if="selectedKbIds.length">已选 {{ selectedKbIds.length }} 个知识库</span><span
            v-else class="warn">请选择知识库</span></div>
      </div>
    </main>

    <aside v-if="showParams" class="panel-r">
      <div class="pr-title">推理参数</div>
      <div class="pr-group">
        <div class="pr-row"><span>Temperature</span><span class="pr-val">{{ temperature }}</span></div>
        <input type="range" class="pr-slider" min="0" max="1" step="0.01" v-model.number="temperature"/></div>
      <div class="pr-group">
        <div class="pr-row"><span>Top P</span><span class="pr-val">{{ topP }}</span></div>
        <input type="range" class="pr-slider" min="0" max="1" step="0.01" v-model.number="topP"/></div>
      <div class="pr-group">
        <div class="pr-row"><span>Max Tokens</span><span class="pr-val">{{ maxTokens }}</span></div>
        <input type="range" class="pr-slider" min="256" max="8192" step="256" v-model.number="maxTokens"/></div>
      <div class="pr-group">
        <div class="pr-row"><span>历史轮数</span><span class="pr-val">{{ historyRounds }}</span></div>
        <input type="range" class="pr-slider" min="0" max="20" step="1" v-model.number="historyRounds"/></div>
    </aside>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden
}

.sidebar {
  width: 72px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
  gap: 2px;
  flex-shrink: 0
}

.sidebar-top {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  flex: 1
}

.s-logo {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 8px;
  cursor: pointer;
  flex-shrink: 0
}

.s-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover
}

.s-item {
  width: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 4px;
  border-radius: 10px;
  cursor: pointer;
  color: var(--text-tertiary);
  font-size: 10px;
  transition: all .2s
}

.s-item:hover {
  color: var(--text-secondary);
  background: var(--bg-hover)
}

.s-item.active {
  color: var(--accent);
  background: var(--accent-soft)
}

.avatar-wrap {
  position: relative
}

.s-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  transition: all .25s
}

.s-avatar:hover {
  transform: scale(1.08)
}

.s-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover
}

.s-avatar-fb {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, var(--red), var(--gold));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: #fff
}

.avatar-menu {
  position: fixed;
  bottom: 40px;
  left: 86px;
  background: var(--bg-surface);
  border: 1px solid var(--border-card);
  border-radius: 10px;
  padding: 4px;
  min-width: 130px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, .12);
  z-index: 1000;
  animation: mIn .15s cubic-bezier(.4, 0, .2, 1)
}

@keyframes mIn {
  from {
    opacity: 0;
    transform: translateY(4px)
  }
  to {
    opacity: 1;
    transform: translateY(0)
  }
}

.menu-item {
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  border-radius: 6px;
  cursor: pointer
}

.menu-item:hover {
  background: var(--bg-hover)
}

.menu-item.danger {
  color: var(--red)
}

.menu-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: 2px 0
}

.panel-l {
  width: 240px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden
}

.pl-hd {
  padding: 12px 14px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: var(--text-tertiary);
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center
}

.pl-btn {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .15s
}

.pl-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary)
}

.kb-list {
  padding: 0 6px 8px;
  max-height: 40%;
  overflow-y: auto
}

.kb-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 1px;
  transition: all .2s
}

.kb-card:hover {
  background: var(--bg-hover);
  transform: translateX(2px)
}

.kb-card.active {
  background: var(--accent-soft)
}

.kb-icon {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  background: var(--accent-soft);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0
}

.kb-info {
  flex: 1;
  min-width: 0
}

.kb-name {
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis
}

.kb-meta {
  font-size: 10px;
  color: var(--text-tertiary)
}

.kb-check {
  color: var(--accent);
  font-size: 13px;
  font-weight: 700
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 6px 8px
}

.conv-row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 1px;
  font-size: 12px;
  color: var(--text-secondary);
  transition: all .2s
}

.conv-row:hover {
  background: var(--bg-hover)
}

.conv-row.active {
  background: var(--accent-soft);
  color: var(--accent)
}

.conv-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--text-tertiary);
  flex-shrink: 0
}

.conv-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis
}

.conv-del {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 13px;
  opacity: 0;
  transition: all .15s
}

.conv-row:hover .conv-del {
  opacity: 1
}

.conv-del:hover {
  background: rgba(239, 68, 68, .12);
  color: var(--red)
}

.empty {
  padding: 20px;
  text-align: center;
  color: var(--text-muted);
  font-size: 11px
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden
}

.main-hd {
  height: 48px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  gap: 10px;
  flex-shrink: 0
}

.main-title {
  font-weight: 600;
  font-size: 13px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap
}

.hdr-model {
  font-size: 11px;
  color: var(--text-secondary);
  padding: 3px 10px;
  border-radius: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  gap: 5px
}

.m-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green)
}

.hdr-btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 6px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 11px;
  font-family: inherit;
  transition: all .2s
}

.hdr-btn:hover, .hdr-btn.active {
  background: var(--bg-hover);
  color: var(--text-primary)
}

.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px
}

.welcome {
  text-align: center;
  margin-top: 60px;
  animation: aIn .6s cubic-bezier(.4, 0, .2, 1)
}

@keyframes aIn {
  from {
    opacity: 0;
    transform: translateY(20px)
  }
  to {
    opacity: 1;
    transform: translateY(0)
  }
}

.welcome-img {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  object-fit: cover;
  margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, .08)
}

.welcome h2 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 6px
}

.welcome p {
  color: var(--text-tertiary);
  font-size: 13px
}

.msg {
  display: flex;
  gap: 10px;
  max-width: 720px;
  animation: msgIn .4s cubic-bezier(.34, 1.56, .64, 1)
}

@keyframes msgIn {
  from {
    opacity: 0;
    transform: translateY(10px) scale(.98)
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1)
  }
}

.msg.user {
  flex-direction: row-reverse;
  align-self: flex-end
}

.msg-av {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  overflow: hidden
}

.msg-av.user {
  background: transparent
}

.msg-av.assistant {
  background: transparent
}

.msg-av-img {
  width: 100%;
  height: 100%;
  object-fit: cover
}

.msg-body {
  font-size: 13px;
  line-height: 1.6;
  min-width: 0
}

.msg-bub {
  padding: 10px 14px;
  border-radius: 12px
}

.msg-bub.user {
  background: var(--accent-soft);
  border: 1px solid rgba(59, 130, 246, .2);
  border-bottom-right-radius: 4px
}

.msg-bub.assistant {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-bottom-left-radius: 4px
}

.msg-text {
  white-space: pre-wrap
}

.eval-box {
  display: flex;
  gap: 8px;
  margin-top: 6px
}

.src-bar-badge {
  width: 218px;
  padding: 3px 10px;
  margin-top: 4px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 500;
  background: var(--accent-soft);
  color: var(--accent);
}

.eval-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 500;
  background: var(--accent-soft);
  color: var(--accent)
}

.thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0
}

.t-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: dotBounce 1.4s ease-in-out infinite
}

.t-dot:nth-child(2) {
  animation-delay: .2s
}

.t-dot:nth-child(3) {
  animation-delay: .4s
}

@keyframes dotBounce {
  0%, 80%, 100% {
    opacity: .2;
    transform: translateY(0)
  }
  40% {
    opacity: 1;
    transform: translateY(-6px)
  }
}

.sources-box {
  margin-top: 4px;
  padding: 8px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  animation: srcIn .25s cubic-bezier(.4, 0, .2, 1)
}

@keyframes srcIn {
  from {
    opacity: 0;
    max-height: 0
  }
  to {
    opacity: 1;
    max-height: 200px
  }
}

.src-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 3px 0;
  font-size: 11px
}

.src-kb {
  color: var(--accent);
  font-weight: 500;
  padding: 1px 6px;
  background: var(--accent-soft);
  border-radius: 3px;
  white-space: nowrap
}

.src-doc {
  color: var(--text-secondary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap
}

.src-score {
  color: var(--green);
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0
}

.input-area {
  padding: 10px 20px 14px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  flex-shrink: 0
}

.input-row {
  max-width: 700px;
  margin: 0 auto;
  display: flex;
  gap: 8px
}

.input-box {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 10px;
  padding: 0 10px 0 14px;
  transition: all .25s
}

.input-box:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
  transform: translateY(-1px)
}

.input-box input {
  width: 100%;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
  outline: none;
  line-height: 38px
}

.input-box input::placeholder {
  color: var(--text-muted)
}

.send-btn {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: var(--accent);
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all .25s
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 16px rgba(59, 130, 246, .2)
}

.send-btn:active:not(:disabled) {
  transform: scale(.95)
}

.send-btn:disabled {
  opacity: .25;
  cursor: not-allowed
}

.input-hint {
  display: flex;
  gap: 14px;
  margin-top: 6px;
  max-width: 700px;
  margin-left: auto;
  margin-right: auto;
  font-size: 10px;
  color: var(--text-muted)
}

.warn {
  color: var(--red)
}

.panel-r {
  width: 240px;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-subtle);
  padding: 14px;
  overflow-y: auto;
  animation: sIn .3s cubic-bezier(.4, 0, .2, 1)
}

@keyframes sIn {
  from {
    transform: translateX(20px);
    opacity: 0
  }
  to {
    transform: translateX(0);
    opacity: 1
  }
}

.pr-title {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--text-tertiary);
  font-weight: 600;
  margin-bottom: 12px
}

.pr-group {
  margin-bottom: 14px
}

.pr-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  margin-bottom: 4px
}

.pr-val {
  color: var(--text-primary);
  font-weight: 500;
  font-family: monospace;
  font-size: 10px
}

.pr-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: var(--border-card);
  outline: none
}

.pr-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  border: 2px solid var(--bg-surface);
  transition: transform .15s
}

.pr-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2)
}

@media (max-width: 768px) {
  .panel-l, .panel-r {
    display: none
  }
}
</style>
.src-bar{display:inline-flex;align-items:center;gap:6px;margin-top:6px;padding:4px 12px;border-radius:12px;background:var(--bg-card);border:1px solid var(--border-subtle);cursor:pointer;font-size:10px;color:var(--text-secondary);transition:all .15s;user-select:none}
.src-bar:hover{background:var(--accent-soft);color:var(--accent)}
.src-bar-icon{font-size:10px}
.src-bar-label{font-weight:500}
.src-bar-hint{font-size:10px;color:var(--text-tertiary)}
.src-item-body{display:flex;align-items:center;gap:4px;min-width:0;overflow:hidden}
.src-sep{color:var(--text-muted);font-size:9px}
.src-more{font-size:10px;color:var(--text-tertiary);text-align:center;padding:4px 0}
.msg-av-img{border-radius:50%}
