# WP 主题插件管理 + 默认 WP 版本设计

日期：2026-11-27

## 背景

当前创建站点时，`backend/api/v1/site.py` 的 `install_wordpress_task()` 直接执行
`wp core download --locale=zh_CN`，WP-CLI 会从 wordpress.org 拉取**最新版** WordPress，
面板无法控制版本，也没有本地资源库。

需求：

1. 创建站点默认不再下载最新版，而是使用管理员配置的默认 WP 版本。
2. 侧边栏"系统管理"上方新增页面"WP主题插件管理"，可设置默认 WP 版本、管理主题与插件、
   进行版本更新和资源增删改查。

已确认的决策：

- 版本来源：**混合模式** —— 优先使用本地缓存包；未缓存时按指定版本从官方下载并缓存，后续离线复用。
- 主题/插件：**本地资源库 + 新站自动安装**（上传/导入 zip，设默认，建站时自动安装激活）。
- "版本更新"：**版本库更新**（拉取新版本入库并设为默认），不影响已有站点。
- 实现方式：**统一 zip 包资源库**（core / theme / plugin 共用一张表与一套 CRUD）。

## 架构与数据模型

### 新表 `wp_assets`（`backend/models/wp_asset.py`）

继承 `backend/models/base.py` 的 `Base`（自带 `id`、`created_at`、`updated_at`）。

| 字段 | 类型 | 说明 |
|---|---|---|
| `kind` | String(16) | `core` / `theme` / `plugin`，必填 |
| `name` | String(128) | 显示名称 |
| `slug` | String(128) | 标识；core 可为空 |
| `version` | String(32) | 版本号 |
| `file_path` | String(512) | 相对项目根的包路径 |
| `file_size` | Integer | 字节数 |
| `source` | String(16) | `official` / `upload` |
| `is_default` | Boolean | 同类资源中最多一条为 true |
| `enabled` | Boolean | 默认 true |
| `notes` | Text | 备注 |

在 `backend/models/__init__.py` 导入；由 `backend/init_db.py` 中已有的
`Base.metadata.create_all()` 建表。不修改 `sites` 表，不需要手写 `ALTER TABLE` 迁移。

### 文件存储

- 目录：`backend/assets/packages/core/`、`backend/assets/packages/themes/`、
  `backend/assets/packages/plugins/`（运行时创建）。
- core 包命名：`wordpress-{version}-zh_CN.zip`。
- 主题/插件包命名：`{slug}-{version}.zip`。
- `.gitignore` 增加 `/backend/assets/packages/`；包文件属于运行时数据，不进 git。

### 默认版本配置

复用 `global_options` 表，键 `default_wp_version`，值为 JSON 字符串。
`init_db()` 中若不存在则插入 `6.5.5`。代码中定义同值常量 `DEFAULT_WP_VERSION` 作为兜底。

## 安装流程（改造 `install_wordpress_task`）

原步骤 1 的 `wp core download` 替换为：

1. 目标版本 = 站点创建请求中显式指定的 `wp_version`，否则读 `default_wp_version` 全局配置。
2. 调用 `ensure_core_package(version)`：
   - 若本地 zip 存在且合法 → 直接复用；
   - 否则下载 `https://cn.wordpress.org/wordpress-{version}-zh_CN.zip`，校验 HTTP 状态与 zip 合法性，
     保存到 core 目录并登记/复用 `wp_assets` 记录（source=official）。
3. 解压 zip 到 `site.root_path`，自动剥离 zip 内的 `wordpress/` 顶层目录（若存在）。
4. 调用 `chown_site_root(site.root_path)`。
5. 后续 `wp config create`、`wp core install`、默认插件/主题清理、`blog_public` 设置等保持不变。
6. 所有 `is_default=true 且 enabled=true` 的主题/插件包，用
   `wp theme install <zip> --activate` / `wp plugin install <zip> --activate` 安装激活（非致命失败）。
7. 写回 `site.wp_version`（优先用目标版本，`wp core version` 探测结果作为校验/回退）。

注意：清理默认主题的步骤需在默认主题安装**之前**执行，避免把刚装的默认主题删掉。

## 后端接口

新增 `backend/api/v1/wp_assets.py`，`router = APIRouter(prefix="/wp-assets")`，
在 `backend/api/v1/api.py` 中 include；所有接口依赖 `Depends(deps.get_current_active_user)`
与 `Depends(deps.get_db)`，遵循现有 Pydantic schema 风格（新文件 `backend/schemas/wp_asset.py`）。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/wp-assets?kind=` | 列表（可选按 kind 过滤） |
| GET | `/wp-assets/defaults` | 默认 WP 版本 + 可选版本列表 + 默认主题/插件 |
| PUT | `/wp-assets/default-version` | `{version}`，写 `global_options` |
| POST | `/wp-assets/core/fetch` | `{version}`，下载官方 zip 入库（版本更新/新增） |
| POST | `/wp-assets/upload` | multipart：`file`、`kind`、`name`、`slug`、`version` |
| PUT | `/wp-assets/{id}` | 修改名称/版本/启用状态 |
| DELETE | `/wp-assets/{id}` | 删除包文件与记录；若为默认则自动取消默认 |
| POST | `/wp-assets/{id}/set-default` | 设为默认（同类互斥） |

工具函数放在 `backend/utils/wp_asset_utils.py`：路径解析、下载、校验、解压、
`ensure_core_package()`、默认主题/插件安装、删除文件时的路径白名单校验。

## 前端

- 路由：`frontend/src/router/index.js` 增加 `path: 'wp-assets'`、`name: 'WPAssets'`、
  `component: () => import('@/views/WordPress/WPAssets.vue')`、`meta: { requiresAuth: true, title: 'WP主题插件管理' }`。
- 侧边栏：`frontend/src/components/layout/BaseLayout.vue` 的 `System` 子菜单中，
  在 `<a-menu-item key="Linux">系统管理</a-menu-item>` **上方**插入
  `<a-menu-item key="WPAssets">WP主题插件管理</a-menu-item>`。菜单 key 必须与路由 name 一致。
- 新页面 `frontend/src/views/WordPress/WPAssets.vue`，使用 Arco Design：
  顶部默认版本设置卡片（版本输入/下拉、拉取新版本、设为默认），
  下方三个 Tab（WP 版本 / 主题管理 / 插件管理），每个 Tab 表格展示
  名称、版本、标识、来源、大小、默认状态，操作列含上传/导入、编辑、删除、设为默认。
  API 调用走 `src/utils/request.js`（baseURL `/api/v1`，自动带 Bearer token）。
- 创建站点弹窗 `frontend/src/views/Website/WebsiteList.vue`：新增"WP 版本"下拉，
  数据来自 `GET /wp-assets/defaults`，默认选中配置的默认版本；`form` 增加 `wp_version` 字段。
  后端 `SiteCreate` schema 同步增加可选 `wp_version`。

## 错误处理

- 版本下载失败（404 / 网络错误 / 非 zip）：接口返回明确错误；安装任务在 `site.notes` 写明原因，
  **不静默回退到最新版**。
- 默认主题/插件安装失败：记录日志并继续建站，与现有非致命副作用处理一致。
- 删除文件：校验解析后的绝对路径必须位于资源库目录内，防止路径穿越。
- 上传文件：校验扩展名为 `.zip`，校验 zip 合法性后再落盘。

## 验证（项目无测试框架，采用手工验证）

1. 启动后端，调用 `POST /wp-assets/core/fetch` 拉取一个版本，设为默认版本。
2. 上传一个主题 zip 与一个插件 zip，设为默认。
3. 创建站点，确认：安装日志无 `wp core download`，站点根目录来自本地包，
   `wp core version` 等于默认版本，默认主题/插件已安装激活。
4. 页面冒烟：三个 Tab 的查询、上传、编辑、删除、设为默认；创建站点弹窗的版本下拉默认值正确。
5. 离线验证：断网后再次创建站点，确认能复用缓存包完成安装。

## 明确不做

- 不修改已有站点的 WP 核心版本（`POST /sites/{id}/wp/update` 保持原样）。
- 不提供对已有站点的批量主题/插件管理。
- 不引入 Alembic 或新的测试框架。
