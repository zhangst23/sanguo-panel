# Sanguo Panel 三国面板

Sanguo Panel 是一款专为 WordPress 优化设计的轻量级托管面板，基于 **OpenLiteSpeed**、**MariaDB**、**Redis** 构建。面板以单个 systemd 服务运行，构建后的前端由 FastAPI 在 8000 端口同源提供。

## 项目结构

```
sanguo-panel/
├── venv/                  # 虚拟环境（项目根目录）
├── backend/               # FastAPI 后端（API + 托管 frontend/dist）
│   ├── api/v1/            # 业务路由（system / sites / security / notifications / agent ...）
│   ├── models/            # SQLAlchemy 模型
│   ├── utils/             # 工具函数（含 notification_utils.py、panel_ops.py 等）
│   └── panel.db           # SQLite 面板库（运行时数据，不入库）
├── frontend/              # Vue 3 + Vite SPA，构建产物在 dist/
├── deploy/                # systemd 服务安装 / 卸载 / 重置脚本
├── .prd/                  # 设计文档、PRD、测试用例、任务清单、开发记录
├── requirements.txt
├── start.sh               # 服务启停 / 状态脚本
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

- **极致性能**：集成 LSCache、Redis、OPcache 和浏览器四层缓存控制；提供 WP 一键提速工具。
- **一键优化**：图片批量压缩 (WebP/AVIF)、前端资源合并、数据库碎片整理。
- **运维便捷**：SSL 自动管理 (Let's Encrypt)、全站备份与恢复、多版本 PHP 切换。
- **安全可靠**：隐藏登录路径、JWT 鉴权（Token 永久有效且可重置）、Fail2ban IP 封禁、系统防火墙。
- **通知提醒**：SMTP 邮件、企业微信/钉钉/飞书 Webhook、13 条告警规则与最近 100 条告警记录。
- **Agent 接入**：内置 MCP（JSON-RPC over HTTP）与 Agent Skill，可让 Claude/Cursor/OpenCode 等直接管理面板。
- **OpenLiteSpeed 技术底座**：LSAPI (lsphp) 运行 PHP，多版本共存，原生支持 LSCache。

## 面板功能地图

侧边栏（自上而下）：仪表盘、网站管理、文件管理、数据库管理、**WP 管理**、安全防御、**AI 管理**、备份迁移、系统工具（系统管理 / 监控中心 / 面板设置 / 操作日志 / 关于）。

| 页面 | 主要标签 |
|------|----------|
| WP 管理 (`/wp-assets`) | **WP一键提速**（默认）、WP安全加固、WP 版本、主题管理、插件管理 |
| AI 管理 (`/tools`) | AI 修复、**模型**、Agent接入 |
| 系统管理 (`/linux`) | 系统状态、**PHP 管理**、OLS 虚拟主机管理、**LS缓存管理**、Rewrite、Redis 管理、Linux 管理、Log |
| 安全防御 (`/security`) | **IP 封禁列表**（默认）、Fail2ban 设置、UFW 防火墙 |
| 面板设置 (`/system/settings`) | 面板设置（含**面板 Token** 管理）、通知提醒、面板运行日志 |
| 文件管理 (`/file-manager`) | 权限列可读化，支持「放开读写 / 一键只读」切换 |

> 亮色主题下侧边栏、IP、菜单与按钮均已做过对比度优化。

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

### 重置为空面板

面板数据保存在 `backend/panel.db`（SQLite，运行时数据，**不在 git 中**）。
`git pull` 更新代码不会覆盖它，所以新部署仍可能沿用旧面板的站点/数据库/备份记录。

```bash
sudo ./deploy/reset-panel.sh          # 清空站点、数据库记录、备份、任务（保留管理员与设置）
sudo ./deploy/reset-panel.sh --full   # 完全重置（删除 panel.db，恢复 admin/admin123）
```

脚本会先把数据库备份到 `backup/panel.db.*.bak`，并把旧备份文件移动到 `backup/_reset_<时间戳>/`，可随时手动恢复。

### 前端界面默认账户

- **用户名**: `admin`
- **密码**: `admin123`

## 面板 Token

面板使用 JWT 鉴权，登录时签发，当前配置为**永久有效**（`ACCESS_TOKEN_EXPIRE_MINUTES=0`）。

- 获取：登录后浏览器控制台执行 `localStorage.getItem('token')`，或调用 `POST /api/v1/login/access-token`
- 管理：`面板设置 → 面板 Token` 卡片，可查看（明文切换）、复制、重新生成
- 重新生成会递增用户 `token_version`，**旧 Token 立即失效**；其他地方使用的 Token 需同步更新
- 请勿把 Token 泄露给不可信人员

## Agent 接入（MCP / Skill）

`AI 管理 → Agent接入` 提供两种接入方式，均复用面板 Bearer Token：

| 能力 | 地址 | 说明 |
|------|------|------|
| MCP | `POST /api/v1/agent/mcp` | JSON-RPC（Streamable HTTP 风格），支持 `initialize` / `tools/list` / `tools/call` |
| Skill 说明 | `GET /api/v1/agent/skill.md` | 可直接交给 Agent 阅读的 Markdown |
| 接入信息 | `GET /api/v1/agent/info` | 返回实际 MCP / Skill 地址与工具列表 |
| 安装提示词 | `GET /api/v1/agent/skill/prompt` | 生成带本机地址的安装提示词 |

当前 MCP 工具（只读）：`panel_status`、`list_sites`、`list_tasks`。页面上的「复制面板 Token」按钮会把当前登录 Token 自动填入 MCP 配置模板。

## 通知提醒

`面板设置 → 通知提醒`：

- **SMTP 邮件配置**：服务器 / 端口 / 加密方式 / 用户名 / 授权码 / 发件邮箱 / 管理员邮箱；保存、测试发送、诊断 SMTP、复制配置码、导入配置码
- **Webhook 推送**：企业微信 / 钉钉 / 飞书，保存即启用、清空 URL 即停用，支持测试发送
- **告警规则**：13 条开关（资源 / 可用性 / 运维 / 安全），阈值与统计窗口
- **告警记录**：最近 100 条，最新在前

配置以 `GlobalOption` 存入 SQLite，记录写入 `backup/notification_records.json`。后端接口位于 `/api/v1/notifications/*`。

## 技术栈

- **Web 服务器**: OpenLiteSpeed (80/443) — 托管 WordPress 站点；面板前端由 FastAPI 在 8000 端口同源提供
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

面板前端由后端在 8000 端口直接托管（`frontend/dist/`）。**修改前端源码后必须重新构建，否则刷新页面看不到变化**：

```bash
cd frontend
pnpm install     # 首次或依赖变更时（npm install 亦可）
pnpm build       # 或 npm run build
sudo systemctl restart sanguo-panel
```

后端代码改动同样需要 `sudo systemctl restart sanguo-panel` 才会生效（systemd 服务未开启 reload）。

构建产物输出到 `frontend/dist/`，不存在时后端仅提供 API（开发模式请用 Vite）。

## 文档参考

设计与开发文档在 `.prd/`：PRD、前端 PRD、技术架构、SQL、测试用例、任务清单、开发记录、OpenLiteSpeed / phpMyAdmin / WP-CLI 指南。
Agent 协作约定见 `AGENTS.md`。

> 当前状态：开发暂告一段落，功能已提交并推送至 `origin/main`；后续如需继续，请从 `.prd/notelist.md` 的开发记录接续。
