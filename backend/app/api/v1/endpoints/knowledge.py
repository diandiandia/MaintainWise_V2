import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.deps import get_current_user, require_engineer
from app.db.session import get_db
from app.schemas.knowledge import KnowledgeCaseCreate, KnowledgeCaseUpdate, KnowledgeCaseOut
from app.services.recommend_service import recommend_solutions

router = APIRouter()

@router.get("", response_model=List[KnowledgeCaseOut])
def list_knowledge_cases(
    search: Optional[str] = None,
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """查询排故知识库案例"""
    cursor = db.cursor()
    query = "SELECT * FROM knowledge_cases WHERE 1=1"
    params = []
    
    if category:
        query += " AND equipment_category = ?"
        params.append(category)
    if featured is not None:
        query += " AND is_featured = ?"
        params.append(int(featured))
    if search:
        kw = f"%{search.strip()}%"
        query += " AND (title LIKE ? OR phenomenon LIKE ? OR root_cause LIKE ? OR tags LIKE ?)"
        params.extend([kw, kw, kw, kw])
        
    query += " ORDER BY is_featured DESC, id DESC"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]

@router.get("/recommend")
def recommend_case(
    query: str = Query(..., description="报修故障简述或现象关键词"),
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    报修时实时排故方案推荐接口：
    根据输入文字快速检索前人高分排查方案，实现“尚未发单，排查方案已至”
    """
    return recommend_solutions(db, query)

@router.post("", response_model=KnowledgeCaseOut)
def create_knowledge_case(
    req: KnowledgeCaseCreate,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """工程师专属：录入新排故案例"""
    cursor = db.cursor()
    cursor.execute(
        """INSERT INTO knowledge_cases 
           (source_order_id, title, equipment_category, phenomenon, root_cause, solution_steps, tags, is_featured, created_by_engineer_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            req.source_order_id, req.title.strip(), req.equipment_category or "通用",
            req.phenomenon.strip(), req.root_cause.strip(), req.solution_steps.strip(),
            req.tags or "", int(req.is_featured or False), engineer["id"]
        )
    )
    db.commit()
    case_id = cursor.lastrowid
    cursor.execute("SELECT * FROM knowledge_cases WHERE id = ?", (case_id,))
    return dict(cursor.fetchone())

@router.put("/{case_id}", response_model=KnowledgeCaseOut)
def update_knowledge_case(
    case_id: int,
    req: KnowledgeCaseUpdate,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """工程师专属：修改案例"""
    cursor = db.cursor()
    cursor.execute("SELECT id FROM knowledge_cases WHERE id = ?", (case_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="案例不存在")
        
    updates = []
    params = []
    for field, val in req.model_dump(exclude_unset=True).items():
        if val is not None:
            updates.append(f"{field} = ?")
            params.append(int(val) if isinstance(val, bool) else val)
            
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(case_id)
        cursor.execute(f"UPDATE knowledge_cases SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()
        
    cursor.execute("SELECT * FROM knowledge_cases WHERE id = ?", (case_id,))
    return dict(cursor.fetchone())

@router.delete("/{case_id}")
def delete_knowledge_case(
    case_id: int,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """工程师专属：删除案例"""
    cursor = db.cursor()
    cursor.execute("DELETE FROM knowledge_cases WHERE id = ?", (case_id,))
    db.commit()
    return {"message": "案例已成功删除"}
