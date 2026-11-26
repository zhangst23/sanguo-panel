#!/bin/bash
# 卸载 Sanguo Panel 系统服务（不会删除项目文件、数据库和站点数据）
set -euo pipefail

SERVICE_NAME="sanguo-panel"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

[ "$(id -u)" -eq 0 ] || { echo "请使用 root 运行：sudo $0"; exit 1; }

if [ -f "$UNIT_PATH" ]; then
  systemctl stop "$SERVICE_NAME" 2>/dev/null || true
  systemctl disable "$SERVICE_NAME" 2>/dev/null || true
  rm -f "$UNIT_PATH"
  systemctl daemon-reload
  echo "[✓] 已卸载 $SERVICE_NAME 系统服务"
else
  echo "[!] 未找到 $SERVICE_NAME 服务，无需卸载"
fi

echo "项目文件、panel.db 与站点数据均已保留。"
