import json
from pathlib import Path
from app.db.session import get_db_connection
from app.core.security import hash_password

DDL_SCRIPT = """
-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(64) NOT NULL,
    employee_no VARCHAR(32) NOT NULL UNIQUE,
    role VARCHAR(16) NOT NULL CHECK(role IN ('ADMIN', 'ENGINEER', 'TECHNICIAN')),
    phone VARCHAR(32),
    email VARCHAR(64),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    must_change_password BOOLEAN NOT NULL DEFAULT 1,
    password_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_frozen BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 2. 设备主表
CREATE TABLE IF NOT EXISTS equipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factory VARCHAR(128) NOT NULL,
    department VARCHAR(128) NOT NULL,
    system_name VARCHAR(128) NOT NULL,
    equipment_name VARCHAR(128) NOT NULL,
    model_spec VARCHAR(128) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    parameters TEXT DEFAULT '',
    equipment_code VARCHAR(64) UNIQUE,
    responsible_engineer_id INTEGER REFERENCES users(id),
    status VARCHAR(16) NOT NULL DEFAULT 'RUNNING' CHECK(status IN ('RUNNING', 'REPAIRING', 'MAINTAINING', 'STOPPED')),
    running_mode VARCHAR(16) NOT NULL DEFAULT 'CONTINUOUS' CHECK(running_mode IN ('CONTINUOUS', 'INTERMITTENT')),
    total_running_hours REAL NOT NULL DEFAULT 0.0,
    maintenance_interval_hours REAL NOT NULL DEFAULT 500.0,
    advance_warning_hours REAL NOT NULL DEFAULT 20.0,
    last_maintenance_hours REAL NOT NULL DEFAULT 0.0,
    last_runtime_updated_at TIMESTAMP,
    qr_code_url VARCHAR(255),
    is_deleted BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_equipments_name ON equipments(equipment_name);
CREATE INDEX IF NOT EXISTS idx_equipments_hierarchy ON equipments(factory, department, system_name);
CREATE INDEX IF NOT EXISTS idx_equipments_status ON equipments(status);

-- 2.1 用户自定义工厂-部门-系统架构树
CREATE TABLE IF NOT EXISTS custom_hierarchies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factory VARCHAR(128) NOT NULL,
    department VARCHAR(128) NOT NULL,
    system_name VARCHAR(128) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(factory, department, system_name)
);
CREATE INDEX IF NOT EXISTS idx_custom_hierarchies_fac ON custom_hierarchies(factory, department, system_name);

-- 3. 设备运行工时流水表
CREATE TABLE IF NOT EXISTS equipment_runtime_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL REFERENCES equipments(id) ON DELETE CASCADE,
    recorded_by INTEGER NOT NULL REFERENCES users(id),
    reading_hours REAL NOT NULL,
    delta_hours REAL NOT NULL,
    remark TEXT DEFAULT '',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_runtime_eq_id ON equipment_runtime_logs(equipment_id);
CREATE INDEX IF NOT EXISTS idx_runtime_date ON equipment_runtime_logs(recorded_at);

-- 4. 设备保养计划表
CREATE TABLE IF NOT EXISTS maintenance_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL REFERENCES equipments(id) ON DELETE CASCADE,
    plan_name VARCHAR(128) NOT NULL,
    created_by_engineer_id INTEGER NOT NULL REFERENCES users(id),
    interval_days INTEGER NOT NULL DEFAULT 30,
    check_items_json TEXT NOT NULL,
    last_completed_date DATE,
    next_due_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mplan_next_due ON maintenance_plans(next_due_date);

-- 5. 维护单打卡记录表 (核心防篡改与历史快照留存)
CREATE TABLE IF NOT EXISTS maintenance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_no VARCHAR(64) NOT NULL UNIQUE,
    equipment_id INTEGER NOT NULL REFERENCES equipments(id) ON DELETE CASCADE,
    equipment_name VARCHAR(128) DEFAULT '',
    plan_id INTEGER REFERENCES maintenance_plans(id),
    technician_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT', 'SUBMITTED', 'REVISED_BY_ENGINEER')),
    is_locked_for_tech BOOLEAN NOT NULL DEFAULT 0,
    submitted_at TIMESTAMP,
    revised_by_engineer_id INTEGER REFERENCES users(id),
    revised_at TIMESTAMP,
    revision_reason TEXT DEFAULT '',
    is_normal BOOLEAN NOT NULL DEFAULT 1,
    checklist_result_json TEXT NOT NULL,
    anomaly_desc TEXT DEFAULT '',
    interlocked_work_order_id INTEGER REFERENCES work_orders(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mrecord_eq ON maintenance_records(equipment_id);
CREATE INDEX IF NOT EXISTS idx_mrecord_lock ON maintenance_records(is_locked_for_tech);

-- 6. 现场维护工单全流程表 (故障现场与修复复盘留存)
CREATE TABLE IF NOT EXISTS work_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no VARCHAR(64) NOT NULL UNIQUE,
    equipment_id INTEGER NOT NULL REFERENCES equipments(id) ON DELETE CASCADE,
    equipment_name VARCHAR(128) DEFAULT '',
    source VARCHAR(16) NOT NULL DEFAULT 'MANUAL' CHECK(source IN ('MANUAL', 'INSPECTION')),
    title VARCHAR(128) NOT NULL,
    phenomenon TEXT DEFAULT '',
    urgency VARCHAR(16) NOT NULL DEFAULT 'NORMAL' CHECK(urgency IN ('NORMAL', 'MAJOR', 'CRITICAL')),
    fault_photo_path VARCHAR(255),
    repair_photos TEXT DEFAULT '',
    reporter_id INTEGER NOT NULL REFERENCES users(id),
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'IN_PROGRESS', 'PENDING_CONFIRM', 'CLOSED')),
    assigned_by_engineer_id INTEGER REFERENCES users(id),
    assignee_id INTEGER REFERENCES users(id),
    claimed_at TIMESTAMP,
    root_cause TEXT DEFAULT '',
    solution_steps TEXT DEFAULT '',
    spare_parts TEXT DEFAULT '',
    repair_duration_minutes INTEGER DEFAULT 0,
    completed_at TIMESTAMP,
    is_featured_case BOOLEAN NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_wo_eq ON work_orders(equipment_id);
CREATE INDEX IF NOT EXISTS idx_wo_status ON work_orders(status);

-- 7. 排故知识库案例表
CREATE TABLE IF NOT EXISTS knowledge_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_order_id INTEGER REFERENCES work_orders(id),
    title VARCHAR(128) NOT NULL,
    equipment_category VARCHAR(64) DEFAULT '通用',
    phenomenon TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    solution_steps TEXT NOT NULL,
    tags VARCHAR(128) DEFAULT '',
    is_featured BOOLEAN NOT NULL DEFAULT 0,
    created_by_engineer_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_cases(equipment_category);
CREATE INDEX IF NOT EXISTS idx_kb_featured ON knowledge_cases(is_featured);

-- 8. 系统参数配置表
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    factory_name VARCHAR(128) NOT NULL DEFAULT 'MaintainWise 智能工厂',
    smtp_host VARCHAR(128) DEFAULT '',
    smtp_port INTEGER DEFAULT 465,
    smtp_user VARCHAR(64) DEFAULT '',
    smtp_pass VARCHAR(64) DEFAULT '',
    smtp_enabled BOOLEAN DEFAULT 0,
    notify_lead_days INTEGER DEFAULT 3
);
"""

def init_db():
    """初始化数据库表结构并写入演示种子数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript(DDL_SCRIPT)

    # 动态平滑迁移：为既有数据库补全字段
    migrations = [
        ("equipments", "maintenance_interval_hours", "REAL NOT NULL DEFAULT 500.0"),
        ("equipments", "last_maintenance_hours", "REAL NOT NULL DEFAULT 0.0"),
        ("equipments", "running_mode", "VARCHAR(16) NOT NULL DEFAULT 'CONTINUOUS'"),
        ("equipments", "advance_warning_hours", "REAL NOT NULL DEFAULT 20.0"),
        ("users", "must_change_password", "BOOLEAN NOT NULL DEFAULT 1"),
        ("users", "password_changed_at", "TIMESTAMP"),
        ("users", "is_frozen", "BOOLEAN NOT NULL DEFAULT 0"),
        ("work_orders", "repair_photos", "TEXT DEFAULT ''"),
        ("work_orders", "equipment_name", "VARCHAR(128) DEFAULT ''"),
        ("maintenance_records", "equipment_name", "VARCHAR(128) DEFAULT ''"),
    ]
    for table, col, dtype in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {dtype}")
        except Exception:
            pass
    try:
        cursor.execute("UPDATE users SET password_changed_at = created_at WHERE password_changed_at IS NULL")
    except Exception:
        pass
    conn.commit()
    
    # 1. 注入默认系统配置
    cursor.execute("SELECT id FROM system_settings WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO system_settings (id, factory_name) VALUES (1, 'MaintainWise 智能工厂')")
    
    # 2. 注入三角色演示账号 (密码统一: password123)
    hashed_pwd = hash_password("password123")
    demo_users = [
        ("admin", hashed_pwd, "系统管理员", "EMP001", "ADMIN", "13800000001", "admin@factory.com"),
        ("engineer1", hashed_pwd, "张工 (主管工程师)", "EMP002", "ENGINEER", "13800000002", "engineer1@factory.com"),
        ("tech1", hashed_pwd, "李师傅 (维保技术员)", "EMP003", "TECHNICIAN", "13800000003", "tech1@factory.com")
    ]
    for u in demo_users:
        cursor.execute("SELECT id FROM users WHERE username = ?", (u[0],))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, password_hash, full_name, employee_no, role, phone, email) VALUES (?, ?, ?, ?, ?, ?, ?)",
                u
            )
            
    # 3. 注入演示设备数据
    cursor.execute("SELECT COUNT(*) FROM equipments WHERE is_deleted = 0")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("SELECT id FROM users WHERE username = 'engineer1'")
        eng = cursor.fetchone()
        eng_id = eng[0] if eng else 1
        
        demo_eqs = [
            ("总厂", "动力车间", "通风系统", "1# 离心排风机", "F-4-72-8C", 1, "功率: 18.5kW, 风量: 15000m3/h", "DEV-2026-F01", eng_id, "RUNNING", 120.0, 500.0, 0.0, "/uploads/qrcodes/qr_dev_1.png"),
            ("总厂", "动力车间", "供水系统", "2# 冷却水循环泵", "IS100-80-160", 2, "扬程: 32m, 流量: 100m3/h", "DEV-2026-P02", eng_id, "RUNNING", 340.5, 360.0, 0.0, "/uploads/qrcodes/qr_dev_2.png"),
            ("第一分厂", "注塑车间", "主成型线", "3# 精密注塑机主电机", "YE3-225M-4", 1, "功率: 45kW, 额定转速: 1480rpm", "DEV-2026-M03", eng_id, "RUNNING", 850.0, 800.0, 0.0, "/uploads/qrcodes/qr_dev_3.png")
        ]
        for eq in demo_eqs:
            cursor.execute(
                """INSERT INTO equipments 
                   (factory, department, system_name, equipment_name, model_spec, quantity, parameters, equipment_code, responsible_engineer_id, status, total_running_hours, maintenance_interval_hours, last_maintenance_hours, qr_code_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                eq
            )
            
        # 4. 注入 1# 离心排风机 保养计划
        check_items = [
            {"item": "检查电机轴承润滑脂情况", "standard": "脂量充足无积碳硬化"},
            {"item": "检查三角传动皮带张紧度", "standard": "按压下陷 10-15mm 无龟裂"},
            {"item": "测量设备运行震动与温升", "standard": "轴承温度 <= 70℃，震动正常"}
        ]
        cursor.execute(
            """INSERT INTO maintenance_plans 
               (equipment_id, plan_name, created_by_engineer_id, interval_days, check_items_json, next_due_date)
               VALUES (1, '离心排风机月度常规维保标准', ?, 30, ?, DATE('now', '+15 days'))""",
            (eng_id, json.dumps(check_items, ensure_ascii=False))
        )
        
        # 5. 注入排故知识库初始典型案例
        cursor.execute(
            """INSERT INTO knowledge_cases
               (title, equipment_category, phenomenon, root_cause, solution_steps, tags, is_featured, created_by_engineer_id)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                "变频主电机启动跳闸报过流(OC)经典排除方案",
                "电机",
                "变频器上电启动瞬间报警 OC (Over Current)，电机发出轻微蜂鸣声无法旋转",
                "电机接线盒内接线端子受潮积水导致相间阻抗下降微短路，驱动模块瞬间过流自保",
                "1. 断开总电源切断进线空气开关；\n2. 拆卸电机接线盒，用兆欧表测量相间及对地绝缘电阻；\n3. 用工业热风枪烘干端子排受潮水汽；\n4. 更换接线盒密封胶圈并复位变频器报警参数；\n5. 空载点动试车正常后合闸带载运行。",
                "变频器,过流,绝缘,短路",
                eng_id
            )
        )
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("MaintainWise 2.0 数据库与种子数据初始化成功！")
