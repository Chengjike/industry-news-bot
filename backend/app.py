"""FastAPI 应用主入口"""
import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.config import settings
from backend.database import init_db, AsyncSessionLocal
from backend.tasks.scheduler import scheduler, reload_schedules
from backend.utils.log_sanitizer import setup_log_sanitizer

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
setup_log_sanitizer()

logger = logging.getLogger(__name__)


def _validate_secrets() -> None:
    """启动时校验关键密钥，防止使用默认值或空值上线"""
    errors = []
    if not settings.secret_key or settings.secret_key == "dev-secret-key-change-in-production":
        errors.append("SECRET_KEY 未配置或使用默认值，请在 .env 中设置强随机密钥")
    if not settings.fernet_key:
        errors.append(
            "FERNET_KEY 未配置，请运行以下命令生成并写入 .env：\n"
            "  python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    if not settings.admin_password or settings.admin_password == "admin123":
        errors.append(
            "ADMIN_PASSWORD 未配置或使用默认值，请运行以下命令生成 bcrypt hash 并写入 .env：\n"
            "  python -c 'import bcrypt; print(bcrypt.hashpw(b\"your_password\", bcrypt.gensalt(12)).decode())'"
        )
    elif not settings.admin_password.startswith("$2b$"):
        errors.append("ADMIN_PASSWORD 必须是 bcrypt hash（以 $2b$ 开头），不允许明文密码")
    if errors:
        msg = "\n".join(f"  - {e}" for e in errors)
        raise RuntimeError(f"启动失败，安全配置不合规：\n{msg}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    _validate_secrets()
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


# 登录速率限制：每个 IP 每分钟最多 10 次尝试
_login_attempts: dict = defaultdict(list)
_LOGIN_LIMIT = 10
_LOGIN_WINDOW = 60  # 秒


def _check_login_rate_limit(ip: str) -> bool:
    """返回 True 表示允许，False 表示超限"""
    now = time.time()
    attempts = _login_attempts[ip]
    # 清理窗口外的记录
    _login_attempts[ip] = [t for t in attempts if now - t < _LOGIN_WINDOW]
    if len(_login_attempts[ip]) >= _LOGIN_LIMIT:
        return False
    _login_attempts[ip].append(now)
    return True


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
    https_only=True,   # 仅通过 HTTPS 传输 Cookie
    same_site="strict",  # 防止 CSRF
)

# 最外层：修正 scope["scheme"]，使所有子应用（含 starlette-admin）感知真实协议
app.add_middleware(ForwardedProtoMiddleware)

# 挂载 starlette-admin
from backend.admin.views import create_admin  # noqa: E402
admin = create_admin()
admin.mount_to(app)


@app.get("/health")
async def health():
    """健康检查：验证数据库连接和定时任务状态"""
    from sqlalchemy import text
    db_ok = False
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    scheduler_ok = scheduler.running

    if not db_ok or not scheduler_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": db_ok, "scheduler": scheduler_ok},
        )
    return {"status": "ok", "db": True, "scheduler": True}


@app.get("/push-log/{log_id}/preview", response_class=HTMLResponse)
async def push_log_preview(log_id: int, request: Request):
    """返回推送记录的邮件 HTML 快照（仅管理员可访问）"""
    from backend.admin.views import SingleAdminAuthProvider
    auth = SingleAdminAuthProvider()
    if not await auth.is_authenticated(request):
        return HTMLResponse("<p style='font-family:sans-serif;padding:2rem'>未授权，请先登录管理后台</p>", status_code=401)
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
