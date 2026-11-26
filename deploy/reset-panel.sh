#!/bin/bash
# ============================================
#  Sanguo Panel - 重置面板数据
#
#  用于把面板恢复到“空面板”状态（站点 / 数据库记录 / 备份记录 / 任务）。
#  默认保留管理员账号与密码、面板设置。
#
#  用法:
#    sudo ./deploy/reset-panel.sh              # 交互确认，清空业务数据
#    sudo ./deploy/reset-panel.sh -y           # 跳过确认
#    sudo ./deploy/reset-panel.sh --full -y    # 完全重置（删除 panel.db，恢复 admin/admin123）
#
#  所有操作前会自动备份数据库到 backup/，备份文件也会移动到隔离目录，
#  不会被真正删除，可随时手动恢复。
# ============================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="sanguo-panel"
DB_PATH="$PROJECT_ROOT/backend/panel.db"
BACKUP_DIR="$PROJECT_ROOT/backup"
VENV_PY="$PROJECT_ROOT/venv/bin/python"
TS="$(date +%Y%m%d_%H%M%S)"
QUARANTINE="$BACKUP_DIR/_reset_$TS"

FULL=false
ASSUME_YES=false

for arg in "$@"; do
  case "$arg" in
    --full) FULL=true ;;
    -y|--yes) ASSUME_YES=true ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "未知参数: $arg"; exit 1 ;;
  esac
done

C_GRN=$'\033[92m'; C_YEL=$'\033[93m'; C_RED=$'\033[91m'; C_CYN=$'\033[96m'; C_RST=$'\033[0m'
info() { echo "${C_GRN}[✓]${C_RST} $*"; }
warn() { echo "${C_YEL}[!]${C_RST} $*"; }
step() { echo; echo "${C_CYN}==> $*${C_RST}"; }

[ "$(id -u)" -eq 0 ] || { echo "${C_RED}[✗]${C_RST} 请使用 root 运行：sudo $0"; exit 1; }
[ -x "$VENV_PY" ] || { echo "${C_RED}[✗]${C_RST} 未找到 venv：$VENV_PY"; exit 1; }

if $FULL; then
  warn "完全重置：将删除 panel.db，管理员恢复为 admin / admin123，所有面板数据丢失。"
else
  warn "将清空站点、数据库记录、备份记录与任务（保留管理员账号和面板设置）。"
fi

if ! $ASSUME_YES; then
  read -r -p "确认继续？输入 yes 回车: " ans
  [ "$ans" = "yes" ] || { echo "已取消。"; exit 0; }
fi

step "停止面板服务"
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
sleep 1

mkdir -p "$BACKUP_DIR"

if $FULL; then
  if [ -f "$DB_PATH" ]; then
    cp -a "$DB_PATH" "$BACKUP_DIR/panel.db.full-reset-$TS.bak"
    info "已备份数据库: backup/panel.db.full-reset-$TS.bak"
    rm -f "$DB_PATH"
  fi
  PYTHONPATH="$PROJECT_ROOT" "$VENV_PY" backend/init_db.py
  info "已重新初始化数据库（admin / admin123）"
else
  if [ ! -f "$DB_PATH" ]; then
    warn "panel.db 不存在，跳过数据清理"
  else
    cp -a "$DB_PATH" "$BACKUP_DIR/panel.db.reset-$TS.bak"
    info "已备份数据库: backup/panel.db.reset-$TS.bak"

    "$VENV_PY" - "$DB_PATH" <<'PY'
import sqlite3, sys
db = sys.argv[1]
tables = ["sites", "backups", "backup_schedules", "tasks", "site_options"]
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys=OFF")
existing = {r[0] for r in cur.execute("select name from sqlite_master where type='table'")}
for t in tables:
    if t in existing:
        cur.execute(f"DELETE FROM {t}")
        try:
            cur.execute("DELETE FROM sqlite_sequence WHERE name=?", (t,))
        except sqlite3.OperationalError:
            pass
conn.commit()
for t in tables:
    if t in existing:
        n = cur.execute(f"select count(*) from {t}").fetchone()[0]
        print(f"  {t}: {n} rows")
conn.close()
PY
    info "业务数据已清空（管理员与设置保留）"
  fi
fi

step "隔离旧备份文件"
mkdir -p "$QUARANTINE"
shopt -s nullglob
moved=0
for f in "$BACKUP_DIR"/*.zip "$BACKUP_DIR"/*.tar.gz "$BACKUP_DIR"/*.sql; do
  mv "$f" "$QUARANTINE"/
  moved=$((moved + 1))
done
shopt -u nullglob
if [ "$moved" -gt 0 ]; then
  info "已移动 $moved 个备份文件到 backup/_reset_$TS/"
else
  info "没有需要移动的备份文件"
fi

# 清空面板备份记录（保留备份计划配置）
if [ -f "$BACKUP_DIR/panel_backups.json" ]; then
  cp -a "$BACKUP_DIR/panel_backups.json" "$QUARANTINE/panel_backups.json.bak" 2>/dev/null || true
  echo "[]" > "$BACKUP_DIR/panel_backups.json"
  info "已清空面板备份记录"
fi

step "启动面板服务"
systemctl start "$SERVICE_NAME" 2>/dev/null || true
for _ in $(seq 1 30); do
  if curl -fs "http://127.0.0.1:8000/api/v1/system/status" >/dev/null 2>&1; then
    info "面板已恢复运行：http://localhost:8000"
    break
  fi
  sleep 1
done

echo
info "重置完成。数据库备份位于 backup/panel.db.*-$TS.bak"
echo "  如需恢复：systemctl stop $SERVICE_NAME && cp <备份文件> $DB_PATH && systemctl start $SERVICE_NAME"
