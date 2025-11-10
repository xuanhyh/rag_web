"""
RAG管理器：管理多个RAG系统实例，支持多数据库
"""
from rag_system import RAGSystem
from database_manager import DatabaseManager
from typing import Dict, Optional, List
from document_processor import DocumentProcessor
from embedding_model import Embedding
import requests


class RAGManager:
    """管理多个RAG系统，支持切换不同的数据库"""
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        chat_model: str = "deepseek-r1:8b",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        初始化RAG管理器
        
        Args:
            ollama_url: Ollama服务地址
            chat_model: 聊天模型名称
            chunk_size: 文本块大小
            chunk_overlap: 文本块重叠大小
        """
        self.ollama_url = ollama_url
        self.chat_model = chat_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 初始化组件
        self.db_manager = DatabaseManager()
        self.doc_processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.embedding_model = Embedding(
            base_url=ollama_url,
            model_name=chat_model
        )
        
        # 当前使用的数据库名称
        self.current_database: Optional[str] = None
    
    def list_databases(self) -> List[Dict]:
        """列出所有数据库"""
        return self.db_manager.list_databases()
    
    def create_database(self, name: str, metadata: Dict = None) -> bool:
        """创建新数据库"""
        return self.db_manager.create_database(name, metadata)
    
    def delete_database(self, name: str) -> bool:
        """删除数据库"""
        return self.db_manager.delete_database(name)
    
    def set_current_database(self, name: str) -> bool:
        """
        设置当前使用的数据库
        
        Args:
            name: 数据库名称
            
        Returns:
            是否设置成功
        """
        vector_store = self.db_manager.get_database(name)
        if vector_store:
            self.current_database = name
            return True
        return False
    
    def get_current_database(self) -> Optional[str]:
        """获取当前数据库名称"""
        return self.current_database
    
    def get_database_info(self, name: str = None) -> Optional[Dict]:
        """获取数据库信息"""
        name = name or self.current_database
        if name:
            return self.db_manager.get_database_info(name)
        return None
    
    def add_document_to_database(self, database_name: str, file_path: str = None, text: str = None, source: str = "input") -> Dict:
        """
        添加文档到指定数据库
        
        Args:
            database_name: 数据库名称
            file_path: 文件路径（如果提供）
            text: 文本内容（如果提供）
            source: 来源标识
            
        Returns:
            操作结果字典
        """
        vector_store = self.db_manager.get_database(database_name)
        if not vector_store:
            return {"success": False, "message": "数据库不存在"}
        
        try:
            # 处理文档
            if file_path:
                documents = self.doc_processor.process_document(file_path)
            elif text:
                documents = self.doc_processor.process_text(text, source)
            else:
                return {"success": False, "message": "必须提供文件路径或文本内容"}
            
            # 获取嵌入向量
            texts = [doc["content"] for doc in documents]
            embeddings = self.embedding_model.embed_texts(texts)
            
            # 添加到向量数据库
            vector_store.add_documents(documents, embeddings)
            
            return {
                "success": True,
                "message": f"成功添加 {len(documents)} 个文档块",
                "chunk_count": len(documents)
            }
        except Exception as e:
            return {"success": False, "message": f"添加文档失败: {str(e)}"}
    
    def query_database(self, database_name: str, query: str, n_results: int = 5, history: List[Dict] = None) -> Dict:
        """
        查询指定数据库
        
        Args:
            database_name: 数据库名称
            query: 查询文本
            n_results: 检索结果数量
            history: 对话历史
            
        Returns:
            查询结果字典
        """
        vector_store = self.db_manager.get_database(database_name)
        if not vector_store:
            return {
                "success": False,
                "message": "数据库不存在",
                "answer": "数据库不存在，请先创建或选择数据库"
            }
        
        try:
            # 获取查询向量
            query_embedding = self.embedding_model.embed_query(query)
            
            # 搜索相似文档
            retrieved_docs = vector_store.search(query_embedding, n_results=n_results)
            
            # 构建上下文
            context = "\n\n".join([
                f"[文档{i+1}]\n{doc['content']}"
                for i, doc in enumerate(retrieved_docs)
            ]) if retrieved_docs else "未找到相关文档"
            
            # 生成回答
            prompt = f"""基于以下上下文信息回答问题。如果上下文中没有相关信息，请基于你的知识回答。

上下文信息：
{context}

用户问题：{query}

请提供准确、详细的回答："""
            
            messages = history.copy() if history else []
            messages.append({"role": "user", "content": prompt})
            
            # 调用Ollama API
            response = requests.post(
                url=f"{self.ollama_url}/api/chat",
                json={
                    "model": self.chat_model,
                    "messages": messages,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("message", {}).get("content", "")
            else:
                answer = f"生成回答失败: {response.status_code}"
            
            return {
                "success": True,
                "query": query,
                "retrieved_documents": retrieved_docs,
                "context": context,
                "answer": answer
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"查询失败: {str(e)}",
                "answer": f"查询时出错: {str(e)}"
            }
    
    def query_database_stream(self, database_name: str, query: str, n_results: int = 5, history: List[Dict] = None):
        """
        流式查询指定数据库（生成器函数）
        
        Args:
            database_name: 数据库名称
            query: 查询文本
            n_results: 检索结果数量
            history: 对话历史
            
        Yields:
            流式数据块
        """
        vector_store = self.db_manager.get_database(database_name)
        if not vector_store:
            yield {
                "type": "error",
                "content": "数据库不存在，请先创建或选择数据库"
            }
            return
        
        try:
            # 获取查询向量
            query_embedding = self.embedding_model.embed_query(query)
            
            # 搜索相似文档
            retrieved_docs = vector_store.search(query_embedding, n_results=n_results)
            
            # 构建上下文
            context = "\n\n".join([
                f"[文档{i+1}]\n{doc['content']}"
                for i, doc in enumerate(retrieved_docs)
            ]) if retrieved_docs else "未找到相关文档"
            
            # 发送检索到的文档信息
            yield {
                "type": "documents",
                "documents": retrieved_docs,
                "context": context
            }
            
            # 构建提示词
            prompt = f"""基于以下上下文信息回答问题。如果上下文中没有相关信息，请基于你的知识回答。

上下文信息：
{context}

用户问题：{query}

请提供准确、详细的回答："""
            
            messages = history.copy() if history else []
            messages.append({"role": "user", "content": prompt})
            
            # 调用Ollama API（流式）
            response = requests.post(
                url=f"{self.ollama_url}/api/chat",
                json={
                    "model": self.chat_model,
                    "messages": messages,
                    "stream": True
                },
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                # 流式处理响应
                full_content = ""
                thinking_content = ""
                
                for line in response.iter_lines():
                    if line:
                        try:
                            line_text = line.decode('utf-8')
                            if line_text.strip():
                                # 解析JSON行
                                import json
                                data = json.loads(line_text)
                                
                                # 检查消息内容
                                if 'message' in data:
                                    message = data['message']
                                    
                                    # DeepSeek R1可能包含推理内容，检查多个可能的字段
                                    # 1. thinking字段（推理过程）
                                    # 2. reasoning字段（推理内容）
                                    # 3. tool_calls或其他字段
                                    thinking_text = None
                                    
                                    if 'thinking' in message and message['thinking']:
                                        thinking_text = message['thinking']
                                    elif 'reasoning' in message and message['reasoning']:
                                        thinking_text = message['reasoning']
                                    elif 'tool_calls' in message:
                                        # 如果有工具调用，也可以作为推理过程的一部分
                                        thinking_text = str(message.get('tool_calls', ''))
                                    
                                    if thinking_text:
                                        thinking_content += thinking_text
                                        yield {
                                            "type": "thinking",
                                            "content": thinking_content
                                        }
                                    
                                    # 检查是否有内容
                                    if 'content' in message:
                                        content = message['content']
                                        if content:  # 只有当content不为空时才处理
                                            full_content += content
                                            yield {
                                                "type": "content",
                                                "content": content,
                                                "full_content": full_content
                                            }
                                
                                # 检查是否完成
                                if data.get('done', False):
                                    yield {
                                        "type": "done",
                                        "full_content": full_content,
                                        "thinking": thinking_content
                                    }
                                    break
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            yield {
                                "type": "error",
                                "content": f"解析响应失败: {str(e)}"
                            }
            else:
                yield {
                    "type": "error",
                    "content": f"生成回答失败: {response.status_code}"
                }
        except Exception as e:
            yield {
                "type": "error",
                "content": f"查询失败: {str(e)}"
            }
    
    def get_database_documents(self, database_name: str, limit: int = 100) -> List[Dict]:
        """
        获取数据库中的文档列表
        
        Args:
            database_name: 数据库名称
            limit: 限制返回数量
            
        Returns:
            文档列表
        """
        vector_store = self.db_manager.get_database(database_name)
        if not vector_store:
            return []
        
        documents = vector_store.get_all_documents()
        return documents[:limit] if limit else documents

