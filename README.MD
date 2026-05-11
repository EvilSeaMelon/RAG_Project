# ServiceBrain：电商售后智能 RAG 知识库平台

ServiceBrain 是一款专为电商售后场景设计的“人工+AI”协同管理平台。它不仅提供完整的客户、资产及工单管理系统（CRUD），更核心地集成了基于 **LangChain** 与 **FastAPI** 的深度 RAG（检索增强生成）引擎，能够针对复杂的产品说明书提供精准的售后诊断建议。

## 🌟 核心技术亮点

### 1. 工业级异步后端架构
* **FastAPI + AsyncSQLAlchemy**：全链路异步非阻塞设计，支撑高并发业务请求。基于 Pydantic 实现严格的接口数据契约与校验。
* **同步隔离线程池**：针对 LangChain 检索链等耗时同步任务，采用 `run_in_threadpool` 方案进行线程隔离，确保大模型推理任务不拖累系统的核心业务吞吐。

### 2. 深度混合检索 (Hybrid RAG) 
* **混合召回架构**：结合了 **Chroma** 向量库的稠密向量检索与 **BM25** 的关键词精准匹配，有效解决长尾问题。
* **BGE 交叉编码器重排 (Rerank)**：集成 `HuggingFaceCrossEncoder` 对初步召回的 Top-N 结果进行二次精排，通过深度语义比对显著抑制模型幻觉。
* **隐式查询增强 (Query Augmentation)**：在检索阶段自动从 MySQL 中提取客户真实的设备型号（如：华为Mate60）并前置拼接至查询语句，极大提升检索相关性。

### 3. 持久化对话记忆与 Token 保护机制
* **MySQL 记忆持久化**：摒弃本地脆弱的 JSON 文件，使用 MySQL 的 `ChatHistory` 表通过手机号（Session ID）统一管理对话上下文，实现分布式环境下的状态共享。
* **Token 触发式滑动窗口**：集成 `tiktoken` 库，实现基于 Token 计数的倒序滑动窗口截断机制，在保障大模型推理精度的同时，严密防范 Context Window 溢出。

### 4. 企业级业务流转系统 (CRUD)
* **全量数据网格管理**：前端采用 Streamlit 的 `st.data_editor` 实现类 Excel 的全量数据维护，支持客户、设备资产、售后工单三张核心表的双击编辑与批量删除。
* **差异化同步 (Diff-Sync)**：前端仅捕获并向后端发送发生变动的数据行（Edited/Deleted），配合异步 PUT/DELETE 接口，极大降低了网络 I/O。
* **外键约束防护**：后端针对删除操作实现了 `IntegrityError` 捕获，有效防止因级联关系导致的数据逻辑破坏。

## 🛠️ 技术栈
* **核心开发**: Python 3.12
* **后端框架**: FastAPI, SQLAlchemy (Async), Uvicorn
* **AI 引擎**: LangChain, DashScope (通义千问), HuggingFace (BGE Reranker)
* **数据存储**: MySQL 8.0, ChromaDB
* **前端交互**: Streamlit, Pandas, Requests

## 📂 项目目录结构
```text
├── main.py                 # FastAPI 应用主入口
├── database.py             # 异步数据库引擎与 Session 配置
├── models.py               # SQLAlchemy 数据库模型 (Customer/OrderAsset/WorkOrder/ChatHistory)
├── schemas.py              # Pydantic 数据验证与序列化模型
├── frontend.py             # Streamlit 多页面前端应用
├── routers/                # 模块化业务路由
│   ├── admin.py            # 管理员数据管理与 KPI 统计接口
│   ├── chat.py             # RAG 问答与知识库上传接口
│   ├── customer.py         # 客户基础 CRUD
│   └── order.py            # 资产订单绑定接口
└── rag_engine/             # RAG 核心引擎逻辑
    ├── rag.py              # LangChain 处理链组装与核心 LCEL 逻辑
    ├── vector_stores.py    # 混合检索、BM25 构建与重排实现
    ├── knowledge_base.py   # 语义分词、MD5 去重与向量化入库
    ├── config_data.py      # 模型参数与全局路径配置
    └── token_utils.py      # tiktoken 滑动窗口截断工具