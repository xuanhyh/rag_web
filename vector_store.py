"""
向量数据库模块：使用ChromaDB存储和检索向量
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os


class VectorStore:
    """向量数据库，用于存储和检索文档向量"""
    
    def __init__(self, collection_name: str = "rag_documents", persist_directory: str = "./chroma_db"):
        """
        初始化向量数据库
        
        Args:
            collection_name: 集合名称
            persist_directory: 持久化目录
        """
        # 创建ChromaDB客户端
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )
        
        self.collection_name = collection_name
    
    def add_documents(self, documents: List[Dict[str, str]], embeddings: List[List[float]]):
        """
        添加文档到向量数据库
        
        Args:
            documents: 文档列表，每个文档包含content和metadata
            embeddings: 嵌入向量列表
        """
        if len(documents) != len(embeddings):
            raise ValueError("文档数量和嵌入向量数量不匹配")
        
        # 准备数据
        ids = []
        texts = []
        metadatas = []
        
        # 获取当前文档数量
        try:
            current_count = self.collection.count()
        except:
            current_count = 0
        
        for i, doc in enumerate(documents):
            ids.append(f"doc_{current_count + i}")
            texts.append(doc["content"])
            metadatas.append(doc.get("metadata", {}))
        
        # 添加到集合
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        
        print(f"成功添加 {len(documents)} 个文档到向量数据库")
    
    def search(self, query_embedding: List[float], n_results: int = 5) -> List[Dict]:
        """
        搜索相似文档
        
        Args:
            query_embedding: 查询向量
            n_results: 返回结果数量
            
        Returns:
            相似文档列表
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # 格式化结果
        documents = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                documents.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else 0
                })
        
        return documents
    
    def get_all_documents(self) -> List[Dict]:
        """
        获取所有文档
        
        Returns:
            所有文档列表
        """
        results = self.collection.get()
        
        documents = []
        if results['documents']:
            for i in range(len(results['documents'])):
                documents.append({
                    "content": results['documents'][i],
                    "metadata": results['metadatas'][i] if results['metadatas'] else {},
                    "id": results['ids'][i]
                })
        
        return documents
    
    def delete_collection(self):
        """删除集合"""
        self.client.delete_collection(name=self.collection_name)
        print(f"已删除集合: {self.collection_name}")
    
    def get_collection_count(self) -> int:
        """获取集合中的文档数量"""
        return self.collection.count()

