# RAG 智能知识库问答系统

基于 RAG（Retrieval-Augmented Generation）架构的企业级知识库问答系统，支持多种文档解析策略、规则引擎检索路由、多模态图片问答、高频问题统计与管理、管理员后台。

---

## 核心功能

### 文档解析 & 智能切块

| 策略 | 说明 |
|------|------|
| **default** | 递归字符切分，优化中英文标点分隔符 |
| **semantic** | 基于 embedding 相似度的语义边界检测 |
| **markdown** | Markdown 标题层级感知，保留 `# -> ## -> ###` 路径 |
| **parent_child** | 父子块双粒度检索：子块精确匹配，父块完整上下文 |

### 图片处理（OCR + MinIO）

- 上传 ZIP 包（Markdown + 图片素材）自动解析
- PaddleOCR 识别图片文字，存入向量库可检索
- MinIO 对象存储图片，生成直接访问 URL
- `qwen-vl-max` 多模态视觉问答（图片内容理解）

### 多策略智能检索

检索策略由**规则引擎**自动选择（零额外 LLM 调用），根据问题长度、关键词特征智能匹配：

```
用户 Query
  -> FAQ Redis 缓存命中? -> 直接返回
  -> LLM 意图识别 -> 闲聊? -> 直接 LLM 回答
  -> 规则引擎策略选择:
      +-- direct       直接检索
      +-- hyde         假设文档检索（生成假设文档 -> 向量匹配）
      +-- sub_question 子问题拆分 -> 并行检索 -> 合并
  -> Dense + Sparse 混合检索
  -> bge-reranker-v2-m3 精排（lifespan 预热，不阻塞首次请求）
  -> LLM 生成回答
  -> RAG 评估（jieba 分词关键词 + LLM 精评）
  -> 自动记录 FAQ 统计
```

### FAQ 高频问答统计与管理

```
用户问题 -> record_query 记录统计（BM25 + 词级重叠聚合）
  -> check_stats_cache 查询 Redis 缓存
  -> 命中 -> 直接返回
  -> 未命中 -> 走完整 RAG -> 自动更新答案

管理员后台:
  - 查看本周/本月高频问题统计（命中次数排序）
  - 手动录入 FAQ → 直接写入 Redis 缓存
  - 编辑 FAQ 答案 → 自动同步 Redis
  - 加入/移除缓存、删除记录
```

### RAG 评估

- **上下文相关性** — 检索结果与问题的语义匹配度
- **答案忠实度** — 回答是否基于检索内容
- **答案相关性** — 回答是否回应了问题
- 基于 jieba 分词的关键词评估 + LLM 精评兜底
- 在线即时：~0ms，对话中 4 指标即时展示（检索精度/召回/忠实度/回答相关性）
- 离线精评：Ragas 批量评估 3 指标（检索精度/检索召回/忠实度）`scripts/eval_ragas.py`

### 用户系统

- 注册/登录（无状态 HMAC 验证码，天然支持多进程部署和服务重启）
- JWT 双 Token 鉴权（access 30min + refresh 7天自动续期）
- 用户头像上传（后端持久化，换设备登录不丢失）
- 管理员权限控制（可访问高频问答管理后台）

### 日志系统

- 统一日志配置：终端实时输出 + 文件自动轮转
- 文件日志：`backend/logs/app.log`（10MB/文件，保留 5 个历史）
- 关键步骤覆盖：RAG 流水线、LLM 调用、FAQ 缓存、用户认证、文档上传

---

## 快速开始

### 1. 环境准备

- Python 3.12+ / Node.js 18+ / Docker & Docker Compose / Conda（推荐）

### 2. 启动基础服务

```bash
docker compose up -d mysql redis milvus minio
```

### 3. 配置环境变量

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，必须填入 DASHSCOPE_API_KEY
```

### 4. 启动后端

```bash
cd backend
conda activate RAG-Project
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`，注册账号后即可使用。

---

## API 概览

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/captcha` | 获取图形验证码 |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/refresh` | 刷新 Token |
| POST | `/api/auth/avatar` | 上传头像 |

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge/kbs` | 知识库列表 |
| POST | `/api/knowledge/kbs` | 创建知识库 |
| DELETE | `/api/knowledge/kbs/{id}` | 删除知识库 |
| POST | `/api/knowledge/{id}/upload` | 上传文档（≤50MB） |
| GET | `/api/knowledge/{id}/documents` | 文档列表 |
| DELETE | `/api/knowledge/{id}/documents/{doc_id}` | 删除文档 |

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/query` | RAG 问答（SSE 流式） |
| GET | `/api/chat/conversations` | 对话列表 |
| POST | `/api/chat/conversations` | 新建对话 |
| DELETE | `/api/chat/conversations/{id}` | 删除对话 |

### 管理员（需要 admin 权限）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/faq-stats` | 高频问题统计列表 |
| POST | `/api/admin/faq-stats/{id}/cache` | 加入 Redis 缓存 |
| DELETE | `/api/admin/faq-stats/{id}/cache` | 移出 Redis 缓存 |
| PUT | `/api/admin/faq-stats/{id}/answer` | 编辑 FAQ 答案 |
| DELETE | `/api/admin/faq-stats/{id}` | 删除统计记录 |
| POST | `/api/admin/faq-stats/manual` | 手动录入 FAQ |

---

## 项目结构

```
RAG-AICoding/
  backend/
    app/
      api/              # API 路由
        auth.py         # 认证 + 头像上传
        chat.py         # 对话（SSE 流式）
        knowledge.py    # 知识库 CRUD + 文档上传
        admin.py        # 管理员接口（FAQ 管理）
        eval.py         # 评估测试
      core/             # 核心配置
        config.py       # 全局配置
        database.py     # MySQL 连接 + Schema 迁移
        auth.py         # JWT 认证
        captcha.py      # 无状态 HMAC 验证码
        logging_config.py  # 统一日志配置
      models/           # SQLAlchemy 模型
        user.py
        knowledge_base.py
        conversation.py
        faq_stats.py    # FAQ 高频统计
      services/         # 核心服务
        document_parser.py              # 文档解析 + 4种切块
        deep_parser.py                  # OCR + 表格跨页合并
        markdown_image_processor.py     # MD图片处理(ZIP→MinIO)
        image_rag_qa.py                 # 多模态视觉问答
        retrieval_strategies.py         # 规则引擎检索策略(3种)
        hybrid_retrieval.py             # Dense+Sparse 混合检索
        vector_store.py                 # Milvus 向量存储
        reranker.py                     # bge-reranker 精排(lifespan预热)
        faq_stats_service.py            # FAQ统计(BM25+词级重叠+Redis)
        intent_recognizer.py            # LLM 意图识别
        query_rewriter.py               # Query 改写
        evaluator.py                    # RAG 评估(jieba分词)
        llm_service.py                  # LLM 调用
        sparse_embedding.py             # 稀疏向量
        minio_store.py                  # MinIO 存储
        qa_stopwords.py                 # FAQ 匹配停用词
    main.py             # FastAPI 入口
  frontend/
    src/
      views/            # 页面
        Chat.vue        # 对话页
        Knowledge.vue   # 知识库管理
        Login.vue       # 登录
        Register.vue    # 注册
        FAQManagement.vue  # 高频问答管理
      components/       # 业务组件
        layout/AppSidebar.vue          # 侧边栏导航 + 头像菜单
        chat/ConversationList.vue      # 知识库选择(全选/取消) + 会话列表
        chat/MessageBubble.vue         # 消息气泡（来源/评估）
        chat/MessageInput.vue          # 输入框 + 自动聚焦
        chat/ParamPanel.vue            # 推理参数面板
        knowledge/KbListPanel.vue      # 知识库列表 + 创建
        knowledge/UploadZone.vue       # 文档上传区
        knowledge/DocumentList.vue     # 文档列表
        knowledge/ChunkPanel.vue       # 分块查看/编辑
        auth/AnimatedCharacters.vue    # 登录页动画角色
        shared/WelcomeScreen.vue       # 欢迎占位
      composables/      # 业务逻辑 Hooks
        useChat.ts        # 会话管理 + SSE 流式
        useKnowledge.ts   # 知识库 CRUD
        useUpload.ts      # 文件上传 + 进度
        useAvatar.ts      # 头像上传与管理
      types/            # TypeScript 类型定义
        api.ts / auth.ts / chat.ts / knowledge.ts
      stores/           # Pinia 状态管理
      router/           # 路由（含 JWT 过期检查）
      api/              # API 封装
  docker/
    docker-compose.yml  # 基础服务编排
    Dockerfile.backend  # 后端镜像
  README.md
```

---

## 配置说明

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DASHSCOPE_API_KEY` | (无) | **必填**，通义千问 API Key |
| `MYSQL_HOST` | localhost | MySQL 地址 |
| `MYSQL_PASSWORD` | 12345678 | MySQL 密码 |
| `MYSQL_DATABASE` | innerQaSystem | 数据库名 |
| `REDIS_HOST` | localhost | Redis 地址 |
| `MILVUS_HOST` | localhost | Milvus 地址 |
| `CHUNK_SIZE` | 500 | 默认切块大小 |
| `CHUNK_OVERLAP` | 50 | 默认重叠大小 |
| `JWT_SECRET_KEY` | change-me-in-production | **生产环境务必修改** |
| `MAX_UPLOAD_SIZE_MB` | 50 | 单文件最大上传大小(MB) |
| `FAQ_STATS_WINDOW_DAYS` | 7 | FAQ 统计窗口(天) |
| `FAQ_STATS_CACHE_THRESHOLD` | 10 | 自动写 Redis 的命中阈值 |

---

## 使用说明

### 上传文档

支持 PDF、DOCX、PPTX、MD、TXT、CSV 格式，选择切块策略后直接上传。单文件限制 50MB。

### 上传 Markdown + 图片（ZIP 方式）

1. 将 `.md` 文件和 `.assets/` 图片文件夹打包为 ZIP：
   ```bash
   zip -r 文档.zip 文档.md 文档.assets/
   ```
2. 上传 ZIP 文件，系统自动解压、OCR 识别、MinIO 存储、父子切块并向量化入库。

### 对话问答

选择知识库（支持一键全选/取消全选），输入问题。系统自动选择最优检索策略、生成回答，显示引用来源和评估分数。发送后光标自动回到输入框。

### 高频问答管理（管理员）

管理员可在「高频问答」页面查看本周/本月的问题统计、编辑答案、手动录入 FAQ、管理 Redis 缓存。文档上传/删除后侧栏计数实时刷新。

### 用户头像

点击左下角头像 → 修改头像，上传后持久化到后端，换设备登录不丢失。

---

## 生产环境注意事项

1. **修改 JWT Secret**: `.env` 中 `JWT_SECRET_KEY` 必须更换
2. **修改数据库密码**: MySQL/Redis 默认密码仅用于开发
3. **关闭调试模式**: `DEBUG=false`
4. **日志**: 生产日志写入 `backend/logs/app.log`（10MB 轮转，保留 5 个历史文件）
5. **HTTPS**: 生产环境使用 Nginx 反向代理 + SSL
6. **MinIO Policy**: 生产环境按需限制 Bucket 访问权限
7. **Reranker**: 首次启动后台线程预热模型，不阻塞 API 响应
### Ragas 离线评估

```bash
cd backend && conda activate RAG-Project
DASHSCOPE_API_KEY=sk-xxx python scripts/eval_ragas.py
```

| 输出 | 路径 |
|------|------|
| 终端实时 | 逐条进度 + 评分 |
| 文本日志 | `logs/eval_ragas.log` |
| JSON 报告 | `logs/ragas_eval_report.json` |

---
