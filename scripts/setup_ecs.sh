#!/bin/bash
# ECS 首次部署初始化脚本
# 使用方式：bash scripts/setup_ecs.sh /opt/news-bot

set -e

DEPLOY_PATH=${1:-/opt/news-bot}

echo ">>> 创建应用目录"
mkdir -p "$DEPLOY_PATH"/{data,logs}

echo ">>> 克隆仓库（如未存在）"
if [ ! -d "$DEPLOY_PATH/.git" ]; then
  read -p "请输入 GitHub 仓库地址（如 https://github.com/user/repo.git）: " REPO_URL
  git clone "$REPO_URL" "$DEPLOY_PATH"
fi

echo ">>> 创建 .env 文件"
if [ ! -f "$DEPLOY_PATH/.env" ]; then
  python3 -c "
from cryptography.fernet import Fernet
import secrets, sys
key = Fernet.generate_key().decode()
secret = secrets.token_hex(32)
print(f'SECRET_KEY={secret}')
print(f'FERNET_KEY={key}')
print('ADMIN_USERNAME=admin')
print('ADMIN_PASSWORD=请修改为强密码')
print(f'DATABASE_URL=sqlite+aiosqlite:///./data/app.db')
print('LOG_LEVEL=INFO')
" > "$DEPLOY_PATH/.env"
  echo ">>> .env 已生成，请编辑 $DEPLOY_PATH/.env 修改管理员密码"
fi

echo ">>> 配置防火墙（ufw）"
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw --force enable

echo ">>> 启动服务"
cd "$DEPLOY_PATH"
docker compose up -d --build

echo ">>> 完成！访问 http://$(curl -s ifconfig.me)/admin 进入管理界面"
