"""
嵌入模型模块：负责将文本转换为向量
使用本地BGE模型进行文本嵌入
"""
from typing import List
import numpy as np


class DeepSeekEmbedding:
    """嵌入模型类，使用本地BGE模型（DeepSeek没有embedding模型）"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "deepseek-r1:8b"):
        """
        初始化嵌入模型
        
        Args:
            base_url: Ollama服务地址（保留参数以兼容，但不使用）
            model_name: 模型名称（保留参数以兼容，但不使用）
        """
        self.base_url = base_url
        self.model_name = model_name
        # 使用本地BGE模型
        self.model_name_bge = "BAAI/bge-large-zh-v1.5"  # 中文嵌入模型
        self._local_model = None
        print(f"初始化嵌入模型: 使用本地BGE模型 {self.model_name_bge}")
    
    def _load_model(self):
        """加载本地BGE模型（延迟加载）"""
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print("正在加载BGE嵌入模型，首次加载可能需要一些时间...")
                self._local_model = SentenceTransformer(self.model_name_bge)
                print("BGE嵌入模型加载完成！")
            except ImportError:
                raise Exception("sentence-transformers库未安装，请安装: pip install sentence-transformers")
            except Exception as e:
                raise Exception(f"加载BGE嵌入模型失败: {str(e)}")
    
    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本嵌入向量（使用本地BGE模型）
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        self._load_model()
        try:
            embedding = self._local_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            raise Exception(f"获取嵌入向量失败: {str(e)}")
    
    def embed_texts(self, texts: List[str], use_ollama: bool = False) -> List[List[float]]:
        """
        批量获取文本嵌入向量（使用本地BGE模型）
        
        Args:
            texts: 文本列表
            use_ollama: 是否使用Ollama API（已废弃，保留以兼容，但不使用）
            
        Returns:
            嵌入向量列表
        """
        self._load_model()
        embeddings = []
        
        # 批量处理
        for i, text in enumerate(texts):
            try:
                embedding = self._local_model.encode(text, normalize_embeddings=True)
                embeddings.append(embedding.tolist())
                if (i + 1) % 10 == 0:
                    print(f"已处理 {i + 1}/{len(texts)} 个文档")
            except Exception as e:
                raise Exception(f"处理文档 {i+1} 失败: {str(e)}")
        
        return embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        获取查询文本的嵌入向量（使用本地BGE模型）
        
        Args:
            query: 查询文本
            
        Returns:
            嵌入向量
        """
        return self.get_embedding(query)

