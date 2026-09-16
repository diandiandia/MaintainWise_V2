import sqlite3
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import verify_password, hash_password, create_access_token
from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.user import Token, UserOut, ResetPasswordRequest, ChangePasswordRequest
from app.services.email_service import notify_password_expired, notify_password_expiring_soon

router = APIRouter()

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    用户登录接口：
    1. 验证账号与 bcrypt 密码；
    2. 检查账号是否停用或冻结；
    3. 检查 180 天密码有效期：到期自动冻结并邮件通知，提前 3 天提供临期预警；
    4. 返回 Token 及首次登录强制改密标记 (must_change_password)
    """
    cursor = db.cursor()
    cursor.execute(
        """SELECT id, username, password_hash, full_name, employee_no, role, phone, email,
                  is_active, must_change_password, password_changed_at, is_frozen, created_at
           FROM users WHERE username = ?""",
        (form_data.username.strip(),)
    )
    user = cursor.fetchone()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或密码错误"
        )
    
    user_dict = dict(user)
    if not user_dict.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账号已被停用，请联系车间主管"
        )

    if user_dict.get("is_frozen"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账号登录密码超期未改已被冻结，请联系系统管理员解冻重置"
        )
        
    if not verify_password(form_data.password, user_dict["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或密码错误"
        )
        
    # 计算密码使用天数
    changed_at_str = user_dict.get("password_changed_at") or user_dict.get("created_at")
    days_used = 0
    if changed_at_str:
        try:
            # 兼容不同格式
            dt_str = changed_at_str.split(".")[0]
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            days_used = (datetime.now() - dt).days
        except Exception:
            days_used = 0

    password_expiring_soon = False
    days_remaining = max(0, 180 - days_used)

    # 超过 180 天：强制冻结
    if days_used > 180 and user_dict["username"] != "admin":  # admin 保留应急兜底
        cursor.execute("UPDATE users SET is_frozen = 1 WHERE id = ?", (user_dict["id"],))
        db.commit()
        if user_dict.get("email"):
            notify_password_expired(user_dict["email"], user_dict["username"], user_dict["full_name"])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的登录密码已超过 180 天安全期限，系统已自动冻结该账号，请联系管理员解冻重置"
        )
    elif days_used >= 177:
        password_expiring_soon = True
        if user_dict.get("email"):
            notify_password_expiring_soon(user_dict["email"], user_dict["username"], user_dict["full_name"], days_remaining)

    access_token = create_access_token(subject=user_dict["id"], role=user_dict["role"])
    user_out = UserOut(**user_dict)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_out,
        "password_expiring_soon": password_expiring_soon,
        "days_remaining": days_remaining
    }

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: dict = Depends(get_current_user)):
    """获取当前登录人员详情"""
    return current_user

@router.put("/password")
def change_my_password(
    req: ResetPasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    用户自主修改个人密码：
    解除首次修改标记 (must_change_password=0)，解冻并重置 180 天倒计时周期
    """
    if len(req.new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="新密码长度不能少于 6 位")
    new_hash = hash_password(req.new_password.strip())
    cursor = db.cursor()
    cursor.execute(
        """UPDATE users 
           SET password_hash = ?, must_change_password = 0, is_frozen = 0, password_changed_at = CURRENT_TIMESTAMP 
           WHERE id = ?""",
        (new_hash, current_user["id"])
    )
    db.commit()
    return {"message": "密码修改成功，密码 180 天安全周期已刷新！"}

@router.post("/change-password")
def change_password_post(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    首次登录强制改密或自主修改接口：
    若提供原密码则校验原密码
    """
    cursor = db.cursor()
    if req.old_password:
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (current_user["id"],))
        row = cursor.fetchone()
        if not row or not verify_password(req.old_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="原密码不正确")
            
    if len(req.new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="新密码长度不能少于 6 位")
        
    new_hash = hash_password(req.new_password.strip())
    cursor.execute(
        """UPDATE users 
           SET password_hash = ?, must_change_password = 0, is_frozen = 0, password_changed_at = CURRENT_TIMESTAMP 
           WHERE id = ?""",
        (new_hash, current_user["id"])
    )
    db.commit()
    return {"message": "密码修改成功，安全策略已达标，欢迎进入 MaintainWise 2.0！"}

