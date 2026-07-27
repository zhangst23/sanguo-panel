from fastapi import APIRouter, Depends, BackgroundTasks
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import requests
import time

from backend.api import deps
from backend.core.config import settings
from backend.models.user import User
from backend.models.site import Site as SiteModel
from backend.utils import tool_utils

router = APIRouter()

DEEPSEEK_BASE_URL = "https://api.deepseek.com"

_ISSUE_LABELS = {
    "500": "网站500错误",
    "wp_admin": "wp-admin无法访问",
    "ssl": "SSL证书故障",
    "db": "数据库连接异常",
    "cache_perm": "缓存/权限异常",
    "perf": "性能问题",
}

_ISSUE_DETAIL = {
    "500": {
        "diagnose": [
            "1. 读取 PHP / OpenLiteSpeed stderr 日志，定位 Fatal error 与抛错堆栈。",
            "2. 检查 memory_limit 是否耗尽（常见 256M 不足导致白屏）。",
            "3. 排查最近启用的插件 / 主题冲突（特别是缓存、安全类插件）。",
            "4. 检查 .htaccess / OLS 重写规则与 wp-config 常量是否损坏。",
        ],
        "fix": [
            "1. 临时切换至默认主题，隔离主题级致命错误。",
            "2. 逐插件重命名目录，定位引发 500 的冲突插件并停用。",
            "3. 将 memory_limit 提升至 512M。",
            "4. 修复损坏的 wp-config 常量并重建对象缓存。",
        ],
    },
    "wp_admin": {
        "diagnose": [
            "1. 检查 wp-admin 目录与入口文件权限（应为 755 / 644）。",
            "2. 确认是否启用了隐藏登录入口（wp_hide_login_path）。",
            "3. 检查 COOKIE / FORCE_SSL_ADMIN 与站点 HTTPS 设置是否一致。",
            "4. 检查防火墙 / Fail2ban 是否误拦截了后台 IP。",
        ],
        "fix": [
            "1. 重置 wp-admin 及上级目录权限为安全推荐值。",
            "2. 临时关闭登录保护类插件，恢复默认登录地址。",
            "3. 修正 FORCE_SSL_ADMIN 与站点协议保持一致。",
            "4. 将管理员 IP 加入白名单，解除误封。",
        ],
    },
    "ssl": {
        "diagnose": [
            "1. 检查证书是否过期或即将到期。",
            "2. 检查证书链是否完整（中间证书缺失会导致混合告警）。",
            "3. 检查 80/443 端口与 DNS 解析是否正常可达。",
            "4. 检查 Cloudflare 代理模式（Flexible 易引发重定向循环）。",
        ],
        "fix": [
            "1. 触发 Let's Encrypt 自动续签并校验证书链。",
            "2. 重新部署完整证书链到 OLS / 站点配置。",
            "3. 统一 HTTPS 重定向规则，消除循环。",
            "4. 将 Cloudflare 调整为 Full 模式以匹配源站证书。",
        ],
    },
    "db": {
        "diagnose": [
            "1. 检查 MariaDB 服务是否正常运行（systemctl status）。",
            "2. 校验 wp-config.php 中的数据库主机 / 账号 / 密码。",
            "3. 检查数据库连接数是否耗尽（max_connections）。",
            "4. 检查服务器磁盘空间与临时表目录是否写满。",
        ],
        "fix": [
            "1. 重启 MariaDB 服务并加入开机自启。",
            "2. 修正 wp-config 中的连接参数，验证可连通。",
            "3. 调优 max_connections 与缓冲池，缓解连接耗尽。",
            "4. 清理慢查询与过期锁，释放磁盘空间。",
        ],
    },
    "cache_perm": {
        "diagnose": [
            "1. 检查 LSCache / Redis 服务是否处于运行状态。",
            "2. 检查站点目录权限（应为 755 / 644）与归属用户。",
            "3. 检查 object-cache 与页面缓存是否冲突。",
            "4. 检查 wp-content / uploads 是否可写。",
        ],
        "fix": [
            "1. 重置站点文件与目录权限为安全推荐值。",
            "2. 清理 LSCache 与 Redis 缓存，重建连接。",
            "3. 修正目录归属为 www-data（或对应运行用户）。",
            "4. 统一缓存配置，避免多缓存插件并存。",
        ],
    },
    "perf": {
        "diagnose": [
            "1. 抓取 PageSpeed 评分并定位瓶颈资源。",
            "2. 检查图片是否未压缩、未转 WebP。",
            "3. 检查 CSS/JS 是否未合并、未开启缓存。",
            "4. 检查外部请求（字体、统计）是否阻塞首屏。",
        ],
        "fix": [
            "1. 开启 LSCache 全站缓存并启用图片 WebP 压缩。",
            "2. 合并压缩前端资源，启用浏览器长缓存。",
            "3. 启用 Redis 对象缓存，降低数据库压力。",
            "4. 接入 CDN，分发静态资源到边缘节点。",
        ],
    },
}


def _build_ai_report(site_id, issue_type, domain, diagnose):
    label = _ISSUE_LABELS.get(issue_type, str(issue_type))
    action = "诊断" if diagnose else "修复"
    lines = [f"【AI{action}报告】问题类型：{label}"]
    if domain:
        lines.append(f"目标站点：{domain}（ID：{site_id}）")
    elif site_id is not None:
        lines.append(f"目标站点 ID：{site_id}")
    lines.append("")
    detail = _ISSUE_DETAIL.get(issue_type)
    if detail:
        lines.extend(detail["diagnose"] if diagnose else detail["fix"])
    else:
        lines.append("暂不支持该问题类型的自动分析，请选择列表中的问题类型。")
    lines.append("")
    lines.append(f"—— 由 AI 工具生成（{time.strftime('%Y-%m-%d %H:%M:%S')}）")
    return "\n".join(lines)


def _ai_messages(issue_type, domain, diagnose):
    """构造发给 DeepSeek 的对话消息。"""
    label = _ISSUE_LABELS.get(issue_type, issue_type or "未知问题")
    action = "诊断" if diagnose else "修复"
    site_txt = f"站点域名：{domain}" if domain else "站点：未指定（请按通用情况给出）"
    system = (
        "你是一位资深的服务器与网站运维专家，精通 WordPress、LNMP、OpenLiteSpeed、"
        "MySQL、Redis、SSL 证书与防火墙等运维排障。请使用简洁、可操作的中文回答，"
        "采用带编号的步骤列表，必要时给出具体命令。"
    )
    task = "分析可能的原因并给出排查步骤" if diagnose else "给出可执行的修复方案与命令步骤"
    user = (
        f"请对以下站点问题进行 AI{action}：\n"
        f"问题类型：{label}\n"
        f"{site_txt}\n\n"
        f"请{task}，输出格式为带编号的步骤清单。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _call_deepseek(messages):
    """调用 .env 中配置的 DeepSeek 模型，返回文本；失败时返回 None（由调用方回退模板）。"""
    model = settings.DEEPSEEK_MODEL
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key or not model:
        return None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "stream": False,
    }
    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[AI] DeepSeek 调用失败，使用本地模板回退: {e}")
        return None


@router.post("/ai/diagnose")
async def ai_diagnose(
    payload: Dict[str, Any],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """AI 一键诊断：根据站点与问题类型生成诊断报告（优先调用 DeepSeek）。"""
    site_id = payload.get("site_id")
    issue_type = payload.get("issue_type")
    domain = None
    if site_id is not None:
        site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
        if site:
            domain = site.domain
    report = _call_deepseek(_ai_messages(issue_type, domain, diagnose=True))
    if not report:
        report = _build_ai_report(site_id, issue_type, domain, diagnose=True)
    return {"report": report}


@router.post("/ai/fix")
async def ai_fix(
    payload: Dict[str, Any],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """AI 一键修复：根据站点与问题类型生成修复方案报告（优先调用 DeepSeek）。"""
    site_id = payload.get("site_id")
    issue_type = payload.get("issue_type")
    domain = None
    if site_id is not None:
        site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
        if site:
            domain = site.domain
    report = _call_deepseek(_ai_messages(issue_type, domain, diagnose=False))
    if not report:
        report = _build_ai_report(site_id, issue_type, domain, diagnose=False)
    return {"report": report}

@router.post("/execute/{tool_id}")
async def execute_tool(
    tool_id: str, 
    site_id: int = None,
    current_user: User = Depends(deps.get_current_active_user)
):
    """执行一键工具"""
    # 这里为了演示，直接同步执行或简单模拟异步
    result = await tool_utils.run_one_click_tool(tool_id, site_id)
    return result

@router.get("/list")
async def list_tools(current_user: User = Depends(deps.get_current_active_user)):
    """获取工具列表及其状态"""
    return [
        {
            "id": "full_optimize",
            "name": "一键全站极速优化",
            "description": "开启四层缓存、图片转WebP、合并压缩CSS/JS、数据库优化等",
            "icon": "Thunderbolt",
            "type": "performance"
        },
        {
            "id": "env_fix",
            "name": "一键环境修复",
            "description": "检测并修复OLS、MariaDB、Redis服务状态及文件权限",
            "icon": "Tool",
            "type": "fix"
        },
        {
            "id": "clean_junk",
            "name": "一键清理垃圾",
            "description": "清理修订版本、草稿、垃圾评论、过期transient等",
            "icon": "Delete",
            "type": "clean"
        },
        {
            "id": "db_optimize",
            "name": "一键数据库优化",
            "description": "对所有数据表执行 OPTIMIZE 和 REPAIR",
            "icon": "Storage",
            "type": "database"
        },
        {
            "id": "reset_perm",
            "name": "一键重置权限",
            "description": "将所有站点目录及文件权限重置为安全推荐值",
            "icon": "Lock",
            "type": "security"
        },
        {
            "id": "fix_wp",
            "name": "一键修复故障",
            "description": "自动修复常见WordPress白屏、内存耗尽、插件冲突等问题",
            "icon": "HeartHealth",
            "type": "fix"
        }
    ]
