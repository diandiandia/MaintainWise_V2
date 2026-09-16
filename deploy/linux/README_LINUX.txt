================================================================================
MaintainWise 2.0 Factory Maintenance System - Linux Deployment Guide
================================================================================

1. Architecture Highlights
--------------------------------------------------------------------------------
- Single-port Full-stack: FastAPI serves both REST API & compiled Vue 3 SPA (Port 8000).
- Single-file SQLite 3 WAL: Zero database configuration, anti-blackout, high concurrency.
- Pure Python: No local C++ compilation required.
- Self-Healing Deployment: Upfront automated installation of OS packages (python3-venv, pip),
  defense against PEP 668, and automated generation of requirements.txt if missing.

2. One-Click Deployment
--------------------------------------------------------------------------------
Recommended Entrance:
  $ bash deploy_linux.sh
  or inside deploy/linux/:
  $ bash 0_deploy_all.sh

Step-by-step Execution:
  1. Initialize Environment:      bash 1_init_env.sh
  2. Foreground Testing:          bash 2_start_foreground.sh  (http://127.0.0.1:8000)
  3. Install Systemd Service:     sudo bash 3_install_service.sh
  4. Start Systemd Service:       sudo bash 4_start_service.sh
  5. Stop Systemd Service:        sudo bash 5_stop_service.sh
  6. Uninstall Systemd Service:   sudo bash 6_uninstall_service.sh
  7. Instant Hot Backup:          bash 7_backup_now.sh

3. Default Credentials (Uniform password: password123)
--------------------------------------------------------------------------------
- Administrator (Full Control):     admin      / password123
- Lead Engineer (Ledger / Orders):  engineer1  / password123
- Technician (Clock-in / Hours):    tech1      / password123
================================================================================
