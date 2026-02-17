"""单元测试 - SSRF 防护"""
import pytest
from unittest.mock import patch
from backend.utils.ssrf_protection import validate_url, SSRFError


class TestValidateUrl:
    def test_reject_file_scheme(self):
        with pytest.raises(SSRFError, match="不允许的协议"):
            validate_url("file:///etc/passwd")

    def test_reject_ftp_scheme(self):
        with pytest.raises(SSRFError, match="不允许的协议"):
            validate_url("ftp://example.com/feed")

    def test_reject_localhost_ip(self):
        with patch("backend.utils.ssrf_protection.socket.getaddrinfo") as mock:
            mock.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
            with pytest.raises(SSRFError, match="内网地址"):
                validate_url("http://localhost/feed")

    def test_reject_private_10_network(self):
        with patch("backend.utils.ssrf_protection.socket.getaddrinfo") as mock:
            mock.return_value = [(None, None, None, None, ("10.0.0.1", 0))]
            with pytest.raises(SSRFError, match="内网地址"):
                validate_url("http://internal-service/feed")

    def test_reject_private_192_168_network(self):
        with patch("backend.utils.ssrf_protection.socket.getaddrinfo") as mock:
            mock.return_value = [(None, None, None, None, ("192.168.1.1", 0))]
            with pytest.raises(SSRFError, match="内网地址"):
                validate_url("http://router.local/feed")

    def test_reject_private_172_16_network(self):
        with patch("backend.utils.ssrf_protection.socket.getaddrinfo") as mock:
            mock.return_value = [(None, None, None, None, ("172.16.0.1", 0))]
            with pytest.raises(SSRFError, match="内网地址"):
                validate_url("http://172.16.0.1/feed")

    def test_allow_public_ip(self):
        with patch("backend.utils.ssrf_protection.socket.getaddrinfo") as mock:
            mock.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
            # 不应抛出异常
            validate_url("https://feeds.example.com/rss")

    def test_missing_hostname(self):
        with pytest.raises(SSRFError, match="主机名"):
            validate_url("http:///feed")
