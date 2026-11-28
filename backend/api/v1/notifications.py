from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api import deps
from backend.models.user import User
from backend.utils import notification_utils as nu

router = APIRouter()


class SMTPConfig(BaseModel):
    host: str = ""
    port: int = 587
    encryption: str = "STARTTLS"
    username: str = ""
    password: str = ""
    from_email: str = ""
    admin_email: str = ""


class WebhookConfig(BaseModel):
    channel: str = "wecom"
    url: str = ""


class RulesUpdate(BaseModel):
    rules: Dict[str, bool] = {}
    thresholds: Dict[str, int] = {}


class ImportRequest(BaseModel):
    code: str


@router.get("/config")
def get_config(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    return {
        "smtp": nu.get_smtp(db),
        "webhook": nu.get_webhook(db),
        "rules": nu.get_rules(db),
        "thresholds": nu.get_thresholds(db),
    }


@router.get("/records")
def get_records(
    current_user: User = Depends(deps.get_current_active_user),
):
    return nu.load_records()


@router.post("/smtp")
def save_smtp(
    data: SMTPConfig,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    nu.set_option(db, nu.SMTP_KEY, data.model_dump(), "SMTP 邮件配置")
    return {"success": True}


@router.post("/smtp/test")
def test_smtp(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    cfg = nu.get_smtp(db)
    try:
        recipient = nu.send_mail(
            cfg,
            "三国面板 SMTP 测试邮件",
            "这是一封来自三国面板的 SMTP 测试邮件，收到即表示邮件发送配置正常。",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"测试发送失败：{e}")
    return {"message": f"测试邮件已发送至 {recipient}"}


@router.post("/smtp/diagnose")
def diagnose_smtp(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    cfg = nu.get_smtp(db)
    return {"report": nu.diagnose_smtp(cfg)}


@router.get("/smtp/export")
def export_smtp(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    return {"code": nu.export_smtp(nu.get_smtp(db))}


@router.post("/smtp/import")
def import_smtp(
    data: ImportRequest,
    current_user: User = Depends(deps.get_current_active_user),
):
    try:
        cfg = nu.import_smtp(data.code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"smtp": cfg}


@router.post("/webhook")
def save_webhook(
    data: WebhookConfig,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    nu.set_option(db, nu.WEBHOOK_KEY, data.model_dump(), "Webhook 推送配置")
    return {"success": True}


@router.post("/webhook/test")
def test_webhook(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    cfg = nu.get_webhook(db)
    try:
        nu.send_webhook(cfg, "三国面板 Webhook 测试", "这是一条来自三国面板的 Webhook 测试消息。")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"测试发送失败：{e}")
    return {"message": "测试消息已发送"}


@router.post("/rules")
def save_rules(
    data: RulesUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    rules = dict(nu.DEFAULT_RULES)
    for key in nu.RULE_KEYS:
        if key in data.rules:
            rules[key] = bool(data.rules[key])
    thresholds = dict(nu.DEFAULT_THRESHOLDS)
    thresholds.update({k: int(v) for k, v in data.thresholds.items() if k in thresholds})

    nu.set_option(db, nu.RULES_KEY, rules, "告警规则开关")
    nu.set_option(db, nu.THRESHOLDS_KEY, thresholds, "告警阈值与统计窗口")
    return {"success": True, "rules": rules, "thresholds": thresholds}
