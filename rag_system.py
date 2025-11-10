"""
RAG系统主模块：整合文档处理、向量存储和检索生成
"""
from document_processor import DocumentProcessor
from embedding_model import Embedding
from vector_store import VectorStore
from typing import List, Dict, Optional
import requests


class RAGSystem:
    """RAG系统，实现检索增强生成"""
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        chat_model: str = "deepseek-r1:8b",
        collection_name: str = "rag_documents",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        初始化RAG系统
        
        Args:
            ollama_url: Ollama服务地址
            chat_model: 聊天模型名称
            collection_name: 向量数据库集合名称
            chunk_size: 文本块大小
            chunk_overlap: 文本块重叠大小
        """
        self.ollama_url = ollama_url
        self.chat_model = chat_model
        
        # 初始化各个组件
        self.doc_processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.embedding_model = Embedding(
            base_url=ollama_url,
            model_name=chat_model
        )
        self.vector_store = VectorStore(collection_name=collection_name)
    
    def add_document_from_file(self, file_path: str):
        """
        从文件添加文档到数据库
        
        Args:
            file_path: 文件路径
        """
        # 处理文档
        documents = self.doc_processor.process_document(file_path)
        
        # 获取嵌入向量
        texts = [doc["content"] for doc in documents]
        embeddings = self.embedding_model.embed_texts(texts)
        
        # 添加到向量数据库
        self.vector_store.add_documents(documents, embeddings)
    
    def add_text(self, text: str, source: str = "input"):
        """
        添加文本到数据库
        
        Args:
            text: 文本内容
            source: 来源标识
        """
        # 处理文本
        documents = self.doc_processor.process_text(text, source)
        
        # 获取嵌入向量
        texts = [doc["content"] for doc in documents]
        embeddings = self.embedding_model.embed_texts(texts)
        
        # 添加到向量数据库
        self.vector_store.add_documents(documents, embeddings)
    
    def retrieve(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            
        Returns:
            相关文档列表
        """
        # 获取查询向量
        query_embedding = self.embedding_model.embed_query(query)
        
        # 搜索相似文档
        results = self.vector_store.search(query_embedding, n_results=n_results)
        
        return results
    
    def generate(self, query: str, context: str, history: List[Dict] = None) -> str:
        """
        使用上下文生成回答
        
        Args:
            query: 用户查询
            context: 检索到的上下文
            history: 对话历史
            
        Returns:
            生成的回答
        """
        # 构建提示词
        prompt = f"""基于以下上下文信息回答问题。如果上下文中没有相关信息，请基于你的知识回答。

上下文信息：
{context}

用户问题：{query}

请提供准确、详细的回答："""
        
        # 构建消息列表
        messages = history.copy() if history else []
        messages.append({"role": "user", "content": prompt})
        
        # 调用Ollama API
        try:
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
                return data.get("message", {}).get("content", "")
            else:
                return f"生成回答失败: {response.status_code}"
        except Exception as e:
            return f"生成回答时出错: {str(e)}"
    
    def query(self, user_query: str, n_results: int = 5, history: List[Dict] = None) -> Dict:
        """
        完整的RAG查询流程
        
        Args:
            user_query: 用户查询
            n_results: 检索结果数量
            history: 对话历史
            
        Returns:
            包含检索结果和生成回答的字典
        """
        # 检索相关文档
        retrieved_docs = self.retrieve(user_query, n_results)
        
        # 构建上下文
        context = "\n\n".join([
            f"[文档{i+1}]\n{doc['content']}"
            for i, doc in enumerate(retrieved_docs)
        ])
        
        # 生成回答
        answer = self.generate(user_query, context, history)
        
        return {
            "query": user_query,
            "retrieved_documents": retrieved_docs,
            "context": context,
            "answer": answer
        }
    
    def get_database_info(self) -> Dict:
        """获取数据库信息"""
        return {
            "collection_name": self.vector_store.collection_name,
            "document_count": self.vector_store.get_collection_count()
        }


