# Sanguo Panel 三国面板

Sanguo Panel 是一款专为 WordPress 优化设计的轻量级托管面板，基于 **OpenLiteSpeed**、**MariaDB**、**Redis** 构建。

## 项目结构
```
sanguo-panel/
├── venv/                  # 虚拟环境（项目根目录）
├── backend/               # FastAPI 后端
├── frontend/              # Vue 前端
├── requirements.txt       # Python 依赖（已包含 requests）
├── start-all.py          # 一键启动脚本（跨平台）
├── .gitignore            # 忽略 venv/ 等
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

> `install.sh` 已经把依赖装好，并用 systemd 守护进程把服务跑起来了（断开 SSH 也不会停）。
> 重新进入项目后，**只需下面这一条命令**即可确认状态或补启动，脚本**不会重新安装依赖**。

在项目根目录执行：

```bash
./start.sh            # 启动全部服务（已运行的自动跳过）
./start.sh status     # 仅查看各服务状态与访问地址
./start.sh stop       # 停止全部服务
./start.sh restart    # 重启全部服务
```

脚本逻辑：
- ✅ 优先复用 `install.sh` 创建的 systemd 服务（`sanguo-backend` / `sanguo-frontend` / `openlitespeed` / `mariadb` / `redis-server`），已运行的自动跳过
- ✅ 没有 systemd 的环境（如容器）自动回退为后台进程方式启动，日志写入 `logs/`
- ✅ 自动等待服务就绪，并列出本机 / 外网访问地址
- ❌ 不安装任何依赖、不初始化数据库，纯启动 / 检查

启动成功后访问：
- **前端界面（外网）**: http://217.69.2.217:5173
- **前端界面（本机开发）**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://217.69.2.217:8000/api-docs

> 若需重新安装依赖、初始化数据库或配置 OpenLiteSpeed / MariaDB，请重新运行 `install.sh`。

### 前端界面默认账户

- **用户名**: `admin`
- **密码**: `admin123`

## 技术栈

- **Web 服务器**: OpenLiteSpeed (端口 80/443) — 服务前端静态文件、反代 API 到后端
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

修改前端代码后需构建静态资源并重启 OpenLiteSpeed 生效：

```bash
cd /sanguo-panel/frontend
npm run build
/usr/local/lsws/bin/lswsctrl restart
```

构建产物输出到 `frontend/dist/`，由 OLS `sanguo-panel` 虚拟主机直接服务。

## 文档参考

详细的设计文档、测试用例和任务清单请参考 `.prd/` 目录。