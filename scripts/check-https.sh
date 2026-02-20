#!/bin/bash
# HTTPS 健康检查脚本
# 用途：验证 HTTPS 配置是否正常
# 使用：./scripts/check-https.sh

set -e

cd "$(dirname "$0")/.."

echo "=== HTTPS 配置健康检查 ==="
echo ""

# 检查证书文件
echo "1. 检查 SSL 证书文件..."
if [ ! -f ssl/selfsigned.crt ] || [ ! -f ssl/selfsigned.key ]; then
    echo "   ❌ 证书文件不存在"
    echo "   请运行：./scripts/renew-ssl-cert.sh"
    exit 1
fi
echo "   ✅ 证书文件存在"
ls -lh ssl/selfsigned.{crt,key}
echo ""

# 检查证书有效期
echo "2. 检查证书有效期..."
EXPIRY_DATE=$(openssl x509 -in ssl/selfsigned.crt -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt 30 ]; then
    echo "   ⚠️  证书将在 $DAYS_LEFT 天后过期（$EXPIRY_DATE）"
    echo "   建议运行：./scripts/renew-ssl-cert.sh"
elif [ $DAYS_LEFT -lt 0 ]; then
    echo "   ❌ 证书已过期（$EXPIRY_DATE）"
    echo "   请运行：./scripts/renew-ssl-cert.sh"
    exit 1
else
    echo "   ✅ 证书有效期：$DAYS_LEFT 天（过期时间：$EXPIRY_DATE）"
fi
echo ""

# 检查容器状态
echo "3. 检查 Docker 容器状态..."
if ! docker compose ps | grep -q "news_bot_nginx.*Up"; then
    echo "   ❌ Nginx 容器未运行"
    echo "   请运行：docker compose up -d"
    exit 1
fi
echo "   ✅ Nginx 容器运行正常"
echo ""

# 检查端口监听
echo "4. 检查端口监听..."
if ! netstat -tuln 2>/dev/null | grep -q ":443.*LISTEN" && ! ss -tuln 2>/dev/null | grep -q ":443.*LISTEN"; then
    echo "   ❌ 443 端口未监听"
    echo "   请检查 Nginx 配置和容器日志"
    exit 1
fi
echo "   ✅ 443 端口监听正常"
echo ""

# 测试 HTTPS 访问
echo "5. 测试 HTTPS 访问..."
if ! curl -k -s --connect-timeout 5 https://localhost/health | grep -q "ok"; then
    echo "   ❌ HTTPS 访问失败"
    echo "   请运行：docker compose logs nginx"
    exit 1
fi
echo "   ✅ HTTPS 访问正常"
echo ""

# 测试 HTTP 跳转
echo "6. 测试 HTTP 跳转到 HTTPS..."
if ! curl -I -s --connect-timeout 5 http://localhost/admin | grep -q "301 Moved Permanently"; then
    echo "   ❌ HTTP 未跳转到 HTTPS"
    echo "   请检查 Nginx 配置"
    exit 1
fi
echo "   ✅ HTTP 跳转正常"
echo ""

echo "=== ✅ 所有检查通过，HTTPS 配置正常 ==="
