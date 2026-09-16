import sqlite3
import secrets
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from app.core.config import settings
from app.core.deps import get_current_user, require_engineer
from app.db.session import get_db
from app.schemas.work_order import WorkOrderCreate, WorkOrderUpdate, WorkOrderDispatch, WorkOrderResolve, WorkOrderOut
from app.services.email_service import notify_work_order_assigned

router = APIRouter()

@router.get("", response_model=List[WorkOrderOut])
def list_work_orders(
    equipment_id: Optional[int] = None,
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """四态工单看板与列表查询接口（安全适配软删除，快照回退）"""
    cursor = db.cursor()
    query = """
        SELECT w.*, COALESCE(NULLIF(w.equipment_name, ''), e.equipment_name, '已归档设备') as equipment_name,
               u.full_name as reporter_name,
               eng.full_name as assigned_by_name, a.full_name as assignee_name
        FROM work_orders w
        LEFT JOIN equipments e ON w.equipment_id = e.id
        LEFT JOIN users u ON w.reporter_id = u.id
        LEFT JOIN users eng ON w.assigned_by_engineer_id = eng.id
        LEFT JOIN users a ON w.assignee_id = a.id
        WHERE 1=1
    """
    params = []
    if equipment_id:
        query += " AND w.equipment_id = ?"
        params.append(equipment_id)
    if status:
        query += " AND w.status = ?"
        params.append(status)
    if urgency:
        query += " AND w.urgency = ?"
        params.append(urgency)
        
    query += " ORDER BY w.id DESC"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]

@router.get("/{order_id}", response_model=WorkOrderOut)
def get_work_order(
    order_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """查询单笔现场维护工单详情"""
    cursor = db.cursor()
    cursor.execute("""
        SELECT w.*, COALESCE(NULLIF(w.equipment_name, ''), e.equipment_name, '已归档设备') as equipment_name,
               u.full_name as reporter_name,
               eng.full_name as assigned_by_name, a.full_name as assignee_name
        FROM work_orders w
        LEFT JOIN equipments e ON w.equipment_id = e.id
        LEFT JOIN users u ON w.reporter_id = u.id
        LEFT JOIN users eng ON w.assigned_by_engineer_id = eng.id
        LEFT JOIN users a ON w.assignee_id = a.id
        WHERE w.id = ?
    """, (order_id,))
    wo = cursor.fetchone()
    if not wo:
        raise HTTPException(status_code=404, detail="未找到该维修工单")
    return dict(wo)

@router.post("", response_model=WorkOrderOut)
def report_fault_work_order(
    req: WorkOrderCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    全员 30 秒极速突发报修：
    创建新工单并联动将设备状态置为 REPAIRING (维修中)，留存设备名称快照
    """
    cursor = db.cursor()
    cursor.execute("SELECT id, equipment_name, responsible_engineer_id FROM equipments WHERE id = ? AND is_deleted = 0", (req.equipment_id,))
    dev = cursor.fetchone()
    if not dev:
        raise HTTPException(status_code=404, detail="报修设备不存在")
        
    order_no = f"WO-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"
    cursor.execute(
        """INSERT INTO work_orders 
           (order_no, equipment_id, equipment_name, source, title, phenomenon, urgency, fault_photo_path, reporter_id, status)
           VALUES (?, ?, ?, 'MANUAL', ?, ?, ?, ?, ?, 'PENDING')""",
        (order_no, req.equipment_id, dev["equipment_name"], req.title.strip(), req.phenomenon or "", req.urgency or "NORMAL", req.fault_photo_path or "", current_user["id"])
    )
    order_id = cursor.lastrowid
    
    # 设备状态联动跃迁为 REPAIRING
    cursor.execute("UPDATE equipments SET status = 'REPAIRING' WHERE id = ?", (req.equipment_id,))
    db.commit()
    
    # 若设备指定了责任工程师，发送报修提醒邮件
    if dev["responsible_engineer_id"]:
        cursor.execute("SELECT email, full_name FROM users WHERE id = ?", (dev["responsible_engineer_id"],))
        eng = cursor.fetchone()
        if eng and eng["email"]:
            notify_work_order_assigned(eng["email"], eng["full_name"], order_no, dev["equipment_name"], req.title.strip(), req.urgency or "NORMAL")
            
    return get_work_order(order_id, db, current_user)

@router.put("/{order_id}", response_model=WorkOrderOut)
def update_work_order(
    order_id: int,
    req: WorkOrderUpdate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    工单纠错与修改接口：
    支持编辑填错的标题、故障现象、紧急程度、根因、步骤与备件
    """
    cursor = db.cursor()
    cursor.execute("SELECT id, status FROM work_orders WHERE id = ?", (order_id,))
    wo = cursor.fetchone()
    if not wo:
        raise HTTPException(status_code=404, detail="未找到该工单")
        
    updates = []
    params = []
    for field, val in req.model_dump(exclude_unset=True).items():
        if val is not None:
            updates.append(f"{field} = ?")
            params.append(val)
            
    if updates:
        params.append(order_id)
        cursor.execute(f"UPDATE work_orders SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()
        
    return get_work_order(order_id, db, current_user)

@router.put("/{order_id}/dispatch", response_model=WorkOrderOut)
def dispatch_work_order(
    order_id: int,
    req: WorkOrderDispatch,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    双轨工单调度：
    1. 工程师派单：可指派给任意技术员，触发邮件通知
    2. 技术员抢单：自主接单 (assignee_id 绑定自身)
    工单跃迁为 IN_PROGRESS (排故抢修中)
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT w.id, w.order_no, w.title, w.urgency, COALESCE(w.equipment_name, e.equipment_name) as eq_name
        FROM work_orders w
        LEFT JOIN equipments e ON w.equipment_id = e.id
        WHERE w.id = ?
    """, (order_id,))
    wo = cursor.fetchone()
    if not wo:
        raise HTTPException(status_code=404, detail="未找到该工单")
        
    assignee_id = req.assignee_id
    assigned_by_id = None
    if current_user["role"] in ("ADMIN", "ENGINEER"):
        assigned_by_id = current_user["id"]
        if not assignee_id:
            assignee_id = current_user["id"]
    else:
        # 技术员自主抢单
        assignee_id = current_user["id"]
        
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """UPDATE work_orders 
           SET status = 'IN_PROGRESS', assignee_id = ?, assigned_by_engineer_id = ?, claimed_at = ?
           WHERE id = ?""",
        (assignee_id, assigned_by_id, now_str, order_id)
    )
    db.commit()
    
    # 发送工单指派通知邮件给接单人
    if assignee_id:
        cursor.execute("SELECT email, full_name FROM users WHERE id = ?", (assignee_id,))
        tech = cursor.fetchone()
        if tech and tech["email"]:
            notify_work_order_assigned(tech["email"], tech["full_name"], wo["order_no"], wo["eq_name"] or "工厂设备", wo["title"], wo["urgency"])
            
    return get_work_order(order_id, db, current_user)

@router.put("/{order_id}/resolve", response_model=WorkOrderOut)
def resolve_work_order(
    order_id: int,
    req: WorkOrderResolve,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    维修复盘干货闭环（后来人经验核心）：
    强制必须填报【根本原因 (root_cause)】与【排除步骤 (solution_steps)】，支持上传【完工修复照片 (repair_photos)】！
    工单跃迁为 PENDING_CONFIRM (完工待验收)
    """
    if not req.root_cause or len(req.root_cause.strip()) < 2:
        raise HTTPException(status_code=422, detail="必须如实填报故障根本原因 (至少2个字符)，留给后来人查阅")
    if not req.solution_steps or len(req.solution_steps.strip()) < 2:
        raise HTTPException(status_code=422, detail="必须填报详细排除步骤 (至少2个字符)，留给后来人查阅")
        
    cursor = db.cursor()
    cursor.execute("SELECT id FROM work_orders WHERE id = ?", (order_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="未找到该工单")
        
    cursor.execute(
        """UPDATE work_orders 
           SET status = 'PENDING_CONFIRM', root_cause = ?, solution_steps = ?, spare_parts = ?,
               repair_duration_minutes = ?, repair_photos = ?
           WHERE id = ?""",
        (req.root_cause.strip(), req.solution_steps.strip(), req.spare_parts or "", req.repair_duration_minutes or 0, req.repair_photos or "", order_id)
    )
    db.commit()
    return get_work_order(order_id, db, current_user)

@router.put("/{order_id}/confirm", response_model=WorkOrderOut)
def confirm_and_close_work_order(
    order_id: int,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """
    主管工程师现场试车验收结案：
    工单状态跃迁为 CLOSED，设备主表状态自动恢复为 RUNNING (正常运行)
    """
    cursor = db.cursor()
    cursor.execute("SELECT id, equipment_id FROM work_orders WHERE id = ?", (order_id,))
    wo = cursor.fetchone()
    if not wo:
        raise HTTPException(status_code=404, detail="未找到该工单")
        
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE work_orders SET status = 'CLOSED', completed_at = ? WHERE id = ?", (now_str, order_id))
    # 联动恢复设备正常运行状态
    cursor.execute("UPDATE equipments SET status = 'RUNNING' WHERE id = ?", (wo["equipment_id"],))
    db.commit()
    return get_work_order(order_id, db, engineer)

@router.post("/{order_id}/to-knowledge")
def extract_to_knowledge(
    order_id: int,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """
    工程师专属：已结案工单人工审核标定并萃取至排故知识库
    需处于已闭环结案 (CLOSED) 状态，由工程师复核后点击确认沉淀入库
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM work_orders WHERE id = ?", (order_id,))
    wo = cursor.fetchone()
    if not wo:
        raise HTTPException(status_code=404, detail="未找到该工单")
        
    if wo["status"] != "CLOSED":
        raise HTTPException(status_code=400, detail="只有已闭环归档 (CLOSED) 的工单，才能标定萃取至知识库")
        
    cursor.execute("""
        SELECT e.equipment_name, e.factory, e.department, e.system_name
        FROM equipments e WHERE e.id = ?
    """, (wo["equipment_id"],))
    eq = cursor.fetchone()
    eq_name = eq["equipment_name"] if eq else (wo["equipment_name"] or "通用设备")
    
    title = f"[{eq_name}] {wo['title']} 排故方案"
    cursor.execute(
        """INSERT INTO knowledge_cases 
           (source_order_id, title, equipment_category, phenomenon, root_cause, solution_steps, tags, is_featured, created_by_engineer_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (
            order_id, title, "典型设备",
            wo["phenomenon"] or wo["title"],
            wo["root_cause"] or "未记录根因",
            wo["solution_steps"] or "未记录步骤",
            wo["spare_parts"] or "标准维修",
            engineer["id"]
        )
    )
    cursor.execute("UPDATE work_orders SET is_featured_case = 1 WHERE id = ?", (order_id,))
    db.commit()
    case_id = cursor.lastrowid
    return {"message": "成功审核并沉淀至全厂排故知识库", "case_id": case_id, "title": title}

@router.post("/upload-photo")
async def upload_work_order_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    现场拍照与本地图库单张照片上传接口：
    支持现场移动终端/手机拍照直传或本地相册图库导入。
    文件保存至 /data/uploads/repairs/ 目录，返回静态访问相对 URL。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择上传文件")
        
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".gif"}
    ext = Path(file.filename).suffix.lower()
    if not ext or ext not in allowed_exts:
        ext = ".jpg"
        
    repair_dir = settings.UPLOADS_DIR / "repairs"
    repair_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand_hex = secrets.token_hex(4)
    file_name = f"repair_{timestamp}_{rand_hex}{ext}"
    target_path = repair_dir / file_name
    
    # 限制上传大小 15MB
    max_size = 15 * 1024 * 1024
    size = 0
    with open(target_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_size:
                target_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="上传照片大小不能超过 15MB")
            buffer.write(chunk)
            
    url = f"/uploads/repairs/{file_name}"
    return {
        "url": url,
        "file_name": file_name,
        "size": size,
        "message": "照片上传成功"
    }

@router.post("/upload-photos")
async def upload_work_order_photos(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    批量照片上传接口：支持一次性导入多张本地照片
    """
    if not files:
        raise HTTPException(status_code=400, detail="未选择上传文件")
        
    repair_dir = settings.UPLOADS_DIR / "repairs"
    repair_dir.mkdir(parents=True, exist_ok=True)
    
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".gif"}
    uploaded = []
    
    for f in files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if not ext or ext not in allowed_exts:
            ext = ".jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rand_hex = secrets.token_hex(4)
        file_name = f"repair_{timestamp}_{rand_hex}{ext}"
        target_path = repair_dir / file_name
        
        with open(target_path, "wb") as buffer:
            while chunk := await f.read(1024 * 1024):
                buffer.write(chunk)
                
        uploaded.append(f"/uploads/repairs/{file_name}")
        
    return {
        "urls": uploaded,
        "count": len(uploaded),
        "message": f"成功上传 {len(uploaded)} 张照片"
    }


