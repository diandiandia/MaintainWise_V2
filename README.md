# MaintainWise 2.0 智能工厂设备在线化便利系统

MaintainWise 2.0 是专为智能制造工厂打造的高性能、轻量化设备资产台账、现场维护打卡与后来人排故知识库系统。系统采用 **FastAPI + Vue 3 + SQLite WAL** 单端口全栈交付架构，具备极低资源占用、高并发读写与跨平台部署能力。

---

## 📖 核心技术规范与指南

系统全生命周期工程规范位于 [`docs/`](file:///root/MaintainWise_V2/docs) 目录，且已完全集成至系统前端【📖 帮助文档】（`/system-docs`）支持在线全文检索与大纲导航：

1. [1. 客户需求说明书 (CRS)](file:///root/MaintainWise_V2/docs/1_customer_requirements_specification.md)：车间业务痛点、CR-* 需求条目与角色权限矩阵
2. [2. 系统设计说明书 (SDD)](file:///root/MaintainWise_V2/docs/2_system_design_document.md)：高并发架构、双模预测工时算法、数据流图与高可用设计
3. [3. 系统设计需求规格说明书 (SysRS)](file:///root/MaintainWise_V2/docs/3_system_design_requirements_specification.md)：SDR-* 条目化系统设计需求与双向追溯矩阵
4. [4. 软件设计说明书 (SwDD)](file:///root/MaintainWise_V2/docs/4_software_design_document.md)：物理表 DDL、REST API 接口契约、状态机跃迁守卫
5. [5. 软件设计需求规格说明书 (SwDRS)](file:///root/MaintainWise_V2/docs/5_software_design_requirements_specification.md)：SWR-* 软件模块需求、Pytest 自动化测试映射
6. [6. 间歇运行设备管理实操手册](file:///root/MaintainWise_V2/docs/intermittent_equipment_operations_guide.md)：间歇/持续双模设备管理、工时抄表与滑动加权预测操作
7. [7. Windows 生产环境部署与运维指南](file:///root/MaintainWise_V2/docs/windows_deployment_guide.md)：Windows Server 一键向导、WinSW 服务安装、防火墙与热备方案

---

## 📂 项目标准文件结构拓扑

```
MaintainWise_V2/
├── README.md                        # 项目主说明文档与极速上手指南
├── .gitignore                       # Git 忽略配置 (屏蔽本地库、pid锁与运行日志)
├── maintainwise.sh                  # Linux 根目录：统一总控脚本 (./mw.sh 为极简别名)
├── maintainwise.bat                 # Windows 根目录：统一总控脚本 (mw.bat 为极简别名)
│
├── backend/                         # 后端工程目录 (Python 3.10+ / FastAPI 微核心)
│   ├── app/
│   │   ├── api/v1/endpoints/        # RESTful API 端点控制器
│   │   │   ├── auth.py              # 认证与长效 Token
│   │   │   ├── users.py             # 人员管理与密码重置
│   │   │   ├── equipments.py        # 设备台账、层级架构、工时抄表
│   │   │   ├── maintenance.py       # 维保计划、技术员打卡与锁定、工程师修正
│   │   │   ├── work_orders.py       # 30秒极速报修、四态看板、复盘结案
│   │   │   ├── knowledge.py         # 后来人排故知识库与智能推荐
│   │   │   ├── system.py            # 大盘统计、系统配置与热备份
│   │   │   └── docs.py              # 在线技术设计文档服务
│   │   ├── core/                    # 核心安全与依赖注入
│   │   │   ├── config.py            # 全局配置 (Pydantic Settings)
│   │   │   ├── security.py          # 原生 bcrypt 密码散列与 JWT
│   │   │   └── deps.py              # 数据库连接与 RBAC 权限切面
│   │   ├── db/                      # 数据持久化底层
│   │   │   ├── session.py           # SQLite 连接上下文与 WAL 模式注入
│   │   │   └── init_db.py           # DDL 初始化与预置种子数据
│   │   ├── schemas/                 # Pydantic 校验模型 (输入/输出)
│   │   ├── services/                # 独立业务领域服务 (二维码/病历/备份/推荐)
│   │   └── main.py                  # 单端口统一宿主 (API + 预编译 SPA 托管)
│   ├── tests/
│   │   └── test_backend_api.py      # 13 项端到端全链路 Pytest 自动化集成测试
│   └── requirements.txt             # 纯 Wheel 无本地编译依赖清单
│
├── frontend/                        # 前端工程目录 (Vue 3 + TypeScript + Vite)
│   ├── src/
│   │   ├── api/                     # 后端 API 接口客户端封装
│   │   ├── components/              # 终身病历抽屉等复用组件
│   │   ├── layout/                  # 系统主布局框架
│   │   ├── router/                  # Vue Router 路由守卫与权限过滤
│   │   ├── stores/                  # Pinia 响应式状态管理 (user, app)
│   │   └── views/                   # 各业务功能页面
│   │       ├── auth/                # 首次登录强制改密独立安全视图
│   │       ├── dashboard/           # 车间态势大盘
│   │       ├── equipments/          # 设备资产与架构层级管理
│   │       ├── maintenance/         # 维保计划与现场打卡
│   │       ├── workorders/          # 四态流转看板
│   │       ├── knowledge/           # 后来人排故知识库
│   │       ├── users/               # 人员管理 (管理员专属)
│   │       ├── settings/            # 系统设置与热备份
│   │       └── docs/                # 在线设计文档与帮助中心
│   └── dist/                        # 预编译静态前端产物 (供后端直接托管)
│
├── deploy/                          # 双轨部署工具包
│   ├── linux/                       # Linux 脚本工具箱
│   │   ├── 0_deploy_all.sh          # 全自动环境校验、依赖安装与服务配置向导
│   │   ├── 1_init_env.sh            # 虚拟环境初始化与依赖安装
│   │   ├── 2_start_foreground.sh    # 前台交互调试模式
│   │   ├── start_background.sh      # setsid 后台守护启动 (退出 Shell 持续运行)
│   │   ├── stop_background.sh       # 安全终止后台进程与清理 PID
│   │   ├── status.sh                # 状态诊断与实时日志探针
│   │   ├── restart_background.sh    # 守护重启脚本
│   │   ├── 3_install_service.sh     # 自动生成并注册 Systemd 服务
│   │   ├── 4_start_service.sh       # 启动 Systemd 服务
│   │   ├── 5_stop_service.sh        # 停止 Systemd 服务
│   │   ├── 6_uninstall_service.sh   # 卸载 Systemd 服务
│   │   ├── 7_backup_now.sh          # 立即执行一次热备份
│   │   └── README_LINUX.txt         # Linux 部署说明
│   └── windows/                     # Windows 批处理工具箱 (全部 CRLF + UTF-8)
│       ├── 0_deploy_all.bat         # Windows 全自动向导
│       ├── 1_init_env.bat           # 依赖与数据库初始化
│       ├── 2_start_foreground.bat   # 前台测试启动
│       ├── 3_install_service.bat    # 安装为 Windows 独立服务 (WinSW)
│       ├── 4_start_service.bat      # 启动 Windows 服务
│       ├── 5_stop_service.bat       # 停止 Windows 服务
│       ├── 6_uninstall_service.bat  # 卸载 Windows 服务
│       ├── 7_backup_now.bat         # 立即备份
│       ├── winsw.xml                # WinSW 服务定义配置
│       └── README_WINDOWS.txt       # Windows 部署说明
│
├── docs/                            # 7 份全生命周期技术规格与实操指南
├── data/                            # 单机持久化存储目录
│   ├── maintainwise.db              # SQLite 3 WAL 单文件数据库
│   ├── uploads/                     # 多媒体附件与设备二维码图片
│   └── backups/                     # 一键热备份 ZIP 归档包目录
└── logs/                            # 生产运行时日志目录 (maintainwise.log)
```

---

## 🚀 极速部署指引与常用运维命令

### Linux 环境（统一单入口总控）
```bash
# 1. 首次完整安装与部署向导
./maintainwise.sh deploy    # 或 ./mw.sh deploy

# 2. 日常快捷运维指令 (支持参数调用)
./maintainwise.sh start     # 启动后台守护进程 (退出终端不中断)
./maintainwise.sh status    # 查看运行状态、PID、CPU/内存占用与日志
./maintainwise.sh restart   # 重启后台守护服务
./maintainwise.sh stop      # 停止后台服务
./maintainwise.sh logs      # 实时追踪最新运行日志 (tail -f)
./maintainwise.sh backup    # 一键执行 SQLite WAL 热备份
```

### Windows 环境（统一单入口总控）
1. 安装 **Python 3.10+**（勾选 `Add python.exe to PATH`）；
2. 命令行执行常用运维指令：
   ```cmd
   maintainwise.bat deploy    :: 一键完整安装向导
   maintainwise.bat start     :: 启动 Windows 后台服务
   maintainwise.bat status    :: 查看服务状态与端口监听
   maintainwise.bat restart   :: 重启 Windows 服务
   maintainwise.bat stop      :: 停止 Windows 服务
   ```
3. 打开浏览器访问：`http://127.0.0.1:8000`。

---

## 🔑 初始账号体系（统一初始密码：`password123`）

* **系统管理员**：`admin`（人员账号管控、系统参数配置、一键热备份）
* **主管工程师**：`engineer1`（设备资产建档、三级架构维护、维保计划制定、维护单修正、验收结案、知识库萃取）
* **现场技术员**：`tech1`（工时抄表填报、维保日常打卡、30秒快速报修、工单接单抢单排故）

> **安全机制**：系统已启用等保合规安全机制，首次登录必须修改初始密码；修改密码后强制退出，需使用新密码重新鉴权登录。密码有效期 180 天。
