"""
RAG系统主程序
支持添加文档、查询和对话
"""
from rag_system import RAGSystem
import os
import sys


def print_menu():
    """打印菜单"""
    print("\n" + "="*50)
    print("RAG系统 - 检索增强生成")
    print("="*50)
    print("1. 添加文本文件到数据库")
    print("2. 添加文本内容到数据库")
    print("3. 查询（RAG模式）")
    print("4. 查看数据库信息")
    print("5. 退出")
    print("="*50)


def main():
    """主函数"""
    # 初始化RAG系统
    print("正在初始化RAG系统...")
    rag = RAGSystem(
        ollama_url="http://localhost:11434",
        chat_model="deepseek-r1:8b",
        collection_name="rag_documents",
        chunk_size=500,
        chunk_overlap=50
    )
    print("RAG系统初始化完成！")
    
    # 对话历史
    conversation_history = []
    
    while True:
        print_menu()
        choice = input("\n请选择操作 (1-5): ").strip()
        
        if choice == "1":
            # 添加文本文件
            file_path = input("请输入文件路径: ").strip()
            if os.path.exists(file_path):
                try:
                    print("正在处理文档...")
                    rag.add_document_from_file(file_path)
                    print("文档添加成功！")
                except Exception as e:
                    print(f"添加文档失败: {str(e)}")
            else:
                print("文件不存在！")
        
        elif choice == "2":
            # 添加文本内容
            print("请输入文本内容（输入'END'结束）:")
            text_lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                text_lines.append(line)
            
            text = "\n".join(text_lines)
            if text.strip():
                try:
                    print("正在处理文本...")
                    rag.add_text(text, source="manual_input")
                    print("文本添加成功！")
                except Exception as e:
                    print(f"添加文本失败: {str(e)}")
            else:
                print("文本内容为空！")
        
        elif choice == "3":
            # RAG查询
            query = input("请输入您的问题: ").strip()
            if query:
                try:
                    print("\n正在检索相关文档...")
                    result = rag.query(query, n_results=5, history=conversation_history)
                    
                    rewritten_query = result.get("rewritten_query")
                    if rewritten_query and rewritten_query != query:
                        print(f"\n改写后的查询：{rewritten_query}")

                    # 显示检索到的文档
                    if result["retrieved_documents"]:
                        print("\n检索到的相关文档:")
                        print("-" * 50)
                        for i, doc in enumerate(result["retrieved_documents"][:3], 1):
                            print(f"\n[文档 {i}]")
                            print(f"来源: {doc['metadata'].get('file_name', doc['metadata'].get('source', '未知'))}")
                            distance = doc.get('distance')
                            if distance is not None:
                                print(f"相似度: {1 - distance:.4f}")
                            if doc.get("rerank_score") is not None:
                                print(f"重排得分: {doc['rerank_score']:.4f}")
                            print(f"内容预览: {doc['content'][:200]}...")

                        # 绘制文档相关性柱状图（前10个文档）
                        try:
                            rag.plot_document_relevance(result["retrieved_documents"], top_k=10, show=True)
                        except ImportError as e:
                            print(f"绘制相关性图失败（缺少依赖）: {e}")
                        except Exception as e:
                            print(f"绘制相关性图失败: {str(e)}")
                    
                    # 显示生成的回答
                    print("\n" + "="*50)
                    print("回答:")
                    print("="*50)
                    answer = result["answer"]
                    print(answer)
                    print("="*50)
                    
                    # 更新对话历史
                    conversation_history.append({"role": "user", "content": query})
                    conversation_history.append({"role": "assistant", "content": answer})
                    
                    # 限制历史长度
                    if len(conversation_history) > 20:
                        conversation_history = conversation_history[-20:]
                    
                except Exception as e:
                    print(f"查询失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
            else:
                print("问题不能为空！")
        
        elif choice == "4":
            # 查看数据库信息
            info = rag.get_database_info()
            print("\n数据库信息:")
            print(f"集合名称: {info['collection_name']}")
            print(f"文档数量: {info['document_count']}")
        
        elif choice == "5":
            # 退出
            print("感谢使用RAG系统，再见！")
            break
        
        else:
            print("无效的选择，请重新输入！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)