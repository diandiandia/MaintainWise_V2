import sqlite3
import secrets
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.deps import get_current_user, require_engineer
from app.db.session import get_db
from app.schemas.equipment import (
    EquipmentCreate, EquipmentUpdate, EquipmentOut,
    HierarchyCreateRequest, HierarchyRenameRequest, HierarchyDeleteRequest, HierarchyDeletePreviewOut,
    RuntimeLogCreate, RuntimeLogOut
)
from app.schemas.knowledge import TimelineItem
from app.services.qr_service import generate_equipment_qr
from app.services.timeline_service import get_equipment_timeline

router = APIRouter()

def format_equipment_out(row: sqlite3.Row, db: Optional[sqlite3.Connection] = None) -> dict:
    if not row:
        return {}
    d = dict(row)
    interval = float(d.get("maintenance_interval_hours") or 500.0)
    total_hours = float(d.get("total_running_hours") or 0.0)
    last_maint = float(d.get("last_maintenance_hours") or 0.0)
    adv_warning = float(d.get("advance_warning_hours") or 20.0)
    running_mode = d.get("running_mode") or "CONTINUOUS"
    
    # 维护倒计时剩余小时数 = 设定维护周期 - (当前累计工时 - 上次保养时工时)
    countdown = round(interval - (total_hours - last_maint), 1)
    d["maintenance_interval_hours"] = interval
    d["last_maintenance_hours"] = last_maint
    d["advance_warning_hours"] = adv_warning
    d["running_mode"] = running_mode
    d["countdown_hours"] = countdown
    
    if countdown <= 0:
        d["countdown_status"] = "OVERDUE"   # 超期高危
    elif countdown <= adv_warning:
        d["countdown_status"] = "WARNING"   # 提前临期预警
    else:
        d["countdown_status"] = "HEALTHY"   # 运行正常
        
    # 计算近期日均开机工时及预计到期天数
    avg_daily = None
    est_days = None
    if running_mode == "INTERMITTENT":
        if db:
            cur = db.cursor()
            cur.execute("""
                SELECT SUM(delta_hours) as total_delta, COUNT(DISTINCT DATE(recorded_at)) as active_days
                FROM equipment_runtime_logs
                WHERE equipment_id = ? AND recorded_at >= DATETIME('now', '-14 days')
            """, (d.get("id"),))
            log_stat = cur.fetchone()
            if log_stat and log_stat["active_days"] and log_stat["active_days"] > 0:
                avg_daily = round(float(log_stat["total_delta"]) / float(log_stat["active_days"]), 1)
        if not avg_daily:
            avg_daily = 4.0  # 行业基准默认日均 4h
        if avg_daily > 0:
            est_days = round(max(0.0, countdown) / avg_daily, 1)
    else:
        avg_daily = 24.0
        est_days = round(max(0.0, countdown) / 24.0, 1)
        
    d["avg_daily_hours"] = avg_daily
    d["estimated_days_left"] = est_days
    return d

@router.get("", response_model=List[EquipmentOut])
def list_equipments(
    search: Optional[str] = None,
    factory: Optional[str] = None,
    department: Optional[str] = None,
    system_name: Optional[str] = None,
    status: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    设备列表查询接口：
    以【设备名称】为主进行全局模糊穿透检索，辅以工厂-部门-系统层级与运行状态钻取
    """
    cursor = db.cursor()
    query = "SELECT * FROM equipments WHERE is_deleted = 0"
    params = []
    
    if factory:
        query += " AND factory = ?"
        params.append(factory)
    if department:
        query += " AND department = ?"
        params.append(department)
    if system_name:
        query += " AND system_name = ?"
        params.append(system_name)
    if status:
        query += " AND status = ?"
        params.append(status)
        
    if search:
        # 现场维护以设备名称为主进行优先模糊检索
        kw = f"%{search.strip()}%"
        query += " AND (equipment_name LIKE ? OR model_spec LIKE ? OR equipment_code LIKE ?)"
        params.extend([kw, kw, kw])
        
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [format_equipment_out(r, db) for r in rows]

@router.get("/hierarchy-tree")
def get_hierarchy_tree(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取“工厂 - 部门 - 系统”三级层级树结构及各节点挂载设备数
    （聚合 equipments 设备表与 custom_hierarchies 自定义架构表）
    """
    cursor = db.cursor()
    
    # 1. 查询所有自定义或预置架构
    cursor.execute("""
        SELECT factory, department, system_name
        FROM custom_hierarchies
        ORDER BY factory, department, system_name
    """)
    ch_rows = cursor.fetchall()
    
    tree = {}
    for r in ch_rows:
        fac = r["factory"]
        dept = r["department"]
        sys = r["system_name"]
        if fac not in tree:
            tree[fac] = {"count": 0, "departments": {}}
        if dept not in tree[fac]["departments"]:
            tree[fac]["departments"][dept] = {"count": 0, "systems": {}}
        if sys not in tree[fac]["departments"][dept]["systems"]:
            tree[fac]["departments"][dept]["systems"][sys] = {"count": 0, "equipments": []}

    # 2. 统计各层级挂载的有效设备并获取设备列表
    cursor.execute("""
        SELECT id, factory, department, system_name, equipment_name, equipment_code, model_spec, status
        FROM equipments
        WHERE is_deleted = 0
        ORDER BY id DESC
    """)
    eq_rows = cursor.fetchall()
    
    for r in eq_rows:
        fac = r["factory"]
        dept = r["department"]
        sys = r["system_name"]
        
        if fac not in tree:
            tree[fac] = {"count": 0, "departments": {}}
        tree[fac]["count"] += 1
        
        if dept not in tree[fac]["departments"]:
            tree[fac]["departments"][dept] = {"count": 0, "systems": {}}
        tree[fac]["departments"][dept]["count"] += 1
        
        if sys not in tree[fac]["departments"][dept]["systems"]:
            tree[fac]["departments"][dept]["systems"][sys] = {"count": 0, "equipments": []}
            
        tree[fac]["departments"][dept]["systems"][sys]["count"] += 1
        tree[fac]["departments"][dept]["systems"][sys]["equipments"].append({
            "id": r["id"],
            "equipment_name": r["equipment_name"],
            "equipment_code": r["equipment_code"],
            "model_spec": r["model_spec"],
            "status": r["status"]
        })
        
    # 组装为 Element Plus el-tree 标准 JSON 结构 (工厂 - 部门 - 系统 - 设备)
    result = []
    for fac_name, fac_data in tree.items():
        dept_children = []
        for dept_name, dept_data in fac_data["departments"].items():
            sys_children = []
            for sys_name, sys_info in dept_data["systems"].items():
                sys_cnt = sys_info["count"]
                eq_list = sys_info["equipments"]
                
                eq_children = []
                for eq in eq_list:
                    eq_children.append({
                        "node_key": f"eq_{eq['id']}",
                        "id": eq["id"],
                        "label": f"📦 {eq['equipment_name']}",
                        "name": eq["equipment_name"],
                        "equipment_code": eq["equipment_code"],
                        "model_spec": eq["model_spec"],
                        "status": eq["status"],
                        "level": "equipment",
                        "factory": fac_name,
                        "department": dept_name,
                        "system_name": sys_name,
                        "count": 0
                    })
                
                sys_children.append({
                    "node_key": f"sys_{fac_name}_{dept_name}_{sys_name}",
                    "label": f"{sys_name} ({sys_cnt})",
                    "name": sys_name,
                    "level": "system_name",
                    "factory": fac_name,
                    "department": dept_name,
                    "system_name": sys_name,
                    "count": sys_cnt,
                    "children": eq_children
                })
            dept_children.append({
                "node_key": f"dept_{fac_name}_{dept_name}",
                "label": f"{dept_name} ({dept_data['count']})",
                "name": dept_name,
                "level": "department",
                "factory": fac_name,
                "department": dept_name,
                "count": dept_data["count"],
                "children": sys_children
            })
        result.append({
            "node_key": f"fac_{fac_name}",
            "label": f"{fac_name} ({fac_data['count']})",
            "name": fac_name,
            "level": "factory",
            "factory": fac_name,
            "count": fac_data["count"],
            "children": dept_children
        })
        
    return result

@router.post("/hierarchy")
def create_hierarchy(
    req: HierarchyCreateRequest,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """
    工程师主动创建“工厂 - 部门 - 系统”层级节点：
    支持在未录入具体设备前，预先规划或新建工厂、部门、系统架构
    """
    fac = req.factory.strip()
    dept = req.department.strip()
    sys = req.system_name.strip()
    if not fac or not dept or not sys:
        raise HTTPException(status_code=400, detail="工厂、部门和系统名称均不能为空")
        
    cursor = db.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO custom_hierarchies (factory, department, system_name)
        VALUES (?, ?, ?)
    """, (fac, dept, sys))
    db.commit()
    return {
        "message": f"成功创建架构层级：{fac} / {dept} / {sys}",
        "factory": fac,
        "department": dept,
        "system_name": sys
    }

@router.get("/hierarchy-options")
def get_hierarchy_options(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取全部已有工厂、部门、系统名称列表（供新建设备或新建层级下拉智能补全）
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT DISTINCT factory FROM (
            SELECT factory FROM equipments WHERE is_deleted = 0
            UNION
            SELECT factory FROM custom_hierarchies
        ) WHERE factory IS NOT NULL AND factory != '' ORDER BY factory
    """)
    factories = [r[0] for r in cursor.fetchall()]

    cursor.execute("""
        SELECT DISTINCT department FROM (
            SELECT department FROM equipments WHERE is_deleted = 0
            UNION
            SELECT department FROM custom_hierarchies
        ) WHERE department IS NOT NULL AND department != '' ORDER BY department
    """)
    departments = [r[0] for r in cursor.fetchall()]

    cursor.execute("""
        SELECT DISTINCT system_name FROM (
            SELECT system_name FROM equipments WHERE is_deleted = 0
            UNION
            SELECT system_name FROM custom_hierarchies
        ) WHERE system_name IS NOT NULL AND system_name != '' ORDER BY system_name
    """)
    systems = [r[0] for r in cursor.fetchall()]

    return {
        "factories": factories,
        "departments": departments,
        "systems": systems
    }

@router.post("/rename-hierarchy")
def rename_hierarchy(
    req: HierarchyRenameRequest,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """
    工厂/部门/系统层级多次任意重命名：
    在单个数据库原子事务中，批量同步更新关联设备及自定义架构表，历史维修病历完好保留
    """
    col_map = {
        "factory": "factory",
        "department": "department",
        "system_name": "system_name"
    }
    col = col_map[req.level]
    cursor = db.cursor()
    cursor.execute(
        f"UPDATE equipments SET {col} = ? WHERE {col} = ? AND is_deleted = 0",
        (req.new_name.strip(), req.old_name.strip())
    )
    affected = cursor.rowcount
    cursor.execute(
        f"UPDATE OR IGNORE custom_hierarchies SET {col} = ? WHERE {col} = ?",
        (req.new_name.strip(), req.old_name.strip())
    )
    cursor.execute(
        f"DELETE FROM custom_hierarchies WHERE {col} = ?",
        (req.old_name.strip(),)
    )
    db.commit()
    return {
        "message": f"层级重命名成功，已原子同步 {affected} 台从属设备",
        "level": req.level,
        "old_name": req.old_name,
        "new_name": req.new_name,
        "affected_count": affected
    }

@router.post("/delete-hierarchy-preview", response_model=HierarchyDeletePreviewOut)
def preview_delete_hierarchy(
    req: HierarchyDeleteRequest,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """
    层级删除前统计预检：
    汇总待删除层级从属的设备数、子系统数，以及将受到完整保护的历史工单与打卡记录数量
    """
    cursor = db.cursor()
    where_clauses = ["is_deleted = 0"]
    params = []
    
    if req.level == "factory":
        where_clauses.append("factory = ?")
        params.append(req.name.strip())
    elif req.level == "department":
        where_clauses.append("department = ?")
        params.append(req.name.strip())
        if req.factory:
            where_clauses.append("factory = ?")
            params.append(req.factory.strip())
    elif req.level == "system_name":
        where_clauses.append("system_name = ?")
        params.append(req.name.strip())
        if req.factory:
            where_clauses.append("factory = ?")
            params.append(req.factory.strip())
        if req.department:
            where_clauses.append("department = ?")
            params.append(req.department.strip())
            
    where_sql = " AND ".join(where_clauses)
    
    # 查找关联设备 ID
    cursor.execute(f"SELECT id, department, system_name FROM equipments WHERE {where_sql}", params)
    eq_rows = cursor.fetchall()
    eq_ids = [r["id"] for r in eq_rows]
    affected_eqs = len(eq_ids)
    affected_depts = len(set(r["department"] for r in eq_rows))
    affected_sys = len(set(r["system_name"] for r in eq_rows))
    
    retained_wos = 0
    retained_mnts = 0
    if eq_ids:
        placeholders = ",".join("?" * len(eq_ids))
        cursor.execute(f"SELECT COUNT(*) FROM work_orders WHERE equipment_id IN ({placeholders})", eq_ids)
        retained_wos = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM maintenance_records WHERE equipment_id IN ({placeholders})", eq_ids)
        retained_mnts = cursor.fetchone()[0]
        
    level_cn = {"factory": "工厂", "department": "车间部门", "system_name": "系统/工段"}.get(req.level, "层级")
    msg = (
        f"⚠️ 安全提示：确认删除{level_cn}【{req.name}】吗？"
        f"该操作将同步停用其下 {affected_eqs} 台设备（包含 {affected_sys} 个系统）。"
        f"系统已锁定其全部 {retained_wos} 张现场工单与 {retained_mnts} 条维保记录，历史数据 100% 完整保留！"
    )
    
    return {
        "level": req.level,
        "name": req.name,
        "affected_equipments": affected_eqs,
        "affected_systems": affected_sys,
        "affected_departments": affected_depts,
        "retained_work_orders": retained_wos,
        "retained_maintenance_records": retained_mnts,
        "warning_message": msg
    }

@router.post("/delete-hierarchy")
def delete_hierarchy(
    req: HierarchyDeleteRequest,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """
    层级级联软删除：
    在单个数据库事务中将对应工厂/部门/系统下的设备标记为 is_deleted = 1。
    【核心防丢失设计】：绝不执行物理 DELETE，所有历史维修工单与保养打卡记录历史快照完好留存！
    """
    cursor = db.cursor()
    where_clauses = ["is_deleted = 0"]
    params = []
    
    if req.level == "factory":
        where_clauses.append("factory = ?")
        params.append(req.name.strip())
    elif req.level == "department":
        where_clauses.append("department = ?")
        params.append(req.name.strip())
        if req.factory:
            where_clauses.append("factory = ?")
            params.append(req.factory.strip())
    elif req.level == "system_name":
        where_clauses.append("system_name = ?")
        params.append(req.name.strip())
        if req.factory:
            where_clauses.append("factory = ?")
            params.append(req.factory.strip())
        if req.department:
            where_clauses.append("department = ?")
            params.append(req.department.strip())
            
    where_sql = " AND ".join(where_clauses)
    cursor.execute(f"UPDATE equipments SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE {where_sql}", params)
    affected = cursor.rowcount

    # 同步从自定义架构表中移除
    if req.level == "factory":
        cursor.execute("DELETE FROM custom_hierarchies WHERE factory = ?", (req.name.strip(),))
    elif req.level == "department":
        if req.factory:
            cursor.execute("DELETE FROM custom_hierarchies WHERE factory = ? AND department = ?", (req.factory.strip(), req.name.strip()))
        else:
            cursor.execute("DELETE FROM custom_hierarchies WHERE department = ?", (req.name.strip(),))
    elif req.level == "system_name":
        del_wh = ["system_name = ?"]
        del_p = [req.name.strip()]
        if req.factory:
            del_wh.append("factory = ?")
            del_p.append(req.factory.strip())
        if req.department:
            del_wh.append("department = ?")
            del_p.append(req.department.strip())
        cursor.execute(f"DELETE FROM custom_hierarchies WHERE {' AND '.join(del_wh)}", del_p)

    db.commit()
    
    level_cn = {"factory": "工厂", "department": "车间部门", "system_name": "系统/工段"}.get(req.level, "层级")
    return {
        "message": f"成功删除{level_cn}【{req.name}】，已联动停用 {affected} 台从属设备，全部历史记录已安全归档留存！",
        "affected_count": affected
    }


@router.get("/{equipment_id}", response_model=EquipmentOut)
def get_equipment_detail(
    equipment_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取单台设备详情与维护倒计时指标"""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM equipments WHERE id = ? AND is_deleted = 0", (equipment_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="设备不存在或已被删除")
    return format_equipment_out(row, db)

@router.post("", response_model=EquipmentOut)
def create_equipment(
    req: EquipmentCreate,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """
    工程师专属：录入新设备 (零前置建树)
    强制项：设备名称、规格型号；
    扩展核心：设备编号、运行模式 (连续常开/间歇作业)、维护倒计时周期、提前预警工时
    """
    code = req.equipment_code.strip() if req.equipment_code else ""
    if not code:
        # 自动生成 DEV-YYYY-XXXX 规范设备编号
        code = f"DEV-{datetime.now().strftime('%Y')}-{secrets.randbelow(9000) + 1000}"
        
    initial_hours = float(req.initial_running_hours or 0.0)
    interval_hours = float(req.maintenance_interval_hours or 500.0)
    adv_warning_hours = float(req.advance_warning_hours or 20.0)
    last_maint_hours = float(req.last_maintenance_hours or 0.0)
    running_mode = req.running_mode or "CONTINUOUS"
    
    cursor = db.cursor()
    try:
        cursor.execute(
            """INSERT INTO equipments 
               (factory, department, system_name, equipment_name, model_spec, quantity, parameters,
                equipment_code, running_mode, maintenance_interval_hours, advance_warning_hours,
                last_maintenance_hours, total_running_hours, responsible_engineer_id, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                req.factory.strip(),
                req.department.strip(),
                req.system_name.strip(),
                req.equipment_name.strip(),
                req.model_spec.strip(),
                req.quantity if req.quantity is not None else 1,
                req.parameters or "",
                code,
                running_mode,
                interval_hours,
                adv_warning_hours,
                last_maint_hours,
                initial_hours,
                req.responsible_engineer_id or engineer["id"],
                req.status or "RUNNING"
            )
        )
        dev_id = cursor.lastrowid

        # 自动同步记录层级架构至 custom_hierarchies
        cursor.execute("""
            INSERT OR IGNORE INTO custom_hierarchies (factory, department, system_name)
            VALUES (?, ?, ?)
        """, (req.factory.strip(), req.department.strip(), req.system_name.strip()))
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail=f"设备编号 [{code}] 已存在，请使用其他编号")
    
    # 自动生成一机一码高清二维码
    qr_url = generate_equipment_qr(dev_id)
    cursor.execute("UPDATE equipments SET qr_code_url = ? WHERE id = ?", (qr_url, dev_id))
    db.commit()
    
    cursor.execute("SELECT * FROM equipments WHERE id = ?", (dev_id,))
    return format_equipment_out(cursor.fetchone(), db)

@router.put("/{equipment_id}", response_model=EquipmentOut)
def update_equipment(
    equipment_id: int,
    req: EquipmentUpdate,
    db: sqlite3.Connection = Depends(get_db),
    engineer: dict = Depends(require_engineer)
):
    """工程师专属：修改设备台账"""
    cursor = db.cursor()
    cursor.execute("SELECT id FROM equipments WHERE id = ? AND is_deleted = 0", (equipment_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="设备不存在或已被删除")
        
    updates = []
    params = []
    for field, val in req.model_dump(exclude_unset=True).items():
        if val is not None:
            updates.append(f"{field} = ?")
            params.append(val)
            
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(equipment_id)
        cursor.execute(f"UPDATE equipments SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()
        
    cursor.execute("SELECT * FROM equipments WHERE id = ?", (equipment_id,))
    return format_equipment_out(cursor.fetchone(), db)

@router.delete("/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """软删除设备"""
    cursor = db.cursor()
    cursor.execute("SELECT id, equipment_name FROM equipments WHERE id = ? AND is_deleted = 0", (equipment_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="未找到该设备或已被删除")
    cursor.execute("UPDATE equipments SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (equipment_id,))
    db.commit()
    return {"message": f"设备 [{row['equipment_name']}] 已成功移除"}

@router.post("/{equipment_id}/runtime-logs", response_model=RuntimeLogOut)
def log_runtime_hours(
    equipment_id: int,
    req: RuntimeLogCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    现场技术员/工程师录入工时：
    双模支持：
    1. 今日增量开机时长 (如 +4h)：适用于无数字表盘设备，直接累加本日工作小时；
    2. 表盘累计总读数 (如 186.5h)：适用于带小时计设备，系统自动推算较上次的差值增量。
    若达到或临近维护周期阈值，系统自动触发邮件推送责任工程师！
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT e.id, e.equipment_name, e.total_running_hours, e.maintenance_interval_hours,
               e.last_maintenance_hours, e.advance_warning_hours, e.running_mode,
               u.email as engineer_email, u.full_name as engineer_name
        FROM equipments e
        LEFT JOIN users u ON e.responsible_engineer_id = u.id
        WHERE e.id = ? AND e.is_deleted = 0
    """, (equipment_id,))
    dev = cursor.fetchone()
    if not dev:
        raise HTTPException(status_code=404, detail="未找到该设备")
        
    current_hours = float(dev["total_running_hours"] or 0.0)
    
    if req.delta_hours is not None and req.delta_hours >= 0:
        delta_hours = round(float(req.delta_hours), 2)
        new_total_hours = round(current_hours + delta_hours, 2)
        reading_hours = new_total_hours
    elif req.reading_hours is not None:
        reading_hours = round(float(req.reading_hours), 2)
        delta_hours = max(0.0, round(reading_hours - current_hours, 2))
        new_total_hours = reading_hours
    else:
        raise HTTPException(status_code=422, detail="请填写今日开机时长或表盘读数")
    
    # 写入工时抄表独立流水表
    cursor.execute(
        """INSERT INTO equipment_runtime_logs (equipment_id, recorded_by, reading_hours, delta_hours, remark)
           VALUES (?, ?, ?, ?, ?)""",
        (equipment_id, current_user["id"], reading_hours, delta_hours, req.remark or "")
    )
    # 同步更新设备总运行时间
    cursor.execute(
        "UPDATE equipments SET total_running_hours = ?, last_runtime_updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_total_hours, equipment_id)
    )
    db.commit()
    log_id = cursor.lastrowid
    
    # 临期预警校验与邮件推送
    interval = float(dev["maintenance_interval_hours"] or 500.0)
    last_maint = float(dev["last_maintenance_hours"] or 0.0)
    adv_warning = float(dev["advance_warning_hours"] or 20.0)
    rem_hours = round(interval - (new_total_hours - last_maint), 1)
    
    if rem_hours <= adv_warning and dev["engineer_email"]:
        from app.services.email_service import notify_maintenance_due
        # 计算近期日均估算
        cursor.execute("""
            SELECT SUM(delta_hours) as sum_h, COUNT(DISTINCT DATE(recorded_at)) as days
            FROM equipment_runtime_logs
            WHERE equipment_id = ? AND recorded_at >= DATETIME('now', '-14 days')
        """, (equipment_id,))
        s_row = cursor.fetchone()
        avg_d = round(float(s_row["sum_h"]) / float(s_row["days"]), 1) if (s_row and s_row["days"] and s_row["days"] > 0) else 4.0
        est_d = round(max(0.0, rem_hours) / avg_d, 1) if avg_d > 0 else None
        
        notify_maintenance_due(
            engineer_email=dev["engineer_email"],
            engineer_name=dev["engineer_name"] or "主管工程师",
            equipment_name=dev["equipment_name"],
            running_mode=dev["running_mode"] or "CONTINUOUS",
            remaining_hours=rem_hours,
            interval_hours=interval,
            est_days=est_d
        )
    
    cursor.execute("SELECT * FROM equipment_runtime_logs WHERE id = ?", (log_id,))
    return dict(cursor.fetchone())

@router.get("/{equipment_id}/runtime-logs", response_model=List[RuntimeLogOut])
def list_runtime_logs(
    equipment_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """查询设备历史运行工时抄表流水"""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM equipment_runtime_logs WHERE equipment_id = ? ORDER BY recorded_at DESC", (equipment_id,))
    return [dict(r) for r in cursor.fetchall()]

@router.get("/{equipment_id}/timeline")
def get_device_timeline(
    equipment_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    后来人第一性原理——终身电子维修病历档案：
    维修工单、维保打卡、工时抄表三流合一，按时间倒序全景展开
    """
    cursor = db.cursor()
    cursor.execute("SELECT id, equipment_name FROM equipments WHERE id = ?", (equipment_id,))
    dev = cursor.fetchone()
    if not dev:
        raise HTTPException(status_code=404, detail="未找到该设备")
        
    timeline = get_equipment_timeline(db, equipment_id)
    return {
        "equipment_id": equipment_id,
        "equipment_name": dev["equipment_name"],
        "timeline_items": timeline
    }
