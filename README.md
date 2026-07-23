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

### 方式一：一键启动（推荐）

在项目根目录执行：

```bash
python3 start-all.py
```

脚本会自动完成以下操作：
- ✅ 检查并激活 Python 虚拟环境 (`./venv`)
- ✅ 检查并安装前端依赖 (`npm install`)
- ✅ 并行启动后端服务 (端口 8000) 和前端开发服务器 (端口 5173)
- ✅ 自动等待服务就绪并显示访问链接

启动成功后访问：
- 前端界面: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/api-docs

### 方式二：首次部署（初始化）

新环境首次部署时，需要依次执行：

```bash
# 1. 克隆项目
git clone <your-repo> sanguo-panel
cd sanguo-panel

# 2. 创建虚拟环境（在项目根目录）
python -m venv venv

# 3. 激活虚拟环境并安装依赖
# Linux/macOS:
source venv/bin/activate
# Windows:
# .\venv\Scripts\activate

pip install -r requirements.txt

# 4. 初始化数据库
$env:PYTHONPATH="."
python backend/init_db.py

# 5. 安装前端依赖
cd frontend && npm install && cd ..

# 6. 一键启动
python start-all.py
```

### 方式三：手动启动（开发调试）

如需分别控制前后端服务，可手动启动：

#### 后端 (Backend)

确保已安装 Python 3.9+ 环境，在项目根目录下运行：

**Windows:**
```powershell
# 激活虚拟环境
.\venv\Scripts\activate

# 安装依赖（首次）
pip install -r requirements.txt

# 初始化数据库（首次）
$env:PYTHONPATH="."
python backend/init_db.py

# 启动后端服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "*.db"
```

**Linux/macOS:**
```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖（首次）
pip install -r requirements.txt

# 初始化数据库（首次）
PYTHONPATH=. python backend/init_db.py

# 启动后端服务
python -m uvicorn backend.main:app --reload --reload-exclude "*.db" --port 8000
```

后端 API 将运行在: `http://localhost:8000`
验证后端服务状态：`http://localhost:8000/api/v1/system/status`

#### 前端 (Frontend)

确保已安装 Node.js (建议 v18+) 和 npm。

```bash
cd frontend

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev
```

前端界面将运行在: `http://localhost:5173`

### 默认账户

- **用户名**: `admin`
- **密码**: `admin123`

## 技术栈

- **后端**: FastAPI, SQLAlchemy (SQLite), Pydantic, JWT, Psutil
- **前端**: Vue 3, Vite, Arco Design, Pinia, Axios, ECharts




## 文档参考

详细的设计文档、测试用例和任务清单请参考 `doc-ai/prd/` 目录。
