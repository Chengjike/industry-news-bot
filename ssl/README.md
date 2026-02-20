# SSL 证书目录

此目录用于存放 HTTPS 证书文件。

## 文件说明

- `selfsigned.crt`：自签名 SSL 证书（公钥）
- `selfsigned.key`：SSL 证书私钥

## 安全提示

⚠️ **证书私钥文件 (*.key) 不应提交到 Git 仓库！**

已在 `.gitignore` 中排除以下文件：
- `*.crt`
- `*.key`
- `*.pem`

## 生成证书

在 ECS 服务器上执行以下命令生成自签名证书：

```bash
cd /opt/news-bot
mkdir -p ssl

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/selfsigned.key \
  -out ssl/selfsigned.crt \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=NewsBot/CN=$(curl -s ifconfig.me)"
```

说明：
- `-days 365`：证书有效期 1 年
- `-newkey rsa:2048`：使用 RSA 2048 位密钥
- `CN=$(curl -s ifconfig.me)`：自动获取 ECS 公网 IP 作为证书 CN 字段
