<script setup lang="ts">
import {ref} from 'vue'
import type {Message} from '../../types'
import ThinkingDots from './ThinkingDots.vue'

defineProps<{
  msg: Message
  avatar: string | null
  username: string
}>()

const expanded = ref(false)
</script>

<template>
  <div :class="['msg', msg.role]">
    <div :class="['msg-av', msg.role]">
      <img v-if="msg.role === 'assistant'" src="@/icon/avatar_anime.jpg" class="msg-av-img" />
      <img v-else-if="avatar" :src="avatar" class="msg-av-img" />
      <span v-else>{{ (username || 'U')[0] }}</span>
    </div>
    <div class="msg-body">
      <div :class="['msg-bub', msg.role]">
        <ThinkingDots v-if="msg.streaming && !msg.content" />
        <div v-else class="msg-text">{{ msg.content }}</div>
        <div v-if="msg._evaluation && !msg.streaming" class="eval-box">
          <span class="eval-badge">上下文相关性 {{ (msg._evaluation.context_relevance * 100).toFixed(0) }}%</span>
          <span class="eval-badge">答案忠实度 {{ (msg._evaluation.faithfulness * 100).toFixed(0) }}%</span>
        </div>
        <div v-if="msg._sources && msg._sources.length && !msg.streaming">
          <div class="src-bar-badge" @click="expanded = !expanded">
            <span class="src-bar-label">{{ msg._sources.length }} 个引用来源</span>
            <span class="src-bar-hint">点击{{ expanded ? '收起' : '展开' }}</span>
          </div>
          <div v-if="expanded" class="sources-box">
            <div v-for="(s, j) in msg._sources.slice(0, 3)" :key="j" class="src-item">
              <div class="src-item-body">
                <span class="src-kb">{{ s.kb_name }}</span>
                <span class="src-sep">/</span>
                <span class="src-doc">{{ s.doc_name }}</span>
              </div>
              <span class="src-score">相关度 {{ (s.score * 100).toFixed(0) }}%</span>
            </div>
            <div v-if="msg._sources.length > 3" class="src-more">+{{ msg._sources.length - 3 }} 条更多</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.msg { display: flex; gap: 10px; max-width: 720px; animation: msgIn .4s cubic-bezier(.34, 1.56, .64, 1) }
@keyframes msgIn { from { opacity: 0; transform: translateY(10px) scale(.98) } to { opacity: 1; transform: translateY(0) scale(1) } }
.msg.user { flex-direction: row-reverse; align-self: flex-end }
.msg-av { width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; overflow: hidden }
.msg-av.user { background: transparent }
.msg-av.assistant { background: transparent }
.msg-av-img { width: 100%; height: 100%; object-fit: cover; border-radius: 50% }
.msg-body { font-size: 13px; line-height: 1.6; min-width: 0 }
.msg-bub { padding: 10px 14px; border-radius: 12px }
.msg-bub.user { background: rgba(99,102,241,0.12); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); border: 1px solid rgba(99,102,241,0.15); border-bottom-right-radius: 4px }
.msg-bub.assistant { background: rgba(255,255,255,0.55); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); border: 1px solid rgba(0,0,0,0.04); box-shadow: 0 1px 4px rgba(0,0,0,0.04); border-bottom-left-radius: 4px }
.msg-text { white-space: pre-wrap }
.eval-box { display: flex; gap: 8px; margin-top: 6px }
.eval-badge { padding: 3px 10px; border-radius: 12px; font-size: 10px; font-weight: 500; background: var(--accent-soft); color: var(--accent) }
.src-bar-badge { width: 218px; padding: 3px 10px; margin-top: 4px; border-radius: 12px; font-size: 10px; font-weight: 500; background: var(--accent-soft); color: var(--accent); cursor: pointer; user-select: none }
.src-bar-label { font-weight: 500 }
.src-bar-hint { font-size: 10px; color: var(--text-tertiary) }
.sources-box { margin-top: 4px; padding: 8px 10px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; animation: srcIn .25s cubic-bezier(.4, 0, .2, 1) }
@keyframes srcIn { from { opacity: 0; max-height: 0 } to { opacity: 1; max-height: 200px } }
.src-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 3px 0; font-size: 11px }
.src-item-body { display: flex; align-items: center; gap: 4px; min-width: 0; overflow: hidden }
.src-kb { color: var(--accent); font-weight: 500; padding: 1px 6px; background: var(--accent-soft); border-radius: 3px; white-space: nowrap }
.src-sep { color: var(--text-muted); font-size: 9px }
.src-doc { color: var(--text-secondary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.src-score { color: var(--green); font-size: 10px; font-weight: 600; flex-shrink: 0 }
.src-more { font-size: 10px; color: var(--text-tertiary); text-align: center; padding: 4px 0 }
</style>
