"""新闻源健康检查服务

检查逻辑：
- 对每个新闻源发起 HTTP 请求（10s 超时）
- 能抓到 ≥1 条链接 → healthy
- 请求成功但无链接 → warning
- 请求失败（超时/网络错误/4xx/5xx）→ error
- 连续失败 ≥3 次 → 发送告警邮件
- 失败只更新状态，不影响推送任务
"""
import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models.news_source import NewsSource

logger = logging.getLogger(__name__)

_HEALTH_TIMEOUT = 10.0
_ALERT_THRESHOLD = 3


async def check_one_source(source: NewsSource) -> tuple[str, str | None]:
    """检查单个新闻源，返回 (status, error_msg)"""
    selector = source.link_selector or "a"
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(source.url, timeout=_HEALTH_TIMEOUT)
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.select(selector)
        if links:
            return "healthy", None
        else:
            return "warning", f"页面正常但未找到链接（选择器: {selector}）"
    except httpx.TimeoutException:
        return "error", f"请求超时（>{_HEALTH_TIMEOUT}s）"
    except httpx.HTTPStatusError as e:
        return "error", f"HTTP {e.response.status_code}"
    except Exception as e:
        return "error", str(e)[:200]


async def run_health_check_all() -> None:
    """检查所有新闻源健康状态，更新数据库，连续失败达阈值时发告警"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(NewsSource))
        sources = result.scalars().all()

    logger.info("开始健康检查，共 %d 个新闻源", len(sources))

    for source in sources:
        status, error_msg = await check_one_source(source)
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            src = await db.get(NewsSource, source.id)
            if not src:
                continue

            src.health_status = status
            src.last_check_at = now
            src.last_error = error_msg

            if status == "error":
                src.consecutive_failures = (src.consecutive_failures or 0) + 1
            else:
                src.consecutive_failures = 0

            await db.commit()

            if status == "error" and src.consecutive_failures >= _ALERT_THRESHOLD:
                await _send_health_alert(src.name, src.url, error_msg or "", src.consecutive_failures)

        logger.info("健康检查 [%s] → %s%s", source.name, status,
                    f" ({error_msg})" if error_msg else "")


async def check_sources_by_ids(source_ids: list[int]) -> list[dict]:
    """手动检查指定新闻源，返回结果列表（供 Admin 按钮调用）"""
    results = []
    for sid in source_ids:
        async with AsyncSessionLocal() as db:
            source = await db.get(NewsSource, sid)
            if not source:
                continue

            status, error_msg = await check_one_source(source)
            now = datetime.now(timezone.utc)

            source.health_status = status
            source.last_check_at = now
            source.last_error = error_msg

            if status == "error":
                source.consecutive_failures = (source.consecutive_failures or 0) + 1
            else:
                source.consecutive_failures = 0

            await db.commit()

            if status == "error" and source.consecutive_failures >= _ALERT_THRESHOLD:
                await _send_health_alert(source.name, source.url, error_msg or "", source.consecutive_failures)

            results.append({
                "id": sid,
                "name": source.name,
                "status": status,
                "error": error_msg,
            })

    return results


async def _send_health_alert(name: str, url: str, error_msg: str, count: int) -> None:
    """连续失败达阈值时发送告警邮件"""
    from sqlalchemy import select as sa_select
    from backend.models.smtp_config import SmtpConfig

    async with AsyncSessionLocal() as db:
        smtp_result = await db.execute(sa_select(SmtpConfig).limit(1))
        smtp_cfg = smtp_result.scalar_one_or_none()
    if not smtp_cfg:
        logger.warning("健康检查告警：无 SMTP 配置，无法发送告警邮件")
        return

    from backend.utils.crypto import decrypt
    from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
    password = decrypt(smtp_cfg.password_encrypted)
    conf = ConnectionConfig(
        MAIL_USERNAME=smtp_cfg.username,
        MAIL_PASSWORD=password,
        MAIL_FROM=smtp_cfg.username,
        MAIL_FROM_NAME="行业新闻机器人告警",
        MAIL_PORT=smtp_cfg.port,
        MAIL_SERVER=smtp_cfg.host,
        MAIL_STARTTLS=not smtp_cfg.use_tls,
        MAIL_SSL_TLS=smtp_cfg.use_tls,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )
    subject = f"【告警】新闻源「{name}」已连续检查失败 {count} 次"
    body = (
        f"<p>新闻源 <b>{name}</b> 已连续健康检查失败 <b>{count}</b> 次。</p>"
        f"<p>地址：<code>{url}</code></p>"
        f"<p>最近错误：<code>{error_msg}</code></p>"
        f"<p>请登录管理后台检查新闻源配置。</p>"
    )
    try:
        fm = FastMail(conf)
        msg = MessageSchema(
            subject=subject,
            recipients=[smtp_cfg.username],
            body=body,
            subtype=MessageType.html,
        )
        await fm.send_message(msg)
        logger.warning("已发送新闻源健康告警：%s 连续失败 %d 次", name, count)
    except Exception as e:
        logger.error("发送健康告警邮件失败: %s", e)
