"""SSRF 防护 - 拒绝内网 IP 地址"""
import ipaddress
import socket
from urllib.parse import urlparse


_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

ALLOWED_SCHEMES = {"http", "https"}


class SSRFError(ValueError):
    pass


def validate_url(url: str) -> None:
    """
    校验 URL 是否安全（非内网地址）。
    如果不安全，抛出 SSRFError。
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFError(f"不允许的协议: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("URL 缺少主机名")

    # 解析主机名到 IP
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFError(f"无法解析主机名 {hostname}: {e}") from e

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        for network in _PRIVATE_NETWORKS:
            if ip in network:
                raise SSRFError(f"目标 IP {addr} 属于内网地址，拒绝访问")
