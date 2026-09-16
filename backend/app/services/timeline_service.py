import json
import sqlite3
from typing import List, Dict, Any

def get_equipment_timeline(db: sqlite3.Connection, equipment_id: int) -> List[Dict[str, Any]]:
    """
    后来人第一性原理核心：将该设备一生的
    1. 维修工单 (含根本原因与排除步骤)
    2. 维护打卡 (含检查明细与工程师批注)
    3. 工时抄表 (含表盘读数与增量运转小时)
    三流合一，按事件时间戳全局倒序排序，输出连续的终身电子维修病历档案
    """
    cursor = db.cursor()
    timeline = []
    
    # 1. 提取突发维修工单
    cursor.execute("""
        SELECT w.id, w.order_no, w.title, w.phenomenon, w.urgency, w.status,
               w.root_cause, w.solution_steps, w.spare_parts, w.repair_duration_minutes,
               w.reported_at, w.completed_at, u.full_name as reporter_name,
               a.full_name as assignee_name
        FROM work_orders w
        LEFT JOIN users u ON w.reporter_id = u.id
        LEFT JOIN users a ON w.assignee_id = a.id
        WHERE w.equipment_id = ?
    """, (equipment_id,))
    
    for row in cursor.fetchall():
        r = dict(row)
        event_time = r["completed_at"] or r["reported_at"]
        timeline.append({
            "event_type": "WORK_ORDER",
            "event_time": str(event_time),
            "title": f"维修工单 [{r['order_no']}]: {r['title']}",
            "operator_id": 0,
            "operator_name": r["assignee_name"] or r["reporter_name"] or "维修人员",
            "details": {
                "order_no": r["order_no"],
                "urgency": r["urgency"],
                "status": r["status"],
                "phenomenon": r["phenomenon"],
                "root_cause": r["root_cause"],
                "solution_steps": r["solution_steps"],
                "spare_parts": r["spare_parts"],
                "duration_minutes": r["repair_duration_minutes"]
            }
        })
        
    # 2. 提取现场维保打卡记录
    cursor.execute("""
        SELECT m.id, m.record_no, m.status, m.is_normal, m.submitted_at,
               m.revision_reason, m.checklist_result_json, m.anomaly_desc,
               u.full_name as tech_name, eng.full_name as eng_name
        FROM maintenance_records m
        LEFT JOIN users u ON m.technician_id = u.id
        LEFT JOIN users eng ON m.revised_by_engineer_id = eng.id
        WHERE m.equipment_id = ?
    """, (equipment_id,))
    
    for row in cursor.fetchall():
        r = dict(row)
        try:
            checklist = json.loads(r["checklist_result_json"])
        except Exception:
            checklist = []
        event_time = r["submitted_at"] or "未记录时间"
        timeline.append({
            "event_type": "MAINTENANCE",
            "event_time": str(event_time),
            "title": f"维护单打卡 [{r['record_no']}] - {'全项正常' if r['is_normal'] else '发现异常'}",
            "operator_id": 0,
            "operator_name": r["tech_name"] or "维保技术员",
            "details": {
                "record_no": r["record_no"],
                "is_normal": bool(r["is_normal"]),
                "status": r["status"],
                "checklist": checklist,
                "anomaly_desc": r["anomaly_desc"],
                "revised_by_engineer": r["eng_name"],
                "revision_reason": r["revision_reason"]
            }
        })
        
    # 3. 提取设备运行工时抄表流水
    cursor.execute("""
        SELECT r.id, r.reading_hours, r.delta_hours, r.remark, r.recorded_at,
               u.full_name as recorder_name
        FROM equipment_runtime_logs r
        LEFT JOIN users u ON r.recorded_by = u.id
        WHERE r.equipment_id = ?
    """, (equipment_id,))
    
    for row in cursor.fetchall():
        r = dict(row)
        timeline.append({
            "event_type": "RUNTIME_LOG",
            "event_time": str(r["recorded_at"]),
            "title": f"运行工时抄表: 表盘 {r['reading_hours']}h (+{r['delta_hours']}h)",
            "operator_id": 0,
            "operator_name": r["recorder_name"] or "抄表人",
            "details": {
                "reading_hours": r["reading_hours"],
                "delta_hours": r["delta_hours"],
                "remark": r["remark"]
            }
        })
        
    # 4. 按事件时间严格倒序排列 (最新发生的排在最前)
    timeline.sort(key=lambda x: str(x["event_time"]), reverse=True)
    return timeline
