================================================================================
MaintainWise 2.0 Factory Maintenance System - Windows Server Deployment Guide
================================================================================

1. Architecture Highlights
--------------------------------------------------------------------------------
- Single-port Full-stack: FastAPI serves REST API & compiled Vue 3 SPA on port 8000.
  No Node.js or Nginx required on Windows Server.
- High Reliability Storage: SQLite 3 (WAL mode) at data/maintainwise.db.
- Zero C++ Compilation: Pure Python and pre-compiled wheels only.

2. Three-Step Deployment
--------------------------------------------------------------------------------
[Step 1] Install Python 3.10+
  Download and install Python 3.10+ from python.org. Check "Add python.exe to PATH".

[Step 2] One-Click Initialization
  Double-click root shortcut:
    deploy_windows.bat
  or in deploy\windows:
    0_deploy_all.bat   (or 1_init_env.bat)

[Step 3] Run the Server
  Option A (Interactive Test):
    Double click [ 2_start_foreground.bat ]
    Open browser: http://127.0.0.1:8000

  Option B (Windows Background Service):
    1. Right-click and Run as Administrator: [ 3_install_service.bat ]
    2. Run: [ 4_start_service.bat ]
    Service starts in background and auto-starts on system boot.

3. Credentials (Uniform password: password123)
--------------------------------------------------------------------------------
- Administrator:  admin      / password123
- Lead Engineer:  engineer1  / password123
- Technician:     tech1      / password123

4. Backup
--------------------------------------------------------------------------------
Double-click [ 7_backup_now.bat ] anytime to create a timestamped ZIP backup.

5. Full Detailed Documentation
--------------------------------------------------------------------------------
For comprehensive firewall configuration, mobile tablet access, offline 
deployment, disaster recovery, and FAQ, please read:
  docs\windows_deployment_guide.md
================================================================================
