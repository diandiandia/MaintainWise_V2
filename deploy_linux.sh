#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Root Linux One-Click Deployment Shortcut
# ==============================================================================
set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/deploy/linux/0_deploy_all.sh"
