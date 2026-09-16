import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.security import hash_password
from app.core.deps import require_admin
from app.db.session import get_db
from app.schemas.user import UserCreate, UserUpdate, UserOut, ResetPasswordRequest

router = APIRouter()

@router.get("", response_model=List[UserOut])
def list_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """管理员专属：获取全厂人员列表"""
    cursor = db.cursor()
    query = """SELECT id, username, full_name, employee_no, role, phone, email,
                      is_active, must_change_password, password_changed_at, is_frozen, created_at
               FROM users WHERE 1=1"""
    params = []
    
    if role:
        query += " AND role = ?"
        params.append(role)
    if search:
        query += " AND (username LIKE ? OR full_name LIKE ? OR employee_no LIKE ?)"
        kw = f"%{search.strip()}%"
        params.extend([kw, kw, kw])
        
    query += " ORDER BY id ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(r) for r in rows]

@router.post("", response_model=UserOut)
def create_user(
    req: UserCreate,
    db: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """管理员专属：录入新员工账号 (初始标记首次强制改密)"""
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ? OR employee_no = ?", (req.username.strip(), req.employee_no.strip()))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="用户名或员工工号已被占用")
        
    pwd_hash = hash_password(req.password.strip())
    cursor.execute(
        """INSERT INTO users (username, password_hash, full_name, employee_no, role, phone, email, is_active, must_change_password, is_frozen)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0)""",
        (req.username.strip(), pwd_hash, req.full_name.strip(), req.employee_no.strip(), req.role, req.phone, req.email or "", int(req.is_active if req.is_active is not None else 1))
    )
    db.commit()
    user_id = cursor.lastrowid
    
    cursor.execute("SELECT id, username, full_name, employee_no, role, phone, email, is_active, must_change_password, password_changed_at, is_frozen, created_at FROM users WHERE id = ?", (user_id,))
    return dict(cursor.fetchone())

@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    req: UserUpdate,
    db: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """管理员专属：修改员工资料"""
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="未找到该用户")
        
    updates = []
    params = []
    if req.full_name is not None:
        updates.append("full_name = ?")
        params.append(req.full_name)
    if req.role is not None:
        updates.append("role = ?")
        params.append(req.role)
    if req.phone is not None:
        updates.append("phone = ?")
        params.append(req.phone)
    if req.email is not None:
        updates.append("email = ?")
        params.append(req.email)
    if req.is_active is not None:
        updates.append("is_active = ?")
        params.append(int(req.is_active))
    if req.must_change_password is not None:
        updates.append("must_change_password = ?")
        params.append(int(req.must_change_password))
    if req.is_frozen is not None:
        updates.append("is_frozen = ?")
        params.append(int(req.is_frozen))
        
    if updates:
        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()
        
    cursor.execute("SELECT id, username, full_name, employee_no, role, phone, email, is_active, must_change_password, password_changed_at, is_frozen, created_at FROM users WHERE id = ?", (user_id,))
    return dict(cursor.fetchone())

@router.put("/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    req: ResetPasswordRequest,
    db: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """管理员专属：一键重置员工密码并解除冻结，设定首次登录强制改密"""
    if len(req.new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="重置密码长度不能少于 6 位")
        
    new_hash = hash_password(req.new_password.strip())
    cursor = db.cursor()
    cursor.execute(
        """UPDATE users 
           SET password_hash = ?, must_change_password = 1, is_frozen = 0, password_changed_at = CURRENT_TIMESTAMP 
           WHERE id = ?""",
        (new_hash, user_id)
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="未找到该用户")
    db.commit()
    return {"message": "员工密码重置成功，已解除冻结并设置下次登录强制改密"}

@router.put("/{user_id}/unfreeze")
def unfreeze_user(
    user_id: int,
    db: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """管理员专属：解冻超期账号并刷新密码倒计时"""
    cursor = db.cursor()
    cursor.execute(
        "UPDATE users SET is_frozen = 0, password_changed_at = CURRENT_TIMESTAMP, must_change_password = 1 WHERE id = ?",
        (user_id,)
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="未找到该用户")
    db.commit()
    return {"message": "用户账号已成功解冻，要求登录后立即修改新密码"}

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """管理员专属：停用人员账号（软删除，保证历史业务签署完好）"""
    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
    db.commit()
    return {"message": "人员账号已成功停用"}

