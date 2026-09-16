import json
import secrets
import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.deps import get_current_user, require_engineer
from app.db.session import get_db
from app.schemas.maintenance import (
    MaintenancePlanCreate, MaintenancePlanOut,
    MaintenanceRecordSubmit, MaintenanceRecordRevise, MaintenanceRecordOut
)

from app.services.email_service import notify_maintenance_anomaly

router = APIRouter()

@router.get("/plans", response_model=List[MaintenancePlanOut])
def list_maintenance_plans(
    equipment_id: Optional[int] = None,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """查询设备保养计划"""
    cursor = db.cursor()
    query = "SELECT * FROM maintenance_plans WHERE is_active = 1"
    params = []
    if equipment_id:
        query += " AND equipment_id = ?"
        params.append(equipment_id)
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]

@router.post("/plans", response_model=MaintenancePlanOut)
def create_maintenance_plan(
    req: MaintenancePlanCreate,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """工程师专属：编制并下发保养计划"""
    cursor = db.cursor()
    cursor.execute("SELECT id FROM equipments WHERE id = ? AND is_deleted = 0", (req.equipment_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="关联设备不存在")
        
    next_due = (date.today() + timedelta(days=req.interval_days or 30)).isoformat()
    check_items_json = json.dumps([item.model_dump() for item in req.check_items], ensure_ascii=False)
    
    cursor.execute(
        """INSERT INTO maintenance_plans 
           (equipment_id, plan_name, created_by_engineer_id, interval_days, check_items_json, next_due_date, is_active)
           VALUES (?, ?, ?, ?, ?, ?, 1)""",
        (req.equipment_id, req.plan_name.strip(), engineer["id"], req.interval_days or 30, check_items_json, next_due)
    )
    db.commit()
    plan_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM maintenance_plans WHERE id = ?", (plan_id,))
    return dict(cursor.fetchone())

@router.get("/records", response_model=List[MaintenanceRecordOut])
def list_maintenance_records(
    equipment_id: Optional[int] = None,
    is_normal: Optional[bool] = None,
    status: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """查询维保打卡记录列表 (支持已软删除设备历史溯源)"""
    cursor = db.cursor()
    query = """
        SELECT m.*, COALESCE(NULLIF(m.equipment_name, ''), e.equipment_name, '已归档设备') as equipment_name,
               u.full_name as technician_name, eng.full_name as revised_by_name
        FROM maintenance_records m
        LEFT JOIN equipments e ON m.equipment_id = e.id
        LEFT JOIN users u ON m.technician_id = u.id
        LEFT JOIN users eng ON m.revised_by_engineer_id = eng.id
        WHERE 1=1
    """
    params = []
    if equipment_id:
        query += " AND m.equipment_id = ?"
        params.append(equipment_id)
    if is_normal is not None:
        query += " AND m.is_normal = ?"
        params.append(int(is_normal))
    if status:
        query += " AND m.status = ?"
        params.append(status)
        
    query += " ORDER BY m.id DESC"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]

@router.get("/records/{record_id}", response_model=MaintenanceRecordOut)
def get_maintenance_record(
    record_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取单张维护单打卡详情"""
    cursor = db.cursor()
    cursor.execute("""
        SELECT m.*, COALESCE(NULLIF(m.equipment_name, ''), e.equipment_name, '已归档设备') as equipment_name,
               u.full_name as technician_name, eng.full_name as revised_by_name
        FROM maintenance_records m
        LEFT JOIN equipments e ON m.equipment_id = e.id
        LEFT JOIN users u ON m.technician_id = u.id
        LEFT JOIN users eng ON m.revised_by_engineer_id = eng.id
        WHERE m.id = ?
    """, (record_id,))
    rec = cursor.fetchone()
    if not rec:
        raise HTTPException(status_code=404, detail="未找到该维护单记录")
    return dict(rec)

@router.post("/records/submit", response_model=MaintenanceRecordOut)
def submit_maintenance_record(
    req: MaintenanceRecordSubmit,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    技术员现场巡检打卡上传并锁定（核心防篡改机制）：
    1. 上传后立即置 is_locked_for_tech = 1，技术员严禁私自修改；
    2. 若发现异常 (is_normal=false)，在同一事务中联锁派发维修工单，设备状态置为 REPAIRING；
    3. 异常时自动发送告警邮件通知设备责任工程师！
    """
    cursor = db.cursor()
    cursor.execute("SELECT id, equipment_name, factory, department, system_name, responsible_engineer_id FROM equipments WHERE id = ? AND is_deleted = 0", (req.equipment_id,))
    dev = cursor.fetchone()
    if not dev:
        raise HTTPException(status_code=404, detail="设备不存在")
        
    record_no = f"MNT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"
    checklist_json = json.dumps([item.model_dump() for item in req.checklist_results], ensure_ascii=False)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    interlocked_wo_id = None
    # 若存在异常，联锁派生创建维修工单
    if not req.is_normal:
        wo_order_no = f"WO-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"
        title = f"巡检异常隐患: {dev['equipment_name']}"
        desc = req.anomaly_desc or "技术员现场巡检打卡发现设备部件异常"
        cursor.execute(
            """INSERT INTO work_orders 
               (order_no, equipment_id, equipment_name, source, title, phenomenon, urgency, reporter_id, status)
               VALUES (?, ?, ?, 'INSPECTION', ?, ?, 'MAJOR', ?, 'PENDING')""",
            (wo_order_no, req.equipment_id, dev["equipment_name"], title, desc, current_user["id"])
        )
        interlocked_wo_id = cursor.lastrowid
        # 设备状态跃迁为维修中
        cursor.execute("UPDATE equipments SET status = 'REPAIRING' WHERE id = ?", (req.equipment_id,))
        
    # 写入维护单记录，上传即锁定，保存设备名称快照
    cursor.execute(
        """INSERT INTO maintenance_records 
           (record_no, equipment_id, equipment_name, plan_id, technician_id, status, is_locked_for_tech, submitted_at, is_normal, checklist_result_json, anomaly_desc, interlocked_work_order_id)
           VALUES (?, ?, ?, ?, ?, 'SUBMITTED', 1, ?, ?, ?, ?, ?)""",
        (
            record_no, req.equipment_id, dev["equipment_name"], req.plan_id, current_user["id"],
            now_str, int(req.is_normal), checklist_json, req.anomaly_desc or "", interlocked_wo_id
        )
    )
    record_id = cursor.lastrowid
    
    # 若现场巡检打卡顺便填报了今日开机工时
    if req.log_runtime_hours and req.log_runtime_hours > 0:
        cursor.execute("SELECT total_running_hours FROM equipments WHERE id = ?", (req.equipment_id,))
        cur_h_row = cursor.fetchone()
        cur_h = float(cur_h_row["total_running_hours"] if cur_h_row else 0.0)
        delta_h = round(float(req.log_runtime_hours), 2)
        new_tot = round(cur_h + delta_h, 2)
        cursor.execute(
            """INSERT INTO equipment_runtime_logs (equipment_id, recorded_by, reading_hours, delta_hours, remark)
               VALUES (?, ?, ?, ?, ?)""",
            (req.equipment_id, current_user["id"], new_tot, delta_h, f"巡检维保打卡({record_no})同步填报开机工时")
        )
        cursor.execute("UPDATE equipments SET total_running_hours = ?, last_runtime_updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_tot, req.equipment_id))

    # 若本次维保正常完成，将设备的“上次维护工时”同步为当前“累计运行工时”，重置倒计时周期
    if req.is_normal:
        cursor.execute("UPDATE equipments SET last_maintenance_hours = total_running_hours WHERE id = ?", (req.equipment_id,))

    # 若关联了保养计划，更新下次保养时间
    if req.plan_id:
        cursor.execute("SELECT interval_days FROM maintenance_plans WHERE id = ?", (req.plan_id,))
        plan = cursor.fetchone()
        if plan:
            interval = plan["interval_days"] or 30
            next_date = (date.today() + timedelta(days=interval)).isoformat()
            cursor.execute(
                "UPDATE maintenance_plans SET last_completed_date = ?, next_due_date = ? WHERE id = ?",
                (date.today().isoformat(), next_date, req.plan_id)
            )
            
    db.commit()
    
    # 维保异常邮件告警
    if not req.is_normal and dev["responsible_engineer_id"]:
        cursor.execute("SELECT email, full_name FROM users WHERE id = ?", (dev["responsible_engineer_id"],))
        eng = cursor.fetchone()
        if eng and eng["email"]:
            notify_maintenance_anomaly(eng["email"], eng["full_name"], dev["equipment_name"], req.anomaly_desc or "现场巡检核验项异常", record_no)

    
    cursor.execute("""
        SELECT m.*, e.equipment_name, u.full_name as technician_name, eng.full_name as revised_by_name
        FROM maintenance_records m
        LEFT JOIN equipments e ON m.equipment_id = e.id
        LEFT JOIN users u ON m.technician_id = u.id
        LEFT JOIN users eng ON m.revised_by_engineer_id = eng.id
        WHERE m.id = ?
    """, (record_id,))
    return dict(cursor.fetchone())

@router.put("/records/{record_id}/revise", response_model=MaintenanceRecordOut)
def engineer_revise_record(
    record_id: int,
    req: MaintenanceRecordRevise,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """
    主管工程师专属：审核修正维护单（必须填写修改理由留痕）
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM maintenance_records WHERE id = ?", (record_id,))
    rec = cursor.fetchone()
    if not rec:
        raise HTTPException(status_code=404, detail="未找到该维护单记录")
        
    if not req.revision_reason or len(req.revision_reason.strip()) < 2:
        raise HTTPException(status_code=422, detail="工程师修正维护单必须填写修改原因与复核批注 (至少2个字符)")
        
    updates = [
        "revised_by_engineer_id = ?",
        "revised_at = CURRENT_TIMESTAMP",
        "revision_reason = ?",
        "status = 'REVISED_BY_ENGINEER'"
    ]
    params = [engineer["id"], req.revision_reason.strip()]
    
    if req.checklist_results is not None:
        updates.append("checklist_result_json = ?")
        params.append(json.dumps([item.model_dump() for item in req.checklist_results], ensure_ascii=False))
    if req.is_normal is not None:
        updates.append("is_normal = ?")
        params.append(int(req.is_normal))
    if req.anomaly_desc is not None:
        updates.append("anomaly_desc = ?")
        params.append(req.anomaly_desc)
        
    params.append(record_id)
    cursor.execute(f"UPDATE maintenance_records SET {', '.join(updates)} WHERE id = ?", params)
    db.commit()
    
    cursor.execute("""
        SELECT m.*, e.equipment_name, u.full_name as technician_name, eng.full_name as revised_by_name
        FROM maintenance_records m
        LEFT JOIN equipments e ON m.equipment_id = e.id
        LEFT JOIN users u ON m.technician_id = u.id
        LEFT JOIN users eng ON m.revised_by_engineer_id = eng.id
        WHERE m.id = ?
    """, (record_id,))
    return dict(cursor.fetchone())

@router.put("/records/{record_id}", response_model=MaintenanceRecordOut)
def update_maintenance_record(
    record_id: int,
    req: MaintenanceRecordSubmit,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    通用维护单修改接口：
    硬拦截守卫：若单据已被锁定且当前用户为技术员，强行返回 HTTP 403 Forbidden 杜绝篡改！
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM maintenance_records WHERE id = ?", (record_id,))
    rec = cursor.fetchone()
    if not rec:
        raise HTTPException(status_code=404, detail="未找到该维护单记录")
        
    # 核心防篡改拦截
    if rec["is_locked_for_tech"] and current_user["role"] == "TECHNICIAN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="维护单已提交上传并锁定，现场技术员严禁私自修改！如需更正请联系工程师审核修正。"
        )
        
    checklist_json = json.dumps([item.model_dump() for item in req.checklist_results], ensure_ascii=False)
    cursor.execute(
        """UPDATE maintenance_records 
           SET checklist_result_json = ?, is_normal = ?, anomaly_desc = ?
           WHERE id = ?""",
        (checklist_json, int(req.is_normal), req.anomaly_desc or "", record_id)
    )
    db.commit()
    
    cursor.execute("""
        SELECT m.*, e.equipment_name, u.full_name as technician_name, eng.full_name as revised_by_name
        FROM maintenance_records m
        LEFT JOIN equipments e ON m.equipment_id = e.id
        LEFT JOIN users u ON m.technician_id = u.id
        LEFT JOIN users eng ON m.revised_by_engineer_id = eng.id
        WHERE m.id = ?
    """, (record_id,))
    return dict(cursor.fetchone())
