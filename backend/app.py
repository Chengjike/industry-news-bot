"""FastAPI 应用主入口"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from backend.config import settings
from backend.database import init_db
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


app = FastAPI(title="行业新闻机器人", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="admin_session",
    max_age=86400,  # 24h
    https_only=False,  # 生产环境设为 True（HTTPS）
)

# 挂载 starlette-admin
from backend.admin.views import create_admin  # noqa: E402
admin = create_admin()
admin.mount_to(app)


@app.get("/health")
async def health():
    return {"status": "ok"}
