"""SQL 数据建模工具 — SQLite 建表、插入、查询"""

import sqlite3
import os
from pathlib import Path
from langchain_core.tools import tool

_DB_PATH = None


def _get_db(db_path: str = None):
    """获取数据库连接，首次使用时自动创建"""
    global _DB_PATH
    if db_path is None:
        if _DB_PATH is None:
            _DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
            os.makedirs(_DB_PATH, exist_ok=True)
        db_path = os.path.join(_DB_PATH, "agent_db.sqlite")
    else:
        db_path = str(Path(db_path).expanduser().resolve())

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn, db_path


def _format_rows(rows, cols=None):
    """格式化查询结果为表格文本"""
    if not rows:
        return "(empty)"
    if cols is None:
        cols = rows[0].keys()
    lines = [" | ".join(cols)]
    lines.append("-" * len(lines[0]))
    for row in rows:
        lines.append(" | ".join(str(row[c]) for c in cols))
    return "\n".join(lines)


@tool
def sql_show_tables() -> str:
    """查看数据库中的所有表及其结构（字段名、类型）。
    用于了解当前数据库的数据模型。
    """
    try:
        conn, db_path = _get_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = cursor.fetchall()

        if not tables:
            conn.close()
            return f"数据库为空（{db_path}），还没有任何表"

        result = [f"数据库：{db_path}\n"]
        for t in tables:
            tname = t["name"]
            cols = conn.execute(f"PRAGMA table_info({tname})").fetchall()
            col_info = ", ".join(f"{c['name']} {c['type']}" for c in cols)
            row_count = conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
            result.append(f"  {tname} ({row_count} rows)")
            result.append(f"    {col_info}")

        conn.close()
        return "\n".join(result)
    except Exception as e:
        return f"查询失败：{e}"


@tool
def sql_execute(sql: str) -> str:
    """执行非查询 SQL 语句：CREATE TABLE、INSERT、UPDATE、DELETE。

    参数 sql 为一条或多条以分号分隔的 SQL 语句。
    CREATE TABLE 示例：
      CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, created_at TEXT)
    INSERT 示例：
      INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')
    """
    if not sql.strip():
        return "SQL 语句为空"

    try:
        conn, db_path = _get_db()
        # 支持多条语句
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        results = []

        for stmt in statements:
            cursor = conn.execute(stmt)
            conn.commit()
            if stmt.upper().startswith("CREATE"):
                table_name = stmt.split()[2].split("(")[0].strip()
                results.append(f"CREATE: 表 {table_name} 创建成功")
            elif stmt.upper().startswith("INSERT"):
                results.append(f"INSERT: {cursor.rowcount} 行已插入")
            elif stmt.upper().startswith("UPDATE"):
                results.append(f"UPDATE: {cursor.rowcount} 行已更新")
            elif stmt.upper().startswith("DELETE"):
                results.append(f"DELETE: {cursor.rowcount} 行已删除")
            else:
                results.append(f"OK: {cursor.rowcount} rows affected")

        conn.close()
        return "\n".join(results)
    except Exception as e:
        return f"SQL 执行失败：{e}"


@tool
def sql_query(query: str, limit: int = 20) -> str:
    """执行 SELECT 查询并返回结果。

    参数 query 为完整的 SELECT 语句，limit 为最大返回行数（默认 20）。
    示例：SELECT * FROM users WHERE email LIKE '%@example.com'
    """
    if not query.strip():
        return "查询语句为空"

    query = query.strip()
    if "LIMIT" not in query.upper():
        query += f" LIMIT {limit}"

    try:
        conn, db_path = _get_db()
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description] if cursor.description else []

        result = f"查询结果（{len(rows)} 行）：\n"
        result += _format_rows(rows, cols)

        conn.close()
        return result
    except Exception as e:
        return f"查询失败：{e}"


@tool
def sql_modeling(requirement: str) -> str:
    """根据需求描述，提供数据库建模建议（表结构、字段、关系）。

    参数 requirement 为业务需求的中文描述，例如：
    "一个电商系统，需要存储用户、商品、订单信息"

    返回推荐的建表 SQL 语句。
    """
    prompt = f"""你是一个数据库建模专家。根据以下需求，提供 SQLite 建表语句：

需求：{requirement}

请输出：
1. 分析关键实体和关系（2-3 句话）
2. CREATE TABLE 语句（SQLite 语法，包含合理的主键和字段类型）

直接输出结果，不要带 markdown 代码块标记。"""

    return f"请 AI 完成以下建模任务：\n\n{prompt}\n\n请输出建模建议和 SQL 语句。"


def get_sql_tools():
    """返回所有 SQL 工具"""
    return [sql_show_tables, sql_execute, sql_query, sql_modeling]
