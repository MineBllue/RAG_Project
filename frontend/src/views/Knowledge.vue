<script setup lang="ts">
import {useAvatar} from '../composables/useAvatar'
import {ref, onMounted} from 'vue'
import {useRouter} from 'vue-router'
import {useAuthStore} from '../stores/auth'
import {
  listKBs,
  createKB,
  deleteKB,
  listDocuments,
  deleteDocument,
  uploadDocument,
  listChunks,
  deleteChunk,
  updateChunk
} from '../api'

const router = useRouter()
const auth = useAuthStore()
const kbList = ref<any[]>([]);
const activeKbId = ref<number | null>(null)
const newKbName = ref('');
const newKbDesc = ref('');
const showCreateKb = ref(false);
const creatingKb = ref(false)
const documents = ref<any[]>([]);
const activeDocId = ref<number | null>(null)
const chunks = ref<any[]>([]);
const editingChunk = ref<{ id: number; content: string } | null>(null)
const uploadFiles = ref<File[]>([]);
const chunkSize = ref(500);
const overlap = ref(50);
const chunkMethod = ref('default')
const loading = ref(false);
const progress = ref(0);
const progStatus = ref('')
const chunkJump = ref<number | null>(null);
const errorMsg = ref('')
const showAvatarMenu = ref(false);
const avatarPreview = ref<string | null>(localStorage.getItem('user_avatar'))
const avatarInput = ref<HTMLInputElement | null>(null)

function showError(m: string) {
  errorMsg.value = m;
  setTimeout(() => errorMsg.value = '', 6000)
}

async function loadKBs() {
  try {
    const r = await listKBs();
    kbList.value = r.data
  } catch (e: any) {
    showError('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function doCreateKB() {
  if (!newKbName.value.trim() || creatingKb.value) return;
  creatingKb.value = true;
  try {
    await createKB({name: newKbName.value, description: newKbDesc.value});
    newKbName.value = '';
    newKbDesc.value = '';
    showCreateKb.value = false;
    await loadKBs()
  } catch (e: any) {
    showError('创建失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    creatingKb.value = false
  }
}

async function doDeleteKB(id: number) {
  if (!confirm('删除知识库？所有数据将被清空。')) return;
  try {
    await deleteKB(id);
    await loadKBs();
    if (activeKbId.value === id) {
      activeKbId.value = null;
      documents.value = []
    }
  } catch (e: any) {
    showError('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function selectKB(id: number) {
  activeKbId.value = id;
  activeDocId.value = null;
  chunks.value = [];
  try {
    const r = await listDocuments(id);
    documents.value = r.data
  } catch (e: any) {
    showError('加载文档失败')
  }
}

async function selectDoc(docId: number) {
  activeDocId.value = docId;
  editingChunk.value = null;
  if (!activeKbId.value) return;
  try {
    const r = await listChunks(activeKbId.value, docId);
    chunks.value = r.data
  } catch (e: any) {
    showError('加载分块失败')
  }
}

async function doDeleteDoc(docId: number) {
  if (!activeKbId.value || !confirm('删除该文档？')) return;
  try {
    await deleteDocument(activeKbId.value, docId);
    documents.value = documents.value.filter(d => d.id !== docId);
    if (activeDocId.value === docId) {
      activeDocId.value = null;
      chunks.value = []
    }
  } catch (e: any) {
    showError('删除文档失败')
  }
}

async function doUpload() {
  if (uploadFiles.value.length === 0 || !activeKbId.value) return
  loading.value = true;
  errorMsg.value = '';
  progress.value = 10;
  progStatus.value = '准备上传...'
  await new Promise(r => setTimeout(r, 300));
  progress.value = 25;
  progStatus.value = '上传中...'
  try {
    const form = new FormData();
    for (const f of uploadFiles.value) form.append('files', f);
    form.append('chunk_size', String(chunkSize.value))
    form.append('chunk_overlap', String(overlap.value));
    form.append('chunk_method', chunkMethod.value)
    progress.value = 40;
    progStatus.value = '解析文档...';
    await new Promise(r => setTimeout(r, 200))
    progress.value = 60;
    progStatus.value = '向量化中...'
    const token = localStorage.getItem('access_token')
    const resp = await fetch('/api/knowledge/' + activeKbId.value + '/upload-batch', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + token },
      body: form,
    })
    const res = await resp.json()
    progress.value = 85;
    progStatus.value = '存储中...';
    await new Promise(r => setTimeout(r, 200))
    progress.value = 100;
    progStatus.value = '完成';
    uploadFiles.value = []
    setTimeout(() => {
      progress.value = 0;
      progStatus.value = ''
    }, 1500)
    await selectKB(activeKbId.value)
  } catch (e: any) {
    progStatus.value = '失败';
    progress.value = 0;
    showError('上传失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function onFileChange(e: Event) {
  const i = e.target as HTMLInputElement;
  if (i.files?.length) uploadFiles.value = Array.from(i.files)
}

async function doDeleteChunk(chunkId: number) {
  if (!activeKbId.value || !activeDocId.value) return;
  try {
    await deleteChunk(activeKbId.value, activeDocId.value, chunkId);
    await selectDoc(activeDocId.value)
  } catch (e: any) {
    showError('删除分块失败')
  }
}

function startEdit(chunk: any) {
  editingChunk.value = {id: chunk.id, content: chunk.content}
}

async function saveEdit() {
  if (!editingChunk.value || !activeKbId.value || !activeDocId.value) return;
  try {
    await updateChunk(activeKbId.value, activeDocId.value, editingChunk.value.id, editingChunk.value.content);
    editingChunk.value = null;
    await selectDoc(activeDocId.value)
  } catch (e: any) {
    showError('保存失败')
  }
}

function doJump() {
  if (chunkJump.value !== null && chunkJump.value >= 1) {
    const idx = chunkJump.value - 1;
    const el = document.getElementById('chunk-' + idx);
    el ? el.scrollIntoView({behavior: 'smooth', block: 'center'}) : showError('找不到 #' + chunkJump.value);
    chunkJump.value = null
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
    r.onload = ev => {
      const b = ev.target?.result as string;
      localStorage.setItem('user_avatar', b);
      avatarPreview.value = b
    };
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

onMounted(() => {
  loadKBs();
  document.addEventListener('click', closeMenu)
})
</script>

<template>
  <div class="app-layout">
    <div v-if="errorMsg" class="toast" @click="errorMsg=''">{{ errorMsg }}</div>
    <nav class="sidebar">
      <div class="s-logo" @click="router.push('/chat')"><img src="@/icon/avatar_anime.jpg" alt="Logo"/></div>
      <div :class="['s-item', $route.path==='/chat'?'active':'']" @click="router.push('/chat')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
        <span>对话</span></div>
      <div :class="['s-item', $route.path==='/knowledge'?'active':'']" @click="router.push('/knowledge')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
        </svg>
        <span>知识库</span></div>
      <div style="flex:1"></div>
      <div class="avatar-wrap">
        <div class="s-avatar" @click="toggleMenu"><img v-if="avatarPreview" :src="avatarPreview"/>
          <div v-else class="s-avatar-fb">{{ (auth.user?.username || 'U')[0] }}</div>
        </div>
        <div v-if="showAvatarMenu" class="avatar-menu">
          <div class="menu-item" @click="triggerUpload">更换头像</div>
          <div class="menu-divider"></div>
          <div class="menu-item danger" @click="doLogout">退出登录</div>
        </div>
        <input ref="avatarInput" type="file" accept="image/*" hidden @change="onAvatarChange"/>
      </div>
    </nav>
    <div class="panel-l">
      <div class="pl-hd">知识库
        <button class="pl-btn" @click="showCreateKb=!showCreateKb">+</button>
      </div>
      <div v-if="showCreateKb" class="create-form"><input v-model="newKbName" placeholder="名称" class="inp"/><input
          v-model="newKbDesc" placeholder="描述" class="inp"/>
        <button class="btn-s" @click="doCreateKB" :disabled="creatingKb">{{
            creatingKb ? '创建中...' : '创建'
          }}
        </button>
      </div>
      <div class="kb-list-f">
        <div v-for="kb in kbList" :key="kb.id" :class="['kb-row',{active:kb.id===activeKbId}]" @click="selectKB(kb.id)">
          <div class="kb-row-i">
            <div class="kb-row-n">{{ kb.name }}</div>
            <div class="kb-row-m">{{ kb.doc_count }} 文档</div>
          </div>
          <button class="kb-del" @click.stop="doDeleteKB(kb.id)">&times;</button>
        </div>
      </div>
    </div>
    <main class="main" v-if="activeKbId">
      <header class="main-hd">
        <div class="main-title">{{ kbList.find(k => k.id === activeKbId)?.name }}</div>
      </header>
      <div class="content">
        <section class="sec"><h3>上传文档</h3>
          <div class="fmts">支持: PDF / Word / PPT / Markdown / TXT / CSV</div>
          <div class="upload-zone" @click="()=>{$refs.fInp.click()}" :class="{has:uploadFiles.length>0}">
            <input ref="fInp" type="file" accept=".pdf,.docx,.doc,.pptx,.ppt,.md,.markdown,.txt,.csv,.zip" multiple
                   @change="onFileChange" hidden/>
            <svg v-if="uploadFiles.length===0" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.5">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span v-if="uploadFiles.length===0">点击选择文件（支持多选）</span><span v-else class="f-name">{{ uploadFiles.length }} 个文件已选择</span>
          </div>
          <div v-if="uploadFiles.length>0" class="up-params">
            <label>块 <input v-model.number="chunkSize" type="number" min="100" max="2000"/></label>
            <label>叠 <input v-model.number="overlap" type="number" min="0" max="500"/></label>
            <label>策略 <select v-model="chunkMethod" class="msel">
              <option value="default">默认</option>
              <option value="semantic">语义</option>
              <option value="markdown">MD格式</option>
              <option value="parent_child">父子</option>
            </select></label>
            <button class="btn-up" @click="doUpload" :disabled="loading">{{
                loading ? progStatus : '上传解析'
              }}
            </button>
            <button class="btn-cl" @click="uploadFiles=[]" v-if="!loading">取消</button>
          </div>
          <div v-if="progress>0" class="prog-wrap">
            <div class="prog-bar">
              <div class="prog-fill" :style="{width:progress+'%'}"></div>
            </div>
            <span class="prog-pct">{{ progress }}% {{ progStatus }}</span></div>
        </section>
        <section class="sec"><h3>文档 ({{ documents.length }})</h3>
          <div class="doc-list">
            <div v-for="doc in documents" :key="doc.id"
                 :class="['doc-row',{active:doc.id===activeDocId},{failed:doc.status==='failed'}]"
                 @click="selectDoc(doc.id)">
              <span class="doc-icon">{{ doc.file_type.replace('.', '') }}</span><span class="doc-name">{{
                doc.filename
              }}</span>
              <span :class="['doc-st',doc.status]">{{
                  {
                    completed: '完成',
                    parsing: '解析中',
                    failed: '失败',
                    pending: '待处理'
                  }[doc.status] || doc.status
                }}</span>
              <span class="doc-ch">{{ doc.chunk_count }}块</span>
              <button class="doc-del" @click.stop="doDeleteDoc(doc.id)">&times;</button>
            </div>
            <div v-if="documents.length===0" class="empty">暂无文档</div>
          </div>
        </section>
        <section class="sec" v-if="activeDocId">
          <div class="chunk-hd-bar"><h3>分块 ({{ chunks.length }})</h3>
            <div class="chunk-nav"><input v-model.number="chunkJump" type="number" :min="1" :max="chunks.length"
                                          placeholder="#" class="jump-inp" @keydown.enter="doJump"/>
              <button class="jump-btn" @click="doJump">跳转</button>
            </div>
          </div>
          <div class="chunk-list">
            <div v-for="chunk in chunks" :key="chunk.id" :id="'chunk-'+chunk.chunk_index" class="chunk-card">
              <div class="chunk-hd"><span>Chunk #{{ chunk.chunk_index + 1 }}</span>
                <div class="chunk-act">
                  <button @click="startEdit(chunk)">编辑</button>
                  <button class="dng" @click="doDeleteChunk(chunk.id)">删除</button>
                </div>
              </div>
              <div v-if="editingChunk?.id===chunk.id" class="chunk-edit"><textarea v-model="editingChunk!.content"
                                                                                   rows="4"></textarea>
                <div class="edit-act">
                  <button @click="saveEdit">保存</button>
                  <button class="sec" @click="editingChunk=null">取消</button>
                </div>
              </div>
              <div v-else class="chunk-content">{{ chunk.content }}</div>
            </div>
          </div>
        </section>
      </div>
    </main>
    <div class="main" v-else>
      <div class="welcome"><img src="@/icon/avatar_anime.jpg" class="welcome-img" alt="Logo"/>
        <h2>知识库管理</h2>
        <p>选择或创建知识库</p></div>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden
}

.toast {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: #ef4444;
  color: #fff;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 13px;
  z-index: 1000;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(239, 68, 68, .3);
  animation: tIn .3s cubic-bezier(.4, 0, .2, 1);
  max-width: 500px;
  text-align: center
}

@keyframes tIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px)
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0)
  }
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
  cursor: pointer;
  transition: all .15s
}

.menu-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary)
}

.menu-item.danger {
  color: var(--red)
}

.menu-item.danger:hover {
  background: var(--red-soft)
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

.create-form {
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-bottom: 1px solid var(--border-subtle);
  animation: aIn .3s cubic-bezier(.4, 0, .2, 1)
}

@keyframes aIn {
  from {
    opacity: 0;
    transform: translateY(-10px)
  }
  to {
    opacity: 1;
    transform: translateY(0)
  }
}

.inp {
  padding: 7px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 12px;
  font-family: inherit;
  outline: none
}

.inp:focus {
  border-color: var(--accent)
}

.btn-s {
  padding: 6px 12px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit
}

.btn-s:disabled {
  opacity: .5;
  cursor: not-allowed
}

.kb-list-f {
  flex: 1;
  overflow-y: auto;
  padding: 4px 6px
}

.kb-row {
  display: flex;
  align-items: center;
  padding: 7px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 1px;
  transition: all .2s
}

.kb-row:hover {
  background: var(--bg-hover);
  transform: translateX(2px)
}

.kb-row.active {
  background: var(--accent-soft)
}

.kb-row-i {
  flex: 1;
  min-width: 0
}

.kb-row-n {
  font-size: 12px;
  font-weight: 500
}

.kb-row-m {
  font-size: 10px;
  color: var(--text-tertiary)
}

.kb-del {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 14px;
  opacity: 0;
  transition: all .15s
}

.kb-row:hover .kb-del {
  opacity: 1
}

.kb-del:hover {
  background: rgba(239, 68, 68, .12);
  color: var(--red)
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
  flex-shrink: 0
}

.main-title {
  font-weight: 600;
  font-size: 13px
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px
}

.sec {
  margin-bottom: 28px
}

.sec h3 {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-secondary)
}

.fmts {
  font-size: 10px;
  color: var(--text-muted);
  margin-bottom: 8px
}

.upload-zone {
  border: 2px dashed var(--border-card);
  border-radius: 12px;
  padding: 28px;
  text-align: center;
  cursor: pointer;
  transition: all .25s;
  color: var(--text-tertiary);
  font-size: 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px
}

.upload-zone:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--text-secondary)
}

.upload-zone.has {
  border-color: var(--accent);
  border-style: solid;
  background: var(--accent-soft)
}

.f-name {
  color: var(--accent);
  font-weight: 500
}

.up-params {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 10px;
  flex-wrap: wrap
}

.up-params label {
  font-size: 11px;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 4px
}

.up-params input {
  width: 52px;
  padding: 5px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 12px;
  text-align: center;
  outline: none
}

.up-params input:focus {
  border-color: var(--accent)
}

.msel {
  padding: 5px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 11px;
  cursor: pointer;
  font-family: inherit;
  outline: none
}

.msel:focus {
  border-color: var(--accent)
}

.btn-up {
  padding: 7px 16px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 7px;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
  font-weight: 500
}

.btn-up:disabled {
  opacity: .4;
  cursor: not-allowed
}

.btn-cl {
  padding: 7px 14px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border: none;
  border-radius: 7px;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit
}

.prog-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px
}

.prog-bar {
  flex: 1;
  height: 6px;
  background: var(--border-card);
  border-radius: 3px;
  overflow: hidden
}

.prog-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #10b981);
  border-radius: 3px;
  transition: width .4s cubic-bezier(.4, 0, .2, 1)
}

.prog-pct {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  min-width: 120px
}

.doc-list {
  display: flex;
  flex-direction: column;
  gap: 3px
}

.doc-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  cursor: pointer;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  transition: all .2s
}

.doc-row:hover {
  border-color: var(--border-card);
  transform: translateX(2px)
}

.doc-row.active {
  border-color: var(--accent);
  background: var(--accent-soft)
}

.doc-row.failed {
  border-color: rgba(239, 68, 68, .3);
  background: rgba(239, 68, 68, .05)
}

.doc-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  color: var(--text-tertiary);
  text-transform: uppercase;
  flex-shrink: 0
}

.doc-name {
  flex: 1;
  font-size: 12px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap
}

.doc-st {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px
}

.doc-st.completed {
  background: var(--green-soft);
  color: var(--green)
}

.doc-st.failed {
  background: var(--red-soft);
  color: var(--red)
}

.doc-st.pending, .doc-st.parsing {
  background: var(--gold-soft);
  color: var(--gold)
}

.doc-ch {
  font-size: 10px;
  color: var(--text-tertiary)
}

.doc-del {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 15px;
  opacity: 0;
  transition: all .15s;
  flex-shrink: 0
}

.doc-row:hover .doc-del {
  opacity: 1
}

.doc-del:hover {
  background: rgba(239, 68, 68, .12);
  color: var(--red)
}

.empty {
  padding: 24px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px
}

.chunk-hd-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  gap: 8px
}

.chunk-nav {
  display: flex;
  gap: 6px;
  align-items: center
}

.jump-inp {
  width: 56px;
  padding: 5px 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 5px;
  color: var(--text-primary);
  font-size: 11px;
  font-family: monospace;
  outline: none;
  text-align: center
}

.jump-inp:focus {
  border-color: var(--accent)
}

.jump-btn {
  padding: 5px 10px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 5px;
  font-size: 11px;
  cursor: pointer;
  font-family: inherit
}

.chunk-list {
  display: flex;
  flex-direction: column;
  gap: 8px
}

.chunk-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  overflow: hidden
}

.chunk-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 12px;
  background: var(--bg-hover);
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 600
}

.chunk-act {
  display: flex;
  gap: 3px
}

.chunk-act button {
  padding: 5px 12px;
  border-radius: 3px;
  border: 1px solid var(--border-card);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer
}

.chunk-act button:hover {
  background: var(--bg-hover)
}

.chunk-act button.dng {
  color: var(--red);
  border-color: rgba(239, 68, 68, .3)
}

.chunk-content {
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.65;
  color: var(--text-secondary);
  white-space: pre-wrap
}

.chunk-edit {
  padding: 10px 12px
}

.chunk-edit textarea {
  width: 100%;
  background: var(--bg-root);
  border: 1px solid var(--border-card);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 12px;
  font-family: inherit;
  padding: 8px;
  resize: vertical;
  outline: none
}

.chunk-edit textarea:focus {
  border-color: var(--accent)
}

.edit-act {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  height: 40px;
}

.edit-act button {
  padding: 5px 14px;
  border-radius: 5px;
  border: none;
  font-size: 11px;
  cursor: pointer;
  background: var(--accent);
  color: #fff;
  font-family: inherit;
  height: 26px;
}

.edit-act button.sec {
  background: var(--bg-hover);
  color: var(--text-secondary)
}

.welcome {
  text-align: center;
  margin-top: 100px;
  animation: aIn .6s cubic-bezier(.4, 0, .2, 1)
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
</style>
