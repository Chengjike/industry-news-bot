#!/bin/bash
# SSL 证书续期脚本
# 用途：自动生成新的自签名证书并重启 Nginx
# 使用：./scripts/renew-ssl-cert.sh
# Cron：0 2 1 1 * /bin/bash /opt/news-bot/scripts/renew-ssl-cert.sh >> /opt/news-bot/logs/ssl-renew.log 2>&1

set -e

# 切换到项目根目录
cd "$(dirname "$0")/.."

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始续期 SSL 证书"

# 备份旧证书
if [ -f ssl/selfsigned.crt ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份旧证书"
    mv ssl/selfsigned.crt ssl/selfsigned.crt.bak.$(date +%Y%m%d)
    mv ssl/selfsigned.key ssl/selfsigned.key.bak.$(date +%Y%m%d)
fi

# 生成新证书
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 生成新证书（有效期 365 天）"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/selfsigned.key \
  -out ssl/selfsigned.crt \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=NewsBot/CN=$(curl -s ifconfig.me)" 2>&1 | grep -v "^\..*+"

# 验证证书生成
if [ ! -f ssl/selfsigned.crt ] || [ ! -f ssl/selfsigned.key ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 错误：证书生成失败"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 证书生成成功"
ls -lh ssl/selfsigned.{crt,key}

# 重启 Nginx
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 重启 Nginx"
docker exec news_bot_nginx nginx -s reload

echo "[$(date '+%Y-%m-%d %H:%M:%S')] SSL 证书续期完成"

# 清理 30 天前的备份
find ssl/ -name "*.bak.*" -mtime +30 -delete 2>/dev/null || true
