"""RAG 知识库工具 — 文档加载、向量化、检索问答"""

import os
from pathlib import Path
from langchain_core.tools import tool

# 全局向量存储（内存模式）
_vector_store = None
_loaded_files = []


def _get_vector_store():
    """获取或创建 ChromaDB 向量存储"""
    global _vector_store
    if _vector_store is None:
        import chromadb
        from chromadb.config import Settings
        client = chromadb.Client(Settings(anonymized_telemetry=False))
        _vector_store = client.get_or_create_collection("rag_knowledge")
    return _vector_store


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """简单文本分块"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def _get_embedding(text: str) -> list:
    """使用 DeepSeek API 或简单哈希做 embedding"""
    # 先使用 ChromaDB 内置的 sentence-transformers
    try:
        from chromadb.utils import embedding_functions
        ef = embedding_functions.DefaultEmbeddingFunction()
        return ef([text])[0]
    except Exception:
        # fallback: use simple word-based embedding
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        return [b / 255.0 for b in h[:128]]


@tool
def rag_add_document(filepath: str) -> str:
    """将本地文档添加到 RAG 知识库。

    参数 filepath 为文档的绝对路径，支持 .txt、.md 格式。
    文档会被自动分块并向量化存储，之后可用 rag_search 检索。
    """
    path = Path(filepath).expanduser().resolve()
    if not path.exists():
        return f"文件不存在：{path}"

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"无法读取文件（编码问题）：{path}"
    except Exception as e:
        return f"读取文件失败：{e}"

    if not text.strip():
        return "文件为空"

    # 分块
    chunks = _chunk_text(text)
    if not chunks:
        return "文件内容太短"

    # 加入向量库
    try:
        store = _get_vector_store()
        embedding = _get_embedding
        ids = [f"{path.stem}_{i}" for i in range(len(chunks))]

        # 逐个添加
        for i, chunk in enumerate(chunks):
            store.add(
                documents=[chunk],
                ids=[ids[i]],
                metadatas=[{"source": str(path), "chunk": i}]
            )

        _loaded_files.append(str(path))
        return f"已添加知识库：{path.name}（{len(chunks)} 个片段，共 {len(text)} 字符）"
    except Exception as e:
        return f"向量化失败：{e}"


@tool
def rag_search(query: str, k: int = 3) -> str:
    """从已添加的 RAG 知识库中检索相关内容。

    参数 query 为搜索查询，k 为返回片段数（默认 3）。
    使用前需先用 rag_add_document 添加文档。
    """
    if not _loaded_files:
        return "知识库为空，请先用 rag_add_document 添加文档"

    try:
        store = _get_vector_store()
        results = store.query(query_texts=[query], n_results=k)

        if not results or not results.get("documents") or not results["documents"][0]:
            return "未找到相关内容"

        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results.get("metadatas", [[{}]])[0][i] if results.get("metadatas") else {}
            source = meta.get("source", "unknown")
            chunks.append(f"[来源: {source}]\n{doc}")

        return "\n\n---\n\n".join(chunks)
    except Exception as e:
        return f"检索失败：{e}"


@tool
def rag_ask(query: str) -> str:
    """基于 RAG 知识库回答问题。

    参数 query 为你的问题。会先从知识库检索相关内容再回答。
    使用前需先用 rag_add_document 添加文档。
    """
    # 先检索
    context = rag_search.invoke({"query": query, "k": 3})
    if context.startswith("知识库为空") or context.startswith("未找到"):
        return context

    # 返回检索结果让 LLM 回答
    return f"以下是与问题相关的知识库内容：\n\n{context}\n\n请基于以上内容回答问题：{query}"


def get_rag_tools():
    """返回所有 RAG 工具"""
    return [rag_add_document, rag_search, rag_ask]


def get_rag_status() -> str:
    """返回 RAG 知识库状态"""
    if not _loaded_files:
        return "RAG 知识库：空（未加载文档）"
    return f"RAG 知识库：已加载 {len(_loaded_files)} 个文件\n" + "\n".join(f"  - {f}" for f in _loaded_files)
