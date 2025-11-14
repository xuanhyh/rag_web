"""
通用RAG检索管线：封装问题重写、检索、重排与回答生成
"""
from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Dict, List, Optional

import requests


class BaseRAGPipeline:
    """
    提供统一的检索流程：问题重写 → 检索 → 重排 → 回答生成
    子类需保证存在 self.embedding_model 属性以及所需的向量库访问能力。
    """

    def __init__(
        self,
        ollama_url: str,
        chat_model: str,
        enable_query_rewrite: bool = True,
        enable_rerank: bool = True,
        reranker_model_name: str = "BAAI/bge-reranker-large",
        retrieval_multiplier: float = 1.8,
        max_retrieve_results: int = 15,
    ):
        self.ollama_url = ollama_url
        self.chat_model = chat_model
        self.enable_query_rewrite = enable_query_rewrite
        self.enable_rerank = enable_rerank
        self.reranker_model_name = reranker_model_name
        self.retrieval_multiplier = max(1.0, retrieval_multiplier)
        self.max_retrieve_results = max_retrieve_results

        self._reranker = None
        self._reranker_available = enable_rerank
        self._last_reranker_error: Optional[str] = None
        self._font_configured = False

    # —— LLM相关工具方法 ————————————————————————————————————————
    def _call_llm(self, messages: List[Dict[str, str]], stream: bool = False, timeout: int = 60):
        """
        调用Ollama聊天接口。
        如果 stream=True，则返回 requests.Response 实例供调用方处理流。
        """
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "stream": stream,
        }
        response = requests.post(
            url=f"{self.ollama_url}/api/chat",
            json=payload,
            timeout=timeout,
            stream=stream,
        )
        if response.status_code != 200:
            detail = response.text if not stream else f"status={response.status_code}"
            raise Exception(f"LLM 调用失败: {response.status_code} - {detail}")
        return response if stream else response.json()

    def build_prompt(self, user_query: str, context: str) -> str:
        """构建回答生成的提示词。子类可按需覆盖。"""
        return f"""基于以下上下文信息回答问题。如果上下文中没有相关信息，请基于你的知识回答。

上下文信息：
{context}

用户问题：{user_query}

请提供准确、详细的回答："""

    def generate_answer(self, user_query: str, context: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """调用大模型生成回答。"""
        messages = deepcopy(history) if history else []
        messages.append({"role": "user", "content": self.build_prompt(user_query, context)})

        try:
            data = self._call_llm(messages)
            return data.get("message", {}).get("content", "")
        except Exception as exc:
            return f"生成回答时出错: {exc}"

    # —— 问题重写 ————————————————————————————————————————————————
    def rewrite_query(self, query: str) -> str:
        """使用LLM将用户问题重写为更适合检索的查询。"""
        if not self.enable_query_rewrite:
            return query

        messages = [
            {
                "role": "system",
                "content": "你是一位检索查询重写助手，请将用户的自然语言问题改写为便于知识库检索的简洁查询，保留关键信息，不要回答问题。",
            },
            {
                "role": "user",
                "content": f"原始问题：{query}\n\n请输出仅包含改写后的查询：",
            },
        ]

        try:
            data = self._call_llm(messages)
            rewritten = data.get("message", {}).get("content", "").strip()
            if not rewritten:
                return query

            # 只取第一行，避免模型输出多余说明
            first_line = rewritten.splitlines()[0].strip()
            if first_line and first_line != query:
                print(f"[RAGPipeline] 查询重写：{query} -> {first_line}")
            return first_line or query
        except Exception as exc:
            print(f"[警告] 问题重写失败，使用原始问题。原因: {exc}")
            return query

    # —— 检索与重排 ————————————————————————————————————————————————
    def _calc_retrieve_count(self, requested: int) -> int:
        """根据倍率计算实际检索数量。"""
        extra = int(math.ceil(requested * self.retrieval_multiplier))
        total = max(requested, extra)
        if self.max_retrieve_results:
            total = min(total, self.max_retrieve_results)
        return total

    def retrieve_documents(self, vector_store, rewritten_query: str, n_results: int) -> List[Dict[str, Any]]:
        """
        执行向量检索。子类需确保 self.embedding_model 存在。
        """
        query_embedding = self.embedding_model.embed_query(rewritten_query)
        return vector_store.search(query_embedding, n_results=n_results)

    def _ensure_reranker(self):
        """懒加载交叉编码器用于重排。"""
        if not self.enable_rerank or not self._reranker_available:
            return
        if self._reranker is not None:
            return
        try:
            from sentence_transformers import CrossEncoder

            print(f"正在加载重排模型: {self.reranker_model_name}，可能需要一些时间...")
            self._reranker = CrossEncoder(self.reranker_model_name, trust_remote_code=False)
            print("重排模型加载完成。")
        except Exception as exc:
            self._reranker_available = False
            self._last_reranker_error = str(exc)
            print(f"[警告] 加载重排模型失败，将跳过重排。原因: {exc}")

    def rerank_documents(
        self,
        original_query: str,
        retrieved_documents: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """对检索结果进行重排，返回前 top_k。"""
        if not retrieved_documents:
            return []

        if not self.enable_rerank or not self._reranker_available:
            return retrieved_documents[:top_k]

        self._ensure_reranker()
        if not self._reranker:
            return retrieved_documents[:top_k]

        try:
            pairs = [(original_query, doc["content"]) for doc in retrieved_documents]
            scores = self._reranker.predict(pairs)

            enriched_docs: List[Dict[str, Any]] = []
            for doc, score in zip(retrieved_documents, scores):
                doc_copy = deepcopy(doc)
                doc_copy["rerank_score"] = float(score)
                enriched_docs.append(doc_copy)

            sorted_docs = sorted(enriched_docs, key=lambda item: item.get("rerank_score", 0.0), reverse=True)
            return sorted_docs[:top_k]
        except Exception as exc:
            print(f"[警告] 文档重排失败，将使用原始顺序。原因: {exc}")
            return retrieved_documents[:top_k]

    # —— 上下文构建 ————————————————————————————————————————————————
    def build_context(self, documents: List[Dict[str, Any]]) -> str:
        """根据文档构建上下文字符串。"""
        if not documents:
            return "未找到相关文档"

        parts = []
        for idx, doc in enumerate(documents, start=1):
            parts.append(f"[文档{idx}]\n{doc.get('content', '')}")
        return "\n\n".join(parts)

    # —— 完整流程辅助 ————————————————————————————————————————————————
    def run_pipeline(
        self,
        vector_store,
        user_query: str,
        n_results: int,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        执行完整检索流程，返回包含中间结果的字典。
        """
        rewritten_query = self.rewrite_query(user_query)
        retrieve_k = self._calc_retrieve_count(n_results)
        initial_docs = self.retrieve_documents(vector_store, rewritten_query, retrieve_k)
        final_docs = self.rerank_documents(user_query, initial_docs, n_results)
        context = self.build_context(final_docs)
        answer = self.generate_answer(user_query, context, history)
        relevance_scores = self.get_document_relevance_scores(final_docs, top_k=n_results)

        return {
            "query": user_query,
            "rewritten_query": rewritten_query,
            "retrieved_documents": final_docs,
            "initial_retrieved_documents": initial_docs,
            "context": context,
            "answer": answer,
            "relevance_scores": relevance_scores,
        }

    # —— 相关性计算与可视化 —————————————————————————————————————————
    def get_document_relevance_scores(
        self,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        计算文档相关性分数，优先使用rerank得分，否则使用1-距离。
        返回按分数从高到低排序的前 top_k 个结果。
        """
        if not documents:
            return []

        scored_docs: List[Dict[str, Any]] = []
        for idx, doc in enumerate(documents):
            if not isinstance(doc, dict):
                continue

            score = None
            if doc.get("rerank_score") is not None:
                score = float(doc["rerank_score"])
            elif doc.get("distance") is not None:
                try:
                    score = 1.0 - float(doc["distance"])
                except (TypeError, ValueError):
                    score = None

            if score is None:
                score = 0.0

            metadata = doc.get("metadata") or {}
            chunk_index = metadata.get("chunk_index")
            if chunk_index is None:
                chunk_index = idx

            source = metadata.get("file_name") or metadata.get("source")
            if source:
                label = f"{source}#片段{int(chunk_index) + 1}"
            else:
                content_preview = doc.get("content", "").strip().replace("\n", " ")
                if content_preview:
                    content_preview = content_preview[:16] + ("…" if len(content_preview) > 16 else "")
                else:
                    content_preview = f"文档{idx + 1}"
                label = f"{content_preview}#片段{int(chunk_index) + 1}"

            scored_docs.append(
                {
                    "label": label,
                    "score": score,
                    "metadata": metadata,
                    "source_index": idx,
                }
            )

        scored_docs.sort(key=lambda item: item["score"], reverse=True)
        return scored_docs[:top_k]

    def plot_document_relevance(
        self,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
        show: bool = True,
        save_path: Optional[str] = None,
    ):
        """
        使用Matplotlib绘制文档相关性柱状图。

        Args:
            documents: 文档列表
            top_k: 展示的文档数量（默认前10）
            show: 是否直接展示图像
            save_path: 如果提供则将图像保存到该路径

        Returns:
            matplotlib.figure.Figure 对象
        """
        scores = self.get_document_relevance_scores(documents, top_k=top_k)
        if not scores:
            raise ValueError("没有可用于绘制的数据，请确认检索结果是否为空。")

        try:
            import matplotlib  # type: ignore
            if not show:
                matplotlib.use("Agg")
            import matplotlib.pyplot as plt  # type: ignore
            from matplotlib import font_manager  # type: ignore

            if not self._font_configured:
                preferred_fonts = [
                    "SimHei",
                    "Microsoft YaHei",
                    "STSong",
                    "Noto Sans CJK SC",
                    "WenQuanYi Micro Hei",
                ]
                available_fonts = {f.name for f in font_manager.fontManager.ttflist}
                for font_name in preferred_fonts:
                    if font_name in available_fonts:
                        current_fonts = list(plt.rcParams.get("font.sans-serif", []))
                        plt.rcParams["font.sans-serif"] = [font_name] + current_fonts
                        plt.rcParams["axes.unicode_minus"] = False
                        self._font_configured = True
                        break
                if not self._font_configured:
                    print("[警告] 未找到可用的中文字体，将继续使用默认字体，可能出现字符缺失。")
        except ImportError as exc:
            raise ImportError("绘制相关性图需要安装 matplotlib，请执行: pip install matplotlib") from exc

        labels = [item["label"] for item in scores]
        values = [item["score"] for item in scores]

        fig, ax = plt.subplots(figsize=(10, 6))
        bar_positions = range(len(values))

        ax.bar(bar_positions, values, color="#4299e1")
        ax.set_xticks(bar_positions)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=10)
        ax.set_ylabel("score", fontsize=12)
        ax.set_xlabel("text", fontsize=12)
        ax.set_title("text_score Top{0}".format(len(values)), fontsize=14)
        ax.set_ylim(bottom=min(0, min(values) - 0.05))

        for pos, val in zip(bar_positions, values):
            ax.text(pos, val, f"{val:.3f}", ha="center", va="bottom", fontsize=9)

        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight")

        if show:
            plt.show()
        else:
            plt.close(fig)

        return fig


