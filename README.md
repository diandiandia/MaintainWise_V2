# MaintainWise 2.0 智能工厂设备管理系统

MaintainWise 2.0 是专为智能制造工厂打造的高性能、轻量化设备资产、现场维护与智能排故系统。

---

## 📖 核心文档与部署指南

* 🪟 **[Windows 生产环境部署与运维指南](file:///root/MaintainWise_V2/docs/windows_deployment_guide.md)**：包含全自动一键向导、Windows Service 守护进程、车间防火墙与移动端配置、灾备热备份及离线部署方案。
* 🐧 **Linux 生产环境一键部署**：直接执行 `bash deploy_linux.sh` 即可完成全自动环境依赖安装、系统服务守护与自启配置。
* 📋 **系统需求与架构设计规范**：详见 `docs/` 目录下的 SRS 与 SDD 设计规范文档。

---

## 🚀 极速部署指引

### Windows 快速部署
1. 安装 **Python 3.10+** 并勾选 `Add python.exe to PATH`；
2. 双击根目录下的 **`deploy_windows.bat`**；
3. 选择 `[1]` 立即进入前台测试，或选择 `[2]` 安装为 Windows 后台自启服务；
4. 打开浏览器访问：`http://127.0.0.1:8000`。

### Linux 快速部署
```bash
# Ubuntu / Debian / CentOS / RHEL
bash deploy_linux.sh
```

---

## 🔑 初始账号体系（初始密码：password123）

* **系统管理员**：`admin`
* **主管工程师**：`engineer1`
* **现场技术员**：`tech1`

> **安全提示**：系统已启用等保合规安全机制，首次登录需修改初始密码，密码有效期 180 天。
