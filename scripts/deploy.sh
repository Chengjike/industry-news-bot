#!/bin/bash
# 部署脚本：拉取最新代码，重建应用，重载 Nginx 配置
set -e

cd /opt/news-bot

echo "==> 拉取最新代码..."
git pull origin main

echo "==> 重建并启动应用容器..."
docker compose up -d --build app

echo "==> 重载 Nginx 配置..."
docker exec news_bot_nginx nginx -s reload

echo "==> 验证健康状态..."
sleep 3
curl -sk https://localhost/industry-news-bot/health

echo ""
echo "==> 部署完成"
