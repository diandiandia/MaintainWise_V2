import sqlite3
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: sqlite3.Connection = Depends(get_db)
) -> dict:
    """从 JWT 提取当前用户信息并校验有效性"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未提供有效登录凭据或会话已超时，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    cursor = db.cursor()
    cursor.execute("SELECT id, username, full_name, employee_no, role, phone, email, is_active FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user is None:
        raise credentials_exception
    
    user_dict = dict(user)
    if not user_dict.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该账号已被停用，请联系管理员")
    
    return user_dict

def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """系统管理员 (ADMIN) 专属权限守卫"""
    if current_user["role"] != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足: 该操作仅限系统管理员 (ADMIN) 执行"
        )
    return current_user

def require_engineer(current_user: dict = Depends(get_current_user)) -> dict:
    """主管工程师 (ENGINEER) 或管理员核心业务守卫"""
    if current_user["role"] not in ("ADMIN", "ENGINEER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足: 该操作仅限主管工程师 (ENGINEER) 执行"
        )
    return current_user

def require_technician(current_user: dict = Depends(get_current_user)) -> dict:
    """合法车间人员（含技术员、工程师、管理员）守卫"""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return current_user
