# MaintainWise 2.0 — 智能工厂设备在线化便利系统
# 软件设计需求规格说明书 (Software Requirements Specification, SWR)

> **文档版本**：V2.0 (全生命周期三层双向跟踪版)  
> **编制日期**：2026-09-15  
> **上游输入**：《系统设计需求规格说明书》(SDR-*) 与《软件设计文档》(SWDD)  
> **核心原则**：原子化可编程 · 函数级输入输出契约 · 自动化测试可测 · 需求 100% 闭环

---

## 目录索引 (Table of Contents)

1. [第一部分：编写目的与软件需求定义规范](#第一部分编写目的与软件需求定义规范)
2. [第二部分：用户与权限模块软件需求 (SWR-USR)](#第二部分用户与权限模块软件需求-swr-usr)
3. [第三部分：设备资产与工时模块软件需求 (SWR-DEV)](#第三部分设备资产与工时模块软件需求-swr-dev)
4. [第四部分：维护单与保养计划软件需求 (SWR-MNT)](#第四部分维护单与保养计划软件需求-swr-mnt)
5. [第五部分：突发报修与维修工单软件需求 (SWR-WO)](#第五部分突发报修与维修工单软件需求-swr-wo)
6. [第六部分：后来人病历与知识库软件需求 (SWR-KB)](#第六部分后来人病历与知识库软件需求-swr-kb)
7. [第七部分：工作台大盘与系统运维软件需求 (SWR-SYS)](#第七部分工作台大盘与系统运维软件需求-swr-sys)
8. [第八部分：跨平台双轨部署工程软件需求 (SWR-DEP)](#第八部分跨平台双轨部署工程软件需求-swr-dep)
9. [第九部分：全生命周期三级需求双向追溯矩阵 (CR -> SDR -> SWR)](#第九部分全生命周期三级需求双向追溯矩阵-cr---sdr---swr)

---

## 第一部分：编写目的与软件需求定义规范

### 1.1 编写目的
本说明书是软件工程开发的基准文档。它承接《系统设计需求规格说明书》（SDR-*），将系统级设计指标细化为程序员可直接编写代码、测试工程师可直接编写测试用例的**原子级软件功能与技术需求（SWR-*，Software Requirements）**。

### 1.2 软件需求条目规范要素
每个 `SWR-*` 条目均严格包含：
1. **需求编号**：唯一标识符；
2. **上游追溯**：对应的系统设计需求（SDR）与客户需求（CR）；
3. **接口契约 / 函数签名**：路径、Method、请求载荷、响应载荷；
4. **校验逻辑与异常错误码**：HTTP 状态码及详细错误信息；
5. **测试验证判据**：对应的 Pytest 测试函数及断言标准。

---

## 第二部分：用户与权限模块软件需求 (SWR-USR)

### SWR-USR-001：用户登录认证与长效 JWT 签发
* **上游追溯**：`SDR-USR-003`, `CR-USR-005`
* **实现定位**：`backend/app/api/v1/endpoints/auth.py`
* **输入契约**：`OAuth2PasswordRequestForm` (`username: str`, `password: str`)
* **输出契约**：`{"access_token": str, "token_type": "bearer", "user": UserOut}`
* **逻辑与异常**：
  - 用户名不存在或密码不匹配：抛出 `HTTP 400 Bad Request: "用户名或密码错误"`；
  - 用户 `is_active == 0`：抛出 `HTTP 403 Forbidden: "该账号已被停用"`；
  - 成功时：签发有效期为 28800 秒（8小时）的 JWT Token。
* **测试用例**：`test_login_and_roles()`

### SWR-USR-002：管理员专属人员创建与工号唯一性校验
* **上游追溯**：`SDR-USR-001`, `SDR-USR-004`, `CR-USR-002`
* **实现定位**：`backend/app/api/v1/endpoints/users.py` (`POST /api/v1/users`)
* **权限守卫**：`Depends(require_admin)`
* **输入契约**：`UserCreate` 模式 (`username`, `full_name`, `employee_no`, `role`, `password`...)
* **逻辑与异常**：
  - 非管理员调用：返回 `HTTP 403 Forbidden`；
  - 工号或用户名已存在：抛出 `HTTP 400 Bad Request: "工号或用户名已存在"`；
  - 成功时：调用 `hash_password()` 存储 bcrypt 密文并返回脱敏 `UserOut`。
* **测试用例**：`test_user_create_and_permissions()`

### SWR-USR-003：管理员一键重置员工密码
* **上游追溯**：`SDR-USR-004`, `CR-USR-002`
* **实现定位**：`backend/app/api/v1/endpoints/users.py` (`PUT /api/v1/users/{id}/reset-password`)
* **权限守卫**：`Depends(require_admin)`
* **输入契约**：`ResetPasswordRequest(new_password: str)`
* **输出契约**：`{"message": "密码重置成功"}`
* **测试用例**：`test_reset_password_by_admin()`

### SWR-USR-004：三角色 RBAC 依赖注入切面
* **上游追溯**：`SDR-USR-005`, `CR-USR-001`
* **实现定位**：`backend/app/core/deps.py`
* **逻辑判据**：
  - `require_admin`: `user.role == 'ADMIN'`
  - `require_engineer`: `user.role in ('ADMIN', 'ENGINEER')`
  - `require_technician`: 任意合法激活用户
  - 越权直接抛出 `HTTP 403 Forbidden: "权限不足"`。
* **测试用例**：`test_rbac_forbidden_matrix()`

### SWR-USR-005：人员软删除保证历史业务签署完好
* **上游追溯**：`SDR-USR-006`, `CR-USR-002`
* **实现定位**：`backend/app/api/v1/endpoints/users.py` (`DELETE /api/v1/users/{id}`)
* **逻辑**：执行 `UPDATE users SET is_active = 0 WHERE id = :id`。已停用人员在工单经办人历史中仍可正常查阅。
* **测试用例**：`test_user_soft_delete()`

### SWR-USR-006：180天密码周期审计、独立安全改密隔离与修改后强制重新登录
* **上游追溯**：`SDR-USR-007`, `CR-USR-006`
* **实现定位**：`backend/app/api/v1/endpoints/auth.py`、`users.py`、`frontend/src/views/auth/ForceChangePasswordView.vue`
* **逻辑与异常**：
  - 登录校验 `password_updated_at`；若超出 180 天，置 `is_frozen = 1` 并返回 HTTP 403；
  - 临期 3 天返回 `password_expiring_soon = True`；
  - 若 `must_change_password = 1`，前端路由拦截强制导向独立全屏改密视图（`/force-change-password`），该视图不加载任何系统大盘与内部导航，杜绝未授权数据窥视；
  - 接口 `POST /api/v1/auth/change-password` 更新哈希与 `password_updated_at = CURRENT_TIMESTAMP`，清除 `must_change_password`；
  - 密码修改成功响应后，前端立即强制调用 `userStore.logout()` 清除本地 Token 与会话信息，并自动重定向至 `/login` 登录页，强制要求用户使用新密码重新鉴权；
  - 接口 `POST /api/v1/users/{id}/unfreeze`（ADMIN）解冻账户并重置密码基线。
* **测试用例**：`test_180_day_password_lifecycle_and_freeze()`, `test_spa_force_change_password_route()`

---

## 第三部分：设备资产与工时模块软件需求 (SWR-DEV)

### SWR-DEV-001：设备录入刚柔校验与内部编码补齐
* **上游追溯**：`SDR-DEV-002`, `SDR-DEV-003`, `CR-DEV-002`, `CR-DEV-003`
* **实现定位**：`backend/app/api/v1/endpoints/equipments.py` (`POST /api/v1/equipments`)
* **权限守卫**：`Depends(require_engineer)`
* **校验逻辑**：
  - `equipment_name` 与 `model_spec` 为必填非空；未填直接由 Pydantic 返回 HTTP 422；
  - `quantity` 默认为 1；
  - `equipment_code` 若为空字符串或 None，自动生成 `DEV-{YYYYMMDDHHMMSS}-{RANDOM}`；
  - 触发调用 `generate_qr_code()` 生成二维码保存至 `data/uploads/qrcodes/`。
* **测试用例**：`test_equipments_and_hierarchy_management()`

### SWR-DEV-002：工厂-部门-系统层级树动态聚合接口
* **上游追溯**：`SDR-DEV-001`, `SDR-DEV-009`, `CR-DEV-001`, `CR-DEV-009`
* **实现定位**：`backend/app/api/v1/endpoints/equipments.py` (`GET /api/v1/equipments/hierarchy-tree`)
* **逻辑**：
  - 执行 `SELECT factory, department, system_name, COUNT(id) FROM equipments WHERE is_deleted = 0 GROUP BY ...`；
  - 动态格式化为带有 `name`, `equipment_count`, `children` 的三层树形 JSON。
* **测试用例**：`test_equipments_and_hierarchy_management()`

### SWR-DEV-003：层级树单事务批量原子更名
* **上游追溯**：`SDR-DEV-008`, `CR-DEV-008`
* **实现定位**：`backend/app/api/v1/endpoints/equipments.py` (`POST /api/v1/equipments/rename-hierarchy`)
* **权限守卫**：`Depends(require_engineer)`
* **输入契约**：`{"level": "factory"|"department"|"system_name", "old_name": str, "new_name": str}`
* **逻辑**：在单个数据库事务中执行 `UPDATE equipments SET {column} = :new_name WHERE {column} = :old_name AND is_deleted = 0`，返回 `{ "affected_count": int }`。
* **测试用例**：`test_equipments_and_hierarchy_management()`

### SWR-DEV-004：设备名称为主的全局穿透模糊查询
* **上游追溯**：`SDR-DEV-004`, `CR-DEV-004`
* **实现定位**：`backend/app/api/v1/endpoints/equipments.py` (`GET /api/v1/equipments`)
* **逻辑**：支持传入 `search` 字符串，SQL 中优先在 `equipment_name` 执行模糊匹配并加权排序。
* **测试用例**：`test_equipments_search_by_name()`

### SWR-DEV-005：技术员现场工时抄表与增量自动计算
* **上游追溯**：`SDR-DEV-006`, `CR-DEV-006`
* **实现定位**：`backend/app/api/v1/endpoints/equipments.py` (`POST /api/v1/equipments/{id}/runtime-logs`)
* **输入契约**：`RuntimeLogCreate(reading_hours: Optional[float], delta_hours: Optional[float], remark: Optional[str])`
* **输出契约**：`RuntimeLogOut(id, equipment_id, reading_hours, delta_hours, recorded_at)`
* **逻辑**：
  - 支持 `reading_hours` 抄表模式与 `delta_hours` 增量填报模式；
  - 单事务插入 `equipment_runtime_logs` 并更新设备 `total_running_hours`。
* **测试用例**：`test_technician_runtime_log()`

### SWR-DEV-006：间歇与持续双模维护算法与14天滑动预测
* **上游追溯**：`SDR-DEV-011`, `CR-DEV-011`
* **实现定位**：`backend/app/api/v1/endpoints/equipments.py`
* **算法实现**：
  - 判定设备 `running_mode`；间歇模式下按 `interval - (total - last_maintenance)` 计算剩余工时；
  - 提取过去 14 天日均运行工时时序，按线性加权计算 $T_{avg}$，推算预计剩余自然日；
  - 若 $\text{Remaining Hours} \le \text{advance\_warning\_hours}$，返回预警状态并触发邮件提醒。
* **测试用例**：`test_dual_mode_maintenance_countdown()`

### SWR-DEV-007：层级级联软删除接口与孤儿数据防御
* **上游追溯**：`SDR-DEV-012`, `CR-DEV-012`
* **实现定位**：`backend/app/api/v1/endpoints/equipments.py` (`POST /hierarchy-delete`)
* **权限守卫**：`Depends(require_engineer)`
* **逻辑**：接收 `factory`, `department`, `system_name`, `cascade_delete_equipments`；单事务级联软删除所有子设备及关联活动工单。
* **测试用例**：`test_hierarchy_cascade_delete()`

### SWR-DEV-008：用户主动预先创建层级与架构选项查询接口
* **上游追溯**：`SDR-DEV-013`, `CR-DEV-013`
* **实现定位**：`backend/app/api/v1/endpoints/equipments.py` (`POST /hierarchy`, `GET /hierarchy-options`, `GET /hierarchy-tree`)
* **权限守卫**：`POST /hierarchy` 挂载 `Depends(require_engineer)`；查询接口面向全员登录用户
* **输入契约**：
  - `POST /api/v1/equipments/hierarchy`: `HierarchyCreate(factory: str, department: Optional[str] = "", system_name: Optional[str] = "")`
* **逻辑契约**：
  - 接口校验 `factory` 非空，未填 `department` 自动补全为 `"默认部门"`，未填 `system_name` 自动补全为 `"默认系统"`；
  - 写入 `custom_hierarchies` 表（`INSERT OR IGNORE INTO custom_hierarchies ...`）；
  - `GET /api/v1/equipments/hierarchy-options` 返回全厂工厂、部门、系统三级扁平去重列表；
  - `GET /api/v1/equipments/hierarchy-tree` 动态合并 `equipments` (is_deleted=0) 与 `custom_hierarchies`，空层级节点设备计数返回 0；
  - 层级更名与级联删除时单事务原子同步更新 `custom_hierarchies`，新增设备自动反向登记入表。
* **测试用例**：`test_custom_hierarchy_creation_and_options()`

### SWR-DEV-009：单台设备软删除与四级树展示契约接口
* **上游追溯**：`SDR-DEV-014`, `CR-DEV-014`
* **实现定位**：`backend/app/api/v1/endpoints/equipments.py` (`DELETE /api/v1/equipments/{id}`, `GET /api/v1/equipments/hierarchy-tree`), `frontend/src/views/equipments/EquipmentListView.vue`
* **权限守卫**：`Depends(get_current_user)` 全员认证开放
* **接口契约**：
  - `DELETE /api/v1/equipments/{id}`:
    - 校验存在性：不存在或已删除返回 `HTTP 404 Not Found: "未找到该设备或已被删除"`；
    - 执行软删除：`UPDATE equipments SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?`；
    - 响应：`{"message": "设备 [xxx] 已成功移除"}`；
  - `GET /api/v1/equipments/hierarchy-tree`:
    - 在系统节点下挂载 `children: [...]` 承载 Level 4 设备子节点；
    - 设备节点包含 `node_key`, `id`, `label` (`📦 {equipment_name}`), `name`, `equipment_code`, `status`, `level: 'equipment'`；
* **业务保证**：
  - 当所属系统设备数为 0 时，保留 `custom_hierarchies` 架构记录，计数显示为 `(0)`；
  - 关联工单与病历通过不可变设备 `id` 与名称快照完整保留。
* **测试用例**：`test_equipment_delete_and_hierarchy_tree_children()`

---

## 第四部分：维护单与保养计划软件需求 (SWR-MNT)

### SWR-MNT-001：技术员维护单提交与“上传即锁定”防篡改守卫
* **上游追溯**：`SDR-MNT-002`, `SDR-MNT-003`, `CR-MNT-002`, `CR-MNT-003`
* **实现定位**：`backend/app/api/v1/endpoints/maintenance.py` (`POST /api/v1/maintenance/records/submit`)
* **逻辑**：
  - 保存记录，设置 `status = 'SUBMITTED'`, `is_locked_for_tech = 1`；
  - 当在后续调用通用编辑接口时，若 `record.is_locked_for_tech == 1` 且 `current_user.role == 'TECHNICIAN'`，直接抛出 `HTTP 403 Forbidden`。
* **测试用例**：`test_maintenance_submit_lock_and_engineer_revise()`

### SWR-MNT-002：工程师独占维护单审核修正与必填修改理由
* **上游追溯**：`SDR-MNT-004`, `CR-MNT-004`
* **实现定位**：`backend/app/api/v1/endpoints/maintenance.py` (`PUT /api/v1/maintenance/records/{id}/revise`)
* **权限守卫**：`Depends(require_engineer)`
* **输入校验**：`revision_reason: str` 必须非空且长度 >= 2；若空返回 `HTTP 422: "修改原因必填"`；
* **更新字段**：`revised_by_engineer_id = current_user.id`, `revised_at = now`, `status = 'REVISED_BY_ENGINEER'`。
* **测试用例**：`test_maintenance_submit_lock_and_engineer_revise()`

### SWR-MNT-003：巡检异常联锁派发维修工单事务
* **上游追溯**：`SDR-MNT-005`, `CR-MNT-005`
* **实现定位**：`backend/app/api/v1/endpoints/maintenance.py` (`POST /records/submit`)
* **逻辑**：
  - 若提交时 `is_normal == False`，在同一事务中：
    1. 生成 `work_orders` 记录 (`source = 'INSPECTION'`)；
    2. 回填 `maintenance_records.interlocked_work_order_id`；
    3. 更新 `equipments.status = 'REPAIRING'`。
* **测试用例**：`test_maintenance_anomaly_interlock()`

### SWR-MNT-004：动态自定义 SOP 检查项与打卡工时闭环
* **上游追溯**：`SDR-MNT-006`, `CR-MNT-006`
* **实现定位**：`backend/app/api/v1/endpoints/maintenance.py` & 前端打卡组件
* **逻辑**：
  - 前端支持动态添加检查条目，每个条目独立选择合格/异常，序列化为 JSON；
  - 提供工厂-部门-系统-设备级联定位器；
  - 打卡请求携带 `log_runtime_hours`，打卡成功后单事务重置 `last_maintenance_hours = total_running_hours`。
* **测试用例**：`test_dynamic_sop_and_runtime_reset()`

---

## 第五部分：突发报修与维修工单软件需求 (SWR-WO)

### SWR-WO-001：全员 30 秒极速报修
* **上游追溯**：`SDR-WO-001`, `CR-WO-001`
* **实现定位**：`backend/app/api/v1/endpoints/work_orders.py` (`POST /api/v1/work-orders`)
* **输入契约**：`WorkOrderCreate(equipment_id: int, title: str, urgency: str, phenomenon: Optional[str])`
* **逻辑**：创建工单并将对应设备状态置为 `REPAIRING`，单号格式为 `WO-YYYYMMDD-XXXX`。
* **测试用例**：`test_work_order_lifecycle_and_timeline()`

### SWR-WO-002：双轨调度接单状态跃迁 (`PENDING` -> `IN_PROGRESS`)
* **上游追溯**：`SDR-WO-003`, `CR-WO-003`
* **实现定位**：`backend/app/api/v1/endpoints/work_orders.py` (`PUT /work-orders/{id}/dispatch`)
* **逻辑**：工程师可指派任意技术员；技术员自主抢单时绑定自身 ID；工单状态跃迁为 `IN_PROGRESS`。
* **测试用例**：`test_work_order_lifecycle_and_timeline()`

### SWR-WO-003：维修复盘根本原因与步骤强制非空校验
* **上游追溯**：`SDR-WO-004`, `CR-WO-004`
* **实现定位**：`backend/app/api/v1/endpoints/work_orders.py` (`PUT /work-orders/{id}/resolve`)
* **校验逻辑**：
  - `root_cause`: 必须非空且长度 >= 2，未填返回 `HTTP 422: "根本原因必填"`；
  - `solution_steps`: 必须非空且长度 >= 2，未填返回 `HTTP 422: "排除步骤必填"`；
  - 成功后工单流转为 `PENDING_CONFIRM`。
* **测试用例**：`test_work_order_lifecycle_and_timeline()`

### SWR-WO-004：工程师现场试车验收结案与设备恢复
* **上游追溯**：`SDR-WO-005`, `CR-WO-005`
* **实现定位**：`backend/app/api/v1/endpoints/work_orders.py` (`PUT /work-orders/{id}/confirm`)
* **权限守卫**：`Depends(require_engineer)`
* **逻辑**：更新工单 `status = 'CLOSED'`，同时单事务执行 `UPDATE equipments SET status = 'RUNNING' WHERE id = :equipment_id`。
* **测试用例**：`test_work_order_lifecycle_and_timeline()`

### SWR-WO-005：工单草稿纠错修改与典型案例标定接口
* **上游追溯**：`SDR-WO-006`, `CR-WO-006`
* **实现定位**：`backend/app/api/v1/endpoints/work_orders.py`
* **逻辑**：
  - `PUT /work-orders/{id}` 允许在 `PENDING` 或 `IN_PROGRESS` 时更新工单简述与现象；
  - `PUT /work-orders/{id}/calibrate-typical`（ENGINEER）将已结案工单 `is_featured_case` 置为 1 并推送知识库。
* **测试用例**：`test_work_order_edit_and_calibration()`

### SWR-WO-006：完工修复照片单张/批量上传契约接口与组件交互
* **上游追溯**：`SDR-WO-007`, `CR-WO-007`
* **实现定位**：`backend/app/api/v1/endpoints/work_orders.py` (`POST /upload-photo`, `POST /upload-photos`), `frontend/src/components/PhotoUploader.vue`
* **权限守卫**：`Depends(get_current_user)` 全员认证开放
* **输入契约**：
  - `POST /api/v1/work-orders/upload-photo`: `file: UploadFile` (multipart/form-data)
  - `POST /api/v1/work-orders/upload-photos`: `files: List[UploadFile]` (multipart/form-data)
* **输出契约**：
  - 单张：`{"url": str, "file_name": str, "size": int, "message": "照片上传成功"}`
  - 批量：`{"urls": List[str], "count": int, "message": "成功上传 N 张照片"}`
* **逻辑与异常**：
  - 校验文件后缀必须属于 `{'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.gif'}`，缺省自动置为 `.jpg`；
  - 单文件限制 15MB，超限抛出 `HTTP 413: "上传照片大小不能超过 15MB"`；
  - 存入 `data/uploads/repairs/` 并生成唯一随机文件名，向外暴露静态访问相对路径；
  - 前端 `PhotoUploader.vue` 统一封装拍照（`capture="environment"`）与本地图库多选，双向绑定逗号拼接字符串，与 `resolveForm`、`editForm` 及 `selectedWo` 缩放预览完全打通。
* **测试用例**：`test_work_order_photo_upload_and_resolve()`

---

## 第六部分：后来人病历与知识库软件需求 (SWR-KB)

### SWR-KB-001：后来人终身维修病历三流合一动态倒序聚合
* **上游追溯**：`SDR-KB-001`, `CR-KB-001`
* **实现定位**：`backend/app/services/timeline_service.py` & `api/v1/endpoints/equipments.py` (`GET /{id}/timeline`)
* **聚合来源**：`work_orders` + `maintenance_records` + `equipment_runtime_logs`
* **输出规范**：列表按 `event_time` 毫秒级倒序排列，每个条目包含 `event_type`, `event_time`, `title`, `operator`, `details`。
* **测试用例**：`test_work_order_lifecycle_and_timeline()`

### SWR-KB-002：结案工单一键萃取至排故知识库
* **上游追溯**：`SDR-KB-002`, `CR-KB-002`
* **实现定位**：`backend/app/api/v1/endpoints/work_orders.py` (`POST /work-orders/{id}/to-knowledge`)
* **权限守卫**：`Depends(require_engineer)`
* **逻辑**：工单必须为 `CLOSED`；提取标题、根因与排除步骤插入 `knowledge_cases`，并设置工单 `is_featured_case = 1`。
* **测试用例**：`test_work_order_to_knowledge()`

### SWR-KB-003：报修输入实时关键词相似度排故推荐接口
* **上游追溯**：`SDR-KB-003`, `CR-KB-003`
* **实现定位**：`backend/app/api/v1/endpoints/knowledge.py` (`GET /knowledge/recommend?query=...`)
* **输出**：返回匹配度最高的前 5 条知识库案例，包含现象剖析与标准排除步骤。
* **测试用例**：`test_knowledge_recommend()`

---

## 第七部分：工作台大盘与系统运维软件需求 (SWR-SYS)

### SWR-SYS-001：车间大盘四态设备与工单指标聚合统计
* **上游追溯**：`SDR-SYS-001`, `CR-SYS-001`
* **实现定位**：`backend/app/api/v1/endpoints/system.py` (`GET /api/v1/system/dashboard`)
* **输出**：设备运行态势统计（正常/在修/待保/停机）与四态工单数量。
* **测试用例**：`test_dashboard_stats()`

### SWR-SYS-002：单文件 SQLite 3 WAL 纯 Python 在线热备份 ZIP
* **上游追溯**：`SDR-SYS-003`, `CR-SYS-003`
* **实现定位**：`backend/app/services/backup_service.py` & `api/v1/endpoints/system.py` (`POST /system/backup`)
* **权限守卫**：`Depends(require_admin)`
* **逻辑**：基于 `zipfile.ZipFile` 流式压缩 `maintainwise.db` 与 `data/uploads/`，生成带时间戳归档包。
* **测试用例**：`test_system_backup()`

### SWR-SYS-003：SMTP 邮件参数配置与测试发送接口
* **上游追溯**：`SDR-SYS-004`, `CR-SYS-004`
* **实现定位**：`backend/app/api/v1/endpoints/system.py` (`POST /api/v1/system/test-email`)
* **权限守卫**：`Depends(require_admin)`
* **逻辑**：验证 SMTP 服务器连接与 SSL/TLS 握手，向指定收件人投递测试邮件。
* **测试用例**：`test_smtp_email_configuration()`

### SWR-SYS-004：在线系统设计文档白名单读取服务与组件
* **上游追溯**：`SDR-SYS-005`, `CR-SYS-005`
* **实现定位**：`backend/app/api/v1/endpoints/docs.py` & `frontend/src/views/docs/DocsReaderView.vue`
* **逻辑**：
  - `GET /api/v1/docs` 映射 6 份系统技术规范的元数据；
  - `GET /api/v1/docs/{doc_id}` 白名单防路径遍历校验，安全读取 Markdown 正文返回；
  - 前端使用 `marked` 库解析 Markdown，支持搜索与大纲跳转。
* **测试用例**：`test_docs_reader_api()`

---

## 第八部分：跨平台双轨部署工程软件需求 (SWR-DEP)

### SWR-DEP-001：FastAPI 单端口同时托管 SPA 与 API
* **上游追溯**：`SDR-DEP-001`, `CR-CON-003`, `CR-CON-004`
* **实现定位**：`backend/app/main.py`
* **逻辑**：挂载 `/assets` 与 `/uploads`，注册回退路由返回 `dist/index.html`，对外单端口 8000。
* **测试用例**：`test_spa_static_and_api_coexist()`

### SWR-DEP-002：全栈 pathlib.Path 路径中立性设计
* **上游追溯**：`SDR-DEP-003`, `CR-CON-001`
* **实现定位**：全后端代码基线
* **规范**：禁止硬编码 `/` 或 `\`，统一采用 `pathlib.Path` 拼接路径。
* **测试用例**：`test_pathlib_neutrality()`

### SWR-DEP-003：Windows 批处理 CRLF、.gitattributes 防护与双模控制总控
* **上游追溯**：`SDR-DEP-004`, `CR-CON-005`
* **实现定位**：`deploy/windows/*.bat`, 根目录 `maintainwise.bat`, `mw.bat`, `.gitattributes`
* **规范**：
  - 文件统一保存为标准 CRLF 换行，首行声明 `chcp 65001 >nul`；
  - 根目录 `.gitattributes` 明确声明 `*.bat text eol=crlf`，防止跨平台拉取时被转为单字节 LF 造成指令截断；
  - 批处理脚本所有 `echo` 提示文本严禁使用裸露 `&`，统一使用 `and`，避免 `cmd.exe` 误当命令分隔符触发系统 `start` 命令；
  - `maintainwise.bat` 支持参数模式（`deploy|test|start|stop|restart|status|backup`）与双击 0~7 交互式菜单；
  - 原生支持 `test` 命令调用 `deploy/windows/2_start_foreground.bat` 进行前台交互调试。
* **测试用例**：`test_spa_static_and_api_coexist()`

### SWR-DEP-004：Linux 容器环境进程脱离常驻与统一命令行控制套件
* **上游追溯**：`SDR-DEP-006`, `CR-CON-006`
* **实现定位**：`deploy/linux/start_background.sh` 等脚本及根目录统一总控 `maintainwise.sh` (或 `./mw.sh`)
* **规范**：
  - 针对无 systemd 环境，启动命令使用 `setsid python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 < /dev/null >> logs/maintainwise.log 2>&1 &`；
  - 启动后将 PID 写入 `maintainwise.pid`；
  - 停止脚本支持基于 PID 发送 SIGTERM，10秒超时后发送 SIGKILL，并释放端口删除 PID 文件；
  - 根目录统一由 `./maintainwise.sh <action>` 提供 `deploy|start|stop|restart|status|logs|backup` 全套参数化运维。
* **测试用例**：`test_spa_static_and_api_coexist()`

---

## 第九部分：全生命周期三级需求双向追溯矩阵 (CR -> SDR -> SWR)

| 客户需求编号 (CR) | 系统设计需求编号 (SDR) | 软件设计需求编号 (SWR) | 负责源代码文件 | 对应自动化测试函数 |
| :--- | :--- | :--- | :--- | :--- |
| **CR-USR-001** | `SDR-USR-001`, `SDR-USR-005` | **SWR-USR-004** | `backend/app/core/deps.py` | `test_login_and_roles` |
| **CR-USR-002** | `SDR-USR-002`, `SDR-USR-004` | **SWR-USR-002**, **SWR-USR-003** | `backend/app/api/v1/endpoints/users.py` | `test_user_management_and_password_reset` |
| **CR-USR-005** | `SDR-USR-003` | **SWR-USR-001** | `backend/app/core/security.py` | `test_login_and_roles` |
| **CR-USR-006** | `SDR-USR-007` | **SWR-USR-006** | `backend/app/api/v1/endpoints/auth.py`, `frontend/src/views/auth/ForceChangePasswordView.vue` | `test_password_security_and_freeze` |
| **CR-DEV-001** | `SDR-DEV-001` | **SWR-DEV-002** | `backend/app/api/v1/endpoints/equipments.py` | `test_equipments_and_hierarchy_management` |
| **CR-DEV-002** | `SDR-DEV-002` | **SWR-DEV-001** | `backend/app/schemas/equipment.py` | `test_equipments_and_hierarchy_management` |
| **CR-DEV-003** | `SDR-DEV-003` | **SWR-DEV-001** | `backend/app/api/v1/endpoints/equipments.py` | `test_equipments_and_hierarchy_management` |
| **CR-DEV-004** | `SDR-DEV-004` | **SWR-DEV-004** | `backend/app/api/v1/endpoints/equipments.py` | `test_equipments_and_hierarchy_management` |
| **CR-DEV-006** | `SDR-DEV-006` | **SWR-DEV-005** | `backend/app/api/v1/endpoints/equipments.py` | `test_technician_runtime_log` |
| **CR-DEV-008** | `SDR-DEV-008` | **SWR-DEV-003** | `backend/app/api/v1/endpoints/equipments.py` | `test_equipments_and_hierarchy_management` |
| **CR-DEV-011** | `SDR-DEV-011` | **SWR-DEV-006** | `backend/app/api/v1/endpoints/equipments.py` | `test_intermittent_equipment_and_countdown_lifecycle` |
| **CR-DEV-012** | `SDR-DEV-012` | **SWR-DEV-007** | `backend/app/api/v1/endpoints/equipments.py` | `test_hierarchy_delete_and_historical_integrity` |
| **CR-DEV-013** | `SDR-DEV-013` | **SWR-DEV-008** | `backend/app/api/v1/endpoints/equipments.py`, `frontend/src/views/equipments/EquipmentListView.vue` | `test_equipments_and_hierarchy_management` |
| **CR-DEV-014** | `SDR-DEV-014` | **SWR-DEV-009** | `backend/app/api/v1/endpoints/equipments.py`, `frontend/src/views/equipments/EquipmentListView.vue` | `test_equipment_delete_and_hierarchy_tree_children` |
| **CR-MNT-001** | `SDR-MNT-001` | **SWR-MNT-001** | `backend/app/api/v1/endpoints/maintenance.py` | `test_maintenance_submit_lock_and_engineer_revise` |
| **CR-MNT-003** | `SDR-MNT-003` | **SWR-MNT-001** | `backend/app/api/v1/endpoints/maintenance.py` | `test_maintenance_submit_lock_and_engineer_revise` |
| **CR-MNT-004** | `SDR-MNT-004` | **SWR-MNT-002** | `backend/app/api/v1/endpoints/maintenance.py` | `test_maintenance_submit_lock_and_engineer_revise` |
| **CR-MNT-005** | `SDR-MNT-005` | **SWR-MNT-003** | `backend/app/api/v1/endpoints/maintenance.py` | `test_maintenance_submit_lock_and_engineer_revise` |
| **CR-MNT-006** | `SDR-MNT-006` | **SWR-MNT-004** | `backend/app/api/v1/endpoints/maintenance.py` | `test_maintenance_submit_lock_and_engineer_revise` |
| **CR-WO-001** | `SDR-WO-001` | **SWR-WO-001** | `backend/app/api/v1/endpoints/work_orders.py` | `test_work_order_lifecycle_and_timeline` |
| **CR-WO-002** | `SDR-WO-002` | **SWR-WO-002** | `backend/app/api/v1/endpoints/work_orders.py` | `test_work_order_lifecycle_and_timeline` |
| **CR-WO-004** | `SDR-WO-004` | **SWR-WO-003** | `backend/app/api/v1/endpoints/work_orders.py` | `test_work_order_lifecycle_and_timeline` |
| **CR-WO-005** | `SDR-WO-005` | **SWR-WO-004** | `backend/app/api/v1/endpoints/work_orders.py` | `test_work_order_lifecycle_and_timeline` |
| **CR-WO-006** | `SDR-WO-006` | **SWR-WO-005** | `backend/app/api/v1/endpoints/work_orders.py` | `test_work_order_lifecycle_and_timeline` |
| **CR-WO-007** | `SDR-WO-007` | **SWR-WO-006** | `backend/app/api/v1/endpoints/work_orders.py`, `frontend/src/components/PhotoUploader.vue` | `test_work_order_photo_upload_and_resolve` |
| **CR-KB-001** | `SDR-KB-001` | **SWR-KB-001** | `backend/app/services/timeline_service.py` | `test_work_order_lifecycle_and_timeline` |
| **CR-KB-002** | `SDR-KB-002` | **SWR-KB-002** | `backend/app/api/v1/endpoints/work_orders.py` | `test_work_order_lifecycle_and_timeline` |
| **CR-KB-003** | `SDR-KB-003` | **SWR-KB-003** | `backend/app/api/v1/endpoints/knowledge.py` | `test_knowledge_recommend_and_system_backup` |
| **CR-SYS-001** | `SDR-SYS-001` | **SWR-SYS-001** | `backend/app/api/v1/endpoints/system.py` | `test_system_smtp_and_executive_kpis` |
| **CR-SYS-003** | `SDR-SYS-003` | **SWR-SYS-002** | `backend/app/services/backup_service.py` | `test_knowledge_recommend_and_system_backup` |
| **CR-SYS-004** | `SDR-SYS-004` | **SWR-SYS-003** | `backend/app/api/v1/endpoints/system.py` | `test_system_smtp_and_executive_kpis` |
| **CR-SYS-005** | `SDR-SYS-005` | **SWR-SYS-004** | `backend/app/api/v1/endpoints/docs.py` | `test_docs_reader_api` |
| **CR-CON-001** | `SDR-DEP-003` | **SWR-DEP-002** | 全后端文件 | `test_spa_static_and_api_coexist` |
| **CR-CON-002** | `SDR-DEP-005` | **SWR-DEP-004** | `deploy/` 双轨脚本目录 | `test_spa_static_and_api_coexist` |
| **CR-CON-003** | `SDR-DEP-001`, `SDR-DEP-002` | **SWR-DEP-001** | `backend/app/main.py` | `test_spa_static_and_api_coexist` |
| **CR-CON-004** | `SDR-DEP-001` | **SWR-DEP-001** | `backend/app/main.py` | `test_spa_static_and_api_coexist` |
| **CR-CON-005** | `SDR-DEP-004` | **SWR-DEP-003** | `maintainwise.bat`, `deploy/windows/*.bat` | `test_spa_static_and_api_coexist` |
| **CR-CON-006** | `SDR-DEP-006` | **SWR-DEP-004** | `maintainwise.sh`, `deploy/linux/` 脚本库 | `test_spa_static_and_api_coexist` |
