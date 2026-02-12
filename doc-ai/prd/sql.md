Sanguo Panel · 纯共享数据库模式数据表设计
核心设计：
所有 WordPress 站点强制共用一个或多个 MariaDB 共享实例，不再支持独立数据库模式。
每个站点通过唯一表前缀在共享库中隔离数据。
面板自身元数据（用户、站点、任务等）独立存储（默认使用 SQLite，亦可配置独立 MySQL 库），不与 WordPress 站点数据库混用。
共享数据库实例的配置集中管理，支持多实例（为未来扩展保留），单服务器场景下仅需一个实例。

## 一、数据表关系图（简略）

┌─────────────────┐       ┌─────────────────┐
│    users        │       │ shared_databases│
│ (面板管理员)    │       │ (共享DB实例)    │
└────────┬────────┘       └────────┬────────┘
         │                         │
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│    tasks        │       │     sites       │
│ (后台任务)      │       │ (WordPress站点) │
└─────────────────┘       └────────┬────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  site_options   │       │  cache_rules    │       │security_configs│
│ (站点配置KV)    │       │ (缓存黑白名单)  │       │  (安全配置)    │
└─────────────────┘       └─────────────────┘       └─────────────────┘
          ▲                         ▲                         ▲
          └─────────────────────────┴─────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │   backups       │
                          │  备份记录       │
                          └─────────────────┘
                          
面板自身数据库：以上所有表均属于面板管理库，建议使用 SQLite（文件 /opt/sanguo/panel.db）或独立 MySQL 库（配置于 .env）。WordPress 站点数据全部存储于 shared_databases 所指向的 MariaDB 实例中。    
 
## 二、完整建表语句（MySQL/MariaDB 语法，适用于面板管理库）
             
-- ------------------------------------------------------------
-- 0. 数据库初始化（面板管理库）
--    字符集必须 utf8mb4，排序规则 utf8mb4_unicode_ci
-- ------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS `sanguo_panel` 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `sanguo_panel`;

-- ------------------------------------------------------------
-- 1. 用户表（面板管理员）
-- ------------------------------------------------------------
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `password_hash` varchar(255) NOT NULL COMMENT 'bcrypt哈希密码',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `avatar` varchar(255) DEFAULT NULL COMMENT '头像URL',
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `is_superuser` tinyint(1) NOT NULL DEFAULT 0 COMMENT '超级管理员',
  `last_login_at` datetime DEFAULT NULL COMMENT '最后登录时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='面板管理员表';

-- ------------------------------------------------------------
-- 2. 共享数据库实例表（WordPress站点共用的数据库）
-- ------------------------------------------------------------
CREATE TABLE `shared_databases` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '实例名称（标识）',
  `db_host` varchar(100) NOT NULL DEFAULT 'localhost' COMMENT '数据库主机',
  `db_port` int(11) NOT NULL DEFAULT 3306 COMMENT '端口',
  `db_name` varchar(64) NOT NULL COMMENT '数据库名',
  `db_user` varchar(64) NOT NULL COMMENT '数据库用户名',
  `db_password` varchar(255) NOT NULL COMMENT '数据库密码（加密存储）',
  `charset` varchar(32) NOT NULL DEFAULT 'utf8mb4' COMMENT '字符集',
  `collation` varchar(32) NOT NULL DEFAULT 'utf8mb4_unicode_ci' COMMENT '排序规则',
  `max_table_count` int(11) DEFAULT NULL COMMENT '最大建议表数量（告警阈值）',
  `status` enum('active','suspended','deleted') NOT NULL DEFAULT 'active' COMMENT '状态',
  `notes` text COMMENT '备注',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_db_host_name` (`db_host`, `db_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='共享数据库实例表';

-- ------------------------------------------------------------
-- 3. 站点元数据表（WordPress站点）
-- ------------------------------------------------------------
CREATE TABLE `sites` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(255) NOT NULL COMMENT '主域名',
  `aliases` json DEFAULT NULL COMMENT '域名别名列表',
  `root_path` varchar(255) NOT NULL COMMENT '网站根目录绝对路径',
  `php_version` varchar(10) NOT NULL DEFAULT '8.2' COMMENT 'PHP版本',
  
  -- 共享数据库关联
  `shared_db_id` int(11) NOT NULL COMMENT '关联共享数据库实例ID',
  `table_prefix` varchar(64) NOT NULL COMMENT 'WordPress表前缀（如 wp_s1_）',
  
  `ssl_status` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'SSL状态：0未开启，1已开启，2强制HTTPS',
  `ssl_cert_id` int(11) DEFAULT NULL COMMENT '关联的SSL证书ID',
  `status` enum('active','suspended','deleted') NOT NULL DEFAULT 'active' COMMENT '站点状态',
  `notes` text COMMENT '备注',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_domain` (`domain`),
  KEY `idx_status` (`status`),
  KEY `idx_shared_db_id` (`shared_db_id`),
  CONSTRAINT `fk_sites_shared_db` FOREIGN KEY (`shared_db_id`) REFERENCES `shared_databases` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='WordPress站点表（共享数据库模式）';

-- ------------------------------------------------------------
-- 4. 站点配置选项表（key-value，存储面板内该站点的个性化设置）
-- ------------------------------------------------------------
CREATE TABLE `site_options` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `site_id` int(11) NOT NULL COMMENT '站点ID',
  `option_key` varchar(100) NOT NULL COMMENT '配置键',
  `option_value` json DEFAULT NULL COMMENT '配置值（支持多种类型）',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_site_key` (`site_id`, `option_key`),
  CONSTRAINT `fk_site_options_site` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='站点配置选项表';

-- ------------------------------------------------------------
-- 5. 全局配置表（面板自身配置）
-- ------------------------------------------------------------
CREATE TABLE `global_options` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `option_key` varchar(100) NOT NULL COMMENT '配置键',
  `option_value` json DEFAULT NULL COMMENT '配置值',
  `description` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_option_key` (`option_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='全局配置表';

-- ------------------------------------------------------------
-- 6. 后台任务表
-- ------------------------------------------------------------
CREATE TABLE `tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `task_uuid` varchar(36) NOT NULL COMMENT '任务唯一标识，用于前端轮询',
  `type` varchar(50) NOT NULL COMMENT '任务类型：backup, optimize, migrate, image_optimize等',
  `site_id` int(11) DEFAULT NULL COMMENT '关联站点ID（可选）',
  `status` enum('pending','running','completed','failed','cancelled') NOT NULL DEFAULT 'pending' COMMENT '状态',
  `progress` int(11) NOT NULL DEFAULT 0 COMMENT '进度0-100',
  `message` text COMMENT '当前状态信息',
  `result` json DEFAULT NULL COMMENT '任务结果（结构化数据）',
  `error` text COMMENT '错误信息',
  `created_by` int(11) NOT NULL COMMENT '创建用户ID',
  `started_at` datetime DEFAULT NULL,
  `completed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_uuid` (`task_uuid`),
  KEY `idx_status` (`status`),
  KEY `idx_site_id` (`site_id`),
  CONSTRAINT `fk_tasks_site` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_tasks_user` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='后台任务表';

-- ------------------------------------------------------------
-- 7. 备份记录表
-- ------------------------------------------------------------
CREATE TABLE `backups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `site_id` int(11) NOT NULL COMMENT '站点ID',
  `name` varchar(100) NOT NULL COMMENT '备份名称',
  `file_path` varchar(500) NOT NULL COMMENT '备份文件路径',
  `file_size` bigint(20) NOT NULL COMMENT '文件大小（字节）',
  `type` enum('manual','schedule') NOT NULL DEFAULT 'manual' COMMENT '备份类型',
  `status` enum('success','failed','in_progress') NOT NULL DEFAULT 'success' COMMENT '状态',
  `include_db` tinyint(1) NOT NULL DEFAULT 1 COMMENT '包含数据库',
  `include_files` tinyint(1) NOT NULL DEFAULT 1 COMMENT '包含文件',
  `backup_scope` enum('full_db','site_only') NOT NULL DEFAULT 'site_only' COMMENT '备份范围（共享库下必为site_only）',
  `md5` varchar(32) DEFAULT NULL COMMENT '文件MD5（用于完整性校验）',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_site_id` (`site_id`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_backups_site` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='站点备份记录表';

-- ------------------------------------------------------------
-- 8. 定时备份策略表
-- ------------------------------------------------------------
CREATE TABLE `backup_schedules` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `site_id` int(11) NOT NULL COMMENT '站点ID',
  `name` varchar(100) NOT NULL COMMENT '策略名称',
  `cron_expression` varchar(100) NOT NULL COMMENT 'Cron表达式',
  `enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `retention_days` int(11) NOT NULL DEFAULT 30 COMMENT '保留天数',
  `include_db` tinyint(1) NOT NULL DEFAULT 1,
  `include_files` tinyint(1) NOT NULL DEFAULT 1,
  `remote_storage` json DEFAULT NULL COMMENT '远程存储配置（如FTP、OSS）',
  `last_run_at` datetime DEFAULT NULL COMMENT '上次执行时间',
  `next_run_at` datetime DEFAULT NULL COMMENT '下次执行时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_site_id` (`site_id`),
  CONSTRAINT `fk_backup_schedules_site` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='定时备份策略表';

-- ------------------------------------------------------------
-- 9. 防火墙端口规则表（系统级）
-- ------------------------------------------------------------
CREATE TABLE `firewall_rules` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '规则名称',
  `port` int(11) NOT NULL COMMENT '端口号',
  `protocol` enum('tcp','udp','both') NOT NULL DEFAULT 'tcp' COMMENT '协议',
  `action` enum('accept','drop','reject') NOT NULL DEFAULT 'accept' COMMENT '动作',
  `enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `description` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_port_protocol` (`port`, `protocol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='防火墙端口规则表';

-- ------------------------------------------------------------
-- 10. IP黑白名单表（全局/站点）
-- ------------------------------------------------------------
CREATE TABLE `ip_lists` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `type` enum('black','white') NOT NULL COMMENT '黑名单/白名单',
  `scope` enum('global','site') NOT NULL DEFAULT 'global' COMMENT '作用域：全局或站点',
  `site_id` int(11) DEFAULT NULL COMMENT '站点ID（当scope=site时）',
  `ip` varchar(50) NOT NULL COMMENT '单个IP或CIDR',
  `description` varchar(255) DEFAULT NULL,
  `enabled` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_scope_site` (`scope`, `site_id`),
  KEY `idx_ip` (`ip`),
  CONSTRAINT `fk_ip_lists_site` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='IP黑白名单表';

-- ------------------------------------------------------------
-- 11. SSL证书表
-- ------------------------------------------------------------
CREATE TABLE `ssl_certificates` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(255) NOT NULL COMMENT '主域名',
  `subject` json NOT NULL COMMENT '证书主题（CN、OU等）',
  `issuer` json NOT NULL COMMENT '颁发者',
  `valid_from` datetime NOT NULL COMMENT '生效时间',
  `valid_to` datetime NOT NULL COMMENT '过期时间',
  `cert_path` varchar(500) NOT NULL COMMENT '证书文件路径',
  `key_path` varchar(500) NOT NULL COMMENT '私钥文件路径',
  `chain_path` varchar(500) DEFAULT NULL COMMENT '证书链路径',
  `auto_renew` tinyint(1) NOT NULL DEFAULT 1 COMMENT '自动续期',
  `renew_status` enum('pending','renewed','failed') DEFAULT NULL COMMENT '续期状态',
  `last_renewed_at` datetime DEFAULT NULL COMMENT '上次续期时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_domain` (`domain`),
  KEY `idx_valid_to` (`valid_to`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='SSL证书表';

-- ------------------------------------------------------------
-- 12. 监控指标历史表（面板服务器资源）
-- ------------------------------------------------------------
CREATE TABLE `monitor_metrics` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `metric_name` varchar(50) NOT NULL COMMENT '指标名称：cpu_usage, mem_usage, disk_usage, network_in, network_out, cache_hit_rate等',
  `value` float NOT NULL COMMENT '指标值',
  `unit` varchar(20) DEFAULT NULL COMMENT '单位：%, MB, GB, kb/s等',
  `timestamp` datetime NOT NULL COMMENT '时间戳',
  PRIMARY KEY (`id`),
  KEY `idx_metric_timestamp` (`metric_name`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='监控指标历史表';

-- ------------------------------------------------------------
-- 13. 缓存黑白名单规则表（站点级）
-- ------------------------------------------------------------
CREATE TABLE `cache_rules` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `site_id` int(11) NOT NULL COMMENT '站点ID',
  `type` enum('black','white') NOT NULL COMMENT '黑名单/白名单',
  `rule_type` enum('url','path','cookie','user_agent') NOT NULL DEFAULT 'url' COMMENT '规则类型',
  `pattern` varchar(500) NOT NULL COMMENT '匹配模式（支持通配符）',
  `enabled` tinyint(1) NOT NULL DEFAULT 1,
  `description` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_site_id` (`site_id`),
  CONSTRAINT `fk_cache_rules_site` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='缓存黑白名单规则表';

-- ------------------------------------------------------------
-- 14. CDN配置表（站点级）
-- ------------------------------------------------------------
CREATE TABLE `cdn_configs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `site_id` int(11) NOT NULL COMMENT '站点ID',
  `provider` varchar(50) DEFAULT NULL COMMENT '厂商：cloudflare, aliyun, tencent, qiniu, custom',
  `cdn_domain` varchar(255) NOT NULL COMMENT 'CDN加速域名',
  `origin_domain` varchar(255) NOT NULL COMMENT '源站域名（通常是站点域名）',
  `enabled` tinyint(1) NOT NULL DEFAULT 0,
  `force_ssl` tinyint(1) NOT NULL DEFAULT 1 COMMENT '强制HTTPS回源',
  `api_key` varchar(255) DEFAULT NULL COMMENT 'API密钥（加密存储）',
  `zone_id` varchar(255) DEFAULT NULL COMMENT 'Cloudflare Zone ID等',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_site_id` (`site_id`),
  CONSTRAINT `fk_cdn_configs_site` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='CDN配置表';

-- ------------------------------------------------------------
-- 15. 安全配置表（站点级）
-- ------------------------------------------------------------
CREATE TABLE `security_configs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `site_id` int(11) NOT NULL COMMENT '站点ID',
  `hide_login_path` varchar(100) DEFAULT NULL COMMENT '自定义登录路径',
  `disable_xmlrpc` tinyint(1) NOT NULL DEFAULT 0 COMMENT '禁用XML-RPC',
  `disable_file_edit` tinyint(1) NOT NULL DEFAULT 0 COMMENT '禁止后台编辑文件',
  `wp_version_hide` tinyint(1) NOT NULL DEFAULT 0 COMMENT '隐藏WP版本',
  `login_attempts_limit` int(11) DEFAULT NULL COMMENT '登录尝试次数限制',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_site_id` (`site_id`),
  CONSTRAINT `fk_security_configs_site` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='安全配置表';

-- ------------------------------------------------------------
-- 16. 登录日志表（安全审计）
-- ------------------------------------------------------------
CREATE TABLE `login_logs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `ip` varchar(50) NOT NULL,
  `user_agent` text,
  `status` enum('success','failed') NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_login_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='登录日志表';

-- ------------------------------------------------------------
-- 17. 操作日志表（记录关键操作）
-- ------------------------------------------------------------
CREATE TABLE `operation_logs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `action` varchar(100) NOT NULL COMMENT '操作类型',
  `target_type` varchar(50) DEFAULT NULL COMMENT '操作对象类型：site, backup, task等',
  `target_id` int(11) DEFAULT NULL COMMENT '操作对象ID',
  `details` json DEFAULT NULL COMMENT '操作详情',
  `ip` varchar(50) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_target` (`target_type`, `target_id`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_operation_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';