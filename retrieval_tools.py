# retrieval_tools.py
from typing import List
from langchain_core.tools import tool
import chromadb
from chromadb.utils import embedding_functions
import os
# 1. 设置离线模式，禁止联网检查更新，这是解决卡顿的核心
os.environ['HF_HUB_OFFLINE'] = '1'
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-small-zh-v1.5"  # 中文专用
)
# 全局ChromaDB客户端（工具函数共享）
_chroma_client = None
db_path = "./chroma_db"
_chroma_client = chromadb.PersistentClient(path=db_path)
def _get_chroma_client(db_path: str = "./chroma_db"):
    """获取或创建ChromaDB客户端（单例模式）- 使用新版 PersistentClient"""
    
        
    return _chroma_client


@tool
def retrieve_knowledge(skill_id: str, query: str, top_k: int = 2) -> str:
    """
    在指定的技能知识库中检索相关故障处理文档。
    
    根据skill_id选择对应的故障领域知识库（如打印机、网络、操作系统、账号权限），
    使用向量检索查找与query最相关的处理文档，返回详细的解决步骤。
    
    Args:
        skill_id: 技能ID，可选值：
            - "hardware_printer"（打印机故障：卡纸、缺墨、脱机等）
            - "hardware_network"（网络故障：WiFi、网线、IP等）
            - "software_os"（系统故障：蓝屏、卡顿、更新失败等）
            - "software_account"（账号故障：锁定、密码、权限等）
        query: 用户的具体问题描述，如"打印机卡纸了"、"WiFi连不上"等
        top_k: 返回最相关的文档数量，范围1-5，默认2个
    
    Returns:
        检索到的故障处理文档内容，多个文档用"---"分隔。
        如果没有找到相关内容，返回"未找到相关文档，请基于通用流程处理"。
    
    Examples:
        >>> retrieve_knowledge("hardware_printer", "打印机卡纸了", 2)
        '【打印机卡纸处理】第一步：立即停止使用...---【打印机维护】定期清理...'
        
        >>> retrieve_knowledge("hardware_network", "WiFi总是断开", 1)
        '【WiFi频繁断开】确认是否仅单台设备问题...'
        
        >>> retrieve_knowledge("software_os", "电脑蓝屏", 2)
        '【蓝屏紧急处理】记录错误代码...'
    """
    try:
        client = _get_chroma_client()
         # 兼容处理：将连字符替换为下划线
        normalized_skill_id = skill_id.replace('-', '_')
        
        collection_name = skill_id
        
        # 获取collection
        try:
            collection = client.get_collection(collection_name,embedding_function=embedding_fn)
        except:
            return f"错误：知识库 '{skill_id}' 不存在，请检查skill_id是否正确"
        
        # 执行检索
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, 5),  # 限制最大5个
            include=["documents", "distances", "metadatas"]
        )
        
        documents = results["documents"][0]
        distances = results["distances"][0]
        
        if not documents or documents[0] is None:
            return "未找到相关文档，请基于通用流程处理"
        
        # 格式化输出（带相似度信息）
        formatted_results = []
        for doc, dist in zip(documents, distances):
            formatted_results.append(f"[距离: {dist:.3f}] {doc}")
            
        
        # 多个文档用分隔符连接
        return "\n---\n".join(formatted_results)
        
    except Exception as e:
        return f"检索出错: {str(e)}"


# 工具列表（供Agent使用）
RETRIEVAL_TOOLS = [retrieve_knowledge]