"""Agent 接入：MCP (JSON-RPC over HTTP) 与 Agent Skill 资源。"""
import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.api import deps
from backend.core.config import settings
from backend.models.user import User
from backend.models.site import Site
from backend.models.task import Task

router = APIRouter()

PROTOCOL_VERSION = "2024-11-05"

TOOL_DEFS = [
    {
        "name": "panel_status",
        "description": "查看面板运行状态、API 版本与服务器 IP",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "list_sites",
        "description": "列出面板中的站点（域名、状态、PHP 版本）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "最多返回条数，默认 50", "default": 50}
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "list_tasks",
        "description": "查看最近的任务与操作日志",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "最多返回条数，默认 20", "default": 20}
            },
            "additionalProperties": False,
        },
    },
]


def _enum(value: Any):
    return value.value if hasattr(value, "value") else value


def _call_tool(name: str, arguments: Dict[str, Any], db: Session) -> Any:
    if name == "panel_status":
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
        except Exception:
            ip = "未知"
        return {"status": "online", "version": "1.0.0", "api": settings.API_V1_STR, "ip": ip}

    if name == "list_sites":
        limit = min(int(arguments.get("limit") or 50), 100)
        sites = db.query(Site).filter(Site.status != "deleted").order_by(Site.id.desc()).limit(limit).all()
        return [
            {
                "id": s.id,
                "domain": s.domain,
                "status": _enum(s.status),
                "php_version": s.php_version,
                "ssl_status": s.ssl_status,
            }
            for s in sites
        ]

    if name == "list_tasks":
        limit = min(int(arguments.get("limit") or 20), 100)
        tasks = db.query(Task).order_by(Task.id.desc()).limit(limit).all()
        return [
            {
                "id": t.id,
                "type": t.type,
                "status": _enum(t.status),
                "message": t.message,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]

    raise ValueError(f"未知工具: {name}")


@router.post("/mcp")
async def mcp_endpoint(
    payload: Dict[str, Any],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """MCP JSON-RPC 端点（Streamable HTTP 风格，Bearer Token 鉴权）。"""
    req_id = payload.get("id")
    method = payload.get("method") or ""

    if method.startswith("notifications/"):
        return Response(status_code=202)

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "sanguo-panel", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOL_DEFS}}

    if method == "tools/call":
        params = payload.get("params") or {}
        try:
            data = _call_tool(params.get("name") or "", params.get("arguments") or {}, db)
            text = json.dumps(data, ensure_ascii=False, indent=2)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": text}], "isError": False},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": str(e)}], "isError": True},
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": "Method not found"},
    }


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.get("/info")
def agent_info(
    request: Request,
    current_user: User = Depends(deps.get_current_active_user),
):
    base = _base_url(request)
    return {
        "mcp_url": f"{base}{settings.API_V1_STR}/agent/mcp",
        "skill_url": f"{base}{settings.API_V1_STR}/agent/skill.md",
        "tools": [{"name": t["name"], "description": t["description"]} for t in TOOL_DEFS],
    }


SKILL_MD = """---
name: sanguo-panel
description: 管理三国面板的站点、查看系统状态与操作日志
---

# 三国面板 Skill

把这台服务器的三国面板接入你的 Agent，用自然语言查询站点与运行状态。

## 认证

面板 API 需要 Bearer Token。先到面板获取管理员 Token，调用时在 HTTP 头携带：

Authorization: Bearer <你的面板 Token>

## MCP（推荐）

MCP 端点：POST {base}{api}/agent/mcp

客户端配置示例：

{
  "mcpServers": {
    "sanguo-panel": {
      "type": "http",
      "url": "{base}{api}/agent/mcp",
      "headers": { "Authorization": "Bearer <你的面板 Token>" }
    }
  }
}

可用工具：

- panel_status：查看面板运行状态、版本与服务器 IP
- list_sites：列出站点（域名、状态、PHP 版本）
- list_tasks：查看最近任务与操作日志

先用 tools/list 获取工具清单，再用 tools/call 调用，参数为 {"name": "工具名", "arguments": {}}。

## REST API

所有业务接口位于 {base}{api}，开关页面为 {base}/system/settings。

## 使用示例

- 服务器现在正常吗？ -> panel_status
- 我有哪些站点？ -> list_sites
- 最近做过哪些操作？ -> list_tasks
"""


@router.get("/skill.md", response_class=PlainTextResponse)
def skill_markdown(
    request: Request,
    current_user: User = Depends(deps.get_current_active_user),
):
    return (
        SKILL_MD.replace("{base}", _base_url(request))
        .replace("{api}", settings.API_V1_STR)
    )


@router.get("/skill/prompt")
def skill_prompt(
    request: Request,
    current_user: User = Depends(deps.get_current_active_user),
):
    base = _base_url(request)
    info_url = f"{base}{settings.API_V1_STR}/agent/info"
    skill_url = f"{base}{settings.API_V1_STR}/agent/skill.md"
    return {
        "prompt": (
            f"请安装三国面板 Skill：{skill_url}\n"
            f"装完在你平时执行命令的环境里请求一次 {info_url}；连不上的话，告诉我要怎么给你开联网。\n"
            "装完告诉我是否需要开启新会话。"
        )
    }
