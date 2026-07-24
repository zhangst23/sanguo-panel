# Sanguo Panel 三国面板

Sanguo Panel 是一款专为 WordPress 优化设计的轻量级托管面板，基于 OpenLiteSpeed、MariaDB、Nginx 和 Redis Object Cache 构建。

## 项目结构
sanguo-panel/
├── venv/                  # 虚拟环境（项目根目录）
├── backend/               # FastAPI 后端
├── frontend/              # Vue 前端
├── requirements.txt       # Python 依赖（已包含 requests）
├── start-all.py          # 一键启动脚本（跨平台）
├── .gitignore            # 忽略 venv/ 等
├── README.md
└── AGENTS.md

## 核心特性

- **极致性能**: 集成 LSCache、Redis、OPcache 和浏览器四层缓存控制。
- **一键优化**: 支持图片批量压缩 (WebP/AVIF)、前端资源合并、数据库碎片整理。
- **运维便捷**: 包含 SSL 自动管理 (Let's Encrypt)、全站备份与恢复、多版本 PHP 切换。
- **安全可靠**: 隐藏登录路径、JWT 安全验证、系统防火墙集成。

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
- 前端界面（外网，推荐，走 80 端口 OpenLiteSpeed 反向代理，可绕过仅放行 80/443 的网络）: http://<服务器IP>/
- 前端界面（本机开发）: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://<服务器IP>/api-docs

> 若需重新安装依赖、初始化数据库或配置 OpenLiteSpeed / MariaDB，请重新运行 `install.sh`。


### 前端界面默认账户

- **用户名**: `admin`
- **密码**: `admin123`

## 技术栈

- **后端**: FastAPI, SQLAlchemy (SQLite), Pydantic, JWT, Psutil
- **前端**: Vue 3, Vite, Arco Design, Pinia, Axios, ECharts




## 文档参考

详细的设计文档、测试用例和任务清单请参考 `doc-ai/prd/` 目录。
