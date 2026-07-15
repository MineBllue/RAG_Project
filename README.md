
# RAG 智能知识库问答系统

基于 RAG（Retrieval-Augmented Generation）架构的企业级知识库问答系统，支持多种文档解析策略、智能检索路由、多模态图片问答、高频问题缓存。

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

```
用户 Query
  -> FAQ Redis 缓存命中? -> 直接返回
  -> LLM 意图识别 -> 闲聊? -> 直接 LLM 回答
  -> 策略选择器:
      +-- direct       直接检索
      +-- hyde         假设文档检索（生成假设文档 -> 向量匹配）
      +-- sub_question 子问题拆分 -> 并行检索 -> 合并
      +-- step_back    抽象回溯 -> 扩大检索范围
  -> Dense + Sparse 混合检索
  -> bge-reranker-v2-m3 精排
  -> LLM 生成回答
  -> 评估（相关性 / 忠实度 / 答案质量）
```

### FAQ 高频问答缓存

```
用户问题 -> Redis 查缓存
  -> 未命中 -> BM25 检索 FAQ 库 -> Softmax 归一化
  -> 最高分 > 0.85 -> MySQL 取答案 -> 写 Redis
  -> RAG 回答后 -> 自动存入 FAQ
```

### RAG 评估

- **上下文相关性** — 检索结果与问题的语义匹配度
- **答案忠实度** — 回答是否基于检索内容
- **答案相关性** — 回答是否回应了问题
- LLM 精评 + 关键词快速兜底

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| 前端 | Vue 3 + TypeScript + Vite |
| 向量数据库 | Milvus 2.4（Dense + Sparse 混合检索） |
| 关系数据库 | MySQL 8.0 |
| 缓存 | Redis |
| 对象存储 | MinIO |
| LLM | 通义千问（DashScope API） |
| Embedding | text-embedding-v3 |
| Reranker | bge-reranker-v2-m3 |
| OCR | PaddleOCR + Tesseract 降级 |
| 检索引擎 | BM25（rank-bm25） + Milvus Hybrid Search |
| 容器化 | Docker Compose |

---

## 快速开始

### 1. 环境要求

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- Conda（推荐）

### 2. 启动基础服务

```bash
cd docker
docker compose up -d
# 启动 MySQL、Milvus、Redis、MinIO
```

### 3. 配置环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY
```

**.env 示例：**

```env
DASHSCOPE_API_KEY=sk-your-key-here
MYSQL_HOST=localhost
MYSQL_PASSWORD=ww232315
```

### 4. 启动后端

```bash
cd backend
conda create -n RAG-Project python=3.12 -y
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

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge/list` | 知识库列表 |
| POST | `/api/knowledge/create` | 创建知识库 |
| DELETE | `/api/knowledge/{id}` | 删除知识库 |
| POST | `/api/knowledge/{id}/upload` | 上传文档（支持 PDF/DOCX/MD/ZIP） |
| POST | `/api/knowledge/{id}/upload-batch` | 批量上传 |
| POST | `/api/knowledge/image-qa` | 多模态图片问答 |

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/query` | RAG 问答（SSE 流式） |
| GET | `/api/chat/conversations` | 对话列表 |
| POST | `/api/chat/conversations` | 新建对话 |
| DELETE | `/api/chat/conversations/{id}` | 删除对话 |

---

## 项目结构

```
RAG-AICoding/
  backend/
    app/
      api/              # API 路由
        auth.py         # 认证（登录/注册/验证码）
        chat.py         # 对话接口
        eval.py         # 评估接口
        knowledge.py    # 知识库 CRUD + 上传
      core/             # 核心配置
        config.py       # 全局配置
        database.py     # MySQL 连接
        auth.py         # JWT 认证
      models/           # SQLAlchemy 模型
        user.py
        knowledge_base.py
        conversation.py
        faq.py
      services/         # 核心服务
        document_parser.py              # 文档解析 + 4种切块
        deep_parser.py                  # OCR + 表格跨页合并
        markdown_image_processor.py     # MD图片处理(ZIP->MinIO)
        image_rag_qa.py                 # 多模态视觉问答
        retrieval_strategies.py         # 4种检索策略
        hybrid_retrieval.py             # Dense+Sparse混合检索
        vector_store.py                 # Milvus 向量存储
        reranker.py                     # bge-reranker 精排
        faq_service.py                  # FAQ缓存(Redis+BM25+MySQL)
        intent_recognizer.py            # LLM 意图识别
        query_rewriter.py               # Query 改写
        evaluator.py                    # RAG 评估
        llm_service.py                  # LLM 调用
        bm25_store.py                   # BM25 索引
        sparse_embedding.py             # 稀疏向量
        minio_store.py                  # MinIO 存储
  frontend/
    src/
      views/            # 页面组件
        Chat.vue        # 对话页
        Knowledge.vue   # 知识库管理
        Login.vue       # 登录
        Register.vue    # 注册
      api/              # API 封装
      stores/           # Pinia 状态管理
      router/           # 路由
  docker/
    docker-compose.yml  # 基础服务编排
    Dockerfile.backend  # 后端镜像
  README.md
```

---

## 配置说明

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DASHSCOPE_API_KEY` | - | **必填**，通义千问 API Key |
| `MYSQL_HOST` | localhost | MySQL 地址 |
| `MYSQL_PASSWORD` | ww232315 | MySQL 密码 |
| `REDIS_HOST` | localhost | Redis 地址 |
| `MILVUS_HOST` | localhost | Milvus 地址 |
| `CHUNK_SIZE` | 500 | 默认切块大小 |
| `CHUNK_OVERLAP` | 50 | 默认重叠大小 |
| `JWT_SECRET_KEY` | change-me-in-production | 生产环境务必修改 |

---

## 使用说明

### 上传普通文档

支持 PDF、DOCX、PPTX、MD、TXT、CSV 格式，选择切块策略后直接上传。

### 上传 Markdown + 图片（ZIP 方式）

1. 将 `.md` 文件和 `.assets/` 图片文件夹打包为 ZIP：
   ```bash
   zip -r 文档.zip 文档.md 文档.assets/
   ```
2. 上传 ZIP 文件，系统自动解压、OCR 识别、MinIO 存储、父子切块并向量化入库。

### 对话问答

选择知识库，输入问题。系统自动判断是否需要检索、选择最优策略、检索相关片段并生成回答，同时显示引用来源和相关度评分。

---

## 生产环境注意事项

1. **修改 JWT Secret**: `.env` 中 `JWT_SECRET_KEY` 必须更换
2. **修改数据库密码**: MySQL/Redis 默认密码仅用于开发
3. **关闭调试模式**: `DEBUG=false`
4. **HTTPS**: 生产环境使用 Nginx 反向代理 + SSL
5. **MinIO Policy**: 生产环境按需限制 Bucket 访问权限
