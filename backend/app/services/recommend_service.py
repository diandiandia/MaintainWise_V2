import sqlite3
from typing import List, Dict, Any

def recommend_solutions(db: sqlite3.Connection, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    根据报修输入的故障现象或标题关键字，实时检索排故知识库
    优先置顶典型金标案例，返回最佳排除方案供后来人参考
    """
    if not query_text or len(query_text.strip()) == 0:
        return []
    
    kw = f"%{query_text.strip()}%"
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, title, equipment_category, phenomenon, root_cause, solution_steps, tags, is_featured
        FROM knowledge_cases
        WHERE title LIKE ? OR phenomenon LIKE ? OR root_cause LIKE ? OR tags LIKE ?
        ORDER BY is_featured DESC, id DESC
        LIMIT ?
    """, (kw, kw, kw, kw, limit))
    
    results = []
    for row in cursor.fetchall():
        results.append(dict(row))
    return results
