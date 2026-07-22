"""Agent 工具定义 — 计算器、时间、文件操作、网页搜索"""

import os
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from langchain_core.tools import tool


# ============================================================
#  计算器
# ============================================================
@tool
def calculator(expression: str) -> str:
    """计算数学表达式的结果。

    支持运算符 + - * / // % ** 以及 math 模块中的所有函数（如 sqrt, sin, cos, log, pi, e 等）。
    参数 expression 为 Python 数学表达式字符串，例如 '123 * 456' 或 'sqrt(144) + 2**10'。
    """
    allowed_names = {
        k: v for k, v in math.__dict__.items() if not k.startswith("_")
    }
    allowed_builtins = {"abs": abs, "round": round, "int": int, "float": float}
    allowed_names.update(allowed_builtins)

    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"计算结果：{expression} = {result}"
    except Exception as e:
        return f"计算失败：{e}"


# ============================================================
#  当前时间
# ============================================================
@tool
def current_time(timezone_offset: str = "+8") -> str:
    """获取当前日期和时间。

    参数 timezone_offset 为 UTC 偏移，如 '+8'（北京时间），'-5'（美东时间），默认 '+8'。
    """
    try:
        offset_hours = int(timezone_offset)
        tz = timezone(timedelta(hours=offset_hours))
        now = datetime.now(tz)
        return f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')} (UTC{timezone_offset})"
    except ValueError:
        return f"时区参数错误：{timezone_offset}，请使用如 '+8'、'-5' 的格式"


# ============================================================
#  文件读取
# ============================================================
@tool
def read_file(filepath: str) -> str:
    """读取本地文件的内容。

    参数 filepath 为文件的绝对路径或相对于当前目录的路径。
    """
    path = Path(filepath).expanduser().resolve()
    if not path.exists():
        return f"文件不存在：{path}"
    if path.is_dir():
        files = os.listdir(path)
        return f"目录内容 ({path})：\n" + "\n".join(f"  - {f}" for f in files[:50])
    try:
        content = path.read_text(encoding="utf-8")
        if len(content) > 5000:
            content = content[:5000] + "\n\n... (文件过长，已截断)"
        return f"文件内容 ({path})：\n\n{content}"
    except UnicodeDecodeError:
        return f"无法以 UTF-8 编码读取文件：{path}（可能是二进制文件）"
    except Exception as e:
        return f"读取文件失败：{e}"


# ============================================================
#  文件写入
# ============================================================
@tool
def write_file(filepath: str, content: str) -> str:
    """将内容写入本地文件。如果文件已存在则覆盖。

    参数 filepath 为文件路径，content 为要写入的内容。
    """
    path = Path(filepath).expanduser().resolve()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"写入成功：{path}（{len(content)} 字符）"
    except Exception as e:
        return f"写入文件失败：{e}"


# ============================================================
#  网页搜索（可选，需要 TAVILY_API_KEY）
# ============================================================
def _create_search_tool():
    """尝试创建 Tavily 搜索工具，如果未配置 API Key 则返回一个占位工具"""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        @tool
        def web_search(query: str) -> str:
            """网页搜索工具（当前不可用，需配置 TAVILY_API_KEY）。"""
            return "网页搜索不可用。请设置 TAVILY_API_KEY 环境变量以启用搜索功能。"
        return web_search

    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        return TavilySearchResults(max_results=3, api_key=api_key)
    except ImportError:
        @tool
        def web_search(query: str) -> str:
            """网页搜索工具（当前不可用，缺少 langchain-community 包）。"""
            return "网页搜索不可用。请安装 langchain-community 包。"
        return web_search


web_search = _create_search_tool()


# ============================================================
#  工具集合
# ============================================================
def get_all_tools():
    """返回所有可用工具"""
    from agent.rag_tool import get_rag_tools, get_rag_status
    rag_tools = get_rag_tools()
    return [calculator, current_time, read_file, write_file, web_search] + rag_tools


def get_rag_status_text():
    """获取 RAG 知识库状态"""
    try:
        from agent.rag_tool import get_rag_status
        return get_rag_status()
    except Exception:
        return "RAG: 未初始化"
