import sqlite3
from typing import Generator
from app.core.config import settings

def get_db_connection() -> sqlite3.Connection:
    """获取启用了 WAL 模式和外键约束的 SQLite3 连接"""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # 强制 WAL 模式与外键级联
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI 依赖注入连接生成器"""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
