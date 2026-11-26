#!/bin/bash
set -e

# ============================================
#  Sanguo Panel - 一键安装脚本
#  支持 Ubuntu 20.04+ / Debian 11+
#  用法:
#    wget -O install.sh https://your-domain.com/install.sh && sudo bash install.sh
# ============================================

COLOR_GREEN='\033[92m'
COLOR_YELLOW='\033[93m'
COLOR_RED='\033[91m'
COLOR_CYAN='\033[96m'
COLOR_BOLD='\033[1m'
COLOR_RESET='\033[0m'

log_info()  { echo -e "${COLOR_GREEN}[INFO]${COLOR_RESET} $1"; }
log_warn()  { echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1"; }
log_error() { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1"; }
log_step()  { echo -e "\n${COLOR_CYAN}${COLOR_BOLD}==> $1${COLOR_RESET}"; }

PROJECT_ROOT="/sanguo-panel"
REPO_URL="${REPO_URL:-https://github.com/your-org/sanguo-panel.git}"
BRANCH="${BRANCH:-main}"
PANEL_PORT=8000
FRONTEND_PORT=5173
OLS_ADMIN_PORT=7080
OLS_HTTP_PORT=8088
OLS_ADMIN_USER="${OLS_ADMIN_USER:-admin}"
OLS_ADMIN_PASS="${OLS_ADMIN_PASS:-$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -12)}"
MARIADB_ROOT_PASS="${MARIADB_ROOT_PASS:-$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -16)}"

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID="$ID"
        OS_VERSION="$VERSION_ID"
    else
        log_error "Cannot detect OS. Only Ubuntu/Debian are supported."
        exit 1
    fi

    if [ "$OS_ID" != "ubuntu" ] && [ "$OS_ID" != "debian" ]; then
        log_error "Unsupported OS: $OS_ID. Only Ubuntu/Debian are supported."
        exit 1
    fi
    log_info "Detected OS: $OS_ID $OS_VERSION"
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)."
        exit 1
    fi
}

install_system_deps() {
    log_step "Installing system dependencies..."

    apt-get update -y --allow-releaseinfo-change
    apt-get install -y \
        curl wget gnupg2 ca-certificates lsb-release \
        software-properties-common \
        python3 python3-pip python3-venv \
        git unzip tar xz-utils openssl apache2-utils \
        mariadb-server mariadb-client \
        redis-server

    log_info "System dependencies installed."
}

install_openlitespeed() {
    log_step "Installing OpenLiteSpeed + lsphp83..."

    if [ -x /usr/local/lsws/bin/lswsctrl ]; then
        log_info "OpenLiteSpeed already installed: $(/usr/local/lsws/bin/lshttpd -v 2>/dev/null | head -1)"
    else
        # 官方仓库脚本（自动识别 Ubuntu/Debian 版本与架构）
        bash <(curl -fsSL https://repo.litespeed.sh)
        DEBIAN_FRONTEND=noninteractive apt-get update -y --allow-releaseinfo-change
        DEBIAN_FRONTEND=noninteractive apt-get install -y openlitespeed
        log_info "OpenLiteSpeed installed."
    fi

    # PHP (LSAPI) 及 WordPress 常用扩展
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        lsphp83 lsphp83-common lsphp83-mysql \
        lsphp83-curl lsphp83-opcache lsphp83-redis lsphp83-intl \
        lsphp83-imagick lsphp83-sqlite3 lsphp83-igbinary \
        lsphp83-msgpack lsphp83-apcu \
        || log_warn "部分 lsphp83 扩展安装失败，可稍后手动补装。"

    # 官方包提供 lshttpd.service（别名 openlitespeed/lsws），确保开机自启
    systemctl daemon-reload
    systemctl enable lshttpd 2>/dev/null || true
    systemctl start lshttpd 2>/dev/null || /usr/local/lsws/bin/lswsctrl start 2>/dev/null || true
    sleep 2

    if /usr/local/lsws/bin/lswsctrl status 2>/dev/null | grep -q "is running"; then
        log_info "OpenLiteSpeed is running (HTTP :$OLS_HTTP_PORT, Admin :$OLS_ADMIN_PORT)."
    else
        log_warn "OpenLiteSpeed installed but not running. Check: /usr/local/lsws/bin/lswsctrl status"
    fi
}

set_ols_password() {
    log_step "Setting OpenLiteSpeed admin password..."

    if [ ! -d /usr/local/lsws/admin/conf ]; then
        log_warn "OpenLiteSpeed admin directory not found, skipping password setup."
        return
    fi

    # OLS htpasswd 使用 bcrypt（$2y$），htpasswd -B 可直接生成
    if ! command -v htpasswd &>/dev/null; then
        DEBIAN_FRONTEND=noninteractive apt-get install -y apache2-utils
    fi
    htpasswd -nbB "$OLS_ADMIN_USER" "$OLS_ADMIN_PASS" > /usr/local/lsws/admin/conf/htpasswd
    chown lsadm:lsadm /usr/local/lsws/admin/conf/htpasswd 2>/dev/null || true
    chmod 600 /usr/local/lsws/admin/conf/htpasswd

    echo "WebAdmin user/password is $OLS_ADMIN_USER/$OLS_ADMIN_PASS" > /usr/local/lsws/adminpasswd
    chmod 600 /usr/local/lsws/adminpasswd

    systemctl restart lshttpd 2>/dev/null || /usr/local/lsws/bin/lswsctrl restart 2>/dev/null || true
    sleep 1

    log_info "OpenLiteSpeed admin: http://<IP>:$OLS_ADMIN_PORT  user: $OLS_ADMIN_USER  pass: $OLS_ADMIN_PASS"
    log_info "凭据已写入 /usr/local/lsws/adminpasswd，面板会自动读取并展示。"
}

install_nodejs() {
    log_step "Installing Node.js (>= 20.19 for Vite 7)..."

    node_ok() {
        command -v node >/dev/null 2>&1 || return 1
        node -e '
          const [a, b] = process.versions.node.split(".").map(Number);
          process.exit(a > 22 || (a === 22 && b >= 12) || (a === 20 && b >= 19) ? 0 : 1)
        ' 2>/dev/null
    }

    if node_ok; then
        log_info "Node.js already installed: $(node --version)"
        return
    fi

    if curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
        && DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs \
        && node_ok; then
        log_info "Node.js installed: $(node --version)"
        return
    fi

    # 兜底：官方二进制包（避免 apt 源/PPA 问题导致安装失败）
    log_warn "NodeSource 安装失败，改用 Node.js 官方二进制包..."
    local arch node_arch node_ver="22.14.0"
    arch="$(uname -m)"
    case "$arch" in
        x86_64) node_arch="x64" ;;
        aarch64|arm64) node_arch="arm64" ;;
        *) log_error "不支持的架构: $arch"; exit 1 ;;
    esac
    curl -fsSL "https://nodejs.org/dist/v${node_ver}/node-v${node_ver}-linux-${node_arch}.tar.xz" -o /tmp/node.tar.xz
    rm -rf /usr/local/lib/nodejs
    mkdir -p /usr/local/lib/nodejs
    tar -xJf /tmp/node.tar.xz -C /usr/local/lib/nodejs --strip-components=1
    for b in node npm npx corepack; do
        ln -sf "/usr/local/lib/nodejs/bin/$b" "/usr/local/bin/$b"
    done
    log_info "Node.js installed: $(node --version)"
}

install_php() {
    log_step "Installing PHP (for phpMyAdmin)..."

    if command -v php &>/dev/null; then
        log_info "PHP already installed: $(php --version | head -1)"
        return
    fi

    apt-get install -y php8.3-cli php8.3-mysqli php8.3-curl php8.3-mbstring php8.3-xml php8.3-zip php8.3-gd
    log_info "PHP installed: $(php --version | head -1)"
}

setup_project() {
    log_step "Setting up Sanguo Panel project..."

    if [ -d "$PROJECT_ROOT" ] && [ -n "$(ls -A "$PROJECT_ROOT" 2>/dev/null)" ]; then
        log_info "Project already exists at $PROJECT_ROOT."
        cd "$PROJECT_ROOT"
        if [ -d ".git" ]; then
            git pull origin "$BRANCH" 2>/dev/null || log_warn "git pull failed."
        fi
    else
        mkdir -p "$PROJECT_ROOT"
        if [ -d "$(dirname "$PROJECT_ROOT")/.git" ] && [ "$(dirname "$PROJECT_ROOT")" != "$PROJECT_ROOT" ]; then
            log_info "Copying project files from parent..."
            cp -r "$(dirname "$PROJECT_ROOT")"/* "$PROJECT_ROOT"/ 2>/dev/null || true
        else
            log_info "Cloning project to $PROJECT_ROOT..."
            git clone -b "$BRANCH" "$REPO_URL" "$PROJECT_ROOT" 2>/dev/null || {
                log_error "Git clone failed. Please place project files in $PROJECT_ROOT manually."
                exit 1
            }
        fi
        cd "$PROJECT_ROOT"
    fi
}

setup_python_env() {
    log_step "Setting up Python virtual environment..."

    cd "$PROJECT_ROOT"

    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_info "Virtual environment created."
    fi

    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    log_info "Python dependencies installed."
}

setup_frontend() {
    log_step "Setting up frontend dependencies..."

    cd "$PROJECT_ROOT/frontend"

    if [ -f pnpm-lock.yaml ]; then
        if ! command -v pnpm &>/dev/null; then
            npm install -g pnpm
        fi
        pnpm install
    else
        npm install
    fi
    log_info "Frontend dependencies installed."
}

init_database() {
    log_step "Initializing database..."

    cd "$PROJECT_ROOT"
    source venv/bin/activate
    export PYTHONPATH="$PROJECT_ROOT"

    python backend/init_db.py
    log_info "Database initialized."
}

create_systemd_services() {
    log_step "Installing Sanguo Panel systemd service..."

    # 面板以单服务方式运行：后端同端口托管构建后的前端（生产模式）
    if [ ! -x "$PROJECT_ROOT/deploy/install-service.sh" ]; then
        log_error "deploy/install-service.sh not found in $PROJECT_ROOT"
        exit 1
    fi

    PANEL_PORT="$PANEL_PORT" bash "$PROJECT_ROOT/deploy/install-service.sh"

    log_info "Sanguo Panel service installed and enabled (sanguo-panel)."
}

configure_mariadb() {
    log_step "Configuring MariaDB..."

    systemctl enable mariadb 2>/dev/null || true
    systemctl start mariadb 2>/dev/null || true

    if mysql -u root -e "SELECT 1" &>/dev/null; then
        mysql -u root << EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY '$MARIADB_ROOT_PASS';
FLUSH PRIVILEGES;
EOF
        log_info "MariaDB root password set."
    else
        mysql -u root -p"$MARIADB_ROOT_PASS" -e "SELECT 1" &>/dev/null && log_info "MariaDB root password already configured."
    fi

    cat > /root/.my.cnf << EOF
[client]
user=root
password=$MARIADB_ROOT_PASS
EOF
    chmod 600 /root/.my.cnf
    log_info "MariaDB configured (root password saved to /root/.my.cnf)."
}

configure_redis() {
    log_step "Configuring Redis..."

    systemctl enable redis-server 2>/dev/null || true
    systemctl start redis-server 2>/dev/null || true

    log_info "Redis configured."
}

configure_firewall() {
    log_step "Configuring firewall..."

    if command -v ufw &>/dev/null; then
        ufw allow $OLS_HTTP_PORT/tcp comment 'OpenLiteSpeed HTTP'
        ufw allow 443/tcp comment 'OpenLiteSpeed HTTPS'
        ufw allow $OLS_ADMIN_PORT/tcp comment 'OpenLiteSpeed Admin'
        ufw allow $PANEL_PORT/tcp comment 'Sanguo Panel'
        ufw allow 22/tcp comment 'SSH'
        log_info "Firewall rules added."
    else
        log_info "UFW not found, skipping firewall configuration."
    fi
}

configure_fail2ban() {
    log_step "Configuring Fail2ban..."

    if command -v fail2ban-client &>/dev/null; then
        log_info "Fail2ban already installed, skipping install."
    else
        apt-get install -y fail2ban
        log_info "Fail2ban installed."
    fi

    # 基础 jail 配置：启用 sshd 防护，避免面板/SSH 被暴力破解
    if [ ! -f /etc/fail2ban/jail.local ]; then
        mkdir -p /etc/fail2ban
        cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
backend = systemd

[sshd]
enabled = true
EOF
        log_info "Default jail.local written (/etc/fail2ban/jail.local)."
    fi

    # 放行面板自身端口，避免误封本机回环（可选保险）
    systemctl enable fail2ban 2>/dev/null || true
    systemctl restart fail2ban 2>/dev/null || fail2ban-client start 2>/dev/null || true

    if command -v fail2ban-client &>/dev/null && systemctl is-active --quiet fail2ban; then
        log_info "Fail2ban is running."
    else
        log_warn "Fail2ban installed but not running. Check: journalctl -u fail2ban"
    fi
}

start_services() {
    log_step "Starting services..."

    systemctl start mariadb 2>/dev/null || true
    systemctl start redis-server 2>/dev/null || true
    systemctl start lshttpd 2>/dev/null || /usr/local/lsws/bin/lswsctrl start 2>/dev/null || true
    systemctl start sanguo-panel 2>/dev/null || true

    sleep 3
}

show_summary() {
    PUBLIC_IP=$(curl -s https://api.ipify.org 2>/dev/null || curl -s https://icanhazip.com 2>/dev/null || echo "<SERVER_IP>")

    echo ""
    echo -e "${COLOR_GREEN}${COLOR_BOLD}============================================${COLOR_RESET}"
    echo -e "${COLOR_GREEN}${COLOR_BOLD}  Sanguo Panel 安装完成！${COLOR_RESET}"
    echo -e "${COLOR_GREEN}${COLOR_BOLD}============================================${COLOR_RESET}"
    echo ""
    echo -e "  ${COLOR_CYAN}面板入口:${COLOR_RESET}  http://$PUBLIC_IP:$PANEL_PORT"
    echo -e "  ${COLOR_CYAN}本机访问:${COLOR_RESET}  http://localhost:$PANEL_PORT"
    echo -e "  ${COLOR_CYAN}API 文档:${COLOR_RESET}  http://$PUBLIC_IP:$PANEL_PORT/api-docs"
    echo ""
    echo -e "  ${COLOR_CYAN}OLS 管理:${COLOR_RESET}  http://$PUBLIC_IP:$OLS_ADMIN_PORT"
    echo -e "  ${COLOR_CYAN}OLS HTTP:${COLOR_RESET}  http://$PUBLIC_IP:$OLS_HTTP_PORT"
    echo ""
    echo -e "  ${COLOR_YELLOW}面板登录:${COLOR_RESET}"
    echo -e "    用户名: admin"
    echo -e "    密  码: admin123"
    echo ""
    echo -e "  ${COLOR_YELLOW}OLS 管理登录:${COLOR_RESET}"
    echo -e "    用户名: $OLS_ADMIN_USER"
    echo -e "    密  码: $OLS_ADMIN_PASS"
    echo ""
    echo -e "  ${COLOR_YELLOW}MariaDB:${COLOR_RESET}  root@localhost 密码: $MARIADB_ROOT_PASS (已保存至 /root/.my.cnf)"
    echo -e "  ${COLOR_YELLOW}Redis:${COLOR_RESET}    127.0.0.1:6379 (无密码)"
    echo ""
    echo -e "  ${COLOR_YELLOW}服务管理:${COLOR_RESET}"
    echo -e "    systemctl {start|stop|restart} sanguo-panel"
    echo -e "    systemctl {start|stop|restart} lshttpd      # 别名 openlitespeed"
    echo ""
    echo -e "  ${COLOR_YELLOW}日志查看:${COLOR_RESET}"
    echo -e "    journalctl -u sanguo-panel -f"
    echo -e "    tail -f /usr/local/lsws/logs/error.log"
    echo ""
    echo -e "${COLOR_GREEN}${COLOR_BOLD}============================================${COLOR_RESET}"
}

wait_for_services() {
    log_step "Waiting for services to be ready..."
    local timeout=60

    for i in $(seq 1 $timeout); do
        if curl -sf "http://127.0.0.1:$PANEL_PORT/api/v1/system/status" > /dev/null 2>&1; then
            log_info "Panel is ready."
            break
        fi
        if [ "$i" -eq "$timeout" ]; then
            log_warn "Panel did not respond within ${timeout}s. Check: journalctl -u sanguo-panel -n 50"
        fi
        sleep 1
    done
}

main() {
    echo ""
    echo -e "${COLOR_CYAN}${COLOR_BOLD}============================================${COLOR_RESET}"
    echo -e "${COLOR_CYAN}${COLOR_BOLD}  Sanguo Panel - 一键安装脚本${COLOR_RESET}"
    echo -e "${COLOR_CYAN}${COLOR_BOLD}============================================${COLOR_RESET}"
    echo ""

    check_root
    detect_os

    install_system_deps
    install_openlitespeed
    set_ols_password
    install_nodejs
    install_php
    setup_project
    setup_python_env
    setup_frontend
    init_database
    configure_mariadb
    configure_redis
    create_systemd_services
    configure_firewall
    configure_fail2ban
    start_services
    wait_for_services
    show_summary
}

main "$@"