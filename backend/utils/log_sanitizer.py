"""日志脱敏过滤器"""
import logging
import re

_PATTERNS = [
    # 邮箱地址
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "***@***.***"),
    # password= 类键值对
    (re.compile(r"(password['\"]?\s*[:=]\s*)['\"]?[\w!@#$%^&*]+['\"]?", re.IGNORECASE), r"\1***"),
    # Authorization header
    (re.compile(r"(Authorization:\s*\w+\s+)[\w.=+/-]+", re.IGNORECASE), r"\1***"),
]


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _sanitize(str(record.msg))
        record.args = None  # 防止 % 格式化二次泄漏
        return True


def _sanitize(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def setup_log_sanitizer() -> None:
    root = logging.getLogger()
    root.addFilter(SensitiveDataFilter())
