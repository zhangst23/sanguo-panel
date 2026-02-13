# Sanguo Panel 三国面板

Sanguo Panel 是一款专为 WordPress 优化设计的轻量级托管面板，基于 OpenLiteSpeed、MariaDB、Nginx 和 Redis Object Cache 构建。

## 核心特性

- **极致性能**: 集成 LSCache、Redis、OPcache 和浏览器四层缓存控制。
- **一键优化**: 支持图片批量压缩 (WebP/AVIF)、前端资源合并、数据库碎片整理。
- **运维便捷**: 包含 SSL 自动管理 (Let's Encrypt)、全站备份与恢复、多版本 PHP 切换。
- **安全可靠**: 隐藏登录路径、JWT 安全验证、系统防火墙集成。

## 快速启动

### 1. 后端启动 (Backend)

确保已安装 Python 3.9+ 环境。建议在项目根目录下运行。

```bash
# 进入项目根目录
cd sanguo-panel

# 安装依赖
pip install -r backend/requirements.txt

# 初始化数据库 (首次运行)
# Windows PowerShell
$env:PYTHONPATH="."
python backend/init_db.py

```

### 运行后端

请确保在项目根目录 `sanguo-panel` 下运行以下命令：

```bash
python -m uvicorn backend.main:app --reload --reload-exclude "*.db" --port 8000
```

后端 API 将运行在: `http://localhost:8000`
验证后端服务状态：`http://localhost:8000/api/v1/system/status`

### 2. 前端启动 (Frontend)

确保已安装 Node.js (建议 v18+) 和 npm。

```bash
cd frontend
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端界面将运行在: `http://localhost:5173`

## 默认账户

- **用户名**: `admin`
- **密码**: `admin123`

## 技术栈

- **后端**: FastAPI, SQLAlchemy (SQLite), Pydantic, JWT, Psutil
- **前端**: Vue 3, Vite, Arco Design, Pinia, Axios, ECharts

## 文档参考

详细的设计文档、测试用例和任务清单请参考 `doc-ai/prd/` 目录。
