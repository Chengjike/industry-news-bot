"""FastAPI 应用主入口"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.config import settings
from backend.database import init_db, AsyncSessionLocal
from backend.tasks.scheduler import scheduler, reload_schedules
from backend.utils.log_sanitizer import setup_log_sanitizer

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
setup_log_sanitizer()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    await init_db()
    await reload_schedules()
    scheduler.start()
    logger.info("应用启动完成，定时任务已注册")
    yield
    # 关闭
    scheduler.shutdown(wait=False)
    logger.info("应用关闭")


class ForwardedProtoMiddleware:
    """读取 X-Forwarded-Proto 头，修正 scope['scheme']，使子应用感知真实协议"""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            proto = headers.get(b"x-forwarded-proto", b"").decode()
            if proto in ("https", "http"):
                scope["scheme"] = proto
        await self.app(scope, receive, send)


app = FastAPI(title="行业新闻机器人", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="admin_session",
    max_age=86400,  # 24h
    https_only=False,
)

# 最外层：修正 scope["scheme"]，使所有子应用（含 starlette-admin）感知真实协议
app.add_middleware(ForwardedProtoMiddleware)

# 挂载 starlette-admin
from backend.admin.views import create_admin  # noqa: E402
admin = create_admin()
admin.mount_to(app)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/push-log/{log_id}/preview", response_class=HTMLResponse)
async def push_log_preview(log_id: int):
    """返回推送记录的邮件 HTML 快照（运维预览用）"""
    from backend.models.push_log import PushLog
    async with AsyncSessionLocal() as db:
        log = await db.get(PushLog, log_id)
    if not log:
        return HTMLResponse("<p style='font-family:sans-serif;padding:2rem'>未找到该推送记录</p>", status_code=404)
    if not log.html_snapshot:
        return HTMLResponse(
            f"<p style='font-family:sans-serif;padding:2rem'>"
            f"记录 #{log_id} 无 HTML 快照（状态：{log.status}，原因：{log.error_msg or '无'}）</p>"
        )
    return HTMLResponse(log.html_snapshot)
