"""单元测试 - Fernet 加密/解密"""
import pytest
from cryptography.fernet import Fernet


class TestCrypto:
    def setup_method(self):
        # 每次测试使用新 key 避免全局状态干扰
        from backend.utils import crypto
        crypto._fernet = Fernet(Fernet.generate_key())

    def test_encrypt_decrypt_roundtrip(self):
        from backend.utils.crypto import encrypt, decrypt
        plaintext = "my-smtp-password-123"
        ciphertext = encrypt(plaintext)
        assert ciphertext != plaintext
        assert decrypt(ciphertext) == plaintext

    def test_encrypted_different_each_time(self):
        from backend.utils.crypto import encrypt
        ct1 = encrypt("same")
        ct2 = encrypt("same")
        assert ct1 != ct2  # Fernet 每次加密结果不同（含时间戳+随机数）

    def test_decrypt_wrong_key_raises(self):
        from backend.utils import crypto
        from backend.utils.crypto import encrypt
        ciphertext = encrypt("secret")
        # 换一把 key
        crypto._fernet = Fernet(Fernet.generate_key())
        from backend.utils.crypto import decrypt
        with pytest.raises(ValueError, match="解密失败"):
            decrypt(ciphertext)
