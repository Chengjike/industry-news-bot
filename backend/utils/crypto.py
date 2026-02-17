"""Fernet 对称加密工具"""
import logging
from cryptography.fernet import Fernet, InvalidToken

from backend.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.fernet_key
        if not key:
            # 开发模式：自动生成临时密钥（重启后失效，仅用于本地测试）
            key = Fernet.generate_key().decode()
            logger.warning("FERNET_KEY 未配置，使用临时密钥（生产环境请设置）")
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("解密失败，密钥可能已变更") from e
