# Sanguo Panel 三国面板

Sanguo Panel 是一款专为 WordPress 优化设计的轻量级托管面板，基于 **OpenLiteSpeed**、**MariaDB**、**Redis** 构建。

## 项目结构
```
sanguo-panel/
├── venv/                  # 虚拟环境（项目根目录）
├── backend/               # FastAPI 后端（同时托管构建后的前端）
├── frontend/              # Vue 前端
├── deploy/                # 系统服务安装 / 卸载脚本（systemd）
├── requirements.txt       # Python 依赖（已包含 requests）
├── start.sh               # 服务启停 / 状态脚本
├── .gitignore             # 忽略 venv/、运行时数据等
├── README.md
└── AGENTS.md
```

**运行时目录（不在代码仓库中）：**
```
/var/www/html/            # WordPress 站点文件（每个站点一个子目录）
├── site1.com/
├── site2.com/
└── ...
```

## 核心特性

- **极致性能**: 集成 LSCache、Redis、OPcache 和浏览器四层缓存控制。
- **一键优化**: 支持图片批量压缩 (WebP/AVIF)、前端资源合并、数据库碎片整理。
- **运维便捷**: 包含 SSL 自动管理 (Let's Encrypt)、全站备份与恢复、多版本 PHP 切换。
- **安全可靠**: 隐藏登录路径、JWT 安全验证、系统防火墙集成。
- **OpenLiteSpeed 技术底座**: 采用 LSAPI (lsphp) 运行 PHP，性能卓越，原生支持 LSCache。

## 快速启动

> 面板以**单个系统级服务**运行（类似宝塔面板）：前端构建后由后端在同一端口提供，
> 由 systemd 守护、开机自启，断开 SSH 也不会停。

首次安装 / 升级（安装依赖、构建前端、注册并启动服务）：

```bash
sudo ./deploy/install-service.sh              # 默认端口 8000
sudo PANEL_PORT=8888 ./deploy/install-service.sh   # 自定义端口
```

日常管理：

```bash
./start.sh            # 启动全部服务（已运行的自动跳过）
./start.sh status     # 仅查看各服务状态与访问地址
./start.sh stop       # 停止面板服务
./start.sh restart    # 重启面板服务

systemctl status sanguo-panel    # 或直接使用 systemctl
journalctl -u sanguo-panel -f    # 查看实时日志
```

脚本逻辑：
- ✅ 已安装 `sanguo-panel` 系统服务时，通过 systemd 管理（面板 + `openlitespeed` / `mariadb` / `redis-server`）
- ✅ 未安装系统服务时，自动回退为 `venv + vite` 开发模式（前端 :5173，后端 :8000）
- ✅ 自动等待服务就绪，并列出本机 / 外网访问地址
- ❌ `start.sh` 不安装依赖、不构建前端；需要时请运行 `deploy/install-service.sh`

启动成功后访问：
- **面板入口**: http://169.58.52.214:8000
- **本机访问**: http://localhost:8000
- **API 文档**: http://localhost:8000/api-docs

> `169.58.52.214` 为本机公网 IP，其他服务器请替换为自己的公网 IP 或域名。
> 若需卸载系统服务（保留数据）：`sudo ./deploy/uninstall-service.sh`。

### 打不开面板（502 / 连接超时）

按顺序检查：

```bash
systemctl status sanguo-panel          # 1. 服务是否运行
curl -I http://127.0.0.1:8000/         # 2. 本机是否正常
ufw allow 8000/tcp                     # 3. 防火墙是否放行（安装脚本会自动处理）
grep 'DPT=8000' /var/log/ufw.log       # 4. 是否被 UFW 拦截
```

云服务器还需在**云厂商安全组**中放行面板端口。若面板暴露在公网，请及时修改默认密码 `admin / admin123`。

### 前端界面默认账户

- **用户名**: `admin`
- **密码**: `admin123`

## 技术栈

- **Web 服务器**: OpenLiteSpeed (端口 80/443) — 托管 WordPress 站点；面板前端由 FastAPI 在 8000 端口同源提供
- **后端**: FastAPI, SQLAlchemy (SQLite), Pydantic, JWT, Psutil
- **前端**: Vue 3, Vite, Arco Design, Pinia, Axios, ECharts
- **数据库**: MariaDB (WordPress 站点), SQLite (面板配置)
- **缓存**: Redis (WordPress 对象缓存)
- **PHP**: OpenLiteSpeed 内置 LSAPI (lsphp83/82/81/74)，多版本共存，按站点切换

## WordPress 站点管理

- **站点根目录**: `/var/www/html/{domain}/` （创建站点时自动生成）
- **文件属主**: `nobody:nogroup` (OLS LSAPI worker 用户)
- **虚拟主机配置**: `/usr/local/lsws/conf/vhosts/{domain}/vhconf.conf`
- **PHP 版本**: 面板创建/编辑站点时可选，自动生成 per-vhost LSAPI handler
- **LSCache**: Rewrite 规则 + WP 插件双重启用
- **SSL**: Let's Encrypt (acme.sh) → 部署到 OLS 443 SNI

## 前端构建部署

面板前端由后端在 8000 端口直接托管（`frontend/dist/`）。修改前端代码后重新构建并重启服务：

```bash
cd frontend
pnpm install     # 首次或依赖变更时
pnpm build
sudo systemctl restart sanguo-panel
```

或直接重新运行 `sudo ./deploy/install-service.sh`，脚本会自动完成依赖安装、构建与服务重启。
构建产物输出到 `frontend/dist/`，不存在时后端仅提供 API（开发模式请用 Vite）。

## 文档参考

详细的设计文档、测试用例和任务清单请参考 `.prd/` 目录。