<script setup lang="ts">
import {ref, onMounted} from 'vue'
import AppSidebar from '../components/layout/AppSidebar.vue'
import {getFAQStats, addFAQToCache, removeFAQFromCache, createManualFAQ, deleteFAQStats, updateFAQAnswer} from '../api'

interface FAQItem {
  id: number
  question: string
  raw_queries: string[]
  raw_query_count: number
  answer: string
  hit_count: number
  is_cached: boolean
  last_hit_at: string
}

const items = ref<FAQItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const window = ref<'week' | 'month'>('week')
const cachedOnly = ref(false)
const loading = ref(false)

const showManual = ref(false)
const manualQ = ref('')
const manualA = ref('')
const manualSaving = ref(false)

const showEdit = ref(false)
const editId = ref(0)
const editAnswer = ref('')
const editSaving = ref(false)

async function fetchStats() {
  loading.value = true
  try {
    const res = await getFAQStats({
      page: page.value,
      page_size: pageSize,
      window: window.value,
      cached_only: cachedOnly.value
    })
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function doCache(id: number) {
  await addFAQToCache(id);
  await fetchStats()
}

async function doUncache(id: number) {
  await removeFAQFromCache(id);
  await fetchStats()
}

async function doDelete(id: number) {
  await deleteFAQStats(id);
  await fetchStats()
}

async function doManualSubmit() {
  if (!manualQ.value.trim() || !manualA.value.trim()) return
  manualSaving.value = true
  try {
    await createManualFAQ({question: manualQ.value, answer: manualA.value})
    showManual.value = false;
    manualQ.value = '';
    manualA.value = ''
    await fetchStats()
  } finally {
    manualSaving.value = false
  }
}

function openEdit(id: number, answer: string) {
  editId.value = id
  editAnswer.value = answer
  showEdit.value = true
}

async function doEdit() {
  if (!editAnswer.value.trim()) return
  editSaving.value = true
  try {
    await updateFAQAnswer(editId.value, editAnswer.value)
    showEdit.value = false
    await fetchStats()
  } finally {
    editSaving.value = false
  }
}

function switchWindow(w: 'week' | 'month') {
  window.value = w;
  page.value = 1;
  fetchStats()
}

onMounted(fetchStats)
</script>

<template>
  <div class="app-layout">
    <AppSidebar/>
    <main class="main">
      <header class="main-hd">
        <div class="main-title">高频问答</div>
        <div class="faq-toolbar">
          <div class="window-tabs">
            <button :class="{ active: window === 'week' }" @click="switchWindow('week')">本周</button>
            <button :class="{ active: window === 'month' }" @click="switchWindow('month')">本月</button>
          </div>
          <label class="filter-check"><input type="checkbox" v-model="cachedOnly" @change="fetchStats"/>已缓存</label>
          <button class="hdr-btn" @click="showManual = true">+ 手动录入</button>
        </div>
      </header>

      <div class="faq-body">
        <div v-if="showManual" class="modal-overlay" @click.self="showManual = false">
          <div class="modal">
            <div class="modal-title">手动录入 FAQ</div>
            <input v-model="manualQ" placeholder="问题" class="modal-input"/>
            <textarea v-model="manualA" placeholder="答案" rows="4" class="modal-input"/>
            <div class="modal-actions">
              <button class="act-btn fill" @click="doManualSubmit" :disabled="manualSaving">录入并缓存</button>
              <button class="act-btn" @click="showManual = false">取消</button>
            </div>
          </div>
        </div>

        <div v-if="showEdit" class="modal-overlay" @click.self="showEdit = false">
          <div class="modal">
            <div class="modal-title">编辑 FAQ 答案</div>
            <textarea v-model="editAnswer" placeholder="答案" rows="5" class="modal-input"/>
            <div class="modal-actions">
              <button class="act-btn fill" @click="doEdit" :disabled="editSaving">保存</button>
              <button class="act-btn" @click="showEdit = false">取消</button>
            </div>
          </div>
        </div>

        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="items.length === 0" class="empty">暂无高频问题数据</div>
        <div v-else class="faq-list">
          <div v-for="item in items" :key="item.id" class="faq-card">
            <div class="card-main">
              <div class="card-q">
                <span class="badge" :class="item.is_cached ? 'on' : 'off'">{{
                    item.is_cached ? '已缓存' : '未缓存'
                  }}</span>
                {{ item.question }}
              </div>
              <div class="card-meta">
                <span>{{ item.hit_count }} 次</span>
                <span class="dot">·</span>
                <span>{{ item.raw_query_count }} 变体</span>
                <span class="dot">·</span>
                <span>{{ item.last_hit_at?.slice(0, 10) }}</span>
              </div>
              <div v-if="item.answer" class="card-a">
                {{ item.answer.slice(0, 200) }}{{ item.answer.length > 200 ? '...' : '' }}
              </div>
              <div v-if="item.raw_queries.length" class="card-variants">
                <span class="variant-label">相似问法</span>
                <span v-for="q in item.raw_queries" :key="q" class="variant-tag">{{ q }}</span>
              </div>
            </div>
            <div class="card-actions">
              <button class="act-btn" @click="openEdit(item.id, item.answer)">编辑答案</button>
              <button v-if="!item.is_cached" class="act-btn fill" @click="doCache(item.id)">加入缓存</button>
              <button v-else class="act-btn warn" @click="doUncache(item.id)">移除缓存</button>
              <button class="act-btn dng" @click="doDelete(item.id)">删除</button>
            </div>
          </div>
          <div class="pagination" v-if="total > pageSize">
            <button :disabled="page <= 1" @click="page--; fetchStats()">上一页</button>
            <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
            <button :disabled="page >= Math.ceil(total / pageSize)" @click="page++; fetchStats()">下一页</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.faq-toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-left: auto;
}

.window-tabs {
  display: flex;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.window-tabs button {
  height: 30px;
  padding: 0 12px;
  border: none;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px);
  cursor: pointer;
  font-size: 11px;
  color: var(--text-secondary);
  font-family: inherit;
}

.window-tabs button.active {
  background: var(--accent);
  color: #fff;
}

.filter-check {
  font-size: 11px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  font-family: inherit;
}

.faq-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px 24px;
}

.loading, .empty {
  text-align: center;
  padding: 80px 0;
  color: var(--text-tertiary);
  font-size: 13px;
}

.faq-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 960px;
}

.faq-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: var(--bg-card);
  border-radius: 8px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
}

.card-main {
  flex: 1;
  min-width: 0;
}

.card-q {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-primary);
}

.badge {
  padding: 1px 7px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 500;
  flex-shrink: 0;
}

.badge.on {
  background: var(--accent-soft);
  color: var(--accent);
}

.badge.off {
  background: var(--red-soft);
  color: var(--red);
}

.card-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.dot {
  font-size: 10px;
}

.card-a {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  line-height: 1.6;
  background: var(--bg-hover);
  padding: 6px 10px;
  border-radius: 4px;
}

.card-variants {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.variant-label {
  font-size: 10px;
  color: var(--text-tertiary);
  flex-shrink: 0;
  margin-right: 2px;
}

.variant-tag {
  font-size: 10px;
  background: var(--accent-soft);
  color: var(--accent);
  padding: 1px 7px;
  border-radius: 8px;
}

.hdr-btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.06);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 11px;
  font-family: inherit;
  transition: all .2s;
}

.card-actions {
  margin-left: 10px;
  flex-shrink: 0;
  display: flex;
  gap: 4px;
}

.act-btn {
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 10px;
  cursor: pointer;
  border: none;
  font-family: inherit;
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.act-btn.fill {
  background: var(--accent);
  color: #fff;
}

.act-btn.warn {
  background: var(--red-soft);
  color: var(--red);
}

.act-btn.dng {
  color: var(--text-tertiary);
}

.act-btn.dng:hover {
  color: var(--red);
  background: var(--red-soft);
}

.act-btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.pagination {
  display: flex;
  justify-content: center;
  gap: 12px;
  align-items: center;
  margin-top: 16px;
  font-size: 11px;
  color: var(--text-secondary);
}

.pagination button {
  padding: 4px 14px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  border-radius: 5px;
  cursor: pointer;
  font-size: 11px;
  color: var(--text-secondary);
  font-family: inherit;
}

.pagination button:disabled {
  opacity: 0.3;
  cursor: default;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 18px 20px;
  width: 380px;
  max-width: 90vw;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid var(--border-subtle);
}

.modal-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-input {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-primary);
  background: var(--bg-hover);
  box-sizing: border-box;
  outline: none;
  font-family: inherit;
}

.modal-input:focus {
  border-color: var(--accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.modal-actions .act-btn {
  padding: 5px 14px;
  border-radius: 5px;
  font-size: 11px;
}
</style>
