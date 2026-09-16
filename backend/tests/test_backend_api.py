import os
import secrets
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_token(username: str = "admin", password: str = "password123") -> str:
    res = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]

def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}

# ==========================================
# 1. 用户认证与三角色权限矩阵测试 (SWR-USR-*)
# ==========================================
def test_login_and_roles():
    # 测试错误密码
    bad_res = client.post("/api/v1/auth/login", data={"username": "admin", "password": "wrongpassword"})
    assert bad_res.status_code == 400
    assert "用户名或密码错误" in bad_res.json()["detail"]

    # 测试管理员登录与资料获取
    admin_token = get_token("admin", "password123")
    me_res = client.get("/api/v1/auth/me", headers=auth_header(admin_token))
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "ADMIN"
    assert me_res.json()["username"] == "admin"

    # 测试工程师登录
    eng_token = get_token("engineer1", "password123")
    me_eng = client.get("/api/v1/auth/me", headers=auth_header(eng_token))
    assert me_eng.status_code == 200
    assert me_eng.json()["role"] == "ENGINEER"

    # 测试技术员登录
    tech_token = get_token("tech1", "password123")
    me_tech = client.get("/api/v1/auth/me", headers=auth_header(tech_token))
    assert me_tech.status_code == 200
    assert me_tech.json()["role"] == "TECHNICIAN"

    # 权限硬隔离拦截测试: 技术员访问管理员专属人员列表 -> 403
    tech_access = client.get("/api/v1/users", headers=auth_header(tech_token))
    assert tech_access.status_code == 403
    assert "仅限系统管理员" in tech_access.json()["detail"]

    # 工程师访问人员列表 -> 403
    eng_access = client.get("/api/v1/users", headers=auth_header(eng_token))
    assert eng_access.status_code == 403

def test_user_management_and_password_reset():
    admin_token = get_token("admin", "password123")
    
    # 管理员创建新人员 (使用随机工号与用户名保证测试幂等)
    rand_suffix = secrets.token_hex(3)
    username = f"tech_{rand_suffix}"
    new_user_data = {
        "username": username,
        "password": "techpassword123",
        "full_name": "王测试技术员",
        "employee_no": f"EMP_{rand_suffix}",
        "role": "TECHNICIAN",
        "phone": "13911112222",
        "email": "wang@test.com"
    }
    create_res = client.post("/api/v1/users", json=new_user_data, headers=auth_header(admin_token))
    assert create_res.status_code == 200
    uid = create_res.json()["id"]

    # 管理员一键重置密码
    reset_res = client.put(f"/api/v1/users/{uid}/reset-password", json={"new_password": "newpassword888"}, headers=auth_header(admin_token))
    assert reset_res.status_code == 200
    assert "重置成功" in reset_res.json()["message"]

    # 使用新密码登录
    new_token = get_token(username, "newpassword888")
    assert new_token is not None

    # SWR-USR-005: 测试管理员软删除人员 (is_active = 0)
    del_res = client.delete(f"/api/v1/users/{uid}", headers=auth_header(admin_token))
    assert del_res.status_code == 200
    # 停用后尝试登录应被拦截 403
    disabled_res = client.post("/api/v1/auth/login", data={"username": username, "password": "newpassword888"})
    assert disabled_res.status_code == 403
    assert "该账号已被停用" in disabled_res.json()["detail"]

# ==========================================
# 2. 设备资产、层级与重命名测试 (SWR-DEV-*)
# ==========================================
def test_equipments_and_hierarchy_management():
    eng_token = get_token("engineer1", "password123")
    tech_token = get_token("tech1", "password123")

    # 技术员无权录入设备 -> 403
    forbidden_create = client.post(
        "/api/v1/equipments",
        json={"factory": "二厂", "department": "车间", "system_name": "产线", "equipment_name": "非法设备", "model_spec": "M1"},
        headers=auth_header(tech_token)
    )
    assert forbidden_create.status_code == 403

    # 工程师录入设备：测试设备编码未填自动生成、数量缺省为1
    create_payload = {
        "factory": "新能源分厂",
        "department": "电极车间",
        "system_name": "涂布烘干线",
        "equipment_name": "超高速双层涂布机",
        "model_spec": "TB-650-2026",
        "parameters": "最高车速: 80m/min, 宽幅: 650mm"
    }
    res = client.post("/api/v1/equipments", json=create_payload, headers=auth_header(eng_token))
    assert res.status_code == 200
    dev = res.json()
    dev_id = dev["id"]
    assert dev["equipment_name"] == "超高速双层涂布机"
    assert dev["quantity"] == 1  # 缺省为 1
    assert dev["equipment_code"].startswith("DEV-")  # 自动生成内部编码
    assert dev["maintenance_interval_hours"] == 500.0  # 默认周期 500 小时
    assert dev["countdown_hours"] == 500.0
    assert dev["countdown_status"] == "HEALTHY"
    assert dev["qr_code_url"] is not None  # 自动生成二维码

    # 测试录入带自定义设备编号与维护倒计时周期 (小时) 的设备
    custom_code = f"DEV-AIR-{secrets.token_hex(3).upper()}"
    custom_payload = {
        "factory": "新能源分厂",
        "department": "电极车间",
        "system_name": "涂布烘干线",
        "equipment_name": "螺杆空压机A组",
        "model_spec": "GA-75VSD",
        "equipment_code": custom_code,
        "maintenance_interval_hours": 300.0,
        "initial_running_hours": 290.0
    }
    custom_res = client.post("/api/v1/equipments", json=custom_payload, headers=auth_header(eng_token))
    assert custom_res.status_code == 200
    c_dev = custom_res.json()
    assert c_dev["equipment_code"] == custom_code
    assert c_dev["maintenance_interval_hours"] == 300.0
    assert c_dev["total_running_hours"] == 290.0
    assert c_dev["countdown_hours"] == 10.0  # 300 - 290 = 10h (临期预警 <= 48h)
    assert c_dev["countdown_status"] == "WARNING"

    # 重复录入相同设备编号拦截测试 -> 400
    dup_res = client.post("/api/v1/equipments", json=custom_payload, headers=auth_header(eng_token))
    assert dup_res.status_code == 400
    assert "已存在" in dup_res.json()["detail"]

    # 测试层级树动态聚合
    tree_res = client.get("/api/v1/equipments/hierarchy-tree", headers=auth_header(eng_token))
    assert tree_res.status_code == 200
    tree = tree_res.json()
    assert any(node["name"] == "新能源分厂" for node in tree)

    # 测试以设备名称为主的全局模糊穿透搜索
    search_res = client.get("/api/v1/equipments?search=超高速", headers=auth_header(eng_token))
    assert search_res.status_code == 200
    assert len(search_res.json()) >= 1
    assert search_res.json()[0]["equipment_name"] == "超高速双层涂布机"

    # 测试工厂/部门/系统层级多次任意原子重命名
    rename_res = client.post(
        "/api/v1/equipments/rename-hierarchy",
        json={"level": "factory", "old_name": "新能源分厂", "new_name": "储能动力第一智造厂"},
        headers=auth_header(eng_token)
    )
    assert rename_res.status_code == 200
    assert rename_res.json()["affected_count"] >= 1

    # 校验更新后设备所属工厂已变更为新名字
    dev_check = client.get(f"/api/v1/equipments?search=超高速", headers=auth_header(eng_token))
    assert dev_check.json()[0]["factory"] == "储能动力第一智造厂"

    # 测试工程师主动创建“工厂 - 部门 - 系统”三级架构节点 (即使尚无设备也能创建并挂载到树上)
    new_hier_res = client.post("/api/v1/equipments/hierarchy", headers=auth_header(eng_token), json={
        "factory": "未来概念第二分厂",
        "department": "自动化无人车间",
        "system_name": "AGV立体物流系统"
    })
    assert new_hier_res.status_code == 200
    assert "成功创建架构层级" in new_hier_res.json()["message"]

    # 验证架构树中成功展现新创建的层级节点（设备数为0）
    updated_tree = client.get("/api/v1/equipments/hierarchy-tree", headers=auth_header(eng_token)).json()
    new_node = next((n for n in updated_tree if n["name"] == "未来概念第二分厂"), None)
    assert new_node is not None
    assert new_node["count"] == 0
    assert new_node["children"][0]["name"] == "自动化无人车间"
    assert new_node["children"][0]["children"][0]["name"] == "AGV立体物流系统"

    # 验证下拉选项接口包含该新建层级
    options_res = client.get("/api/v1/equipments/hierarchy-options", headers=auth_header(eng_token)).json()
    assert "未来概念第二分厂" in options_res["factories"]
    assert "自动化无人车间" in options_res["departments"]
    assert "AGV立体物流系统" in options_res["systems"]

# ==========================================
# 3. 技术员运行工时抄表与增量数学推算测试 (SWR-DEV-005)
# ==========================================
def test_technician_runtime_log():
    tech_token = get_token("tech1", "password123")
    
    # 获取一台初始设备
    eq_list = client.get("/api/v1/equipments", headers=auth_header(tech_token)).json()
    target_eq = eq_list[0]
    eq_id = target_eq["id"]
    initial_hours = float(target_eq["total_running_hours"])

    # 抄表录入当前读数：比初始多 35.5 小时
    new_reading = initial_hours + 35.5
    log_res = client.post(
        f"/api/v1/equipments/{eq_id}/runtime-logs",
        json={"reading_hours": new_reading, "remark": "白班巡检正常运行抄表"},
        headers=auth_header(tech_token)
    )
    assert log_res.status_code == 200
    log_data = log_res.json()
    assert log_data["delta_hours"] == 35.5
    assert log_data["reading_hours"] == new_reading

    # 验证设备主表总工时已同步更新
    updated_eq = client.get(f"/api/v1/equipments?search={target_eq['equipment_name']}", headers=auth_header(tech_token)).json()[0]
    assert updated_eq["total_running_hours"] == new_reading

# ==========================================
# 4. 维护单打卡、防篡改锁定与工程师留痕修正测试 (SWR-MNT-*)
# ==========================================
def test_maintenance_submit_lock_and_engineer_revise():
    tech_token = get_token("tech1", "password123")
    eng_token = get_token("engineer1", "password123")

    eq_list = client.get("/api/v1/equipments", headers=auth_header(tech_token)).json()
    eq_id = eq_list[0]["id"]

    # 1. 技术员打卡提交维护单 (发现异常)
    submit_payload = {
        "equipment_id": eq_id,
        "checklist_results": [
            {"item": "主电机润滑油脂", "status": "NORMAL", "remark": "油位正常"},
            {"item": "减速机箱体油温", "status": "ABNORMAL", "remark": "温升过高超85度"}
        ],
        "is_normal": False,
        "anomaly_desc": "减速机温升过高异响严重",
        "create_work_order_if_abnormal": True
    }
    sub_res = client.post("/api/v1/maintenance/records/submit", json=submit_payload, headers=auth_header(tech_token))
    assert sub_res.status_code == 200
    rec = sub_res.json()
    record_id = rec["id"]
    assert rec["is_locked_for_tech"] is True
    assert rec["status"] == "SUBMITTED"
    assert rec["interlocked_work_order_id"] is not None  # 自动联锁派生突发工单

    # 校验关联设备状态已自动置为 REPAIRING
    eq_check = client.get(f"/api/v1/equipments?search={eq_list[0]['equipment_name']}", headers=auth_header(tech_token)).json()[0]
    assert eq_check["status"] == "REPAIRING"

    # 2. 核心防篡改验证：技术员尝试再次修改已锁定维护单 -> 必须拦截 403 Forbidden!
    tamper_res = client.put(
        f"/api/v1/maintenance/records/{record_id}",
        json={"equipment_id": eq_id, "checklist_results": [{"item": "偷改", "status": "NORMAL"}], "is_normal": True},
        headers=auth_header(tech_token)
    )
    assert tamper_res.status_code == 403
    assert "现场技术员严禁私自修改" in tamper_res.json()["detail"]

    # 3. 工程师独占修改权验证：工程师修改单据必须提供修改理由留痕
    no_reason = client.put(
        f"/api/v1/maintenance/records/{record_id}/revise",
        json={"revision_reason": ""},
        headers=auth_header(eng_token)
    )
    assert no_reason.status_code == 422  # 校验必须有理由

    revise_res = client.put(
        f"/api/v1/maintenance/records/{record_id}/revise",
        json={"revision_reason": "工程师复核：现场已重新补加润滑脂并调试测温正常"},
        headers=auth_header(eng_token)
    )
    assert revise_res.status_code == 200
    assert revise_res.json()["status"] == "REVISED_BY_ENGINEER"
    assert "工程师复核" in revise_res.json()["revision_reason"]

# ==========================================
# 5. 突发报修、四态工单闭环与后来人病历测试 (SWR-WO-* & SWR-KB-*)
# ==========================================
def test_work_order_lifecycle_and_timeline():
    tech_token = get_token("tech1", "password123")
    eng_token = get_token("engineer1", "password123")

    eq_list = client.get("/api/v1/equipments", headers=auth_header(tech_token)).json()
    eq_id = eq_list[0]["id"]

    # 1. 30 秒极速报修
    report_res = client.post(
        "/api/v1/work-orders",
        json={
            "equipment_id": eq_id,
            "title": "主轴承抱死异响",
            "phenomenon": "电机带不动负载，发出刺耳金属摩擦声",
            "urgency": "CRITICAL"
        },
        headers=auth_header(tech_token)
    )
    assert report_res.status_code == 200
    order_id = report_res.json()["id"]
    assert report_res.json()["status"] == "PENDING"

    # 2. 技术员自主接单抢单 -> IN_PROGRESS
    claim_res = client.put(f"/api/v1/work-orders/{order_id}/dispatch", json={}, headers=auth_header(tech_token))
    assert claim_res.status_code == 200
    assert claim_res.json()["status"] == "IN_PROGRESS"

    # 3. 完工提交复盘干货：强制必须填报根本原因与排除步骤
    fail_resolve = client.put(
        f"/api/v1/work-orders/{order_id}/resolve",
        json={"root_cause": "", "solution_steps": ""},
        headers=auth_header(tech_token)
    )
    assert fail_resolve.status_code == 422

    resolve_res = client.put(
        f"/api/v1/work-orders/{order_id}/resolve",
        json={
            "root_cause": "轴承防尘盖破损，金属切削粉尘侵入滚珠轨道造成干磨抱死",
            "solution_steps": "1. 拆除机壳端盖与损坏轴承；2. 彻底清洗轴颈；3. 热装原厂 NSK-6208 深沟球轴承并压紧；4. 涂抹高温耐磨复合锂基脂。",
            "spare_parts": "NSK-6208 轴承 x 2",
            "repair_duration_minutes": 45
        },
        headers=auth_header(tech_token)
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "PENDING_CONFIRM"

    # 4. 主管工程师现场验收试车并结案 -> CLOSED，联动恢复设备状态为 RUNNING
    confirm_res = client.put(f"/api/v1/work-orders/{order_id}/confirm", headers=auth_header(eng_token))
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "CLOSED"

    eq_after = client.get(f"/api/v1/equipments?search={eq_list[0]['equipment_name']}", headers=auth_header(eng_token)).json()[0]
    assert eq_after["status"] == "RUNNING"  # 自动恢复正常

    # 5. 1 键萃取沉淀至知识库
    kb_res = client.post(f"/api/v1/work-orders/{order_id}/to-knowledge", headers=auth_header(eng_token))
    assert kb_res.status_code == 200
    assert kb_res.json()["case_id"] is not None

    # 6. 后来人终身维修病历动态倒序聚合查询
    timeline_res = client.get(f"/api/v1/equipments/{eq_id}/timeline", headers=auth_header(tech_token))
    assert timeline_res.status_code == 200
    items = timeline_res.json()["timeline_items"]
    assert len(items) >= 2  # 包含该工单和此前的维保记录
    first_event = items[0]
    assert "event_type" in first_event
    assert "event_time" in first_event
    assert "details" in first_event

# ==========================================
# 6. 知识库实时排查推荐与全量热备份测试 (SWR-KB-003 & SWR-SYS-*)
# ==========================================
def test_knowledge_recommend_and_system_backup():
    admin_token = get_token("admin", "password123")
    tech_token = get_token("tech1", "password123")

    # 报修实时推荐
    rec_res = client.get("/api/v1/knowledge/recommend?query=变频", headers=auth_header(tech_token))
    assert rec_res.status_code == 200
    cases = rec_res.json()
    assert len(cases) >= 1
    assert "变频" in cases[0]["title"] or "变频" in cases[0]["phenomenon"]

    # 工作台大盘统计
    dash_res = client.get("/api/v1/system/dashboard", headers=auth_header(admin_token))
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert "equipment_stats" in dash
    assert "work_order_stats" in dash
    assert "role_todos" in dash

    # 管理员一键执行全量数据热备份
    backup_res = client.post("/api/v1/system/backup", headers=auth_header(admin_token))
    assert backup_res.status_code == 200
    b_data = backup_res.json()
    assert b_data["backup_file"].endswith(".zip")
    assert b_data["size_bytes"] > 0
    assert os.path.exists(b_data["backup_path"])

# ==========================================
# 7. 单端口 SPA 静态托管与回退路由测试 (SWR-DEP-*)
# ==========================================
def test_spa_static_and_api_coexist():
    # 测试根路径返回 index.html
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert "MaintainWise 2.0" in root_res.text or "<!DOCTYPE html>" in root_res.text

    # 测试 SPA 路由回退 (如 /equipments 页面直刷)
    route_res = client.get("/equipments")
    assert route_res.status_code == 200
    assert "<!DOCTYPE html>" in route_res.text

    # 测试首次登录强制改密专属独立页面直刷回退
    force_res = client.get("/force-change-password")
    assert force_res.status_code == 200
    assert "<!DOCTYPE html>" in force_res.text

    # 测试 API 路由不受影响 (携带 Token 访问)
    token = get_token("admin", "password123")
    api_res = client.get("/api/v1/system/settings", headers=auth_header(token))
    assert api_res.status_code == 200
    assert "factory_name" in api_res.json()

# ==========================================
# 8. 密码安全策略与 180 天防线测试
# ==========================================
def test_password_security_and_freeze():
    admin_token = get_token("admin", "password123")
    rand_user = f"sec_{secrets.token_hex(3)}"
    
    # 1. 创建新员工账号，默认必须首次强制改密
    create_res = client.post("/api/v1/users", headers=auth_header(admin_token), json={
        "username": rand_user,
        "password": "initialPassword123",
        "full_name": "安全测试员",
        "employee_no": f"EMP-{rand_user}",
        "role": "TECHNICIAN",
        "email": "sectest@factory.com"
    })
    assert create_res.status_code == 200
    user_id = create_res.json()["id"]
    
    # 登录检测 must_change_password 标志
    login_res = client.post("/api/v1/auth/login", data={"username": rand_user, "password": "initialPassword123"})
    assert login_res.status_code == 200
    assert login_res.json()["user"]["must_change_password"] is True
    tech_token = login_res.json()["access_token"]
    
    # 用户在专属独立页面提交新密码（无需重复输旧密码，直接设置新密码）
    chg_res = client.post("/api/v1/auth/change-password", headers=auth_header(tech_token), json={
        "new_password": "brandNewPassword456"
    })
    assert chg_res.status_code == 200
    
    # 再次登录，must_change_password 已解除
    relogin_res = client.post("/api/v1/auth/login", data={"username": rand_user, "password": "brandNewPassword456"})
    assert relogin_res.status_code == 200
    assert relogin_res.json()["user"]["must_change_password"] is False
    
    # 模拟账号冻结测试
    freeze_res = client.put(f"/api/v1/users/{user_id}", headers=auth_header(admin_token), json={"is_frozen": True})
    assert freeze_res.status_code == 200
    blocked_login = client.post("/api/v1/auth/login", data={"username": rand_user, "password": "brandNewPassword456"})
    assert blocked_login.status_code == 403
    assert "冻结" in blocked_login.json()["detail"]
    
    # 管理员解冻账号
    unfreeze_res = client.put(f"/api/v1/users/{user_id}/unfreeze", headers=auth_header(admin_token))
    assert unfreeze_res.status_code == 200
    ok_login = client.post("/api/v1/auth/login", data={"username": rand_user, "password": "brandNewPassword456"})
    assert ok_login.status_code == 200

# ==========================================
# 9. 层级级联软删除与历史工单 100% 保留测试
# ==========================================
def test_hierarchy_delete_and_historical_integrity():
    eng_token = get_token("engineer1", "password123")
    fac_name = f"测试特种分厂_{secrets.token_hex(2)}"
    dept_name = "试验车间"
    sys_name = "高压试验系统"
    
    # 1. 录入一台测试设备
    eq_res = client.post("/api/v1/equipments", headers=auth_header(eng_token), json={
        "factory": fac_name,
        "department": dept_name,
        "system_name": sys_name,
        "equipment_name": "1000kV 特高压试验变压器",
        "model_spec": "S-1000-TEST",
        "maintenance_interval_hours": 300.0,
        "initial_running_hours": 50.0
    })
    assert eq_res.status_code == 200
    eq_id = eq_res.json()["id"]
    
    # 2. 为该设备生成一张工单和一条维保记录
    wo_res = client.post("/api/v1/work-orders", headers=auth_header(eng_token), json={
        "equipment_id": eq_id,
        "title": "试验升压套管微裂纹检修",
        "urgency": "MAJOR"
    })
    assert wo_res.status_code == 200
    wo_id = wo_res.json()["id"]
    
    mnt_res = client.post("/api/v1/maintenance/records/submit", headers=auth_header(eng_token), json={
        "equipment_id": eq_id,
        "checklist_results": [{"item": "绝缘油耐压", "status": "NORMAL"}],
        "is_normal": True
    })
    assert mnt_res.status_code == 200
    
    # 3. 预检删除层级
    prev_res = client.post("/api/v1/equipments/delete-hierarchy-preview", headers=auth_header(eng_token), json={
        "level": "factory",
        "name": fac_name
    })
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["affected_equipments"] == 1
    assert prev_data["retained_work_orders"] >= 1
    assert prev_data["retained_maintenance_records"] >= 1
    
    # 4. 执行级联删除层级
    del_res = client.post("/api/v1/equipments/delete-hierarchy", headers=auth_header(eng_token), json={
        "level": "factory",
        "name": fac_name
    })
    assert del_res.status_code == 200
    assert del_res.json()["affected_count"] == 1
    
    # 5. 核心检验：设备主表已被软删除，不在活跃列表中
    list_eq = client.get("/api/v1/equipments", headers=auth_header(eng_token), params={"factory": fac_name})
    assert len(list_eq.json()) == 0
    
    # 6. 核心检验：历史工单与维保记录完好留存，仍可正常查询，设备名称快照未丢失！
    wo_get = client.get(f"/api/v1/work-orders/{wo_id}", headers=auth_header(eng_token))
    assert wo_get.status_code == 200
    assert "变压器" in wo_get.json()["equipment_name"]
    
    # 7. 测试工单纠错编辑 API 与完工修复照片上传
    up_res = client.put(f"/api/v1/work-orders/{wo_id}", headers=auth_header(eng_token), json={
        "title": "试验升压套管微裂纹检修 (纠错修正版)",
        "repair_photos": "/uploads/repairs/after_repair_01.jpg"
    })
    assert up_res.status_code == 200
    assert up_res.json()["title"] == "试验升压套管微裂纹检修 (纠错修正版)"
    assert up_res.json()["repair_photos"] == "/uploads/repairs/after_repair_01.jpg"

def test_system_smtp_and_executive_kpis():
    admin_token = get_token("admin", "password123")
    
    # 1. 测试数据平台大盘 executive_kpis 与部门故障统计
    dash_res = client.get("/api/v1/system/dashboard", headers=auth_header(admin_token))
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "executive_kpis" in dash_data
    assert "availability_rate" in dash_data["executive_kpis"]
    assert "avg_mttr_minutes" in dash_data["executive_kpis"]
    assert "inspection_pass_rate" in dash_data["executive_kpis"]
    assert "department_issue_stats" in dash_data

    # 2. 测试系统配置读取与更新 (含 SMTP)
    set_get = client.get("/api/v1/system/settings", headers=auth_header(admin_token))
    assert set_get.status_code == 200
    
    set_up = client.put("/api/v1/system/settings", headers=auth_header(admin_token), json={
        "factory_name": "MaintainWise 2.0 数字化灯塔工厂",
        "smtp_host": "smtp.test-server.local",
        "smtp_port": 465,
        "smtp_user": "alert@factory.com",
        "smtp_pass": "secret_pass_123",
        "smtp_enabled": True,
        "notify_lead_days": 5
    })
    assert set_up.status_code == 200
    assert set_up.json()["factory_name"] == "MaintainWise 2.0 数字化灯塔工厂"
    assert set_up.json()["smtp_enabled"] is True

    # 3. 测试 SMTP 探测接口 (由于本地测试无外网 SMTP 服务器，检验返回格式即可)
    smtp_test = client.post("/api/v1/system/smtp/test", headers=auth_header(admin_token), json={
        "host": "smtp.invalid-domain-testing.xyz",
        "port": 465,
        "user": "test@domain.com",
        "password": "pwd",
        "to_email": "receiver@domain.com"
    })
    assert smtp_test.status_code == 200
    assert "success" in smtp_test.json()

def test_intermittent_equipment_and_countdown_lifecycle():
    eng_token = get_token("engineer1", "password123")
    tech_token = get_token("tech1", "password123")
    
    # 1. 工程师录入一台间歇作业型设备 (CNC 加工中心，每天开2-8h不等，周期100h，预警15h)
    create_res = client.post("/api/v1/equipments", headers=auth_header(eng_token), json={
        "factory": "精密制造分厂",
        "department": "机加工车间",
        "system_name": "5轴联动加工单元",
        "equipment_name": "5轴高速立式加工中心",
        "model_spec": "VMC-850",
        "equipment_code": f"CNC-{secrets.token_hex(2).upper()}",
        "running_mode": "INTERMITTENT",
        "maintenance_interval_hours": 100.0,
        "advance_warning_hours": 15.0,
        "initial_running_hours": 60.0
    })
    assert create_res.status_code == 200
    eq_data = create_res.json()
    eq_id = eq_data["id"]
    assert eq_data["running_mode"] == "INTERMITTENT"
    assert eq_data["maintenance_interval_hours"] == 100.0
    assert eq_data["countdown_hours"] == 40.0
    assert eq_data["countdown_status"] == "HEALTHY"
    
    # 2. 技术员模式 A：填报今日增量开机工时 (+8h)
    log_delta_res = client.post(f"/api/v1/equipments/{eq_id}/runtime-logs", headers=auth_header(tech_token), json={
        "delta_hours": 8.0,
        "remark": "白班排产加急切削件 8 小时"
    })
    assert log_delta_res.status_code == 200
    assert log_delta_res.json()["delta_hours"] == 8.0
    assert log_delta_res.json()["reading_hours"] == 68.0
    
    # 3. 技术员模式 B：填报表盘累计读数 (读数增加至 88.0h，剩余 12h <= 15h 触发临期预警)
    log_reading_res = client.post(f"/api/v1/equipments/{eq_id}/runtime-logs", headers=auth_header(tech_token), json={
        "reading_hours": 88.0,
        "remark": "晚班机床数控累计计数表盘抄表"
    })
    assert log_reading_res.status_code == 200
    assert log_reading_res.json()["reading_hours"] == 88.0
    assert log_reading_res.json()["delta_hours"] == 20.0
    
    # 4. 校验设备详情倒计时与智能预计到期天数
    eq_detail = client.get(f"/api/v1/equipments/{eq_id}", headers=auth_header(tech_token)).json()
    assert eq_detail["total_running_hours"] == 88.0
    assert eq_detail["countdown_hours"] == 12.0
    assert eq_detail["countdown_status"] == "WARNING"  # 12h <= 15h，已触发临期预警
    assert eq_detail["avg_daily_hours"] is not None
    assert eq_detail["estimated_days_left"] is not None
    
    # 5. 校验大盘中是否识别到该间歇型设备的倒计时预警
    dash = client.get("/api/v1/system/dashboard", headers=auth_header(tech_token)).json()
    warning_cnt = dash["countdown_stats"]["warning_count"]
    assert warning_cnt >= 1
    found_item = any(item["id"] == eq_id and item["running_mode"] == "INTERMITTENT" for item in dash["countdown_stats"]["urgent_items"])
    assert found_item
    
    # 6. 现场执行维保打卡，验证倒计时清零复位与顺手记工时 (+2h)
    maint_res = client.post("/api/v1/maintenance/records/submit", headers=auth_header(tech_token), json={
        "equipment_id": eq_id,
        "checklist_results": [{"item": "更换主轴专用冷却切削液及主轴高精密轴承润滑脂", "standard": "油质清澈无金属屑", "status": "NORMAL"}],
        "is_normal": True,
        "log_runtime_hours": 2.0  # 顺手填报今日运行 2 小时
    })
    assert maint_res.status_code == 200
    
    # 7. 再次查询设备，验证已复位为 100h 全新周期，状态重返 HEALTHY
    eq_after = client.get(f"/api/v1/equipments/{eq_id}", headers=auth_header(tech_token)).json()
    assert eq_after["total_running_hours"] == 90.0
    assert eq_after["last_maintenance_hours"] == 90.0  # 基准已同步
    assert eq_after["countdown_hours"] == 100.0         # 100 - (90 - 90) = 100h
    assert eq_after["countdown_status"] == "HEALTHY"


# ==========================================
# 13. 在线设计文档与帮助中心 API 验证测试
# ==========================================
def test_docs_reader_api():
    tech_token = get_token("tech1", "password123")
    
    # 1. 列表获取 7 份工程技术规范与现场实操元数据
    docs_res = client.get("/api/v1/docs", headers=auth_header(tech_token))
    assert docs_res.status_code == 200
    docs_list = docs_res.json()
    assert len(docs_list) == 7
    
    expected_ids = {"crs", "sdd", "srs", "swdd", "swdrs", "windows_deploy", "intermittent_sop"}
    actual_ids = {d["id"] for d in docs_list}
    assert expected_ids == actual_ids
    
    # 2. 验证逐个安全读取 Markdown 内容
    for doc in docs_list:
        doc_id = doc["id"]
        res = client.get(f"/api/v1/docs/{doc_id}", headers=auth_header(tech_token))
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == doc_id
        assert len(data["content"]) > 100
        assert "MaintainWise" in data["content"] or "Windows" in data["content"]
        
    # 3. 验证白名单与非法路径注入防御
    bad_res = client.get("/api/v1/docs/../../etc/passwd", headers=auth_header(tech_token))
    assert bad_res.status_code in (404, 400)


# ==========================================
# 14. 系统下设备挂载与单设备删除测试
# ==========================================
def test_equipment_delete_and_hierarchy_tree_children():
    eng_token = get_token("engineer1", "password123")
    fac_name = f"智能工厂_{secrets.token_hex(2)}"
    dept_name = "自动化车间"
    sys_name = "精密冲压系统"
    
    # 1. 录入一台设备
    eq_res = client.post("/api/v1/equipments", headers=auth_header(eng_token), json={
        "factory": fac_name,
        "department": dept_name,
        "system_name": sys_name,
        "equipment_name": "500T 伺服冲压机",
        "model_spec": "SP-500",
        "maintenance_interval_hours": 200.0,
        "initial_running_hours": 10.0
    })
    assert eq_res.status_code == 200
    eq_id = eq_res.json()["id"]
    
    # 2. 检查 hierarchy-tree 返回包含四级结构 (工厂 -> 部门 -> 系统 -> 设备)
    tree_res = client.get("/api/v1/equipments/hierarchy-tree", headers=auth_header(eng_token))
    assert tree_res.status_code == 200
    tree_data = tree_res.json()
    
    target_fac = next((f for f in tree_data if f["name"] == fac_name), None)
    assert target_fac is not None
    assert target_fac["count"] >= 1
    
    target_dept = next((d for d in target_fac["children"] if d["name"] == dept_name), None)
    assert target_dept is not None
    
    target_sys = next((s for s in target_dept["children"] if s["name"] == sys_name), None)
    assert target_sys is not None
    assert target_sys["count"] >= 1
    assert "children" in target_sys
    assert len(target_sys["children"]) >= 1
    
    target_eq = next((e for e in target_sys["children"] if e["id"] == eq_id), None)
    assert target_eq is not None
    assert target_eq["level"] == "equipment"
    assert "500T 伺服冲压机" in target_eq["label"]
    
    # 3. 执行删除设备 DELETE /api/v1/equipments/{id}
    del_res = client.delete(f"/api/v1/equipments/{eq_id}", headers=auth_header(eng_token))
    assert del_res.status_code == 200
    assert "已成功移除" in del_res.json()["message"]
    
    # 4. 再次获取列表与树，确认设备已被软删除，但系统层级完整保留且计数归零
    eq_list = client.get("/api/v1/equipments", headers=auth_header(eng_token), params={"factory": fac_name})
    assert len(eq_list.json()) == 0
    
    tree_res_after = client.get("/api/v1/equipments/hierarchy-tree", headers=auth_header(eng_token))
    assert tree_res_after.status_code == 200
    tree_after = tree_res_after.json()
    
    fac_after = next((f for f in tree_after if f["name"] == fac_name), None)
    assert fac_after is not None
    assert fac_after["count"] == 0
    
    dept_after = next((d for d in fac_after["children"] if d["name"] == dept_name), None)
    assert dept_after is not None
    
    sys_after = next((s for s in dept_after["children"] if s["name"] == sys_name), None)
    assert sys_after is not None
    assert sys_after["count"] == 0
    assert len(sys_after["children"]) == 0

