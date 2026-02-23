#!/bin/bash
# 代码同步脚本：将工作目录代码同步到部署目录
#
# 用途：开发完成后，将代码从工作目录同步到实际部署的目录
# 工作目录：/root/workspace/industry-news-bot
# 部署目录：/opt/news-bot
#
# 注意：此脚本会排除以下内容：
#   - .env（环境变量文件，包含敏感信息）
#   - data/（数据库和缓存，不应覆盖）
#   - logs/（日志文件，不应覆盖）
#   - ssl/（SSL证书，不应覆盖）
#
set -e

WORK_DIR="/root/workspace/industry-news-bot"
DEPLOY_DIR="/opt/news-bot"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==> 开始同步代码...${NC}"
echo "  工作目录: $WORK_DIR"
echo "  部署目录: $DEPLOY_DIR"
echo ""

# 检查目录是否存在
if [ ! -d "$WORK_DIR" ]; then
    echo -e "${RED}错误: 工作目录不存在: $WORK_DIR${NC}"
    exit 1
fi

if [ ! -d "$DEPLOY_DIR" ]; then
    echo -e "${RED}错误: 部署目录不存在: $DEPLOY_DIR${NC}"
    exit 1
fi

# 同步代码
echo -e "${YELLOW}==> 同步中...${NC}"
rsync -av --delete \
    --exclude='.env' \
    --exclude='data/' \
    --exclude='logs/' \
    --exclude='ssl/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache/' \
    --exclude='htmlcov/' \
    --exclude='.coverage' \
    --exclude='plan.md' \
    "$WORK_DIR/" "$DEPLOY_DIR/"

echo ""
echo -e "${GREEN}==> 同步完成！${NC}"
echo ""
echo "下一步操作："
echo "  1. cd $DEPLOY_DIR"
echo "  2. docker compose up -d --build app"
echo "  3. docker exec news_bot_nginx nginx -s reload"
echo ""
