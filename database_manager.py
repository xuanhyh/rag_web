"""
数据库管理模块：管理多个向量数据库集合
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from vector_store import VectorStore


class DatabaseManager:
    """管理多个向量数据库集合"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        初始化数据库管理器
        
        Args:
            persist_directory: 持久化目录
        """
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self._vector_stores: Dict[str, VectorStore] = {}
    
    def list_databases(self) -> List[Dict[str, any]]:
        """
        列出所有数据库集合
        
        Returns:
            数据库列表，每个包含名称和文档数量
        """
        collections = self.client.list_collections()
        databases = []
        
        for collection in collections:
            try:
                count = collection.count()
                databases.append({
                    "name": collection.name,
                    "document_count": count,
                    "metadata": collection.metadata or {}
                })
            except:
                databases.append({
                    "name": collection.name,
                    "document_count": 0,
                    "metadata": {}
                })
        
        return databases
    
    def create_database(self, name: str, metadata: Dict = None) -> bool:
        """
        创建新的数据库集合
        
        Args:
            name: 数据库名称
            metadata: 元数据
            
        Returns:
            是否创建成功
        """
        try:
            # 验证名称
            if not name or not name.strip():
                raise ValueError("数据库名称不能为空")
            
            name = name.strip()
            
            # 检查是否已存在
            try:
                existing = self.client.get_collection(name=name)
                return False  # 已存在
            except Exception:
                # 集合不存在，继续创建
                pass
            
            # 确保metadata不为空（ChromaDB要求metadata不能为空字典）
            # 使用与vector_store.py相同的metadata格式
            if metadata is None:
                metadata = {"hnsw:space": "cosine"}
            elif not metadata:
                # 如果是空字典，使用默认metadata
                metadata = {"hnsw:space": "cosine"}
            else:
                # 如果提供了metadata，确保包含必要的配置
                if "hnsw:space" not in metadata:
                    metadata = metadata.copy()  # 创建副本避免修改原始字典
                    metadata["hnsw:space"] = "cosine"
            
            # 创建新集合
            self.client.create_collection(
                name=name,
                metadata=metadata
            )
            return True
        except ValueError as e:
            # 重新抛出验证错误
            raise e
        except Exception as e:
            error_msg = str(e)
            # 重新抛出异常，让调用者处理
            raise Exception(f"创建数据库失败: {error_msg}")
    
    def delete_database(self, name: str) -> bool:
        """
        删除数据库集合
        
        Args:
            name: 数据库名称
            
        Returns:
            是否删除成功
        """
        try:
            # 如果VectorStore已缓存，先删除
            if name in self._vector_stores:
                del self._vector_stores[name]
            
            self.client.delete_collection(name=name)
            return True
        except Exception as e:
            print(f"删除数据库失败: {str(e)}")
            return False
    
    def get_database(self, name: str) -> Optional[VectorStore]:
        """
        获取数据库VectorStore实例
        
        Args:
            name: 数据库名称
            
        Returns:
            VectorStore实例，如果不存在返回None
        """
        # 如果已缓存，直接返回
        if name in self._vector_stores:
            return self._vector_stores[name]
        
        try:
            # 检查集合是否存在
            collection = self.client.get_collection(name=name)
            # 创建VectorStore实例
            vector_store = VectorStore(collection_name=name, persist_directory=self.persist_directory)
            self._vector_stores[name] = vector_store
            return vector_store
        except:
            return None
    
    def get_database_info(self, name: str) -> Optional[Dict]:
        """
        获取数据库信息
        
        Args:
            name: 数据库名称
            
        Returns:
            数据库信息字典
        """
        try:
            collection = self.client.get_collection(name=name)
            return {
                "name": collection.name,
                "document_count": collection.count(),
                "metadata": collection.metadata or {}
            }
        except:
            return None

