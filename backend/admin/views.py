"""starlette-admin 管理界面配置"""
import bcrypt
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin import action
from starlette_admin.contrib.sqla import Admin, ModelView
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed
from starlette_admin.fields import (
    EmailField, IntegerField, StringField, TextAreaField,
    BooleanField, EnumField, PasswordField, DateTimeField,
)

from backend.config import settings
from backend.database import engine
from backend.models import Industry, NewsSource, FinanceItem, Recipient, SmtpConfig, PushSchedule
from backend.models.push_log import PushLog
# ────────────────────────────────────────
# 认证 Provider（单管理员账号）
# ────────────────────────────────────────
class SingleAdminAuthProvider(AuthProvider):
    async def login(
        self, username: str, password: str, remember_me: bool,
        request: Request, response: Response,
    ) -> Response:
        if username != settings.admin_username:
            raise LoginFailed("用户名或密码错误")
        stored = settings.admin_password
        # 支持 bcrypt hash（生产）和明文（开发）
        if stored.startswith("$2b$"):
            if not bcrypt.checkpw(password.encode(), stored.encode()):
                raise LoginFailed("用户名或密码错误")
        else:
            if password != stored:
                raise LoginFailed("用户名或密码错误")
        request.session.update({"username": username})
        return response

    async def is_authenticated(self, request: Request) -> bool:
        return request.session.get("username") == settings.admin_username

    def get_admin_user(self, request: Request) -> AdminUser:
        return AdminUser(username=request.session.get("username", "admin"))

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response
# ────────────────────────────────────────
# ModelView 定义
# ────────────────────────────────────────
class IndustryView(ModelView):
    name = "行业"
    label = "行业管理"
    icon = "fa fa-industry"
    fields = [
        IntegerField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
        StringField("name", label="行业名称", required=True),
        IntegerField("top_n", label="早报 Top N 条数"),
    ]

    @action(
        name="send_morning",
        text="发送今日早报",
        confirmation="确认立即触发该行业早报推送？推送结果可在【推送记录】页面查看。",
        submit_btn_text="确认发送",
        submit_btn_class="btn-primary",
    )
    async def send_morning_action(self, request: Request, pks: list) -> str:
        from backend.tasks.scheduler import run_morning_push
        for pk in pks:
            await run_morning_push(int(pk), triggered_by="manual")
        return f"已触发 {len(pks)} 个行业的早报推送，请前往【推送记录】页面查看推送结果及内容"

    @action(
        name="send_evening",
        text="发送今日晚报",
        confirmation="确认立即触发该行业晚报推送？推送结果可在【推送记录】页面查看。",
        submit_btn_text="确认发送",
        submit_btn_class="btn-primary",
    )
    async def send_evening_action(self, request: Request, pks: list) -> str:
        from backend.tasks.scheduler import run_evening_push
        for pk in pks:
            await run_evening_push(int(pk), triggered_by="manual")
        return f"已触发 {len(pks)} 个行业的晚报推送，请前往【推送记录】页面查看推送结果及内容"

    @action(
        name="reset_seen",
        text="重置已见文章（重新采集）",
        confirmation="确认清空该行业的已见文章记录？\n清空后下次推送将把当前网站上的所有文章视为新文章重新采集推送。",
        submit_btn_text="确认重置",
        submit_btn_class="btn-warning",
    )
    async def reset_seen_action(self, request: Request, pks: list) -> str:
        from backend.tasks.scheduler import reset_seen_articles
        total = 0
        for pk in pks:
            total += await reset_seen_articles(int(pk))
        return f"已清空 {len(pks)} 个行业的已见文章记录（共 {total} 条），下次推送将重新采集所有文章"


class NewsSourceView(ModelView):
    name = "新闻源"
    label = "新闻源管理"
    icon = "fa fa-newspaper"
    fields = [
        IntegerField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
        StringField("name", label="来源名称", required=True),
        StringField("url", label="新闻列表页地址", required=True),
        StringField("link_selector", label="链接选择器（CSS，留空默认 'a'）", required=False),
        IntegerField("weight", label="权重 (1-10)"),
        TextAreaField("keywords", label="关键词 (+必须 !排除 普通)", required=False),
        EnumField(
            "language", label="语言",
            choices=[("zh", "中文"), ("en", "英文")],
            required=True,
        ),
        IntegerField("industry_id", label="所属行业 ID", required=True),
    ]


class FinanceItemView(ModelView):
    name = "金融项"
    label = "金融数据管理"
    icon = "fa fa-chart-line"
    fields = [
        IntegerField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
        StringField("name", label="名称", required=True),
        StringField("symbol", label="代码", required=True),
        EnumField(
            "item_type", label="类型",
            choices=[("stock", "A股"), ("stock_hk", "港股"), ("futures", "大宗商品")],
            required=True,
        ),
        IntegerField("industry_id", label="所属行业 ID", required=True),
    ]


class RecipientView(ModelView):
    name = "收件人"
    label = "收件人管理"
    icon = "fa fa-users"
    fields = [
        IntegerField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
        StringField("name", label="姓名"),
        EmailField("email", label="邮箱", required=True),
        IntegerField("industry_id", label="所属行业 ID", required=True),
    ]


class SmtpConfigView(ModelView):
    name = "SMTP配置"
    label = "SMTP 配置"
    icon = "fa fa-envelope"
    fields = [
        IntegerField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
        StringField("host", label="SMTP 服务器", required=True),
        IntegerField("port", label="端口"),
        StringField("username", label="账号（需含@域名）", required=True),
        PasswordField("password_encrypted", label="密码/授权码（保存时自动加密）", required=True),
        StringField("sender_name", label="发件人名称"),
        EmailField("contact_email", label="侵权联系邮箱"),
        BooleanField("use_tls", label="使用 SSL/TLS（465端口请开启）"),
    ]

    async def before_create(self, request: Request, data: dict, obj: SmtpConfig) -> None:
        _encrypt_smtp_password(data, obj)

    async def before_edit(self, request: Request, data: dict, obj: SmtpConfig) -> None:
        _encrypt_smtp_password(data, obj)


class PushScheduleView(ModelView):
    name = "推送计划"
    label = "推送计划"
    icon = "fa fa-clock"
    fields = [
        IntegerField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
        IntegerField("industry_id", label="行业 ID", required=True),
        EnumField(
            "push_type", label="类型",
            choices=[("morning", "早报"), ("evening", "晚报")],
            required=True,
        ),
        IntegerField("hour", label="小时 (0-23)"),
        IntegerField("minute", label="分钟 (0-59)"),
        BooleanField("enabled", label="启用"),
    ]


class PushLogView(ModelView):
    """推送记录（只读）"""
    name = "推送记录"
    label = "推送记录"
    icon = "fa fa-history"

    def can_create(self, request: Request) -> bool:
        return False

    def can_edit(self, request: Request) -> bool:
        return False

    fields = [
        IntegerField("id", label="ID"),
        IntegerField("industry_id", label="行业 ID"),
        EnumField(
            "push_type", label="类型",
            choices=[("morning", "早报"), ("evening", "晚报")],
        ),
        EnumField(
            "status", label="状态",
            choices=[("success", "成功"), ("failed", "失败"), ("skipped", "跳过")],
        ),
        IntegerField("article_count", label="推送文章数"),
        IntegerField("recipient_count", label="收件人数"),
        EnumField(
            "triggered_by", label="触发方式",
            choices=[("scheduler", "定时任务"), ("manual", "手动触发")],
        ),
        StringField("error_msg", label="跳过/失败原因"),
        DateTimeField("created_at", label="推送时间"),
    ]

    def get_list_columns(self):
        """自定义列表页显示的列，添加预览链接"""
        columns = super().get_list_columns()
        # 在 ID 列后插入预览链接列
        columns.insert(1, {
            "label": "预览",
            "name": "_preview_link",
            "searchable": False,
            "sortable": False,
        })
        return columns

    async def serialize_field_value(self, obj, field_name: str, request):
        """自定义字段序列化，为预览链接列生成 HTML"""
        if field_name == "_preview_link":
            if obj.html_snapshot:
                preview_url = f"/push-log/{obj.id}/preview"
                return f'<a href="{preview_url}" target="_blank" class="btn btn-sm btn-info">查看内容</a>'
            else:
                return '<span class="text-muted">无快照</span>'
        return await super().serialize_field_value(obj, field_name, request)

    @action(
        name="view_html",
        text="查看推送内容",
        confirmation="将在新窗口打开推送邮件内容预览，每次只能查看一条记录。",
        submit_btn_text="查看",
        submit_btn_class="btn-info",
    )
    async def view_html_action(self, request: Request, pks: list) -> str:
        if len(pks) != 1:
            return "请只选择一条记录"
        log_id = pks[0]
        return f"推送内容预览地址（请在浏览器中打开）：/push-log/{log_id}/preview"

    @action(
        name="delete_selected",
        text="删除所选记录",
        confirmation="确认删除所选推送记录？此操作不可恢复。",
        submit_btn_text="确认删除",
        submit_btn_class="btn-danger",
    )
    async def delete_selected_action(self, request: Request, pks: list) -> str:
        from backend.database import AsyncSessionLocal
        from sqlalchemy import delete as sql_delete
        async with AsyncSessionLocal() as db:
            await db.execute(
                sql_delete(PushLog).where(PushLog.id.in_([int(pk) for pk in pks]))
            )
            await db.commit()
        return f"已删除 {len(pks)} 条推送记录"


def _encrypt_smtp_password(data: dict, obj: SmtpConfig) -> None:
    """如果密码字段不为空且未加密，则 Fernet 加密后写入 obj"""
    from backend.utils.crypto import encrypt
    raw = data.get("password_encrypted", "")
    if raw and not raw.startswith("gAAAAA"):  # Fernet token 特征前缀
        obj.password_encrypted = encrypt(raw)


def create_admin() -> Admin:
    admin = Admin(
        engine,
        title="行业新闻机器人",
        auth_provider=SingleAdminAuthProvider(),
    )
    admin.add_view(IndustryView(Industry))
    admin.add_view(NewsSourceView(NewsSource))
    admin.add_view(FinanceItemView(FinanceItem))
    admin.add_view(RecipientView(Recipient))
    admin.add_view(SmtpConfigView(SmtpConfig))
    admin.add_view(PushScheduleView(PushSchedule))
    admin.add_view(PushLogView(PushLog))
    return admin
