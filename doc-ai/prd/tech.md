# WordPress云托管面板，把速度优化到极致。

## 技术组合栈（WordPress极致速度面板）
OpenLiteSpeed + LSAPI + MariaDB + Redis Object Cache + LSCache + 自动图片优化 + OPcache + 数据库清理 + CDN + 静态化全站缓存
面板下安装的多个 WordPress 站点的数据表使用不同前缀进行隔离。通过配置文件 wp-config.php 中的 $table_prefix 变量支持在同一数据库中安装多个独立站点。

首选 OpenLiteSpeed：免费、性能强、适配 WordPress 缓存、无授权风险
搭配 MariaDB + Redis Object Cache + LSAPI，形成完整免费高性能栈

后端：FastAPI（Python）
前端：Vue.js + Arco Design Vue
运行环境：OpenLiteSpeed + MariaDB + Redis


## 整体架构（最稳、最快、最适合面板）
用户浏览器
   ↓
Vue.js 管理后台（前端）
   ↓
FastAPI 后端（REST API + WebSocket）
   ↓
系统层 / 服务控制层
   ↓
OpenLiteSpeed + PHP(LSAPI) + MariaDB + Redis

特点：
前后端完全分离
API 自动生成文档（FastAPI 自带）
支持实时状态（CPU / 内存 / 服务状态）
高并发、低占用、适合服务器面板


## 技术栈明细

### 后端 FastAPI 技术栈
Python 3.10+
FastAPI（高性能 Web 框架）
Uvicorn / Gunicorn（运行服务）
SSH / Systemd / Subprocess（执行系统命令）
PyMySQL（MariaDB 管理）
Redis-py（Redis 控制）
JWT 身份验证
APScheduler（定时任务：备份、优化、清理）
WebSockets（前端实时刷新状态）

### 前端 Vue.js 技术栈
Vue 3 + Vite
Arco Design Vue（UI）
Pinia（状态管理）
Axios（请求 API）
ECharts（性能曲线图）
WS 实时推送




## 6. 代码结构参考（附录）

### 6.1 后端项目结构
```
sanguo-panel-api/
├── main.py                      # 应用入口
├── core/                        # 核心基础设施
│   ├── __init__.py
│   ├── config.py               # 配置加载（Pydantic Settings）
│   ├── security.py             # JWT、密码哈希、认证依赖
│   ├── exceptions.py           # 自定义异常及全局异常处理器
│   ├── constants.py            # 系统常量（错误码、路径、默认值）
│   ├── events.py               # 启动/关闭事件（如检查服务、启动定时任务）
│   └── dependencies.py         # 全局依赖（如获取当前用户、Redis客户端）
├── api/                        # 路由层（HTTP 接口）
│   ├── __init__.py
│   └── v1/                    # API 版本 v1
│       ├── __init__.py
│       ├── api.py             # 路由聚合，供 main.py 注册
│       ├── auth.py            # 登录、登出、刷新 Token
│       ├── system.py          # 系统信息、实时负载
│       ├── websites.py        # 网站管理（站点增删改查、迁移）
│       ├── litespeed.py       # OpenLiteSpeed 服务状态、虚拟主机、配置
│       ├── php.py             # PHP 版本、扩展、OPcache 配置
│       ├── mariadb.py         # MariaDB 服务、库/用户管理、慢查询（支持对 shared-databases 的api接口）
│       ├── redis_mgt.py       # Redis 服务、配置、对象缓存部署
│       ├── cache.py           # 缓存中心（四层缓存开关、模式、预热）
│       ├── image.py           # 图片优化（压缩、转换、懒加载）
│       ├── frontend.py        # 前端优化（CSS/JS 合并、Critical CSS）
│       ├── cdn.py             # CDN 接入配置、资源替换
│       ├── system_optimize.py # 系统级优化（参数调优状态，数据库优化任务需支持按站点操作：在共享库中获取该站点的所有表，执行 OPTIMIZE TABLE。）
│       ├── security.py        # 安全加固（防火墙、后台隐藏、IP封禁）
│       ├── backup.py          # 备份/迁移、站点复制
│       ├── monitor.py         # 监控数据查询（历史曲线、实时指标）
│       ├── oneclick.py        # 一键工具（全站优化、环境修复等）
│       ├── settings.py        # 面板系统设置（密码、端口、日志）
│       └── ws.py              # WebSocket 实时状态推送
├── schemas/                   # Pydantic 模型（请求/响应）
│   ├── __init__.py
│   ├── common.py             # 通用响应包装、分页参数
│   ├── auth.py               # 登录请求、Token 响应
│   ├── system.py             # 系统信息、CPU/内存等
│   ├── website.py            # 站点创建、列表、详情
│   ├── litespeed.py          # OLS 服务控制、虚拟主机配置
│   ├── php.py                # PHP 版本切换、扩展开关
│   ├── mariadb.py            # 数据库创建、用户授权
│   ├── redis.py              # Redis 配置、缓存清空
│   ├── cache.py              # 缓存模式、清理范围
│   ├── image.py              # 批量优化参数
│   ├── frontend.py           # 前端优化设置
│   ├── cdn.py                # CDN 配置
│   ├── backup.py             # 备份任务、迁移源信息
│   ├── monitor.py            # 监控查询参数
│   ├── oneclick.py           # 一键工具执行结果
│   └── settings.py           # 面板设置修改
├── services/                 # 业务逻辑层
│   ├── __init__.py
│   ├── auth_service.py       # 认证、用户管理
│   ├── system_service.py     # 系统资源采集、服务状态检测
│   ├── website_service.py    # WordPress 站点全生命周期管理（）
│   ├── litespeed_service.py  # OLS 配置生成、控制、解析
│   ├── php_service.py        # PHP 版本安装/切换、扩展管理、php.ini 编辑
│   ├── mariadb_service.py    # 数据库操作、权限管理、备份恢复（增加 create_shared_database, drop_shared_database, get_shared_db_list, validate_table_prefix_unique 等方法）
│   ├── shared_db_service.py  # 管理共享数据库实例的创建、删除、状态检查；生成唯一表前缀；处理共享库连接等。
│   ├── redis_service.py      # Redis 控制、配置持久化
│   ├── cache_service.py      # 缓存策略应用、缓存清理、预热引擎
│   ├── image_service.py      # 图片压缩、格式转换（调用本地工具）
│   ├── frontend_service.py   # 前端资源优化（Minify、Critical 生成）
│   ├── cdn_service.py        # CDN URL 替换、厂商 API 封装
│   ├── sys_optimize_service.py # 系统内核参数优化、服务禁用
│   ├── security_service.py   # 防火墙规则、fail2ban 集成、权限修复
│   ├── backup_service.py     # 打包/解包、远程上传、迁移解析，（若用户选择“仅备份此站点”，则 mysqldump db_name --tables $(show tables like 'wp_site1_%')。）
│   ├── monitor_service.py    # 监控数据采集、聚合、存储
│   ├── oneclick_service.py   # 组合任务编排、进度跟踪
│   ├── settings_service.py   # 面板配置读写（env 或数据库）
│   └── task_service.py       # 后台任务管理（状态、取消、日志）
├── models/                   # 数据模型（SQLAlchemy / Tortoise-ORM）
│   ├── __init__.py
│   ├── base.py              # 基类（时间戳、主键）
│   ├── user.py              # 管理员用户表（单用户或多用户）
│   ├── task.py              # 异步任务记录（进度、结果、错误）
│   └── site.py              # （可选）站点缓存配置备份
├── repositories/            # 数据仓储层（可选，与 models 配套）
│   ├── __init__.py
│   ├── base.py             # 通用 CRUD
│   ├── user_repo.py        # 用户数据操作
│   └── task_repo.py        # 任务记录操作
├── utils/                   # 工具与辅助函数
│   ├── __init__.py
│   ├── response.py         # 统一响应格式（code, msg, data）
│   ├── logger.py           # 日志配置（结构化 JSON 日志）
│   ├── shell.py            # 安全执行系统命令（异步、超时、环境变量）
│   ├── validator.py        # 自定义验证器（域名、IP、端口）
│   ├── file.py             # 文件/目录操作（权限修改、压缩、解压）
│   ├── process.py          # 进程检测（pidof, systemctl status）
│   ├── web_tools.py        # HTTP 请求（缓存预热、PageSpeed 调用）
│   ├── scheduler.py        # APScheduler 初始化、任务注册
│   └── websocket.py        # WebSocket 连接管理器（广播、群发）
├── tests/                   # 测试套件
│   ├── __init__.py
│   ├── conftest.py         # pytest 夹具
│   ├── test_api/           # API 接口测试
│   └── test_services/      # 业务逻辑单元测试
├── .env.example             # 环境变量模板
├── .env                     # 本地环境变量（不提交）
├── requirements.txt         # 生产依赖
├── requirements-dev.txt     # 开发依赖（可选）
├── pyproject.toml           # 项目元数据、工具配置
├── README.md               # 项目说明
└── run.sh                  # 生产启动脚本（Gunicorn + Uvicorn）
```

### 6.2 前端项目结构
```
sanguo-panel-frontend/
├── public/                             # 静态资源（不会被打包）
│   ├── favicon.ico
│   ├── logo.png
│   └── index.html                     # 主 HTML 模板（Vite 默认）
├── src/
│   ├── api/                           # API 接口分层封装
│   │   ├── http.js                   # Axios 实例配置（拦截器、基础路径）
│   │   ├── ws.js                     # WebSocket 单例管理
│   │   ├── modules/                  # 按业务模块划分的 API
│   │   │   ├── auth.js              # 认证相关
│   │   │   ├── system.js            # 系统信息、监控
│   │   │   ├── website.js           # 网站管理
│   │   │   ├── litespeed.js         # OLS 管理
│   │   │   ├── php.js               # PHP 管理
│   │   │   ├── mariadb.js           # 数据库管理
│   │   │   ├── redis.js             # Redis 管理
│   │   │   ├── cache.js             # 缓存中心
│   │   │   ├── image.js             # 图片优化
│   │   │   ├── frontend.js          # 前端优化
│   │   │   ├── cdn.js               # CDN 接入
│   │   │   ├── security.js          # 安全加固
│   │   │   ├── backup.js            # 备份迁移
│   │   │   ├── monitor.js           # 监控数据
│   │   │   ├── oneclick.js          # 一键工具
│   │   │   └── settings.js          # 系统设置
│   │   └── index.js                 # 统一导出所有 API
│   ├── assets/                        # 静态资源（会经过 Vite 处理）
│   │   ├── images/                  # 图片资源
│   │   ├── icons/                   # 自定义 SVG 图标
│   │   └── styles/                  # 全局样式
│   │       ├── global.scss         # 全局 CSS 变量、覆盖 Arco 主题
│   │       ├── reset.scss          # 样式重置
│   │       └── mixins.scss         # 混合宏
│   ├── components/                   # 公共组件
│   │   ├── layout/                 # 布局组件
│   │   │   ├── AppLayout.vue      # 整体布局框架（侧边栏+头部+内容区）
│   │   │   ├── Sidebar.vue        # 侧边导航（折叠、菜单）
│   │   │   ├── Header.vue         # 顶部状态栏（用户、服务器时间、快捷入口）
│   │   │   └── Footer.vue         # 页脚（版本信息）
│   │   ├── common/                 # 通用组件（跨页面复用）
│   │   │   ├── StatusBadge.vue    # 状态标签（运行中/停止/故障）
│   │   │   ├── EmptyState.vue     # 空状态展示
│   │   │   ├── LoadingSpinner.vue # 加载指示器
│   │   │   ├── ConfirmDialog.vue  # 确认弹窗（二次确认）
│   │   │   ├── FileUpload.vue     # 文件上传（迁移备份包）
│   │   │   └── ProgressBar.vue    # 进度条（长时间任务）
│   │   ├── chart/                  # 图表组件（基于 ECharts）
│   │   │   ├── LineChart.vue      # 折线图（监控曲线）
│   │   │   ├── PieChart.vue       # 饼图（状态分布）
│   │   │   └── GaugeChart.vue     # 仪表盘（缓存命中率）
│   │   ├── form/                   # 表单类组件
│   │   │   ├── SiteCreateForm.vue # 创建网站分步表单
│   │   │   ├── CacheModeSlider.vue# 缓存模式三级滑块
│   │   │   └── PhpExtensionCheckbox.vue # PHP 扩展复选框组
│   │   └── business/               # 业务块组件（页面内局部模块）
│   │       ├── SystemStats.vue     # 系统指标卡片组（CPU/内存/磁盘）
│   │       ├── QuickActions.vue    # 一键优化悬浮球/快捷操作
│   │       └── TaskProgress.vue   # 后台任务进度展示
│   ├── composables/                 # 组合式函数（复用逻辑）
│   │   ├── useSystemInfo.js       # 系统状态轮询、WebSocket 订阅
│   │   ├── useWebSocket.js        # WebSocket 连接管理
│   │   ├── useTask.js             # 后台任务状态轮询
│   │   ├── usePagination.js       # 分页逻辑
│   │   └── useForm.js             # 表单验证与提交状态
│   ├── router/                      # Vue Router 路由配置
│   │   ├── index.js               # 路由实例创建、全局守卫
│   │   ├── routes.js              # 路由表（按模块拆分）
│   │   └── guard.js               # 导航守卫（权限校验、进度条）
│   ├── store/                       # Pinia 状态管理
│   │   ├── index.js               # Pinia 实例创建
│   │   ├── modules/               # 业务模块状态
│   │   │   ├── user.js           # 用户信息、Token、权限
│   │   │   ├── system.js         # 系统全局状态（侧边栏折叠、主题）
│   │   │   ├── website.js        # 当前选中站点、站点列表缓存
│   │   │   ├── monitor.js        # 实时监控数据（WebSocket 更新）
│   │   │   └── task.js           # 后台任务列表
│   │   └── plugins/               # Pinia 插件（持久化）
│   │       └── persist.js         # 状态持久化（localStorage）
│   ├── utils/                       # 工具函数
│   │   ├── auth.js                # Token 存储、权限校验
│   │   ├── format.js             # 数据格式化（文件大小、时间、百分比）
│   │   ├── validator.js          # 表单校验规则（域名、IP、端口）
│   │   ├── request.js            # 请求封装（统一错误处理）
│   │   ├── dom.js                # DOM 操作辅助
│   │   └── constant.js           # 常量定义（状态映射、预设选项）
│   ├── views/                       # 页面视图（路由组件）
│   │   ├── Login/                 # 登录页
│   │   │   └── Login.vue
│   │   ├── Dashboard/             # 控制台
│   │   │   └── Dashboard.vue
│   │   ├── Website/               # 网站管理
│   │   │   ├── WebsiteList.vue   # 站点列表
│   │   │   ├── WebsiteDetail.vue # 站点详情（标签页：概览、域名SSL、缓存、高级）
│   │   │   └── WebsiteCreate.vue # 创建站点（分步表单）
│   │   ├── LiteSpeed/             # OLS 管理
│   │   │   └── LiteSpeed.vue     # 服务状态、虚拟主机、配置
│   │   ├── PHP/                   # PHP 管理
│   │   │   └── PHPManager.vue    # 版本切换、扩展、OPcache
│   │   ├── MariaDB/               # 数据库管理
│   │   │   └── MariaDB.vue       # 服务状态、库管理、慢查询
│   │   ├── Redis/                 # Redis 管理
│   │   │   └── Redis.vue         # 服务状态、配置、对象缓存
│   │   ├── Cache/                 # 缓存中心
│   │   │   └── CacheCenter.vue   # 四层缓存总控、模式选择、命中率
│   │   ├── Image/                 # 图片优化
│   │   │   └── ImageOptimizer.vue # 批量压缩、格式转换
│   │   ├── Frontend/              # 前端优化
│   │   │   └── FrontendOptimizer.vue # PageSpeed 检测、一键修复
│   │   ├── Cdn/                   # CDN 接入
│   │   │   └── CdnManager.vue    # 厂商配置、资源替换
│   │   ├── Security/              # 安全加固
│   │   │   └── SecurityCenter.vue # 防火墙、后台隐藏、IP封禁
│   │   ├── Backup/                # 备份迁移
│   │   │   └── BackupManager.vue  # 备份列表、定时策略、迁移工具
│   │   ├── Monitor/               # 监控中心（全屏）
│   │   │   └── MonitorCenter.vue  # 详细监控图表、历史数据
│   │   ├── OneClick/              # 一键工具
│   │   │   └── OneClickTools.vue  # 所有一键工具卡片
│   │   └── System/                # 系统设置
│   │       └── SystemSettings.vue # 面板配置、日志查看
│   ├── App.vue                     # 根组件
│   └── main.js                    # 入口文件
├── .env.development                # 开发环境变量
├── .env.production                 # 生产环境变量
├── .eslintrc.js                   # ESLint 配置
├── .prettierrc                    # Prettier 配置
├── .stylelintrc                   # Stylelint 配置（可选）
├── vite.config.js                 # Vite 主配置文件
├── vitest.config.js              # 单元测试配置（若使用）
├── package.json                  # 项目依赖与脚本
├── pnpm-lock.yaml / yarn.lock    # 包锁文件
└── README.md                     # 项目说明
```

### 6.3 环境变量示例（.env）
```
APP_NAME=WP Speed Panel API
APP_VERSION=1.0.0
API_PREFIX=/api/v1
DEBUG=False

SECRET_KEY=your-secret-key-keep-it-safe
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

PANEL_PORT=8000
PANEL_USER=admin
PANEL_PASS_HASH=

LINUX_USER=root
```

### 共享数据库模式下 wp-config.php 关键配置示例
```
define('DB_NAME', 'shared_wordpress');
define('DB_USER', 'panel_user');
define('DB_PASSWORD', 'xxxxxxxx');
define('DB_HOST', 'localhost');

$table_prefix = 'wp_123_';  // 唯一前缀

if ( ! defined('WP_ALLOW_MULTISITE') ) {
    define('WP_ALLOW_MULTISITE', false);  // 确保不是多站点网络
}
```
