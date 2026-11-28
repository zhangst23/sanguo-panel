# Sanguo Panel — Agent Guide

## Quick start

### System service (production, recommended)

The panel runs as a single systemd unit — the **built frontend is served by the
backend on port 8000**, so there is one process to manage (BT-panel style).
OpenLiteSpeed serves the WordPress sites on 80/443; it does not serve the panel UI.

```bash
# Install/upgrade: installs deps, builds frontend, registers + enables service
sudo ./deploy/install-service.sh          # default port 8000
sudo PANEL_PORT=8888 ./deploy/install-service.sh

# Daily management
systemctl status sanguo-panel
systemctl restart sanguo-panel
./start.sh status                         # convenience wrapper
```

Access URLs after startup:
- Panel UI: http://localhost:8000 (or http://169.58.52.214:8000)
- API Docs: http://localhost:8000/api-docs
- Default login: `admin` / `admin123` (change in production)

Uninstall the service (keeps files/data): `sudo ./deploy/uninstall-service.sh`

### Development startup

```bash
./start.sh          # falls back to venv + vite dev mode if the service isn't installed
```

### Manual startup

**Windows:**
```powershell
# Backend (run from project root)
$env:PYTHONPATH="."
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --reload-exclude "*.db" --port 8000

# Init DB (first run)
$env:PYTHONPATH="."
python backend.init_db.py

# Frontend
cd frontend
npm install
npm run dev
```

**Linux/macOS:**
```bash
# Backend (run from project root)
export PYTHONPATH="."
source venv/bin/activate
python -m uvicorn backend.main:app --reload --reload-exclude "*.db" --port 8000

# Init DB (first run)
PYTHONPATH=. python backend/init_db.py

# Frontend
cd frontend
npm install
npm run dev
```

## Architecture

- **Web Server**: OpenLiteSpeed (80/443) — serves WordPress sites, proxies nothing for the panel
- **Backend**: FastAPI + SQLAlchemy (SQLite at `backend/panel.db`) + JWT auth; serves `frontend/dist/` on port 8000
- **Frontend**: Vue 3 + Vite + Arco Design + Pinia + Axios + ECharts
- **Database**: MariaDB (WordPress sites) + SQLite (panel config)
- **Cache**: Redis (WordPress object cache)
- **API prefix**: `/api/v1`
- **Swagger**: `http://localhost:8000/api-docs`
- **phpMyAdmin**: Proxied through backend at `/phpmyadmin/*` (PHP required in PATH, managed by `backend/utils/pma_server.py`)

### Registered API routers (`backend/api/v1/api.py`)

`auth`, `system`, `monitor`, `tools`, `linux`, `security`, `sites`, `service`,
`litespeed`, `php`, `cache`, `ssl`, `image`, `database`, `assets`, `cdn`,
`ultimate`, `tasks`, `files`, `wp-assets`, `notifications`, `agent`.

Newer modules:
- `backend/api/v1/notifications.py` + `backend/utils/notification_utils.py` — SMTP/Webhook config, alert rules, last-100 records
- `backend/api/v1/agent.py` — MCP JSON-RPC endpoint, Skill markdown, install prompt
- `backend/api/v1/system.py` — `/system/token`, `/system/token/regenerate`, `/system/status` (public, returns `ip`)

## Conventions

- `@` in frontend imports = `src/` (configured in `vite.config.js`)
- Arco Design is the UI framework (`@arco-design/web-vue`, `@arco-design/web-vue/es/icon`)
- **Arco theme vars are `--color-*`** (e.g. `--color-bg-1`, `--color-text-1`), not `--arco-color-*`.
  `global.scss` defines compatibility aliases on `body` for legacy `--arco-color-*` usages.
  Prefer `--color-*` in new code.
- Styles: `src/assets/styles/global.scss` (Sass)
- API client: `src/utils/request.js` — base URL `/api/v1`, 10 s timeout, auto-attaches Bearer token from `localStorage`
- Login: POST `/api/v1/login/access-token` (OAuth2 form data); frontend stores result as `localStorage.token`
- Default credentials: `admin` / `admin123` (hardcoded in `init_db.py`)
- JWT secret key in `backend/core/config.py` defaults to `"secret"` (override in `.env` for production)
- **Tokens are permanent**: `ACCESS_TOKEN_EXPIRE_MINUTES = 0` → no `exp` claim.
  JWT payload carries `token_ver`; `users.token_version` (added by `ensure_schema()`) enables revocation.
  `POST /system/token/regenerate` increments it and invalidates old tokens.
- All backend API routes require `Depends(deps.get_current_active_user)` except auth and `/system/status`
- `.env` currently holds `DEEPSEEK_MODEL` / `DEEPSEEK_API_KEY`; settings read from env via `pydantic-settings`

## Dev server quirks

- Vite proxies `/api`, `/api-docs`, `/phpmyadmin`, `/ws` → backend at `localhost:8000`
- `--reload-exclude "*.db"` avoids reload loops from SQLite writes
- No lint/format/typecheck tooling is configured
- No tests exist (`backend/tests/__init__.py` is empty, no test runner config)

### Build/deploy requirement (important)

The production panel serves **`frontend/dist/`**, not the Vue sources. After any frontend
edit, run `cd frontend && npm run build` (or `pnpm build`) before reloading the page;
otherwise the browser still gets the old hashed assets. Backend edits require
`systemctl restart sanguo-panel` (no reload in the systemd unit).

## Directory layout

| Path | Content |
|------|---------|
| `backend/` | Python FastAPI app |
| `frontend/` | Vue 3 SPA (`src/`, built output in `dist/`) |
| `frontend/src/views/` | Pages; extracted shared blocks live next to their original page (e.g. `Tools/QuickSpeedTools.vue`, `Security/WordPressHardening.vue`) |
| `deploy/` | systemd install/uninstall/reset scripts |
| `.prd/` | Design docs, PRD, test cases, task lists, dev log |
| `/var/www/html/` | **WordPress site files** (one subdirectory per site) |
| `backup/` | Backup storage + `notification_records.json` |

## Key Technical Details

### WordPress Site Structure
- **Root directory**: `/var/www/html/{domain}/`
- Created automatically when adding sites via panel
- Owned by `nobody:nogroup` (OLS LSAPI worker user)
- OLS virtual host `vhRoot` points here

### OpenLiteSpeed Configuration
- Installer: `install.sh` installs OLS from the official LiteSpeed repo and enables `lshttpd.service`
- Main config: `/usr/local/lsws/conf/httpd_config.conf`
- Virtual hosts: `/usr/local/lsws/conf/vhosts/{domain}/vhconf.conf`
- Panel listener: `Panel80` on `*:80`
- Default ports: HTTP `8088`, WebAdmin `7080` (HTTPS)
- WebAdmin credentials: `/usr/local/lsws/adminpasswd`
- PHP: per-vhost LSAPI handler (`lsphp83`, `lsphp82`, `lsphp81`, `lsphp74`)
- LSCache: rewrite rules + WP plugin
- SSL: Let's Encrypt via `acme.sh` → OLS 443 SNI

### Multi-PHP Support
- Versions under `/usr/local/lsws/lsphp{83,82,81,74}/`
- Per-site PHP version → per-vhost `extProcessor` + `scriptHandler`
- Default version from global `extProcessor lsphp`

### Database (MariaDB)
- Shared databases: each site gets its own DB + user (isolated)
- Panel config stored in SQLite (`backend/panel.db`)
- Notification settings stored as `GlobalOption` JSON rows; alert records in `backup/notification_records.json` (capped at 100)

### Background Tasks
- WordPress install runs in FastAPI `BackgroundTasks`
- WP-CLI uses OLS-bundled PHP (`/usr/local/lsws/lsphp83/bin/lsphp`)

### Panel UI map (current)
- Sidebar: Dashboard, Websites, File Manager, MariaDB, **WP 管理** (gray WordPress SVG icon), Security, **AI 管理**, Backup, System Tools
- `/wp-assets`: **WP一键提速** (default), WP安全加固, WP 版本, 主题管理, 插件管理
- `/tools`: AI 修复, 模型, Agent接入 (MCP / Skill)
- `/linux`: PHP 管理 (9 Chinese sub-tabs), LS缓存管理, etc.
- `/security`: IP 封禁列表 (default, with manual ban/unban cards), Fail2ban 设置, UFW 防火墙
- `/system/settings`: 面板设置 (incl. Token card), 通知提醒, 面板运行日志

### Agent / MCP
- `POST /api/v1/agent/mcp` — JSON-RPC 2.0: `initialize`, `tools/list`, `tools/call`
- Read-only tools: `panel_status`, `list_sites`, `list_tasks`
- `GET /api/v1/agent/skill.md` — Skill instructions; `GET /api/v1/agent/skill/prompt` — install prompt
- All agent endpoints require Bearer token

### Runtime data
- `backend/panel.db` is local runtime state (sites, backups, tasks) and is **not tracked by git**
- Pulling code never overwrites it; use `deploy/reset-panel.sh` to get an empty panel
- Reset keeps the admin account by default; `--full` restores `admin/admin123`

## Notes

- Only `main` branch exists; no CI/CD workflows
- Backend depends on `psutil` (Windows-compatible system metrics)
- phpMyAdmin PHP server starts on lifespan; crashes result in 503 errors
- Development is currently paused at a stable, pushed state (`origin/main`); see `.prd/notelist.md` for history
