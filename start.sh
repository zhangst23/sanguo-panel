#!/bin/bash
# ============================================
#  Sanguo Panel - 简易启动 / 状态管理脚本
#  适用于已通过 install.sh 安装后的日常使用
#  ⚠️ 本脚本「不安装任何依赖」，只检查并启动服务
#
#  用法:
#    ./start.sh          启动全部服务（已运行的会跳过）
#    ./start.sh status   查看各服务运行状态与访问地址
#    ./start.sh stop     停止全部服务
#    ./start.sh restart  重启全部服务
# ============================================

set -u

# ---------- 配置 ----------
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PANEL_PORT=8000
FRONTEND_PORT=5173
LOG_DIR="$PROJECT_ROOT/logs"

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

# ---------- 检测 systemd（install.sh 已创建服务） ----------
USE_SYSTEMD=false
if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
  USE_SYSTEMD=true
fi

SYSTEMD_SERVICES=(sanguo-backend sanguo-frontend openlitespeed mariadb redis-server)

# ---------- 健康检查 ----------
backend_ok()  { curl -fs "http://127.0.0.1:$PANEL_PORT/api/v1/system/status" >/dev/null 2>&1; }
frontend_ok() { curl -fs "http://127.0.0.1:$FRONTEND_PORT" >/dev/null 2>&1; }

# ---------- 状态 ----------
do_status() {
  step "服务状态"
  if $USE_SYSTEMD; then
    for svc in "${SYSTEMD_SERVICES[@]}"; do
      active=$($SD systemctl is-active "$svc" 2>/dev/null)
      if [ "$active" = "active" ]; then
        info "$svc 进程运行中"
      else
        warn "$svc 未运行 (systemctl: $active)"
      fi
    done
    echo
    # 端口级真实健康检查（防止 systemd 误报“假活”）
    if backend_ok; then  info "后端端口 :$PANEL_PORT 已响应 ✅"; else warn "后端端口 :$PANEL_PORT 无响应 ❌（可运行 ./start.sh 重启）"; fi
    if frontend_ok; then info "前端端口 :$FRONTEND_PORT 已响应 ✅"; else warn "前端端口 :$FRONTEND_PORT 无响应 ❌（可运行 ./start.sh 重启）"; fi
  else
    backend_ok  && info "后端  (:$PANEL_PORT) 运行中" || warn "后端  (:$PANEL_PORT) 未运行"
    frontend_ok && info "前端  (:$FRONTEND_PORT) 运行中" || warn "前端  (:$FRONTEND_PORT) 未运行"
  fi

  echo
  backend_ok  && info "后端 API 就绪:  http://localhost:$PANEL_PORT"      || warn "后端 API 未就绪"
  frontend_ok && info "前端界面就绪: http://localhost:$FRONTEND_PORT"     || warn "前端界面未就绪"

  echo
  PUBLIC_IP=$(curl -s --max-time 3 https://api.ipify.org 2>/dev/null || echo "localhost")
  echo -e "  面板入口: http://217.69.2.217:$FRONTEND_PORT"
  echo -e "  本机开发访问: http://localhost:$FRONTEND_PORT"
  echo -e "  API 文档: http://localhost:$PANEL_PORT/api-docs"
}

# ---------- 等待就绪 ----------
wait_ready() {
  step "等待服务就绪"
  for _ in $(seq 1 60); do backend_ok && break; sleep 1; done
  for _ in $(seq 1 60); do frontend_ok && break; sleep 1; done
}

# ---------- 手动启动（无 systemd 时的回退方案） ----------
start_manual() {
  mkdir -p "$LOG_DIR"
  if [ ! -x "$PROJECT_ROOT/venv/bin/python" ]; then
    err "未找到虚拟环境 $PROJECT_ROOT/venv，请先运行 install.sh 安装依赖。"
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
  step "启动服务（不安装依赖）"
  if $USE_SYSTEMD; then
    for svc in mariadb redis-server openlitespeed sanguo-backend sanguo-frontend; do
      if $SD systemctl is-active --quiet "$svc" 2>/dev/null; then
        # 进程在，但端口可能没响应（假活）→ 强制重启
        if [ "$svc" = "sanguo-backend" ] && ! backend_ok; then
          warn "$svc 进程在但端口无响应，重启中…"
          $SD systemctl restart "$svc" 2>/dev/null && info "已重启 $svc" || warn "重启 $svc 失败"
        elif [ "$svc" = "sanguo-frontend" ] && ! frontend_ok; then
          warn "$svc 进程在但端口无响应，重启中…"
          $SD systemctl restart "$svc" 2>/dev/null && info "已重启 $svc" || warn "重启 $svc 失败"
        else
          info "$svc 已在运行，跳过"
        fi
      else
        if $SD systemctl start "$svc" 2>/dev/null; then
          info "已启动 $svc"
        else
          warn "启动 $svc 失败（可忽略，详情: $SD journalctl -u $svc -n 50）"
        fi
      fi
    done
  else
    start_manual
  fi
  wait_ready
  do_status
}

# ---------- 停止 ----------
do_stop() {
  step "停止服务"
  if $USE_SYSTEMD; then
    for svc in sanguo-frontend sanguo-backend openlitespeed redis-server mariadb; do
      $SD systemctl stop "$svc" 2>/dev/null && info "已停止 $svc" || true
    done
  else
    pkill -f "uvicorn backend.main:app" 2>/dev/null && info "已停止后端" || true
    pkill -f "vite" 2>/dev/null && info "已停止前端" || true
  fi
  info "停止完成"
}

# ---------- 入口 ----------
case "${1:-start}" in
  status)  do_status ;;
  start)   do_start ;;
  stop)    do_stop ;;
  restart) do_stop; sleep 2; do_start ;;
  *) echo "用法: $0 {start|status|stop|restart}"; exit 1 ;;
esac
