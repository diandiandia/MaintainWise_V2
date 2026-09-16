import sqlite3
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.schemas.system import SystemSettingOut, SystemSettingUpdate, DashboardOut
from app.services.backup_service import execute_system_backup

router = APIRouter()

@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard_data(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    车间态势大盘与角色个性化待办接口：
    1. 汇总全厂设备四态运行指标
    2. 汇总突发维修工单四态流向
    3. 根据当前登录角色计算专属待办事项
    """
    cursor = db.cursor()
    
    # 1. 设备健康态势统计
    eq_stats = {"RUNNING": 0, "REPAIRING": 0, "MAINTAINING": 0, "STOPPED": 0}
    cursor.execute("SELECT status, COUNT(id) as cnt FROM equipments WHERE is_deleted = 0 GROUP BY status")
    for r in cursor.fetchall():
        if r["status"] in eq_stats:
            eq_stats[r["status"]] = r["cnt"]
    cursor.execute("SELECT COUNT(id) FROM equipments WHERE is_deleted = 0")
    total_eq = cursor.fetchone()[0]
    
    # 2. 工单四态流转统计
    wo_stats = {"PENDING": 0, "IN_PROGRESS": 0, "PENDING_CONFIRM": 0, "CLOSED": 0}
    cursor.execute("SELECT status, COUNT(id) as cnt FROM work_orders GROUP BY status")
    for r in cursor.fetchall():
        if r["status"] in wo_stats:
            wo_stats[r["status"]] = r["cnt"]
            
    # 3. 角色专属待办任务分发
    role = current_user["role"]
    todos = []
    
    if role == "TECHNICIAN":
        # 技术员待办：指派给自己的在修工单 + 到期维护任务
        cursor.execute("""
            SELECT id, order_no, title, urgency FROM work_orders 
            WHERE assignee_id = ? AND status = 'IN_PROGRESS' ORDER BY id DESC LIMIT 5
        """, (current_user["id"],))
        for r in cursor.fetchall():
            todos.append({
                "type": "WORK_ORDER",
                "title": f"抢修任务: {r['title']} ({r['order_no']})",
                "urgency": r["urgency"],
                "target_url": f"/workorders?id={r['id']}"
            })
    elif role == "ENGINEER":
        # 工程师待办：待派单工单 + 完工待验收工单
        cursor.execute("SELECT id, order_no, title, urgency FROM work_orders WHERE status = 'PENDING' ORDER BY id DESC LIMIT 5")
        for r in cursor.fetchall():
            todos.append({
                "type": "DISPATCH",
                "title": f"新报修待指派: {r['title']} ({r['order_no']})",
                "urgency": r["urgency"],
                "target_url": f"/workorders?id={r['id']}"
            })
        cursor.execute("SELECT id, order_no, title, urgency FROM work_orders WHERE status = 'PENDING_CONFIRM' ORDER BY id DESC LIMIT 5")
        for r in cursor.fetchall():
            todos.append({
                "type": "CONFIRM",
                "title": f"现场已修好待验收: {r['title']} ({r['order_no']})",
                "urgency": r["urgency"],
                "target_url": f"/workorders?id={r['id']}"
            })
    else:
        # 管理员：全厂异常关注
        if wo_stats["PENDING"] > 0:
            todos.append({
                "type": "NOTICE",
                "title": f"车间当前有 {wo_stats['PENDING']} 张突发报修工单等待工程师指派处理",
                "urgency": "MAJOR",
                "target_url": "/workorders"
            })
        if eq_stats["REPAIRING"] > 0:
            todos.append({
                "type": "NOTICE",
                "title": f"全厂有 {eq_stats['REPAIRING']} 台设备处于停机检修状态",
                "urgency": "CRITICAL",
                "target_url": "/equipments?status=REPAIRING"
            })

    # 4. 全厂设备维护倒计时分析 (周期工时预警与智能天数预估)
    cursor.execute("""
        SELECT id, equipment_name, equipment_code, factory, department, system_name,
               total_running_hours, maintenance_interval_hours, last_maintenance_hours,
               running_mode, advance_warning_hours
        FROM equipments WHERE is_deleted = 0
    """)
    all_eqs = cursor.fetchall()
    overdue_cnt = 0
    warning_cnt = 0
    healthy_cnt = 0
    urgent_countdown_items = []
    
    for r in all_eqs:
        interval = float(r["maintenance_interval_hours"] or 500.0)
        total_h = float(r["total_running_hours"] or 0.0)
        last_h = float(r["last_maintenance_hours"] or 0.0)
        adv_warning = float(r["advance_warning_hours"] or 20.0)
        running_mode = r["running_mode"] or "CONTINUOUS"
        used_h = round(total_h - last_h, 1)
        rem_h = round(interval - used_h, 1)
        
        # 计算近期日均开机工时及预计到期天数
        if running_mode == "INTERMITTENT":
            cursor.execute("""
                SELECT SUM(delta_hours) as sum_h, COUNT(DISTINCT DATE(recorded_at)) as days
                FROM equipment_runtime_logs
                WHERE equipment_id = ? AND recorded_at >= DATETIME('now', '-14 days')
            """, (r["id"],))
            s_row = cursor.fetchone()
            if s_row and s_row["days"] and s_row["days"] > 0:
                avg_daily = round(float(s_row["sum_h"]) / float(s_row["days"]), 1)
            else:
                avg_daily = 4.0  # 默认日均 4h
            est_days = round(max(0.0, rem_h) / avg_daily, 1) if avg_daily > 0 else None
        else:
            avg_daily = 24.0
            est_days = round(max(0.0, rem_h) / 24.0, 1)

        c_status = "HEALTHY"
        if rem_h <= 0:
            overdue_cnt += 1
            c_status = "OVERDUE"
        elif rem_h <= adv_warning:
            warning_cnt += 1
            c_status = "WARNING"
        else:
            healthy_cnt += 1
            
        urgent_countdown_items.append({
            "id": r["id"],
            "equipment_name": r["equipment_name"],
            "equipment_code": r["equipment_code"] or f"DEV-{r['id']}",
            "location": f"{r['factory']} / {r['department']} / {r['system_name']}",
            "countdown_hours": rem_h,
            "interval_hours": interval,
            "total_running_hours": total_h,
            "used_hours": used_h,
            "running_mode": running_mode,
            "advance_warning_hours": adv_warning,
            "avg_daily_hours": avg_daily,
            "estimated_days_left": est_days,
            "status": c_status
        })
        
    urgent_countdown_items.sort(key=lambda x: x["countdown_hours"])
    # 优先展示所有处于超期和临期预警状态的设备
    urgent_candidates = [x for x in urgent_countdown_items if x["status"] in ("OVERDUE", "WARNING")]
    if len(urgent_candidates) < 10:
        urgent_candidates.extend([x for x in urgent_countdown_items if x["status"] == "HEALTHY"][:10 - len(urgent_candidates)])
        
    countdown_stats = {
        "overdue_count": overdue_cnt,
        "warning_count": warning_cnt,
        "healthy_count": healthy_cnt,
        "urgent_items": urgent_candidates[:50]
    }
    
    # 将维护倒计时告警推送到待办提醒
    if overdue_cnt > 0:
        todos.insert(0, {
            "type": "COUNTDOWN",
            "title": f"🚨 维保倒计时超期告警: 车间有 {overdue_cnt} 台设备已超出维护工时周期，请尽快安排保养！",
            "urgency": "CRITICAL",
            "target_url": "/equipments"
        })
    elif warning_cnt > 0:
        todos.insert(0, {
            "type": "COUNTDOWN",
            "title": f"⏰ 维保临期预警: 车间有 {warning_cnt} 台设备即将到达维护工时（含间歇作业设备），请提前备件",
            "urgency": "MAJOR",
            "target_url": "/equipments"
        })
    # 5. 车间/部门问题分布统计与领导层综合 KPI (数据平台赋能)
    cursor.execute("""
        SELECT department,
               COUNT(id) as total_devs,
               SUM(CASE WHEN status = 'REPAIRING' THEN 1 ELSE 0 END) as repairing_devs,
               SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END) as running_devs
        FROM equipments WHERE is_deleted = 0
        GROUP BY department
    """)
    dept_stats = []
    for d in cursor.fetchall():
        dept_stats.append({
            "department": d["department"],
            "total_devs": d["total_devs"],
            "repairing_devs": d["repairing_devs"],
            "running_devs": d["running_devs"]
        })

    # 计算平均修复时长 MTTR (以已完成工单计算)
    cursor.execute("SELECT AVG(repair_duration_minutes) as avg_mttr, COUNT(id) as resolved_cnt FROM work_orders WHERE status IN ('PENDING_CONFIRM', 'CLOSED')")
    mttr_row = cursor.fetchone()
    avg_mttr = round(float(mttr_row["avg_mttr"] or 45.0), 1)

    # 计算巡检合规率
    cursor.execute("SELECT COUNT(id) as total_rec, SUM(CASE WHEN is_normal = 1 THEN 1 ELSE 0 END) as normal_rec FROM maintenance_records")
    rec_row = cursor.fetchone()
    total_rec = rec_row["total_rec"] or 0
    normal_rec = rec_row["normal_rec"] or 0
    inspection_pass_rate = round((normal_rec / total_rec * 100.0) if total_rec > 0 else 100.0, 1)

    avail_rate = round((eq_stats["RUNNING"] / total_eq * 100.0) if total_eq > 0 else 100.0, 1)

    executive_kpis = {
        "availability_rate": avail_rate,
        "avg_mttr_minutes": avg_mttr,
        "inspection_pass_rate": inspection_pass_rate,
        "total_inspections": total_rec,
        "pending_confirm_orders": wo_stats["PENDING_CONFIRM"],
        "urgent_orders": wo_stats["PENDING"] + wo_stats["IN_PROGRESS"]
    }

    return {
        "equipment_stats": eq_stats,
        "work_order_stats": wo_stats,
        "role_todos": todos,
        "total_equipments": total_eq,
        "countdown_stats": countdown_stats,
        "executive_kpis": executive_kpis,
        "department_issue_stats": dept_stats
    }

@router.get("/settings", response_model=SystemSettingOut)
def get_system_settings(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取系统定制参数"""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM system_settings WHERE id = 1")
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO system_settings (id, factory_name) VALUES (1, 'MaintainWise 智能工厂')")
        db.commit()
        cursor.execute("SELECT * FROM system_settings WHERE id = 1")
        row = cursor.fetchone()
    return dict(row)

@router.put("/settings", response_model=SystemSettingOut)
def update_system_settings(
    req: SystemSettingUpdate,
    db: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """管理员专属：保存系统全局定制标题与参数"""
    cursor = db.cursor()
    cursor.execute(
        """UPDATE system_settings 
           SET factory_name = ?, smtp_host = ?, smtp_port = ?, smtp_user = ?, smtp_pass = ?, smtp_enabled = ?, notify_lead_days = ?
           WHERE id = 1""",
        (
            req.factory_name.strip(), req.smtp_host or "", req.smtp_port or 465,
            req.smtp_user or "", req.smtp_pass or "", int(req.smtp_enabled or False),
            req.notify_lead_days or 3
        )
    )
    db.commit()
    cursor.execute("SELECT * FROM system_settings WHERE id = 1")
    return dict(cursor.fetchone())

@router.post("/smtp/test")
def test_smtp_endpoint(
    req: dict,
    admin: dict = Depends(require_admin)
):
    """管理员专属：在线测试 SMTP 邮件通信并发送探测邮件"""
    from app.services.email_service import test_smtp_connection
    res = test_smtp_connection(
        host=req.get("host", ""),
        port=int(req.get("port", 465)),
        user=req.get("user", ""),
        password=req.get("password", ""),
        to_email=req.get("to_email", admin.get("email", ""))
    )
    return res

@router.post("/backup")
def trigger_backup(
    admin: dict = Depends(require_admin)
):
    """
    管理员专属：一键执行全量数据热备份
    在线流式打包 SQLite 数据库与全部附件，生成标准 ZIP 归档包
    """
    res = execute_system_backup()
    return res

