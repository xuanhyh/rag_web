"""
FastAPI后端：提供RAG系统的Web API接口
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from rag_manager import RAGManager
from pathlib import Path
import os
import uuid
import tempfile
import json

# 创建FastAPI应用
app = FastAPI(title="RAG系统API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化RAG管理器
rag_manager = RAGManager(
    ollama_url="http://localhost:11434",
    chat_model="deepseek-r1:8b",
    chunk_size=500,
    chunk_overlap=50
)

# 临时文件目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 对话历史管理（数据库名称 -> 对话历史列表）
# 使用字典存储，每个数据库维护独立的对话历史
chat_histories: Dict[str, List[Dict]] = {}


# Pydantic模型
class DatabaseCreate(BaseModel):
    name: str
    metadata: Optional[Dict] = None


class QueryRequest(BaseModel):
    database_name: str
    query: str
    n_results: int = 5
    history: Optional[List[Dict]] = None


class TextAddRequest(BaseModel):
    database_name: str
    text: str
    source: str = "web_input"


# 静态文件服务（需要在路由之前）
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# API路由
@app.get("/", response_class=HTMLResponse)
async def root():
    """返回前端页面"""
    html_path = Path(__file__).parent / "templates" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    else:
        return HTMLResponse("<h1>前端页面未找到</h1><p>请确保templates/index.html文件存在</p>")


@app.get("/api/databases", response_model=List[Dict])
async def list_databases():
    """列出所有数据库"""
    try:
        databases = rag_manager.list_databases()
        return databases
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/databases")
async def create_database(db: DatabaseCreate):
    """创建新数据库"""
    try:
        # 验证数据库名称
        if not db.name or not db.name.strip():
            raise HTTPException(status_code=400, detail="数据库名称不能为空")
        
        # 清理数据库名称（移除前后空格）
        db_name = db.name.strip()
        
        # 创建数据库
        try:
            success = rag_manager.create_database(db_name, db.metadata)
            if success:
                return {"success": True, "message": "数据库创建成功", "name": db_name}
            else:
                raise HTTPException(status_code=400, detail="数据库已存在")
        except ValueError as e:
            # 验证错误
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # 其他错误
            error_msg = str(e)
            raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=500, detail=f"创建数据库失败: {error_msg}")


@app.delete("/api/databases/{database_name}")
async def delete_database(database_name: str):
    """删除数据库"""
    try:
        success = rag_manager.delete_database(database_name)
        if success:
            # 同时删除该数据库的对话历史
            if database_name in chat_histories:
                del chat_histories[database_name]
            return {"success": True, "message": "数据库删除成功"}
        else:
            raise HTTPException(status_code=404, detail="数据库不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/databases/{database_name}")
async def get_database_info(database_name: str):
    """获取数据库信息"""
    try:
        info = rag_manager.get_database_info(database_name)
        if info:
            return info
        else:
            raise HTTPException(status_code=404, detail="数据库不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/databases/{database_name}/documents/upload")
async def upload_document(database_name: str, file: UploadFile = File(...)):
    """上传文件到数据库（支持txt, pdf, docx, xlsx, xls格式）"""
    temp_path = None
    try:
        # 检查文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 获取文件扩展名
        file_ext = os.path.splitext(file.filename)[1].lower()
        supported_formats = ['.txt', '.pdf', '.docx', '.xlsx', '.xls', '.pptx']
        
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件格式: {file_ext}。支持格式: {', '.join(supported_formats)}"
            )
        
        # 保存上传的文件（二进制方式保存，因为PDF、Word、Excel都是二进制文件）
        temp_filename = f"{uuid.uuid4()}{file_ext}"
        temp_path = os.path.join(UPLOAD_DIR, temp_filename)
        
        # 读取文件内容
        content = await file.read()
        
        # 写入临时文件（二进制模式）
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # 添加文档到数据库（document_processor会自动识别文件类型）
        result = rag_manager.add_document_to_database(
            database_name=database_name,
            file_path=temp_path,
            source=file.filename
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=500, detail=f"上传文件失败: {error_msg}")
    finally:
        # 删除临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@app.post("/api/databases/{database_name}/documents/text")
async def add_text_document(database_name: str, request: TextAddRequest):
    """添加文本到数据库"""
    try:
        result = rag_manager.add_document_to_database(
            database_name=database_name,
            text=request.text,
            source=request.source
        )
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/databases/{database_name}/documents")
async def get_database_documents(database_name: str, limit: int = 100):
    """获取数据库中的文档列表"""
    try:
        documents = rag_manager.get_database_documents(database_name, limit)
        return {"documents": documents, "count": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def query_database(request: QueryRequest):
    """查询数据库"""
    try:
        result = rag_manager.query_database(
            database_name=request.database_name,
            query=request.query,
            n_results=request.n_results,
            history=request.history
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: QueryRequest):
    """聊天接口（与query相同，为了前端统一）"""
    # 获取或初始化该数据库的对话历史
    if request.database_name not in chat_histories:
        chat_histories[request.database_name] = []
    
    # 始终使用存储的历史（前端不应该发送历史，而是从后端获取）
    # 这样可以确保历史的一致性
    current_history = chat_histories[request.database_name].copy()
    
    # 使用存储的历史进行查询
    result = rag_manager.query_database(
        database_name=request.database_name,
        query=request.query,
        n_results=request.n_results,
        history=current_history
    )
    
    # 更新对话历史
    if result.get("success", True) and result.get("answer"):
        chat_histories[request.database_name].append({"role": "user", "content": request.query})
        chat_histories[request.database_name].append({"role": "assistant", "content": result.get("answer", "")})
        # 限制历史长度（保留最近20轮对话）
        if len(chat_histories[request.database_name]) > 40:
            chat_histories[request.database_name] = chat_histories[request.database_name][-40:]
    
    return result


@app.get("/api/databases/{database_name}/chat/history")
async def get_chat_history(database_name: str):
    """获取数据库的对话历史"""
    try:
        # 如果数据库不存在，返回空历史
        if database_name not in chat_histories:
            chat_histories[database_name] = []
        return {
            "success": True,
            "database_name": database_name,
            "history": chat_histories[database_name],
            "message_count": len(chat_histories[database_name])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/databases/{database_name}/chat/history")
async def clear_chat_history(database_name: str):
    """清除数据库的对话历史"""
    try:
        if database_name in chat_histories:
            chat_histories[database_name] = []
        return {
            "success": True,
            "message": "对话历史已清除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: QueryRequest):
    """流式聊天接口"""
    # 获取或初始化该数据库的对话历史
    if request.database_name not in chat_histories:
        chat_histories[request.database_name] = []
    
    # 始终使用存储的历史（前端不应该发送历史，而是从后端获取）
    # 这样可以确保历史的一致性
    current_history = chat_histories[request.database_name].copy()
    
    async def generate():
        try:
            full_content = ""
            # 使用流式查询
            for chunk in rag_manager.query_database_stream(
                database_name=request.database_name,
                query=request.query,
                n_results=request.n_results,
                history=current_history
            ):
                # 转换为SSE格式
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"
                
                # 如果完成，更新对话历史
                if chunk.get("type") == "done":
                    full_content = chunk.get("full_content", "")
                    # 更新对话历史
                    chat_histories[request.database_name].append({"role": "user", "content": request.query})
                    chat_histories[request.database_name].append({"role": "assistant", "content": full_content})
                    # 限制历史长度（保留最近20轮对话）
                    if len(chat_histories[request.database_name]) > 40:
                        chat_histories[request.database_name] = chat_histories[request.database_name][-40:]
        except Exception as e:
            error_data = json.dumps({
                "type": "error",
                "content": f"流式处理失败: {str(e)}"
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

