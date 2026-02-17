"""邮件发送模块 - 使用 fastapi-mail"""
import logging
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from backend.utils.crypto import decrypt

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _build_connection(smtp_cfg) -> ConnectionConfig:
    """从数据库 SmtpConfig 对象构建 fastapi-mail 连接配置"""
    password = decrypt(smtp_cfg.password_encrypted)
    return ConnectionConfig(
        MAIL_USERNAME=smtp_cfg.username,
        MAIL_PASSWORD=password,
        MAIL_FROM=smtp_cfg.username,
        MAIL_FROM_NAME=smtp_cfg.sender_name or "行业新闻机器人",
        MAIL_PORT=smtp_cfg.port,
        MAIL_SERVER=smtp_cfg.host,
        MAIL_STARTTLS=not smtp_cfg.use_tls,
        MAIL_SSL_TLS=smtp_cfg.use_tls,
        TEMPLATE_FOLDER=str(TEMPLATE_DIR),
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


async def send_morning_report(
    smtp_cfg,
    recipients: list[str],
    industry_name: str,
    news_items: list,
    contact_email: str = "",
) -> None:
    """发送早报"""
    if not news_items:
        logger.info("行业 %s 无新闻，跳过早报", industry_name)
        return

    conf = _build_connection(smtp_cfg)
    fm = FastMail(conf)

    message = MessageSchema(
        subject=f"【{industry_name}】行业早报 - 今日要闻",
        recipients=recipients,
        template_body={
            "industry_name": industry_name,
            "news_items": news_items,
            "contact_email": contact_email or smtp_cfg.username,
        },
        subtype=MessageType.html,
    )

    await fm.send_message(message, template_name="email_morning.html")
    logger.info("早报已发送至 %d 位收件人（行业: %s）", len(recipients), industry_name)


async def send_evening_report(
    smtp_cfg,
    recipients: list[str],
    industry_name: str,
    quotes: list,
    contact_email: str = "",
) -> None:
    """发送晚报"""
    if not quotes:
        logger.info("行业 %s 无金融数据，跳过晚报", industry_name)
        return

    conf = _build_connection(smtp_cfg)
    fm = FastMail(conf)

    message = MessageSchema(
        subject=f"【{industry_name}】行业晚报 - 今日行情",
        recipients=recipients,
        template_body={
            "industry_name": industry_name,
            "quotes": quotes,
            "contact_email": contact_email or smtp_cfg.username,
        },
        subtype=MessageType.html,
    )

    await fm.send_message(message, template_name="email_evening.html")
    logger.info("晚报已发送至 %d 位收件人（行业: %s）", len(recipients), industry_name)
