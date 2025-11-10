# RAG系统 - 检索增强生成

基于DeepSeek R1模型的RAG（检索增强生成）系统，支持多数据库管理、多格式文档处理和智能问答。

## 📋 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [配置说明](#配置说明)
- [API文档](#api文档)
- [故障排除](#故障排除)
- [项目结构](#项目结构)
- [许可证](#许可证)

## ✨ 功能特性

### 核心功能
- ✅ **多数据库管理**：支持创建、选择、删除多个独立的向量数据库
- ✅ **多格式文档支持**：支持TXT、PDF、Word、Excel、PowerPoint等多种文件格式
- ✅ **智能文档处理**：自动分块、提取元数据，支持中文文本处理
- ✅ **向量检索**：基于ChromaDB的高效向量相似度检索
- ✅ **检索增强生成**：结合检索文档和生成模型的智能问答
- ✅ **多轮对话**：支持上下文感知的多轮对话
- ✅ **流式输出**：支持实时流式响应生成

### 界面功能
- ✅ **现代化Web界面**：美观易用的前端界面
- ✅ **实时交互**：支持实时文档管理和聊天交互
- ✅ **文档预览**：显示检索到的相关文档片段
- ✅ **数据库管理**：可视化的数据库创建、选择和删除

### 命令行功能
- ✅ **命令行界面**：支持命令行方式的文档管理和查询
- ✅ **批量处理**：支持批量添加文档
- ✅ **信息查询**：查看数据库信息和统计

## 🛠 技术栈

### 后端框架
- **FastAPI**：现代化的Python Web框架
- **Uvicorn**：ASGI服务器

### 向量数据库
- **ChromaDB**：开源向量数据库，支持持久化存储

### 嵌入模型
- **BGE-large-zh-v1.5**：中文文本嵌入模型（本地部署）
- **sentence-transformers**：嵌入模型加载框架

### 生成模型
- **DeepSeek R1**：通过Ollama部署的大语言模型
- **Ollama**：本地模型部署和管理工具

### 文档处理
- **langchain-text-splitters**：文本分块工具
- **pdfplumber / pypdf**：PDF文件处理
- **python-docx**：Word文档处理
- **openpyxl / xlrd**：Excel文件处理
- **python-pptx**：PowerPoint文件处理
- **pandas**：数据处理

## 🏗 系统架构

```
RAG系统
├── 文档处理层
│   └── DocumentProcessor      # 文档加载、分块、元数据提取
├── 向量化层
│   └── DeepSeekEmbedding      # 文本向量化（BGE模型）
├── 存储层
│   ├── VectorStore            # 向量数据库操作
│   └── DatabaseManager        # 多数据库管理
├── RAG核心层
│   ├── RAGSystem              # 单数据库RAG系统
│   └── RAGManager             # 多数据库RAG管理器
└── 接口层
    ├── api.py                 # FastAPI REST API
    ├── main.py                # 命令行接口
    └── start_web.py           # Web服务器启动
```

### 工作流程

```
1. 文档处理
   文档文件 → 加载文本 → 文本分块 → 提取元数据

2. 向量化
   文本块 → BGE模型 → 向量表示

3. 存储
   向量 + 元数据 → ChromaDB → 持久化存储

4. 检索
   用户查询 → 向量化 → 相似度检索 → 相关文档

5. 生成
   相关文档 + 用户查询 → 构建提示词 → DeepSeek R1 → 生成回答
```

## 📦 安装指南

### 环境要求

- Python 3.8+
- Ollama（用于运行DeepSeek R1模型）

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd rag_web
```

2. **安装Python依赖**
```bash
pip install -r requirements.txt
```

3. **安装和配置Ollama**

   - 下载并安装Ollama：https://ollama.ai
   - 启动Ollama服务：
   ```bash
   ollama serve
   ```
   - 拉取DeepSeek R1模型：
   ```bash
   ollama pull deepseek-r1:8b
   ```

4. **验证安装**

   - 检查Ollama服务：
   ```bash
   curl http://localhost:11434/api/tags
   ```
   - 检查模型是否已安装：
   ```bash
   ollama list
   ```

## 🚀 快速开始

### 方式一：Web界面（推荐）

1. **启动Web服务器**
```bash
python start_web.py
```

2. **访问Web界面**
   - 打开浏览器访问：`http://localhost:8000`
   - 您将看到现代化的Web界面

3. **创建数据库**
   - 点击侧边栏的"创建数据库"按钮
   - 输入数据库名称（例如："知识库1"）
   - 点击"创建"

4. **添加文档**
   - **上传文件**：点击"上传文件"按钮，选择文件（支持.txt、.pdf、.docx、.xlsx、.xls、.pptx）
   - **添加文本**：点击"添加文本"按钮，直接输入文本内容

5. **开始对话**
   - 在聊天区域的下拉菜单中选择数据库
   - 在输入框中输入问题
   - 按Enter或点击"发送"按钮
   - 系统会检索相关文档并生成回答

### 方式二：命令行界面

1. **启动命令行程序**
```bash
python main.py
```

2. **使用菜单操作**
   - 选择 `1`：添加文本文件到数据库
   - 选择 `2`：添加文本内容到数据库
   - 选择 `3`：查询（RAG模式）
   - 选择 `4`：查看数据库信息
   - 选择 `5`：退出

## 📖 使用指南

### Web界面使用

#### 数据库管理

- **创建数据库**
  - 点击侧边栏的"创建数据库"按钮
  - 输入数据库名称
  - 点击"创建"按钮

- **选择数据库**
  - 在数据库列表中点击"选择"按钮
  - 或在聊天区域的下拉菜单中选择

- **删除数据库**
  - 点击数据库列表中的"删除"按钮
  - 确认删除操作（注意：删除后数据不可恢复）

#### 文档管理

- **上传文件**
  - 支持格式：`.txt`、`.pdf`、`.docx`、`.xlsx`、`.xls`、`.pptx`
  - 点击"上传文件"按钮，选择文件
  - 系统会自动处理并添加到数据库

- **添加文本**
  - 点击"添加文本"按钮
  - 在文本框中输入内容
  - 点击"添加"按钮

- **查看信息**
  - 侧边栏显示当前数据库的文档数量
  - 点击数据库名称查看详细信息

#### 聊天交互

- **选择数据库**：在聊天区域的下拉菜单中选择要查询的数据库
- **输入问题**：在输入框中输入问题，按Enter或点击"发送"按钮
- **查看回答**：系统会显示生成的回答和参考的文档片段
- **对话历史**：系统会自动保存对话历史，支持多轮对话
- **流式输出**：支持实时流式响应显示

### 命令行使用

#### 添加文档

```bash
请选择操作 (1-5): 1
请输入文件路径: example.txt
正在处理文档...
成功添加 10 个文档到向量数据库
文档添加成功！
```

#### 查询

```bash
请选择操作 (1-5): 3
请输入您的问题: 什么是RAG？

正在检索相关文档...
检索到的相关文档:
[文档 1]
来源: example.txt
相似度: 0.8542
内容预览: RAG（检索增强生成）是一种...

回答:
RAG（检索增强生成）是一种结合了信息检索和文本生成的技术...
```

## ⚙️ 配置说明

### 系统配置

在 `api.py` 和 `main.py` 中可以修改以下配置：

- **Ollama服务地址**：`ollama_url = "http://localhost:11434"`
- **聊天模型名称**：`chat_model = "deepseek-r1:8b"`
- **文本块大小**：`chunk_size = 500`
- **文本块重叠大小**：`chunk_overlap = 50`
- **向量数据库目录**：`persist_directory = "./chroma_db"`

### 嵌入模型配置

在 `embedding_model.py` 中：

- **嵌入模型**：`model_name_bge = "BAAI/bge-large-zh-v1.5"`
- 首次使用时会自动下载模型（约1.3GB）
- 模型会缓存在本地，后续使用无需重新下载

### 文档处理配置

在 `document_processor.py` 中：

- **文本分块器**：使用 `RecursiveCharacterTextSplitter`
- **分隔符**：`["\n\n", "\n", "。", "！", "？", "；", " ", ""]`
- **编码支持**：UTF-8、GBK、GB2312、Latin-1

## 📡 API文档

### 数据库管理API

#### 列出所有数据库
```http
GET /api/databases
```

#### 创建数据库
```http
POST /api/databases
Content-Type: application/json

{
  "name": "数据库名称",
  "metadata": {}
}
```

#### 删除数据库
```http
DELETE /api/databases/{database_name}
```

#### 获取数据库信息
```http
GET /api/databases/{database_name}
```

### 文档管理API

#### 上传文件
```http
POST /api/databases/{database_name}/documents/upload
Content-Type: multipart/form-data

file: <文件>
```

#### 添加文本
```http
POST /api/databases/{database_name}/documents/text
Content-Type: application/json

{
  "text": "文本内容",
  "source": "web_input"
}
```

#### 获取文档列表
```http
GET /api/databases/{database_name}/documents?limit=100
```

### 查询API

#### 查询数据库
```http
POST /api/query
Content-Type: application/json

{
  "database_name": "数据库名称",
  "query": "用户问题",
  "n_results": 5,
  "history": []
}
```

#### 流式查询
```http
POST /api/chat/stream
Content-Type: application/json

{
  "database_name": "数据库名称",
  "query": "用户问题",
  "n_results": 5,
  "history": []
}
```

## 🔧 故障排除

### 常见问题

#### 1. Ollama连接失败

**问题**：无法连接到Ollama服务

**解决方案**：
- 检查Ollama服务是否运行：`ollama serve`
- 检查服务地址是否正确：默认是 `http://localhost:11434`
- 检查防火墙设置
- 验证模型是否已安装：`ollama list`

#### 2. 嵌入模型加载失败

**问题**：BGE模型加载失败

**解决方案**：
- 检查网络连接（首次使用需要下载模型）
- 检查磁盘空间（模型约1.3GB）
- 尝试手动下载模型：
  ```bash
  python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-zh-v1.5')"
  ```

#### 3. 文档处理失败

**问题**：文件上传后处理失败

**解决方案**：
- **文本文件**：确保文件编码为UTF-8或GBK
- **PDF文件**：确保PDF文件可以正常打开，且包含可提取的文本（非扫描版图片）
- **Word文件**：仅支持.docx格式，不支持旧的.doc格式
- **Excel文件**：确保文件格式正确，且可以正常打开
- **PowerPoint文件**：仅支持.pptx格式
- 检查文件路径是否正确
- 如果缺少处理库，请重新安装依赖：`pip install -r requirements.txt`

#### 4. 查询无结果

**问题**：查询时没有返回结果

**解决方案**：
- 检查数据库是否有文档
- 检查数据库是否正确选择
- 尝试调整查询关键词
- 检查文档是否成功添加到数据库

#### 5. 生成回答失败

**问题**：无法生成回答或回答为空

**解决方案**：
- 检查Ollama服务是否正常运行
- 检查模型是否已正确安装
- 检查网络连接
- 查看服务器日志了解详细错误信息

#### 6. 端口被占用

**问题**：8000端口已被占用

**解决方案**：
- 修改 `start_web.py` 中的端口号
- 或停止占用端口的进程

## 📁 项目结构

```
rag_web/
├── api.py                    # FastAPI后端接口
├── main.py                   # 命令行主程序
├── start_web.py              # Web服务器启动脚本
├── rag_system.py             # RAG系统核心模块
├── rag_manager.py            # RAG管理器（多数据库）
├── document_processor.py     # 文档处理模块
├── embedding_model.py        # 嵌入模型模块
├── vector_store.py           # 向量数据库模块
├── database_manager.py       # 数据库管理模块
├── requirements.txt          # Python依赖
├── README.md                 # 项目说明文档
├── QUICKSTART.md             # 快速开始指南
├── chroma_db/                # 向量数据库存储目录
├── uploads/                  # 文件上传临时目录
├── templates/                # HTML模板
│   └── index.html           # 前端页面
└── static/                   # 静态文件
    ├── css/
    │   └── style.css        # 样式文件
    └── js/
        └── app.js           # 前端JavaScript
```

## 📝 示例

### 示例1：技术文档问答

1. 创建数据库"技术文档"
2. 上传API文档（PDF格式）
3. 提问："如何使用这个API？"
4. 系统会检索相关文档并生成回答

### 示例2：知识库问答

1. 创建数据库"产品知识库"
2. 添加产品相关信息（文本或文件）
3. 提问："产品的主要功能是什么？"
4. 系统会基于知识库内容生成回答

### 示例3：多数据库切换

1. 创建多个数据库（如"技术"、"产品"、"FAQ"）
2. 在不同数据库中添加相应内容
3. 在聊天时切换不同的数据库进行查询
4. 每个数据库独立管理，互不干扰

## 🔒 注意事项

1. **模型下载**：首次使用BGE嵌入模型时会自动下载（约1.3GB），请确保网络连接正常
2. **数据持久化**：向量数据库会持久化存储在 `./chroma_db` 目录
3. **对话历史**：对话历史会保留最近20轮对话
4. **文件处理**：上传的文件会临时存储在 `uploads` 目录，处理完成后会自动删除
5. **Ollama服务**：确保Ollama服务正常运行且模型已部署
6. **内存占用**：BGE模型会占用约1-2GB内存，请确保系统有足够内存
7. **文件格式**：支持的文件格式有限，请确保文件格式正确

## 📄 许可证

MIT License

## 🙏 致谢

- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [BAAI/bge-large-zh-v1.5](https://huggingface.co/BAAI/bge-large-zh-v1.5) - 中文嵌入模型
- [DeepSeek](https://www.deepseek.com/) - 大语言模型
- [Ollama](https://ollama.ai/) - 模型部署工具
- [FastAPI](https://fastapi.tiangolo.com/) - Web框架
- [LangChain](https://www.langchain.com/) - LLM应用框架

## 📞 技术支持

如有问题，请检查：
1. 控制台错误信息
2. 浏览器控制台（F12）
3. 服务器日志
4. 项目文档和故障排除部分

祝您使用愉快！
