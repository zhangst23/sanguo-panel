#!/bin/bash
# ============================================
#  Sanguo Panel - 简易启动 / 状态管理脚本
#
#  推荐方式：安装为系统服务后，用 systemctl 管理
#    sudo ./deploy/install-service.sh
#    systemctl {start|stop|restart|status} sanguo-panel
#
#  本脚本为便捷入口：
#    ./start.sh          启动全部服务（已运行的会跳过）
#    ./start.sh status   查看各服务运行状态与访问地址
#    ./start.sh stop     停止全部服务
#    ./start.sh restart  重启全部服务
#
#  - 已安装 sanguo-panel 系统服务时 → 通过 systemctl 管理
#  - 未安装时 → 回退为 venv + vite 的手动开发模式
# ============================================

set -u

# ---------- 配置 ----------
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PANEL_PORT=8000
FRONTEND_PORT=5173
LOG_DIR="$PROJECT_ROOT/logs"
SERVICE_NAME="sanguo-panel"

# ---------- 颜色（非终端时不加颜色） ----------
if [ -t 1 ]; then
  C_RED=$'\033[91m'; C_GRN=$'\033[92m'; C_YEL=$'\033[93m'
  C_CYN=$'\033[96m'; C_BLD=$'\033[1m'; C_RST=$'\033[0m'
else
  C_RED=; C_GRN=; C_YEL=; C_CYN=; C_BLD=; C_RST=
fi
info() { echo -e "${C_GRN}[✓]${C_RST} $*"; }
warn() { echo -e "${C_YEL}[!]${C_RST} $*"; }
err()  { echo -e "${C_RED}[✗]${C_RST} $*"; }
step() { echo -e "\n${C_CYN}${C_BLD}==> $*${C_RST}"; }

# 非 root 时，调用 systemctl 自动加 sudo
SD=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
  SD="sudo"
fi

# ---------- 检测 systemd 与面板服务 ----------
USE_SYSTEMD=false
if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
  USE_SYSTEMD=true
fi

HAS_PANEL_UNIT=false
if $USE_SYSTEMD && systemctl list-unit-files "${SERVICE_NAME}.service" 2>/dev/null | grep -q "^${SERVICE_NAME}.service"; then
  HAS_PANEL_UNIT=true
fi

# ---------- 健康检查 ----------
backend_ok()  { curl -fs "http://127.0.0.1:$PANEL_PORT/api/v1/system/status" >/dev/null 2>&1; }
frontend_ok() {
  if $HAS_PANEL_UNIT; then
    # 系统服务模式下前端由后端同端口提供
    backend_ok
  else
    curl -fs "http://127.0.0.1:$FRONTEND_PORT" >/dev/null 2>&1
  fi
}

# ---------- 状态 ----------
do_status() {
  step "服务状态"
  if $HAS_PANEL_UNIT; then
    for svc in "$SERVICE_NAME" mariadb redis-server openlitespeed; do
      active=$($SD systemctl is-active "$svc" 2>/dev/null)
      if [ "$active" = "active" ]; then
        info "$svc 进程运行中"
      else
        warn "$svc 未运行 (systemctl: $active)"
      fi
    done
    echo
    if backend_ok; then info "面板端口 :$PANEL_PORT 已响应 ✅"; else warn "面板端口 :$PANEL_PORT 无响应 ❌（运行 ./start.sh restart）"; fi
  elif $USE_SYSTEMD; then
    for svc in mariadb redis-server openlitespeed; do
      active=$($SD systemctl is-active "$svc" 2>/dev/null)
      if [ "$active" = "active" ]; then
        info "$svc 进程运行中"
      else
        warn "$svc 未运行 (systemctl: $active)"
      fi
    done
    echo
    backend_ok  && info "后端  (:$PANEL_PORT) 运行中（手动模式）" || warn "后端  (:$PANEL_PORT) 未运行"
    frontend_ok && info "前端  (:$FRONTEND_PORT) 运行中（手动模式）" || warn "前端  (:$FRONTEND_PORT) 未运行"
  else
    backend_ok  && info "后端  (:$PANEL_PORT) 运行中" || warn "后端  (:$PANEL_PORT) 未运行"
    frontend_ok && info "前端  (:$FRONTEND_PORT) 运行中" || warn "前端  (:$FRONTEND_PORT) 未运行"
  fi

  echo
  backend_ok  && info "后端 API 就绪:  http://localhost:$PANEL_PORT"      || warn "后端 API 未就绪"
  if $HAS_PANEL_UNIT; then
    info "面板界面就绪:  http://localhost:$PANEL_PORT"
  else
    frontend_ok && info "前端界面就绪:  http://localhost:$FRONTEND_PORT" || warn "前端界面未就绪"
  fi

  echo
  echo -e "  本机访问: http://localhost:$PANEL_PORT$($HAS_PANEL_UNIT || echo "  (前端 :$FRONTEND_PORT)")"
  echo -e "  API 文档: http://localhost:$PANEL_PORT/api-docs"

  if ! $HAS_PANEL_UNIT; then
    echo
    warn "尚未安装系统服务，当前为手动/开发模式"
    echo "  安装为开机自启的系统级面板服务：sudo ./deploy/install-service.sh"
  fi
}

# ---------- 等待就绪 ----------
wait_ready() {
  step "等待服务就绪"
  for _ in $(seq 1 60); do backend_ok && break; sleep 1; done
  if ! $HAS_PANEL_UNIT; then
    for _ in $(seq 1 60); do frontend_ok && break; sleep 1; done
  fi
}

# ---------- 手动启动（开发模式回退方案） ----------
start_manual() {
  mkdir -p "$LOG_DIR"
  if [ ! -x "$PROJECT_ROOT/venv/bin/python" ]; then
    err "未找到虚拟环境 $PROJECT_ROOT/venv"
    echo "  请运行：sudo ./deploy/install-service.sh（会安装依赖、构建前端并注册系统服务）"
    exit 1
  fi

  if backend_ok; then
    info "后端已在运行，跳过"
  else
    ( cd "$PROJECT_ROOT"
      PYTHONPATH="$PROJECT_ROOT" nohup ./venv/bin/python -m uvicorn backend.main:app \
        --host 0.0.0.0 --port "$PANEL_PORT" --reload --reload-exclude "*.db" \
        > "$LOG_DIR/backend.log" 2>&1 &
    )
    info "后端已在后台启动（日志: $LOG_DIR/backend.log）"
  fi

  if frontend_ok; then
    info "前端已在运行，跳过"
  else
    ( cd "$PROJECT_ROOT/frontend"
      nohup npm run dev -- --host 0.0.0.0 > "$LOG_DIR/frontend.log" 2>&1 &
    )
    info "前端已在后台启动（日志: $LOG_DIR/frontend.log）"
  fi
}

# ---------- 启动 ----------
do_start() {
  step "启动服务"
  if $HAS_PANEL_UNIT; then
    for svc in mariadb redis-server openlitespeed; do
      if $SD systemctl is-active --quiet "$svc" 2>/dev/null; then
        info "$svc 已在运行，跳过"
      elif $SD systemctl start "$svc" 2>/dev/null; then
        info "已启动 $svc"
      else
        warn "启动 $svc 失败（面板本身仍可运行，详情: $SD journalctl -u $svc -n 50）"
      fi
    done

    if $SD systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null && ! backend_ok; then
      warn "$SERVICE_NAME 进程在但端口无响应，重启中…"
      $SD systemctl restart "$SERVICE_NAME" && info "已重启 $SERVICE_NAME" || warn "重启 $SERVICE_NAME 失败"
    elif ! $SD systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
      if $SD systemctl start "$SERVICE_NAME" 2>/dev/null; then
        info "已启动 $SERVICE_NAME"
      else
        warn "启动 $SERVICE_NAME 失败（详情: $SD journalctl -u $SERVICE_NAME -n 50）"
      fi
    else
      info "$SERVICE_NAME 已在运行，跳过"
    fi
  else
    start_manual
  fi
  wait_ready
  do_status
}

# ---------- 停止 ----------
do_stop() {
  step "停止服务"
  if $HAS_PANEL_UNIT; then
    $SD systemctl stop "$SERVICE_NAME" 2>/dev/null && info "已停止 $SERVICE_NAME" || true
    info "面板服务已停止（MariaDB / Redis / OpenLiteSpeed 未受影响）"
  else
    pkill -f "uvicorn backend.main:app" 2>/dev/null && info "已停止后端" || true
    pkill -f "vite" 2>/dev/null && info "已停止前端" || true
    info "停止完成"
  fi
}

# ---------- 入口 ----------
case "${1:-start}" in
  status)  do_status ;;
  start)   do_start ;;
  stop)    do_stop ;;
  restart) do_stop; sleep 2; do_start ;;
  *) echo "用法: $0 {start|status|stop|restart}"; exit 1 ;;
esac
