# MaintainWise 2.0 — 智能工厂设备在线化便利系统
# 系统设计需求规格说明书 (System Design Requirements Specification)

> **文档版本**：V2.0 (系统设计需求条目化与精确编号版)  
> **编制日期**：2026-09-15  
> **上游输入**：《客户需求规格说明书》(CR-*) 与《系统总体设计方案说明书》各功能章节  
> **核心原则**：第一性原理驱动 · 严密条目编号 · 双向追踪矩阵 · 零遗漏零冗余

---

## 目录 (Table of Contents)

1. [第一部分：编写目的与需求导出原则](#第一部分编写目的与需求导出原则)
2. [第二部分：用户与权限系统设计需求 (SDR-USR)](#第二部分用户与权限系统设计需求-sdr-usr)
3. [第三部分：设备资产与工时系统设计需求 (SDR-DEV)](#第三部分设备资产与工时系统设计需求-sdr-dev)
4. [第四部分：设备维护单与日常保养系统设计需求 (SDR-MNT)](#第四部分设备维护单与日常保养系统设计需求-sdr-mnt)
5. [第五部分：突发故障报修与维修工单系统设计需求 (SDR-WO)](#第五部分突发故障报修与维修工单系统设计需求-sdr-wo)
6. [第六部分：终身病历与排故知识库系统设计需求 (SDR-KB)](#第六部分终身病历与排故知识库系统设计需求-sdr-kb)
7. [第七部分：工作台大盘与系统运维系统设计需求 (SDR-SYS)](#第七部分工作台大盘与系统运维系统设计需求-sdr-sys)
8. [第八部分：跨平台双轨部署系统设计需求 (SDR-DEP)](#第八部分跨平台双轨部署系统设计需求-sdr-dep)
9. [第九部分：客户需求与系统设计需求双向跟踪矩阵 (Traceability Matrix)](#第九部分客户需求与系统设计需求双向跟踪矩阵-traceability-matrix)

---

## 第一部分：编写目的与需求导出原则

### 1.1 编写目的
本规范承接《客户需求规格说明书》（CR-*）与《系统总体设计方案说明书》中的九大功能章节，将架构设计方案逐项分解、收敛并导出为**具有唯一编号、技术细节明确、可测试、可验收的系统设计需求（SDR-*，System Design Requirements）**。

### 1.2 需求导出原则
1. **单一职责原则**：每一条设计需求只阐述一个明确的技术实现与业务规则，严禁模糊笼统；
2. **闭环可测原则**：每项设计需求均配有明确的技术验收判据与测试验证方式；
3. **严格双向追溯**：每项 `SDR-*` 均与上游客户需求 `CR-*` 精准对应，杜绝私设冗余功能，也杜绝客户需求遗漏。

---

## 第二部分：用户与权限系统设计需求 (SDR-USR)

### SDR-USR-001：单表用户实体与字段完整性设计
* **对应客户需求**：`CR-USR-001`, `CR-USR-002`
* **所属系统层级**：数据持久化层 / 后端核心
* **设计实现规范**：
  在 SQLite 3 数据库建立单张 `users` 表，包含字段：
  - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
  - `username`: VARCHAR(64) NOT NULL UNIQUE
  - `password_hash`: VARCHAR(255) NOT NULL
  - `full_name`: VARCHAR(64) NOT NULL
  - `employee_no`: VARCHAR(32) NOT NULL UNIQUE
  - `role`: VARCHAR(16) NOT NULL CHECK(role IN ('ADMIN', 'ENGINEER', 'TECHNICIAN'))
  - `phone`: VARCHAR(32)
  - `email`: VARCHAR(64)
  - `is_active`: BOOLEAN NOT NULL DEFAULT 1
  - `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
* **验证方式**：数据库 DDL 执行与唯一性索引约束测试。

### SDR-USR-002：原生 bcrypt 密码加盐散列设计
* **对应客户需求**：`CR-USR-002`
* **所属系统层级**：后端安全服务
* **设计实现规范**：
  为避免 passlib 1.7.4 与 Python 3.14 的 `__about__.__version__` 不兼容漏洞，系统必须直接调用底层原生 `bcrypt` 模块：
  - 散列密码：`bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')`
  - 校验密码：`bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))`
* **验证方式**：单元测试对明文与哈希串进行正确性与抗碰撞校验。

### SDR-USR-003：JWT 480 分钟长效免密会话设计
* **对应客户需求**：`CR-USR-005`
* **所属系统层级**：认证与令牌服务
* **设计实现规范**：
  用户登录成功（`POST /api/v1/auth/login`）后，系统签发带有加密签名的 JWT Token：
  - Payload 载荷包含：`{"sub": str(user.id), "role": user.role, "exp": now + 28800}`（480 分钟）；
  - 算法采用 `HS256`；
  - 前端 Axios 拦截器在每个请求头部自动注入 `Authorization: Bearer <token>`。
* **验证方式**：接口测试验证 Token 解析的有效期时间戳为签发时间+8小时。

### SDR-USR-004：系统管理员专属人员与密码重置接口设计
* **对应客户需求**：`CR-USR-002`
* **所属系统层级**：用户服务 API
* **设计实现规范**：
  提供人员管理 REST 接口族：
  - `GET /api/v1/users`：分页查询全员；
  - `POST /api/v1/users`：录入新员工账号；
  - `PUT /api/v1/users/{id}`：编辑员工资料与角色；
  - `PUT /api/v1/users/{id}/reset-password`：一键重置指定员工密码；
  - `DELETE /api/v1/users/{id}`：停用人员账号；
  上述所有接口必须挂载 `require_admin` 守卫，非管理员访问返回 `HTTP 403 Forbidden`。
* **验证方式**：使用技术员与工程师 Token 分别请求接口，断言 HTTP 403。

### SDR-USR-005：三角色前端动态视图与后端切面硬隔离设计
* **对应客户需求**：`CR-USR-001`, `CR-USR-003`, `CR-USR-004`
* **所属系统层级**：前端视图路由 / 后端切面
* **设计实现规范**：
  - 前端 Pinia `userStore` 保存当前用户角色；Vue Router 导航守卫根据角色动态过滤侧边栏菜单；
  - 界面顶部常驻彩色角色标签（ADMIN 红色、ENGINEER 蓝色、TECHNICIAN 绿色）；
  - 后端依赖注入提供严格切面函数：`require_admin`、`require_engineer`、`require_technician`。
* **验证方式**：各角色登录后检查前端侧边栏渲染项与后端越权接口拦截。

### SDR-USR-006：人员软删除与历史签署终身保真设计
* **对应客户需求**：`CR-USR-002`, `CR-USR-003`
* **所属系统层级**：数据持久化层
* **设计实现规范**：
  用户删除操作执行 `UPDATE users SET is_active = 0 WHERE id = :id`，严禁物理执行 `DELETE FROM users`。已停用账号禁止登录，但其历史签署的单据在病历中完整展示历史姓名。
* **验证方式**：停用账号后发起登录提示失败，查看历史工单显示原处理人信息完好。

### SDR-USR-007：180天密码强制轮换、独立改密隔离与修改后强制重新登录设计
* **对应客户需求**：`CR-USR-006`
* **所属系统层级**：安全鉴权微核心 / 前端全局拦截
* **设计实现规范**：
  - `users` 表持久化 `password_updated_at` (DATETIME) 与 `is_frozen` (BOOLEAN)；
  - 登录接口执行密码生命周期审计：
    1. 计算 $\Delta D = \text{now}() - \text{password\_updated\_at}$；
    2. 若 $\Delta D > 180$，置 `is_frozen = 1` 并返回 HTTP 403 抛出异常；
    3. 若 $177 \le \Delta D \le 180$（临期 3 天内），登录响应中下发 `password_expiring_soon = true` 及剩余天数；前端顶栏弹出黄色提醒 Banner；
    4. 若 `must_change_password = 1`，前端路由守卫强制跳转至专属独立的改密隔离页面（`/force-change-password`，独立全屏容器，彻底阻断主布局与背景数据大盘的加载），强制用户设置 $\ge 6$ 位新密码；
    5. 密码修改成功（`POST /api/v1/auth/change-password`）后，系统立即触发前端全量注销（`userStore.logout()`），清空本地 Token 与缓存，并自动重定向跳转回登录界面（`/login`），强制要求用户使用新设密码重新鉴权方可重新签发新 Token 进入系统；
    6. 管理员专属重置密码与解冻接口：`POST /api/v1/users/{id}/reset-password` 与 `POST /api/v1/users/{id}/unfreeze`。
* **验证方式**：修改模拟过期时间，验证登录时自动锁定且阻断访问；测试首次登录强制跳转独立隔离页面修改密码，修改成功后自动退出并要求新密码登录。

---

## 第三部分：设备资产与工时系统设计需求 (SDR-DEV)

### SDR-DEV-001：“工厂-部门-系统”三级扁平存储设计
* **对应客户需求**：`CR-DEV-001`
* **所属系统层级**：数据持久化层
* **设计实现规范**：
  在 `equipments` 表中直接定义三级层级字段：
  - `factory`: VARCHAR(128) NOT NULL (工厂名称)
  - `department`: VARCHAR(128) NOT NULL (部门/车间)
  - `system_name`: VARCHAR(128) NOT NULL (系统/产线)
  无需建立冗余的组织树中间表，查询时通过 `SELECT DISTINCT factory, department, system_name FROM equipments` 毫秒级动态聚合出树形结构。
* **验证方式**：查询 `GET /api/v1/equipments/hierarchy-tree` 返回标准化嵌套 JSON 树。

### SDR-DEV-002：设备必填与选填字段刚柔校验设计
* **对应客户需求**：`CR-DEV-002`
* **所属系统层级**：后端模型校验 (Pydantic)
* **设计实现规范**：
  定义 `EquipmentCreate` 模式：
  - `equipment_name`: str (必填，非空且长度 >= 1)
  - `model_spec`: str (必填，非空且长度 >= 1)
  - `factory`: str (必填)
  - `department`: str (必填)
  - `system_name`: str (必填)
  - `quantity`: Optional[int] = Field(default=1, ge=1) (选填，缺省为 1)
  - `parameters`: Optional[str] = "" (选填，设备工况参数)
  - `equipment_code`: Optional[str] = "" (选填)
* **验证方式**：提交仅包含名称、规格和层级的载荷，成功保存且数量为 1。

### SDR-DEV-003：设备编码缺省自动生成引擎设计
* **对应客户需求**：`CR-DEV-003`
* **所属系统层级**：后端领域服务
* **设计实现规范**：
  若客户端提交的 `equipment_code` 为空字符串或 `None`，后端自动生成规范编码：
  `equipment_code = f"DEV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"`
* **验证方式**：留空编码保存设备，落库数据包含有效的 `DEV-*` 编码。

### SDR-DEV-004：以设备名称为主的全局穿透模糊匹配设计
* **对应客户需求**：`CR-DEV-004`
* **所属系统层级**：后端查询服务 / 前端搜索组件
* **设计实现规范**：
  `GET /api/v1/equipments?search={query}` 查询逻辑中，SQL 检索条件优先对 `equipment_name` 执行模糊匹配：
  `WHERE (equipment_name LIKE :kw OR model_spec LIKE :kw OR equipment_code LIKE :kw)`
  界面列表对设备名称加粗高亮渲染，搜索提示首项展示设备名称。
* **验证方式**：输入设备名称关键字，验证匹配结果置顶且毫秒级响应。

### SDR-DEV-005：设备台账工程师专属管控与软删除设计
* **对应客户需求**：`CR-DEV-005`
* **所属系统层级**：后端权限切面
* **设计实现规范**：
  - `POST /api/v1/equipments` (创建) 挂载 `require_engineer`；
  - `PUT /api/v1/equipments/{id}` (修改) 挂载 `require_engineer`；
  - `DELETE /api/v1/equipments/{id}` (删除) 挂载 `require_engineer`，底层执行 `is_deleted = 1` 软删除；
  技术员发起写操作直接拦截并返回 HTTP 403。
* **验证方式**：技术员 Token 调用创建/删除接口，断言 HTTP 403。

### SDR-DEV-006：技术员现场工时抄表与增量数学推算设计
* **对应客户需求**：`CR-DEV-006`
* **所属系统层级**：工时服务 API
* **设计实现规范**：
  接口 `POST /api/v1/equipments/{id}/runtime-logs` 允许技术员、工程师与管理员提交：
  - 接收表盘当前读数 `reading_hours: float`；
  - 系统查询上一条记录或设备当前 `total_running_hours`，自动推算：
    `delta = max(0.0, reading_hours - current_total_hours)`
  - 单事务中写入 `equipment_runtime_logs` 表，并同步执行：
    `UPDATE equipments SET total_running_hours = :reading_hours, last_runtime_updated_at = CURRENT_TIMESTAMP WHERE id = :id`
* **验证方式**：设备总工时为 100，抄表输入 150，写入流水 delta=50，设备总工时变为 150。

### SDR-DEV-007：输入即建树与顺畅连续录入交互设计
* **对应客户需求**：`CR-DEV-007`
* **所属系统层级**：前端组件与交互
* **设计实现规范**：
  - 工厂/部门/系统输入框采用 Element Plus `el-select` 带 `filterable` 与 `allow-create` 属性，既可选择已有项，也可直接手打敲回车创建新层级；
  - 弹窗底部设置【保存并继续录入】按钮，点击后提交当前设备，保留当前工厂/部门/系统选择，清空名称与规格，光标自动聚焦至名称输入框。
* **验证方式**：连续录入 3 台不同设备，无需中途离开页面，10秒内完成保存。

### SDR-DEV-008：层级多次任意更名单事务原子批量同步设计
* **对应客户需求**：`CR-DEV-008`
* **所属系统层级**：后端层级管理 API
* **设计实现规范**：
  接口 `POST /api/v1/equipments/rename-hierarchy` 权限限于管理员与工程师：
  - 参数：`{"level": "factory"|"department"|"system_name", "old_name": str, "new_name": str}`
  - 在单个原子事务中执行：
    `UPDATE equipments SET {column} = :new_name WHERE {column} = :old_name AND is_deleted = 0`
  - 设备关联的历史病历、工单、维护单通过设备不可变 `id` 关联，层级名称更新零断层。
* **验证方式**：将“第一车间”更名为“精密加工车间”，关联的 20 台设备及历史病历完好同步。

### SDR-DEV-009：左树右表/卡片双模联动与钻取设计
* **对应客户需求**：`CR-DEV-009`
* **所属系统层级**：前端视图架构
* **设计实现规范**：
  - 界面左侧为 `el-tree` 层级导航树，节点包含徽标 `badge` 显示从属设备数量；
  - 节点悬浮出现操作菜单【重命名】；
  - 点击节点时，触发右侧列表更新过滤参数 `current_factory`, `current_department`, `current_system`；
  - 右侧提供 `Table` 与 `Card` 视图切换开关。
* **验证方式**：点击左树节点，右侧毫秒级过滤呈现对应设备。

### SDR-DEV-010：一机一码高清二维码自动生成与流式导出设计
* **对应客户需求**：`CR-DEV-010`
* **所属系统层级**：后端二维码服务
* **设计实现规范**：
  - 设备保存时调用 `qrcode.make(f"/equipments/{dev.id}")` 生成图片保存至 `data/uploads/qrcodes/qr_dev_{dev.id}.png`；
  - 设备表记录相对路径 `qr_code_url = f"/uploads/qrcodes/qr_dev_{dev.id}.png"`；
  - 列表提供二维码弹窗预览与一键下载打印。
* **验证方式**：新增设备后检查磁盘文件生成成功，手机扫码能正确解析地址。

### SDR-DEV-011：间歇与持续双模维护工时算法与14天滑动预测设计
* **对应客户需求**：`CR-DEV-011`
* **所属系统层级**：领域计算核心 / 设备资产服务
* **设计实现规范**：
  - `equipments` 表扩展字段：
    - `running_mode`: VARCHAR(20) DEFAULT 'CONTINUOUS' (`CONTINUOUS` 持续运行 / `INTERMITTENT` 间歇运行)；
    - `advance_warning_hours`: FLOAT DEFAULT 20.0 (提前预警阈值小时)；
    - `last_maintenance_hours`: FLOAT DEFAULT 0.0 (上一次维保归零基线工时)；
  - 间歇设备保养倒计时算法：
    $$\text{Remaining Hours} = \text{maintenance\_interval\_hours} - (\text{total\_running\_hours} - \text{last\_maintenance\_hours})$$
  - 14 天滑动加权预测日均开机工时算法：
    提取该设备最近 14 天内的抄表工时增量时序数据，计算加权日均时长：
    $$T_{\text{avg}} = \frac{\sum_{i=1}^{N} w_i \cdot \Delta H_i}{\sum_{i=1}^{N} w_i} \quad (w_i = i, \text{近重远轻})$$
    $$\text{Estimated Days} = \left\lceil \frac{\text{Remaining Hours}}{\max(T_{\text{avg}}, 0.5)} \right\rceil$$
  - 工时抄表双模接口：`POST /api/v1/equipments/{id}/runtime-logs` 支持 `delta_hours` 增量填报与 `reading_hours` 表盘抄表。
* **验证方式**：测试持续与间歇模式设备工时倒计时计算，验证 14 天滑动预测剩余天数，验证预警阈值判定。

### SDR-DEV-012：层级节点级联软删除与资产防孤儿设计
* **对应客户需求**：`CR-DEV-012`
* **所属系统层级**：后端层级管理服务 / 数据库事务
* **设计实现规范**：
  - 接口 `POST /api/v1/equipments/hierarchy-delete`（`require_engineer`）：
  - 接收参数：`factory`, `department`, `system_name`, `cascade_delete_equipments: bool`；
  - 若 `cascade_delete_equipments == True`，单事务中将该层级下所有设备的 `is_deleted` 置为 1，并软删除未完工关联工单；
  - 历史病历完整保留外键，前台通过弹窗提示影响设备数量并强制用户二次确认。
* **验证方式**：级联删除测试层级，断言该层级下所有设备均标记软删除且在活动列表中不可见。

### SDR-DEV-013：用户主动预先创建层级与聚合树双源合并设计
* **对应客户需求**：`CR-DEV-013`
* **所属系统层级**：数据持久化层 / 资产管理 API / 前端交互树
* **设计实现规范**：
  - 持久化层引入 `custom_hierarchies` 表：包含 `id`, `factory`, `department`, `system_name`, `created_by`, `created_at`，加 `UNIQUE(factory, department, system_name)` 联合唯一约束；
  - 架构创建接口：`POST /api/v1/equipments/hierarchy`（`require_engineer`）：
    - 支持用户按需主动预先搭建工厂、部门与系统；
    - 支持三种创建粒度：仅工厂（部门与系统自动落默认占位或由用户选定）、工厂+部门、工厂+部门+系统；
  - 选项补全接口：`GET /api/v1/equipments/hierarchy-options`：向前端设备录入弹窗与全局筛选器下发全厂所有工厂、部门、系统三级扁平去重列表；
  - 双源聚合树：`GET /api/v1/equipments/hierarchy-tree` 联合 `equipments` 表与 `custom_hierarchies` 表执行动态 UNION 聚合去重；对于暂无设备的空层级，设备计数徽标如实展示为 `(0)`；
  - 前端交互：层级树顶栏提供【+ 创建层级】入口，树节点悬浮快捷【➕】操作（工厂节点点击快捷创建部门，部门节点点击快捷创建系统，系统节点点击一键打开带层级预填的录入设备对话框）；
  - 单事务级联同步：当调用 `rename-hierarchy` 或 `hierarchy-delete` 时，单事务中同步更新或级联软删除 `custom_hierarchies` 对应记录；新增设备时自动反向同步登记至 `custom_hierarchies`。
* **验证方式**：调用接口或前台弹窗创建无设备的系统层级，树中立即渲染该系统且计数为 0；在录入设备表单中可从下拉框选出该层级，录入设备后计数即时更新为 1。

### SDR-DEV-014：系统归属设备四级树可视化与单台设备便捷软删除设计
* **对应客户需求**：`CR-DEV-014`
* **所属系统层级**：资产服务 API / 前端交互树 / 列表视图
* **设计实现规范**：
  - 架构树查询接口扩展：`GET /api/v1/equipments/hierarchy-tree` 返回结果由三级扩展为标准四级树形结构（工厂 `factory` $\rightarrow$ 部门 `department` $\rightarrow$ 系统 `system_name` $\rightarrow$ 设备 `equipment`）；
  - 节点数据结构：四级节点赋予全局唯一 `node_key`（格式为 `fac_*`, `dept_*`, `sys_*`, `eq_{id}`），挂载 `id`, `name`, `equipment_code`, `model_spec`, `status` 与 `level: 'equipment'`；
  - 单设备软删除接口：`DELETE /api/v1/equipments/{id}`（全员认证开放 `Depends(get_current_user)`）：
    - 校验设备存在且未删除（否则抛出 404）；
    - 执行原子软删除：`UPDATE equipments SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = :id`；
  - 空系统架构保留机制：当删除某系统下的最后 1 台设备时，系统不触动 `custom_hierarchies` 架构表，该系统在架构树中保留并展示徽标 `(0)`，历史工单与维保记录快照 100% 完整留存；
  - 多视图显式删除入口：
    - 架构树：设备节点悬浮展示 `📋` 查看病历与 `🗑️` 移除设备；
    - 卡片视图：卡片底部增加危险线框按钮 `🗑️ 移除设备`；
    - 表格视图：操作列配置固定宽度的 `🗑️ 移除` 按钮并提供带设备名称的二次确认提示框。
* **验证方式**：创建系统并录入设备，树中正确展开四级子节点；调用删除接口或前端删除，设备从列表消失，系统节点仍存留且计数变为 0，历史工单完好留存。

---

## 第四部分：设备维护单与日常保养系统设计需求 (SDR-MNT)

### SDR-MNT-001：周期保养计划编制与应保倒计时设计
* **对应客户需求**：`CR-MNT-001`
* **所属系统层级**：维保服务 API
* **设计实现规范**：
  `maintenance_plans` 记录设备标准保养计划：
  - 工程师配置保养周期 `interval_days` 与检查清单 JSON `check_items_json`；
  - 系统在每次打卡完成后自动计算：`next_due_date = today + timedelta(days=interval_days)`；
  - 工作台根据 `next_due_date - today <= 3` 触发临期黄色预警。
* **验证方式**：创建周期为 30 天的计划，提交维护单后下次保养日期正确延后 30 天。

### SDR-MNT-002：技术员现场移动打卡与异常说明录入设计
* **对应客户需求**：`CR-MNT-002`
* **所属系统层级**：前端打卡页面 / 维保 API
* **设计实现规范**：
  `POST /api/v1/maintenance/records/submit`：
  - 接收检查项勾选明细 `checklist_results: [{"item": str, "status": "NORMAL"|"ABNORMAL", "remark": str}]`；
  - 校验：若有任意一项为 `ABNORMAL`，必须要求提供 `anomaly_desc`。
* **验证方式**：勾选异常且不填异常描述，提交时系统返回 422 校验失败。

### SDR-MNT-003：维护单“上传即锁定”`is_locked_for_tech` 防篡改设计
* **对应客户需求**：`CR-MNT-003`
* **所属系统层级**：后端切面 / 前端控制
* **设计实现规范**：
  - 技术员点击提交打卡后，落库数据显式设置 `status = 'SUBMITTED'`, `is_locked_for_tech = 1`；
  - 前端：技术员端此记录变为只读，禁用并隐藏编辑/删除按钮；
  - 后端：在 `PUT /api/v1/maintenance/records/{id}` 接口挂载检查切面：
    ```python
    if record.is_locked_for_tech and current_user.role == "TECHNICIAN":
      raise HTTPException(
          status_code=403, detail="维护单已上传锁定，技术员严禁修改，如需更正请联系工程师"
      )
```
* **验证方式**：技术员调用 PUT 修改已提交维护单，接口强行阻断并断言 HTTP 403。

### SDR-MNT-004：工程师独占修改权与强制 `revision_reason` 批注设计
* **对应客户需求**：`CR-MNT-004`
* **所属系统层级**：维保服务 API
* **设计实现规范**：
  接口 `PUT /api/v1/maintenance/records/{id}/revise` 仅限工程师访问（`require_engineer`）：
  - 载荷必须包含非空 `revision_reason: str`；
  - 更新数据：`revised_by_engineer_id = current_user.id`, `revised_at = CURRENT_TIMESTAMP`, `status = 'REVISED_BY_ENGINEER'`;
  - 历史病历中高亮展示修改人与修改原因。
* **验证方式**：工程师修正单据不填 `revision_reason` 报错；填写后成功更新并记录工程师 ID。

### SDR-MNT-005：巡检异常联锁派单与状态跃迁单事务设计
* **对应客户需求**：`CR-MNT-005`
* **所属系统层级**：后端数据库事务引擎
* **设计实现规范**：
  在 `POST /api/v1/maintenance/records/submit` 内部，若 `is_normal == False`：
  - 同一 DB 事务中执行：
    1. 插入 `maintenance_records`；
    2. 插入 `work_orders`（`source = 'INSPECTION'`, `title = f"巡检异常: {anomaly_desc[:20]}"`）；
    3. 反写 `maintenance_records.interlocked_work_order_id = wo.id`；
    4. 执行 `UPDATE equipments SET status = 'REPAIRING' WHERE id = :equipment_id`；
  - 任意一步失败全量回滚。
* **验证方式**：打卡提交异常项，断言生成了关联工单且设备状态变为 `REPAIRING`。

### SDR-MNT-006：动态 SOP 检查项标准扩展与设备级联检索设计
* **对应客户需求**：`CR-MNT-006`
* **所属系统层级**：维保打卡视图与领域服务
* **设计实现规范**：
  - 前端打卡组件支持动态增删行：用户可动态添加自定义检查项目（输入项目名称及核验标准）；
  - 每项单选【合格】或【异常】，检查项列表结构化序列化为 JSON 存储于 `checklist_result_json`；
  - 界面提供【工厂 - 部门 - 系统 - 设备】四级级联选择器，根据层级树逐级收敛过滤目标设备，解决重名与归属混淆；
  - 打卡提交支持携带本次运行工时（`log_runtime_hours`），全项合格时后台自动更新 `last_maintenance_hours = total_running_hours`，开启新一轮倒计时。
* **验证方式**：动态添加自定义检查项并勾选异常，验证提交后正确落库 JSON 并联锁生成工单。

---

## 第五部分：突发故障报修与维修工单系统设计需求 (SDR-WO)

### SDR-WO-001：30秒极速报修载荷与设备状态跃迁设计
* **对应客户需求**：`CR-WO-001`
* **所属系统层级**：工单服务 API
* **设计实现规范**：
  全员开放接口 `POST /api/v1/work-orders`：
  - 最小必要字段：`equipment_id: int`, `title: str`, `urgency: str` (`NORMAL`|`MAJOR`|`CRITICAL`)；
  - 选填字段：`phenomenon: str`, `fault_photo_path: str`；
  - 系统在事务中将设备状态置为 `REPAIRING`，生成工单号 `WO-YYYYMMDD-XXXX`，初始状态为 `PENDING`。
* **验证方式**：提交报修后，设备表状态立即变为 `REPAIRING`，工单出现在待派单列表。

### SDR-WO-002：四态工单流转状态机与流向守卫设计
* **对应客户需求**：`CR-WO-002`
* **所属系统层级**：工单服务状态机引擎
* **设计实现规范**：
  工单状态流向只能按以下合法路径跃迁：
  - `PENDING` $\rightarrow$ `IN_PROGRESS` (派发或接单)
  - `IN_PROGRESS` $\rightarrow$ `PENDING_CONFIRM` (承修人完工并填报根因)
  - `PENDING_CONFIRM` $\rightarrow$ `CLOSED` (工程师现场复核验收结案)
  - 任何逆向或跨步跃迁（如 `PENDING` 直接到 `CLOSED`）直接拒绝并抛出 400 错误。
* **验证方式**：尝试从 `PENDING` 直接结案，断言抛出非法状态跃迁异常。

### SDR-WO-003：工程师看板指派与技术员自主抢单设计
* **对应客户需求**：`CR-WO-003`
* **所属系统层级**：工单服务 API
* **设计实现规范**：
  接口 `PUT /api/v1/work-orders/{id}/dispatch`：
  - 工程师访问：可指定任何有效 `assignee_id`；
  - 技术员访问：`assignee_id` 强制覆盖绑定为 `current_user.id`（自主接单）；
  - 更新工单状态为 `IN_PROGRESS`，记录 `claimed_at = CURRENT_TIMESTAMP`。
* **验证方式**：技术员点击自主接单，承修人成功更新为该技术员，工单进入维修中。

### SDR-WO-004：维修复盘根因与排除步骤强制非空校验设计
* **对应客户需求**：`CR-WO-004`
* **所属系统层级**：工单服务 API
* **设计实现规范**：
  接口 `PUT /api/v1/work-orders/{id}/resolve`：
  - 强制非空字段校验：
    `root_cause`: 长度必须 >= 2（如“轴承缺油抱死”）；
    `solution_steps`: 长度必须 >= 2（如“清洗轴承并加注耐温润滑脂”）；
  - 选填：`spare_parts`, `repair_duration_minutes`；
  - 校验通过后工单状态置为 `PENDING_CONFIRM`。
* **验证方式**：留空 `root_cause` 提交完工，接口返回 HTTP 422 并拒绝流转。

### SDR-WO-005：工程师试车复核验收结案与设备状态恢复设计
* **对应客户需求**：`CR-WO-005`
* **所属系统层级**：工单服务 API
* **设计实现规范**：
  接口 `PUT /api/v1/work-orders/{id}/confirm` 仅限工程师访问（`require_engineer`）：
  - 校验工单当前状态必须为 `PENDING_CONFIRM`；
  - 更新工单 `status = 'CLOSED'`, `completed_at = CURRENT_TIMESTAMP`；
  - 单事务中更新关联设备：`UPDATE equipments SET status = 'RUNNING' WHERE id = :equipment_id`。
* **验证方式**：工程师结案后，断言工单状态变为 `CLOSED`，关联设备状态恢复为 `RUNNING`。

### SDR-WO-006：工单草稿纠错编辑与典型案例标定设计
* **对应客户需求**：`CR-WO-006`
* **所属系统层级**：工单流转服务 / 知识库服务
* **设计实现规范**：
  - 工单草稿编辑接口：`PUT /api/v1/work-orders/{id}` 允许报修人或工程师在工单处于 `PENDING` 或 `IN_PROGRESS` 状态时重新编辑故障标题、详细现象与紧急程度；
  - 完工待验收详情下钻：`PENDING_CONFIRM` 卡片支持弹窗调用 `GET /api/v1/work-orders/{id}` 查看完整的复盘字段（根本原因、排除步骤、维修用时、更换备件）；
  - 典型案例标定接口：`PUT /api/v1/work-orders/{id}/calibrate-typical`（`require_engineer`）：
    - 仅限处于 `CLOSED` 状态的工单；
    - 将 `is_featured_case` 置为 1，自动同步至知识库并在列表展现金色典型案例勋章。
* **验证方式**：测试待处理工单编辑成功；已结案工单点击标定后，知识库列表中成功展示该典型排故案例。

### SDR-WO-007：完工修复照片双通道采集与试车凭证存证设计（拍照直传+本地图库导入）
* **对应客户需求**：`CR-WO-007`
* **所属系统层级**：工单服务 API / 多媒体静态存储 / 前端组件层
* **设计实现规范**：
  - 单张照片上传接口：`POST /api/v1/work-orders/upload-photo`：
    - 接收 `file: UploadFile`（multipart/form-data）；
    - 支持扩展名白名单校验（`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.heic`, `.gif`）与 15MB 尺寸限制；
    - 安全保存至 `data/uploads/repairs/` 目录，生成格式为 `repair_{YYYYMMDD_HHMMSS}_{hex}.{ext}` 的唯一文件名，返回静态 URL（如 `/uploads/repairs/...`）；
  - 批量照片上传接口：`POST /api/v1/work-orders/upload-photos`：接收 `files: List[UploadFile]`，循环保存并返回 URL 数组；
  - 前端通用图片上传组件：`PhotoUploader.vue`（双向绑定 `v-model` 逗号分隔字符串）：
    - 现场直接拍照：通过 `<input type="file" accept="image/*" capture="environment">` 唤起手机/移动端后置环境摄像头；
    - 本地图库导入：通过 `<input type="file" accept="image/*" multiple>` 唤起系统相册/文件选择器批量多选导入；
    - 缩略图列表网格：渲染 100x100px 缩略图、序号徽标与一键删除 `✕` 按钮；
    - 预览交互：集成 `el-image` 穿透全屏大图预览、多图翻页与缩放；
  - 业务流转与结案存证：完工复盘 `PUT /resolve` 与工单纠错 `PUT /{id}` 均支持持久化 `repair_photos`，并在详细信息弹窗与终身病历时间轴中永久展示。
* **验证方式**：模拟拍照与图库上传，文件成功落盘至 uploads/repairs/ 并可通过 HTTP 静态访问；带照片提交完工复盘，工单详情中成功渲染高保真修复照片。

---

## 第六部分：终身病历与排故知识库系统设计需求 (SDR-KB)

### SDR-KB-001：维修+维保+工时三合一病历倒序聚合服务设计
* **对应客户需求**：`CR-KB-001`
* **所属系统层级**：终身病历聚合引擎
* **设计实现规范**：
  接口 `GET /api/v1/equipments/{id}/timeline`：
  - 查询指定设备的三源记录：
    1. `work_orders`: 抽取工单号、报修现象、根本原因、排除步骤、换件、维修人与时间；
    2. `maintenance_records`: 抽取维护单号、打卡人、检查结论、异常说明、工程师修改批注与时间；
    3. `equipment_runtime_logs`: 抽取抄表人、表盘读数、增量工时、备注与时间；
  - 统一映射为事件字典，统一按照事件发生时间倒序排列（最新事件排在最前）；
  - 输出格式化列表供前端时间轴渲染。
* **验证方式**：制造工单、维护单和抄表流水，请求该接口，断言返回按时间严格倒序的综合事件序列。

### SDR-KB-002：结案工单一键萃取至排故知识库设计
* **对应客户需求**：`CR-KB-002`
* **所属系统层级**：知识库服务 API
* **设计实现规范**：
  接口 `POST /api/v1/work-orders/{id}/to-knowledge` 仅限工程师访问（`require_engineer`）：
  - 校验工单状态必须为 `CLOSED`；
  - 提取工单的 `title`、`phenomenon`、`root_cause`、`solution_steps` 自动插入 `knowledge_cases` 表；
  - 标记工单 `is_featured_case = 1`。
* **验证方式**：调用萃取接口后，知识库列表新增对应条目，且工单金标点亮。

### SDR-KB-003：报修输入实时关键词相似度排故推荐引擎设计
* **对应客户需求**：`CR-KB-003`
* **所属系统层级**：推荐算法引擎 / 前端防抖组件
* **设计实现规范**：
  接口 `GET /api/v1/knowledge/recommend?query={text}`：
  - 后端对 `query` 进行多模式分词匹配，查询 `knowledge_cases` 中的 `title`、`phenomenon`、`root_cause`；
  - 优先返回置顶案例（`is_featured = 1`），返回前 5 条最高相关度案例；
  - 前端报修输入框设置 300ms 防抖请求，在右侧弹出“后来人排故参考卡片”。
* **验证方式**：输入“变频器过流”，返回匹配的变频器排故 SOP 案例。

---

## 第七部分：工作台大盘与系统运维系统设计需求 (SDR-SYS)

### SDR-SYS-001：全厂设备四态健康比例与工单大盘聚合设计
* **对应客户需求**：`CR-SYS-001`
* **所属系统层级**：大盘统计服务 API
* **设计实现规范**：
  接口 `GET /api/v1/system/dashboard`：
  - 实时统计设备状态分布：`RUNNING`, `REPAIRING`, `MAINTAINING`, `STOPPED` 各状态台数；
  - 实时统计四态工单数量：`pending_count`, `in_progress_count`, `pending_confirm_count`, `closed_count`；
  - 毫秒级汇总响应。
* **验证方式**：变更设备状态后刷新大盘，数字即时对应更新。

### SDR-SYS-002：角色差异化智能待办事项分发设计
* **对应客户需求**：`CR-SYS-002`
* **所属系统层级**：大盘待办计算服务
* **设计实现规范**：
  大盘接口根据当前用户 Token 角色动态计算专属待办任务：
  - `TECHNICIAN`: `assignee_id = me AND status = 'IN_PROGRESS'` 的工单 + 到期维护任务；
  - `ENGINEER`: `status = 'PENDING'` (待派单) + `status = 'PENDING_CONFIRM'` (待验收) + 到期维保计划；
  - `ADMIN`: 全厂异常与未处理工单总数。
* **验证方式**：技术员与工程师分别请求大盘接口，返回与各自职责严格对应的待办列表。

### SDR-SYS-003：单文件 SQLite 3 WAL 纯 Python 在线热备份 ZIP 设计
* **对应客户需求**：`CR-SYS-003`
* **所属系统层级**：系统备份服务 API
* **设计实现规范**：
  接口 `POST /api/v1/system/backup`（`require_admin`）：
  - 使用 Python 内置 `zipfile.ZipFile`，在 `data/backups/` 目录创建带时间戳的 ZIP；
  - 将 `data/maintainwise.db` 与 `data/uploads/` 递归压入 ZIP 包；
  - 利用 SQLite WAL 模式特性，备份期间数据库读写零中断、零锁死；
  - 返回生成的备份文件名与字节大小。
* **验证方式**：调用备份接口，验证在 `data/backups/` 生成了合法且可解压还原的 ZIP 文件。

### SDR-SYS-004：系统全局参数配置与 SMTP 邮件调度服务设计
* **对应客户需求**：`CR-SYS-004`
* **所属系统层级**：系统配置与邮件调度服务 API
* **设计实现规范**：
  - `system_settings` 表支持存储 `factory_name`, `smtp_host`, `smtp_port`, `smtp_user`, `smtp_pass`, `smtp_sender`, `smtp_recipients`, `smtp_enabled`；
  - 接口 `POST /api/v1/system/test-email` 验证 SMTP 服务器连通性；
  - 告警调度：当设备剩余工时 $\le$ `advance_warning_hours` 时，后台异步派发预警邮件给责任工程师。
* **验证方式**：配置有效 SMTP 并点击测试邮件，验证发信成功；模拟达到预警阈值，系统自动触发邮件推送。

### SDR-SYS-005：网页端在线系统设计文档与帮助中心服务设计
* **对应客户需求**：`CR-SYS-005`
* **所属系统层级**：系统设计文档微核心 / 前端 Markdown 渲染器
* **设计实现规范**：
  - 后端接口：
    1. `GET /api/v1/docs`：读取系统工程文档元数据目录（包含标题、分类、文件名、大小、更新时间）；
    2. `GET /api/v1/docs/{doc_id}`：白名单安全校验后读取指定 Markdown 文件内容并以 UTF-8 文本返回；
  - 前端路由与视图：
    1. 注册 `/docs` 路由，挂载 `DocsReaderView.vue`；
    2. 使用 `marked` 库客户端实时解析渲染 Markdown；
    3. 支持左侧目录按“全部 / 需求规范 / 架构设计 / 部署运维”过滤，支持实时关键字搜索；
    4. 自动提取文档内 H1~H3 标题生成大纲目录，点击平滑滚动跳转；
    5. 主布局左侧侧边栏增加【设计文档与帮助】，顶栏增加【📖 帮助文档】直达入口。
* **验证方式**：访问 `/docs` 页面，成功展示 6 份系统技术文档，点击切换秒级加载，排版优美。

---

## 第八部分：跨平台双轨部署系统设计需求 (SDR-DEP)

### SDR-DEP-001：FastAPI 单端口统一托管 SPA 与回退路由设计
* **对应客户需求**：`CR-CON-003`, `CR-CON-004`
* **所属系统层级**：统一宿主服务层
* **设计实现规范**：
  在 `app/main.py` 中：
  - 挂载静态目录：`app.mount("/assets", StaticFiles(directory=".../dist/assets"))`；
  - 挂载上传目录：`app.mount("/uploads", StaticFiles(directory=".../data/uploads"))`；
  - 注册通配回退路由：未匹配到 API 的所有 GET 请求统一响应返回 `dist/index.html`，实现 Vue HTML5 History 模式单端口托管。
* **验证方式**：单端口 8000 访问页面及直接刷新二级路由 `/equipments` 均正常展示。

### SDR-DEP-002：纯 Python / 预编译 Wheel 零本地编译依赖设计
* **对应客户需求**：`CR-CON-001`, `CR-CON-003`
* **所属系统层级**：依赖管理规范
* **设计实现规范**：
  `requirements.txt` 中严格挑选支持 Windows 官方 Wheel 轮子的成熟纯 Python 库：
  `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `python-jose`, `bcrypt`, `python-multipart`, `aiofiles`, `qrcode`, `pillow`；
  杜绝任何需本地调用 MSVC/gcc 编译器的未知第三方扩展。
* **验证方式**：在无 Visual Studio 编译环境的 Windows 机器上 `pip install` 顺利安装。

### SDR-DEP-003：Python pathlib.Path 路径中立性设计
* **对应客户需求**：`CR-CON-001`
* **所属系统层级**：后端全代码基线
* **设计实现规范**：
  全系统所有文件读写、目录创建、静态挂载强制采用 `pathlib.Path` 对象拼接（`BASE_DIR / "data" / "uploads"`），严禁用字符串手动硬编码 `/` 或 `\`。
* **验证方式**：代码静态扫描无任何手工拼接操作系统专有斜杠行为。

### SDR-DEP-004：Windows 批处理标准 CRLF 换行与 UTF-8 编码设计
* **对应客户需求**：`CR-CON-005`
* **所属系统层级**：部署脚本工程规范
* **设计实现规范**：
  `deploy/windows/*.bat` 及根目录 `maintainwise.bat`、`mw.bat`：
  - 文本换行符强制锁定为 `CRLF (\r\n)`；
  - 根目录配置 `.gitattributes`，声明 `*.bat text eol=crlf`，永久免疫跨操作系统拉取或虚拟机挂载导致的 LF 错位；
  - 脚本第一行统一声明：`@echo off` 与 `chcp 65001 >nul`；
  - 杜绝 Windows 命令提示符执行时出现乱码或因 LF 导致的 `cmd.exe` 指针偏移命令截断与跳转穿透。
* **验证方式**：在中文版 Windows CMD / PowerShell 中执行，汉字清晰且命令正常流转。

### SDR-DEP-005：Linux Shell 与 Windows Batch 0~7 双轨同构脚本设计
* **对应客户需求**：`CR-CON-002`
* **所属系统层级**：运维工具包工程
* **设计实现规范**：
  同时维护功能完全对等的双轨运维体系：
  - 根目录顶级入口：`maintainwise.sh` 与 `maintainwise.bat`，以及简写别名 `mw.sh` 与 `mw.bat`；
  - `maintainwise.bat` 提供参数化与鼠标双击 0~7 交互式菜单双模支持，新增 `test` 前台交互测试启动指令；
  - `deploy/linux/`: `0_deploy_all.sh`, `1_init_env.sh`, `2_start_foreground.sh`, `start_background.sh`, `stop_background.sh`, `status.sh`, `restart_background.sh`, `3_install_service.sh`, `4_start_service.sh`, `5_stop_service.sh`, `6_uninstall_service.sh`, `7_backup_now.sh`, `README_LINUX.txt`；
  - `deploy/windows/`: `0_deploy_all.bat`, `1_init_env.bat`, `2_start_foreground.bat`, `3_install_service.bat`, `4_start_service.bat`, `5_stop_service.bat`, `6_uninstall_service.bat`, `7_backup_now.bat`, `winsw.xml`, `README_WINDOWS.txt`。
* **验证方式**：分别在 Linux 与 Windows 环境执行双轨各编号脚本，服务均正常管理。

### SDR-DEP-006：Linux 进程级后台常驻守护与脱离控制终端运行设计
* **对应客户需求**：`CR-CON-006`
* **所属系统层级**：运维工具包工程 / 容器化与轻量化部署
* **设计实现规范**：
  - 在无 Systemd 守护进程支持的轻量级 Linux 容器环境（如 Docker、Kubernetes 容器或无 init 进程环境）中，避免使用容易因终端断开而挂起的裸 `nohup ... &`；
  - 采用 `setsid python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 < /dev/null >> logs/maintainwise.log 2>&1 &` 启动后台进程，通过重定向标准输入脱离 tty，并独立分配 Session ID，免疫会话断开产生的 `SIGHUP` 信号；
  - 自动化记录进程标识符至 `maintainwise.pid`；
  - 配套标准控制脚本：
    - `deploy/linux/start_background.sh`：启动后台守护并校验健康心跳；
    - `deploy/linux/stop_background.sh`：基于 PID 与端口优雅平滑终止进程（SIGTERM 超时转 SIGKILL）并自动清理 PID 文件；
    - `deploy/linux/status.sh`：检测后台进程存活、PID、内存/CPU 开销、端口监听与最近日志输出；
    - `deploy/linux/restart_background.sh`：原子重启服务；
    - 根目录统一命令行总控：`./maintainwise.sh <action>`（简写 `./mw.sh <action>`），支持 `deploy|start|stop|restart|status|logs|backup`；
  - 一键部署总脚本 `0_deploy_all.sh` 首选项默认联动后台常驻守护启动，保障退出 shell 后业务稳定在线。
* **验证方式**：执行 `./maintainwise.sh start` 后退出当前 SSH 终端会话，重新连接后执行 `./maintainwise.sh status` 断言 PID 与 8000 端口持续在线服务。

---

## 第九部分：客户需求与系统设计需求双向跟踪矩阵 (Traceability Matrix)

| 客户需求编号 (CR) | 客户需求名称 | 映射系统设计需求编号 (SDR) | 系统设计需求简述 | 覆盖状态 |
| :--- | :--- | :--- | :--- | :---: |
| **CR-USR-001** | 三角色严格划分 | `SDR-USR-001`, `SDR-USR-005` | 单表用户枚举、前端菜单过滤与后端切面守卫 | 100% 覆盖 |
| **CR-USR-002** | 管理员人员管理与重置密码 | `SDR-USR-002`, `SDR-USR-004`, `SDR-USR-006`| bcrypt 加盐、用户 CRUD API、一键重置密码与软删除 | 100% 覆盖 |
| **CR-USR-003** | 工程师业务中枢管控权 | `SDR-USR-005`, `SDR-DEV-005`, `SDR-MNT-004`| 工程师独占设备管理、修改维护单与验收权限 | 100% 覆盖 |
| **CR-USR-004** | 技术员现场执行权 | `SDR-USR-005`, `SDR-DEV-006`, `SDR-MNT-002`| 现场打卡、工时抄表与极速报修 | 100% 覆盖 |
| **CR-USR-005** | 8小时长效会话 | `SDR-USR-003` | JWT 480 分钟有效令牌与 Axios 拦截器 | 100% 覆盖 |
| **CR-USR-006** | 180天密码轮换与安全改密 | `SDR-USR-007` | 180天周期审计、超期冻结、独立隔离改密页与修改后强制退出重登 | 100% 覆盖 |
| **CR-DEV-001** | 工厂-部门-系统三级划分 | `SDR-DEV-001` | 扁平三级字段存储与毫秒级动态聚合树 | 100% 覆盖 |
| **CR-DEV-002** | 设备字段刚柔兼顾 | `SDR-DEV-002` | 名称与规格强制非空，数量默认1，参数可选 | 100% 覆盖 |
| **CR-DEV-003** | 设备编码非强制项 | `SDR-DEV-003` | 编码选填，未填后台自动生成 DEV-唯一码 | 100% 覆盖 |
| **CR-DEV-004** | 以设备名称为主检索 | `SDR-DEV-004` | 全局优先按设备名称模糊穿透匹配 | 100% 覆盖 |
| **CR-DEV-005** | 设备台账工程师录入 | `SDR-DEV-005` | 设备管理接口挂载 require_engineer 切面 | 100% 覆盖 |
| **CR-DEV-006** | 技术员运行工时抄表 | `SDR-DEV-006` | 表盘抄表录入，系统自动推算本次增量运转工时 | 100% 覆盖 |
| **CR-DEV-007** | 设备录入极致顺畅 | `SDR-DEV-007` | 输入即建树，保存并继续录入下一台，10秒录一台 | 100% 覆盖 |
| **CR-DEV-008** | 层级多次任意重命名 | `SDR-DEV-008` | 单事务批量原子更名，历史病历外键 ID 不受影响 | 100% 覆盖 |
| **CR-DEV-009** | 层级-设备双模展示与钻取 | `SDR-DEV-009` | 左侧层级树带徽标，右侧表格/卡片双模联动 | 100% 覆盖 |
| **CR-DEV-010** | 一机一码二维码自动生成 | `SDR-DEV-010` | 自动生成二维码图片并支持前端预览与导出 | 100% 覆盖 |
| **CR-DEV-011** | 间歇与持续双模维护预测 | `SDR-DEV-011` | 持续/间歇双模，自适应预警小时，14天滑动预测剩余天数 | 100% 覆盖 |
| **CR-DEV-012** | 层级级联软删除与资产防护 | `SDR-DEV-012` | 厂部系统级联软删除子设备与未完工单，杜绝孤儿数据 | 100% 覆盖 |
| **CR-DEV-013** | 用户主动创建三级层级 | `SDR-DEV-013` | 自定义层级持久化表、独立创建与树形双源合并、空层级挂载设备 | 100% 覆盖 |
| **CR-DEV-014** | 四级树可视与单设备软删除 | `SDR-DEV-014` | 四级展开挂载设备，单设备软删除与空系统架构留存 | 100% 覆盖 |
| **CR-MNT-001** | 工程师编制下发维保计划 | `SDR-MNT-001` | 周期天数+SOP检查清单，下次应保日期自动推算 | 100% 覆盖 |
| **CR-MNT-002** | 技术员现场打卡 | `SDR-MNT-002` | 逐项合格/异常勾选，异常必须录入异常描述 | 100% 覆盖 |
| **CR-MNT-003** | 维护单上传即锁定只读防篡改 | `SDR-MNT-003` | 上传置 `is_locked_for_tech=1`，技术员修改报 403 | 100% 覆盖 |
| **CR-MNT-004** | 工程师独占修改权与强制批注 | `SDR-MNT-004` | 独占修正接口，强制必填 revision_reason 留痕 | 100% 覆盖 |
| **CR-MNT-005** | 巡检异常联锁派单 | `SDR-MNT-005` | 单事务派生创建工单，设备自动置为 REPAIRING | 100% 覆盖 |
| **CR-MNT-006** | 动态自定义检查项目标准 | `SDR-MNT-006` | SOP 检查项动态增删，合格/异常单选判定，厂部级联定位 | 100% 覆盖 |
| **CR-WO-001** | 30秒极速突发报修 | `SDR-WO-001` | 选设备+一句话现象+紧急度，设备变维修态 | 100% 覆盖 |
| **CR-WO-002** | 极简四态工单流转看板 | `SDR-WO-002` | 四态合法跃迁状态机守卫与四泳道看板 | 100% 覆盖 |
| **CR-WO-003** | 工程师派单与技术员抢单双轨 | `SDR-WO-003` | 支持工程师指派与技术员自主接单并发处理 | 100% 覆盖 |
| **CR-WO-004** | 维修复盘根因与步骤强制闭环 | `SDR-WO-004` | 完工强制校验 root_cause 与 solution_steps 非空 | 100% 覆盖 |
| **CR-WO-005** | 工程师现场验收结案 | `SDR-WO-005` | 工程师验收结案，设备状态自动恢复为 RUNNING | 100% 覆盖 |
| **CR-WO-006** | 工单草稿纠错与典型案例标定 | `SDR-WO-006` | 待派单编辑纠错，完工待验收弹窗详情，结案标定典型案例 | 100% 覆盖 |
| **CR-WO-007** | 修复照片拍照与图库双通道 | `SDR-WO-007` | 现场拍照与图库批量上传，PhotoUploader组件与缩放预览 | 100% 覆盖 |
| **CR-KB-001** | 终身维修病历时间轴 | `SDR-KB-001` | 维修+维保+工时三源动态归并倒序时间轴服务 | 100% 覆盖 |
| **CR-KB-002** | 结案工单1键萃取知识库 | `SDR-KB-002` | 提取工单根因步骤沉淀为案例并标定置顶金标 | 100% 覆盖 |
| **CR-KB-003** | 报修实时排故联想 | `SDR-KB-003` | 300ms防抖分词检索，即时浮现历史解决对策 | 100% 覆盖 |
| **CR-SYS-001** | 全厂资产与工单态势大盘 | `SDR-SYS-001` | 设备四态比例与工单大盘毫秒级聚合 | 100% 覆盖 |
| **CR-SYS-002** | 角色差异化智能待办 | `SDR-SYS-002` | 按登录角色精准派发专属待办事项 | 100% 覆盖 |
| **CR-SYS-003** | 单文件 SQLite WAL 一键热备 | `SDR-SYS-003` | 纯 Python 在线打包数据库与 uploads 目录为 ZIP | 100% 覆盖 |
| **CR-SYS-004** | SMTP 预警邮件通知与调度 | `SDR-SYS-004` | 保养临期与抢修邮件自动推送，支持在线测试 | 100% 覆盖 |
| **CR-SYS-005** | 在线设计文档与帮助中心 | `SDR-SYS-005` | 内置 `/docs` 查阅6份技术文档，搜索/大纲/导出/打印 | 100% 覆盖 |
| **CR-CON-001** | Linux 开发 Windows 部署约束 | `SDR-DEP-002`, `SDR-DEP-003` | 纯 Wheel 依赖与 pathlib 路径中立性设计 | 100% 覆盖 |
| **CR-CON-002** | 双轨同构一键部署工具集 | `SDR-DEP-005` | Linux Shell 与 Windows Batch 0~7 对称工具箱 | 100% 覆盖 |
| **CR-CON-003** | Windows 生产端零 Node 依赖 | `SDR-DEP-001`, `SDR-DEP-002` | 前端预编译静态托管，生产端仅需 Python 运行时 | 100% 覆盖 |
| **CR-CON-004** | 单端口全栈交付 (:8000) | `SDR-DEP-001` | 单端口托管 SPA + RESTful API + 多媒体 | 100% 覆盖 |
| **CR-CON-005** | Windows 批处理 CRLF 与 UTF-8 | `SDR-DEP-004` | CRLF 换行 + chcp 65001 >nul，杜绝乱码 | 100% 覆盖 |
| **CR-CON-006** | Linux后台常驻守护与控制套件 | `SDR-DEP-006` | setsid脱离终端会话、PID锁、start/stop/status/restart全套脚本 | 100% 覆盖 |
