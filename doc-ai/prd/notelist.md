# Sanguo Panel 开发记录 (Notelist)

## 2026-02-12: 项目启动与骨架搭建

### 已完成功能
1.  **后端基础架构**:
    - 基于 FastAPI 的模块化结构。
    - Pydantic Settings 环境配置。
    - SQLAlchemy + SQLite 数据库初始化，支持自动建表。
    - JWT 认证系统（OAuth2 兼容）。
    - 系统监控接口（psutil 获取硬件状态）。
2.  **前端基础架构**:
    - Vue3 + Vite + Arco Design 组合。
    - 响应式布局设计（BaseLayout）。
    - 动态路由配置与权限控制（路由守卫）。
    - Axios 请求拦截器封装（处理 Token 和错误提示）。
    - Dashboard 实时监控图表基础实现。
3.  **站点管理 (P0)**:
    - 后端实现了 Site 和 SharedDatabase 的模型与 API。
    - 前端实现了站点列表展示、创建站点弹窗、删除确认。
    - 初始化时自动创建默认管理员和默认共享数据库。
4.  **LiteSpeed 管理 (P1)**:
    - 后端实现了服务状态查询和重启的通用接口。
    - 在 Windows 环境下对服务操作进行了 Mock 处理。
    - 前端实现了 LiteSpeed 管理面板，支持查看状态和重启操作。
5.  **PHP 管理 (P1)**:
    - 延用了通用的服务管理接口。
    - 前端实现了多版本 PHP (8.2, 8.1, 7.4) 的管理界面。

### 技术要点
- **数据库**: 使用 `as_declarative` 统一基类，自动生成表名。
- **认证**: 使用 `passlib` (bcrypt) 处理密码，`jose` 处理 JWT。
- **前端布局**: 使用 Arco Design 的 `a-layout` 组合，支持侧边栏折叠。
- **实时性**: Dashboard 采用 `setInterval` 定期拉取监控数据。

### 注意事项
- 当前 Node.js 版本 (20.12.0) 低于 Vite 推荐版本，但在开发环境下运行正常。
- 数据库目前使用本地 SQLite (`panel.db`)，便于开发调试。
- 后端需要 `PYTHONPATH` 环境变量才能正确识别 `backend` 模块。
