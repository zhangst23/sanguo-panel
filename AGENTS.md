# Sanguo Panel — Agent Guide

## Quick start

### One-click startup (recommended)

```bash
# From project root, starts both backend and frontend
python start-all.py
```

Access URLs after startup:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api-docs

### Manual startup

**Windows:**
```powershell
# Backend (run from project root)
$env:PYTHONPATH="."
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --reload-exclude "*.db" --port 8000

# Init DB (first run)
$env:PYTHONPATH="."
python backend/init_db.py

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

- **Web Server**: OpenLiteSpeed (port 80/443) — serves frontend static files & proxies API to backend
- **Backend**: FastAPI + SQLAlchemy (SQLite by default at `backend/panel.db`) + JWT auth
- **Frontend**: Vue 3 + Vite + Arco Design + Pinia + Axios
- **Database**: MariaDB (for WordPress sites) + SQLite (for panel config)
- **Cache**: Redis (object cache for WordPress)
- **API prefix**: `/api/v1`
- **Swagger**: `http://localhost:8000/api-docs`
- **phpMyAdmin**: Proxied through backend at `/phpmyadmin/*` (PHP required in PATH, managed by `backend/utils/pma_server.py`)

## Conventions

- `@` in frontend imports = `src/` (configured in `vite.config.js`)
- Arco Design is the UI framework (`@arco-design/web-vue`, `@arco-design/web-vue/es/icon`)
- Styles: `src/assets/styles/global.scss` (Sass)
- API client: `src/utils/request.js` — base URL `/api/v1`, auto-attaches Bearer token from `localStorage`
- Login: POST `/api/v1/login/access-token` (OAuth2 form data)
- Default credentials: `admin` / `admin123` (hardcoded in `init_db.py`)
- JWT secret key in `backend/core/config.py` defaults to `"secret"` (change in production via `.env`)
- All backend API routes require `Depends(deps.get_current_active_user)` except auth and `/system/status`

## Dev server quirks

- Vite proxies `/api`, `/api-docs`, `/phpmyadmin`, `/ws` → backend at `localhost:8000`
- `--reload-exclude "*.db"` avoids reload loops from SQLite writes
- No lint/format/typecheck tooling is configured
- No tests exist (`backend/tests/__init__.py` is empty, no test runner config)

## Directory layout

| Path | Content |
|------|---------|
| `backend/` | Python FastAPI app |
| `frontend/` | Vue 3 SPA |
| `wordpress/` | Legacy (empty after migration) |
| `/var/www/html/` | **WordPress site files** (each site in subdirectory: `site1.com/`, `site2.com/`, etc.) |
| `backup/` | Backup storage |
| `doc-ai/prd/` | Design docs, test cases, task lists |

## Key Technical Details

### WordPress Site Structure
- **Root directory**: `/var/www/html/{domain}/`
- Created automatically when adding sites via panel
- Owned by `nobody:nogroup` (OLS LSAPI worker user)
- OLS virtual host `vhRoot` points here

### OpenLiteSpeed Configuration
- Main config: `/usr/local/lsws/conf/httpd_config.conf`
- Virtual hosts: `/usr/local/lsws/conf/vhosts/{domain}/vhconf.conf`
- Panel listener: `Panel80` on `*:80` (maps all panel domains)
- PHP: Per-vhost LSAPI handler (`lsphp83`, `lsphp82`, `lsphp81`, `lsphp74`)
- LSCache: Enabled via rewrite rules + WP plugin
- SSL: Let's Encrypt via `acme.sh`, deployed to OLS 443 SNI

### Multi-PHP Support
- Installed versions under `/usr/local/lsws/lsphp{83,82,81,74}/`
- Per-site PHP version configured via panel → creates per-vhost `extProcessor` + `scriptHandler`
- Default version from global `extProcessor lsphp`

### Database (MariaDB)
- Shared databases: Each site gets its own DB + user (isolated)
- Panel config stored in SQLite (`backend/panel.db`)

### Background Tasks
- WordPress install runs in FastAPI `BackgroundTasks`
- WP-CLI uses OLS-bundled PHP (`/usr/local/lsws/lsphp83/bin/lsphp`)

## Notes

- Only `main` branch exists; no CI/CD workflows
- `.env` file is empty — settings read from env with `pydantic-settings`
- Backend depends on `psutil` (Windows-compatible system metrics)
- phpMyAdmin PHP server starts on lifespan; crashes result in 503 errors
- Frontend builds to `frontend/dist/` → served by OLS `sanguo-panel` vhost