#!/bin/bash
# ============================================
#  Sanguo Panel - 安装为系统级服务 (systemd)
#
#  安装后：
#    systemctl start|stop|restart|status sanguo-panel
#    systemctl enable sanguo-panel     # 开机自启（安装脚本已自动启用）
#
#  面板前端会被构建为静态文件，由后端在同一端口直接提供，
#  因此整个面板只需要一个系统服务，类似宝塔面板。
#
#  用法:
#    sudo ./deploy/install-service.sh              # 默认端口 8000
#    sudo PANEL_PORT=8888 ./deploy/install-service.sh
# ============================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PANEL_PORT="${PANEL_PORT:-8000}"
SERVICE_NAME="sanguo-panel"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
VENV_PY="$PROJECT_ROOT/venv/bin/python"

C_GRN=$'\033[92m'; C_YEL=$'\033[93m'; C_RED=$'\033[91m'; C_CYN=$'\033[96m'; C_RST=$'\033[0m'
info() { echo "${C_GRN}[✓]${C_RST} $*"; }
warn() { echo "${C_YEL}[!]${C_RST} $*"; }
err()  { echo "${C_RED}[✗]${C_RST} $*"; }
step() { echo; echo "${C_CYN}==> $*${C_RST}"; }

[ "$(id -u)" -eq 0 ] || { err "请使用 root 运行：sudo $0"; exit 1; }
command -v systemctl >/dev/null 2>&1 || { err "当前系统没有 systemd，无法安装系统服务"; exit 1; }

cd "$PROJECT_ROOT"

# ---------- 1. Python 依赖 ----------
step "检查 Python 虚拟环境"
if [ ! -x "$VENV_PY" ]; then
  info "创建 venv"
  python3 -m venv "$PROJECT_ROOT/venv"
fi
"$VENV_PY" -c "import fastapi, uvicorn" >/dev/null 2>&1 || {
  info "安装 Python 依赖"
  "$VENV_PY" -m pip install --upgrade pip setuptools wheel >/dev/null
  "$VENV_PY" -m pip install -r requirements.txt
}
info "Python 依赖就绪"

# ---------- 2. 数据库 ----------
if [ ! -f "$PROJECT_ROOT/backend/panel.db" ]; then
  step "初始化面板数据库"
  PYTHONPATH="$PROJECT_ROOT" "$VENV_PY" backend/init_db.py
  info "数据库已初始化（默认账号 admin / admin123）"
fi

# ---------- 3. 前端构建 ----------
step "构建前端"
command -v npm >/dev/null 2>&1 || { err "未找到 npm，请先安装 Node.js >= 20.19"; exit 1; }
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [ "$NODE_MAJOR" -lt 20 ]; then
  err "Node.js 版本过低（当前 $(node -v)），Vite 7 需要 >= 20.19"
  exit 1
fi
cd "$PROJECT_ROOT/frontend"
if [ -f pnpm-lock.yaml ]; then
  command -v pnpm >/dev/null 2>&1 || npm install -g pnpm >/dev/null
  pnpm install
  pnpm run build
else
  [ -d node_modules ] || npm install --no-audit --no-fund
  npm run build
fi
cd "$PROJECT_ROOT"
[ -f "$PROJECT_ROOT/frontend/dist/index.html" ] || { err "前端构建失败：缺少 frontend/dist/index.html"; exit 1; }
info "前端已构建到 frontend/dist"

# ---------- 4. 释放旧的手动进程 ----------
step "停止遗留的手动进程（如有）"
pkill -f "uvicorn backend.main:app" 2>/dev/null && warn "已停止手动启动的后端" || true
pkill -f "vite" 2>/dev/null && warn "已停止手动启动的前端" || true
sleep 1

# ---------- 5. 写入 systemd 单元 ----------
step "安装 systemd 服务：$SERVICE_NAME"
cat > "$UNIT_PATH" <<EOF
[Unit]
Description=Sanguo Panel (Web Hosting Control Panel)
Documentation=https://github.com/zhangst23/sanguo-panel
After=network-online.target mariadb.service redis-server.service
Wants=network-online.target
# 面板本身不因 MariaDB/Redis 未安装而启动失败
StartLimitIntervalSec=0

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONPATH=$PROJECT_ROOT
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV_PY -m uvicorn backend.main:app --host 0.0.0.0 --port $PANEL_PORT
Restart=always
RestartSec=3
LimitNOFILE=65535
# 面板需要管理 OpenLiteSpeed / MariaDB / 站点文件，保留 root 权限
NoNewPrivileges=no

[Install]
WantedBy=multi-user.target
EOF
info "单元文件：$UNIT_PATH"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME" >/dev/null
systemctl restart "$SERVICE_NAME"

# ---------- 6. 防火墙放行 ----------
step "检查防火墙"
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "^Status: active"; then
  ufw allow "$PANEL_PORT/tcp" comment 'Sanguo Panel' >/dev/null && info "已放行 ${PANEL_PORT}/tcp"
else
  info "未启用 UFW，跳过防火墙配置（如有云安全组请手动放行 ${PANEL_PORT}）"
fi

# ---------- 7. 健康检查 ----------
step "等待面板就绪"
READY=false
for _ in $(seq 1 60); do
  if curl -fs "http://127.0.0.1:${PANEL_PORT}/api/v1/system/status" >/dev/null 2>&1; then
    READY=true; break
  fi
  sleep 1
done

if $READY; then
  info "面板服务已启动"
  echo
  systemctl --no-pager --full status "$SERVICE_NAME" | head -12
  echo
  PUBLIC_IP="$(curl -s --max-time 3 https://api.ipify.org 2>/dev/null || echo localhost)"
  info "面板入口:  http://${PUBLIC_IP}:${PANEL_PORT}"
  info "本机访问:  http://localhost:${PANEL_PORT}"
  info "API 文档:  http://localhost:${PANEL_PORT}/api-docs"
  info "默认账号:  admin / admin123（请尽快修改）"
else
  err "服务已安装但健康检查失败，请查看日志："
  echo "  journalctl -u $SERVICE_NAME -n 100 --no-pager"
  exit 1
fi
