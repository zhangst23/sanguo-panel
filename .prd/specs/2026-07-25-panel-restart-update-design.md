# 面板更新 & 重启功能设计

> **日期**: 2026-07-25
> **范围**: 后端 `system.py` + 前端 `Dashboard.vue`
> **决策**: 更新用 git fetch/rev-parse 比对；重启走 `./start.sh restart`；共用 `tasks` 表

## 1. 需求

1. Dashboard 右上角：**重启面板**按钮（始终显示）
2. Dashboard 右上角：**更新面板**按钮（仅检测到新版本时显示，进入页面查询一次）
3. 两个按钮点击后弹出二次确认弹窗；执行期间按钮禁用 + 全屏 loading
4. 重启/更新均异步写入 `tasks` 表，前端 2s 轮询状态

## 2. 后端 API

### `GET /system/update-check`
- 认证：需要登录
- 逻辑：`git fetch origin` → `git rev-parse HEAD` vs `git rev-parse @{u}` 比对
- 返回：`{ available, current_commit, latest_commit, commit_message, error? }`
- 超时：8 秒（git 网络可能慢）；失败返回 `{available:false}`，不抛异常

### `POST /system/update`
- 认证：需要登录
- 逻辑：写入 tasks 表（type=system_update），后台线程跑 `git pull && ./start.sh restart`
- 返回：`{ task_uuid }`

### `POST /system/restart`
- 认证：需要登录
- 逻辑：写入 tasks 表（type=system_restart），后台线程跑 `nohup ./start.sh restart &`
- 返回：`{ task_uuid }`

### `GET /system/task/{task_uuid}`
- 认证：需要登录
- 返回：`{ task_uuid, type, status, message, error, progress, created_at, updated_at }`

## 3. 后端实现文件

| 文件 | 改动 |
|---|---|
| `backend/api/v1/system.py` | 新增 4 个路由 + 辅助函数 |
| `backend/models/task.py` | 无需改（task_uuid/type/status/message/error 全有） |
| `backend/utils/panel_ops.py` | **新建**：`check_update()`, `run_update()`, `restart_panel()` |

## 4. 前端

| 文件 | 改动 |
|---|---|
| `frontend/src/views/Dashboard/Dashboard.vue` | header-bar、按钮、模态框、轮询逻辑 |

### 变量
- `updateInfo` — `{ available, current_commit, latest_commit, commit_message }`
- `restartModalVisible` / `updateModalVisible` — 模态框开关
- `operating` — 正在执行中（禁用按钮 + show spin）
- `taskUuid` — 当前任务 ID
- `pollTimer` — 轮询定时器

### 生命周期
- `onMounted`：调 `fetchUpdateStatus()` 一次
- `onUnmounted`：清理 `pollTimer`

## 5. 错误与边界

| 场景 | 处理 |
|---|---|
| git 不可用 / 无 remote | `{available:false}`，不显示更新按钮 |
| 重启后后端被杀 | 轮询 60s 超时 → 提示手动刷新 |
| 重复点击 | `operating=true` 时按钮 disabled |
| 更新/重启中后端报错 | task error 字段 + 模态框提示 |

## 6. 不做的 (YAGNI)
- 不轮询更新
- 不做回滚
- 不写自动化测试（项目无测试基础设施）
- 不改 BaseLayout / 全局 header
